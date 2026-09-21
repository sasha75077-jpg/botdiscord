"""Подача контрактов из Discord командой /контракт (когда нет доступа к сайту)."""
import json
from datetime import datetime, timedelta, timezone

import discord
from discord import app_commands
from discord.ext import commands

from config import GUILD_ID, GUILD_IDS_LIST
from database import execute, fetch_one

GUILD_OBJECTS = [discord.Object(id=g) for g in GUILD_IDS_LIST] or [discord.Object(id=GUILD_ID)]

MSK = timezone(timedelta(hours=3))

CONTRACT_CHOICES = [
    app_commands.Choice(name="Активация", value="активация"),
    app_commands.Choice(name="Дары моря", value="дары-моря"),
    app_commands.Choice(name="Металлургия - Сдача", value="металлургия-сдача"),
    app_commands.Choice(name="Металлургия - Добыча", value="металлургия-добыча"),
    app_commands.Choice(name="Товары", value="товары"),
    app_commands.Choice(name="Ателье", value="ателье"),
    app_commands.Choice(name="Агитации - Маркетплейс", value="агитации-маркетплейс"),
    app_commands.Choice(name="Агитации - WN", value="агитации-wn"),
    app_commands.Choice(name="Тюнинг", value="тюнинг"),
]

AGITATION_TYPES = {"агитации-маркетплейс", "агитации-wn"}

# Доп. поля модалки по типам: (id, label, required, paragraph)
EXTRA_FIELDS: dict[str, list[tuple[str, str, bool, bool]]] = {
    "активация": [("price", "Сумма", True, False)],
    "дары-моря": [("fishType", "Вид рыбы", True, False), ("fishQty", "Количество", True, False)],
    "металлургия-сдача": [("oreType", "Руда (напр. Железная руда)", True, False)],
    "металлургия-добыча": [("iron", "Железо", False, False), ("silver", "Серебро", False, False),
                            ("copper", "Медь", False, False), ("tin", "Олово", False, False),
                            ("gold", "Золото", False, False)],
    "товары": [("delivery", "Доставка (да/нет)", False, False), ("loading", "Погрузка (да/нет)", False, False)],
    "ателье": [("totalUniforms", "Количество формы", True, False)],
    "агитации-маркетплейс": [("links", "Ссылки (каждая с новой строки)", True, True),
                             ("price", "Сумма за контракт", False, False)],
    "агитации-wn": [("wnCategory", "Категория", True, False), ("price", "Сумма за контракт", False, False)],
    "тюнинг": [],
}


class ContractModal(discord.ui.Modal):
    def __init__(self, cog: "ContractSubmit", guild_id: int, contract_type: str,
                 attachments: list, price: float | None):
        super().__init__(title=f"Контракт: {contract_type}")
        self.cog = cog
        self.guild_id = guild_id
        self.contract_type = contract_type
        self.attachments = attachments
        self.base_price = price
        self.inputs: list[tuple[str, discord.ui.TextInput]] = []
        for fid, label, req, para in EXTRA_FIELDS.get(contract_type, []):
            inp = discord.ui.TextInput(
                label=label[:45],
                style=discord.TextStyle.paragraph if para else discord.TextStyle.short,
                required=req, max_length=1000,
            )
            self.add_item(inp)
            self.inputs.append((fid, inp))

    async def on_submit(self, interaction: discord.Interaction):
        fields: dict = {}
        price = self.base_price or 0
        for fid, inp in self.inputs:
            v = (inp.value or "").strip()
            if fid == "price" and v:
                try:
                    price = float(v.replace(" ", "").replace(",", "."))
                except ValueError:
                    return await interaction.response.send_message("❌ Сумма - число.", ephemeral=True)
                fields["price"] = price
            elif fid in ("fishQty", "totalUniforms"):
                try:
                    fields[fid] = int(v) if v else 0
                except ValueError:
                    return await interaction.response.send_message(f"❌ {fid} - число.", ephemeral=True)
            elif fid in ("iron", "silver", "copper", "tin", "gold"):
                try:
                    fields[fid] = int(v) if v else 0
                except ValueError:
                    fields[fid] = 0
            elif fid == "links":
                fields["links"] = [x.strip() for x in v.split("\n") if x.strip()]
            else:
                fields[fid] = v
        # Легкие проверки как на сайте
        ct = self.contract_type
        if ct == "активация" and (not price or price <= 0 or price > 20000):
            return await interaction.response.send_message("❌ Сумма 1..20000.", ephemeral=True)
        if ct == "металлургия-добыча" and not any(fields.get(k, 0) > 0 for k in ("iron", "silver", "copper", "tin", "gold")):
            return await interaction.response.send_message("❌ Укажи хотя бы один ресурс.", ephemeral=True)
        await interaction.response.defer(ephemeral=True)
        try:
            cid = await self.cog.create_contract(
                self.guild_id, interaction, ct, self.attachments, fields, price)
        except Exception as e:
            return await interaction.followup.send(f"❌ Ошибка: {e}", ephemeral=True)
        await interaction.followup.send(
            f"✅ Контракт отправлен на проверку (локальный ID {cid}).", ephemeral=True)


class ContractSubmit(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="контракт", description="Отправить контракт (тип + скрины)")
    @app_commands.guilds(*GUILD_OBJECTS)
    @app_commands.describe(
        тип="Тип контракта",
        скрин="Скриншот (обязательно)",
        скрин2="Второй скриншот (для товаров)",
        сумма="Сумма (активация / агитации рекрута)",
    )
    @app_commands.choices(тип=CONTRACT_CHOICES)
    async def contract_cmd(
        self,
        interaction: discord.Interaction,
        тип: app_commands.Choice[str],
        скрин: discord.Attachment,
        скрин2: discord.Attachment | None = None,
        сумма: float | None = None,
    ):
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message("❌ Только на сервере.", ephemeral=True)
        ct = тип.value
        # Роли: рекрут только агитации, юзеру агитации нельзя
        try:
            from cogs.applications import panel_role_of, is_admin as _is_admin
            prole = await panel_role_of(str(interaction.guild.id), str(interaction.user.id))
            is_adm = _is_admin(interaction.user) or prole in ("admin", "owner")
        except Exception:
            prole, is_adm = "user", False
        if ct in AGITATION_TYPES and prole == "user" and not is_adm:
            return await interaction.response.send_message("❌ Агитации только для рекрутов.", ephemeral=True)
        if ct not in AGITATION_TYPES and prole == "recruiter":
            return await interaction.response.send_message("❌ Рекрут отправляет только агитации.", ephemeral=True)

        atts = [скрин] + ([скрин2] if скрин2 else [])
        if ct == "агитации-маркетплейс" and atts:
            return await interaction.response.send_message("❌ Для маркетплейса скрины не нужны, только ссылки.", ephemeral=True)
        if ct != "агитации-маркетплейс" and not atts:
            return await interaction.response.send_message("❌ Прикрепи скриншот.", ephemeral=True)
        if len(atts) > 2:
            return await interaction.response.send_message("❌ Максимум 2 скриншота.", ephemeral=True)

        extras = EXTRA_FIELDS.get(ct, [])
        if not extras:
            await interaction.response.defer(ephemeral=True)
            try:
                cid = await self.create_contract(
                    interaction.guild.id, interaction, ct, atts, {}, сумма or 0)
            except Exception as e:
                return await interaction.followup.send(f"❌ Ошибка: {e}", ephemeral=True)
            return await interaction.followup.send(
                f"✅ Контракт отправлен на проверку (локальный ID {cid}).", ephemeral=True)
        await interaction.response.send_modal(
            ContractModal(self, interaction.guild.id, ct, atts, сумма))

    async def create_contract(self, guild_id: int, interaction: discord.Interaction,
                              contract_type: str, attachments: list,
                              fields: dict, price: float | None) -> int:
        from database import insert_contract_if_new
        now = datetime.now(MSK)
        urls = [a.url for a in attachments if getattr(a, "url", None)]
        images = [{"filename": getattr(a, "filename", "image.jpg"),
                   "mime": getattr(a, "content_type", "image/jpeg") or "image/jpeg"} for a in attachments]
        row = {
            "ts": now.strftime("%d.%m.%Y %H:%M:%S"),
            "discord_id": str(interaction.user.id),
            "contract_type": contract_type,
            "channel_id": str(interaction.channel.id) if interaction.channel else "",
            "discord_message_id": str(interaction.id),
            "attachment_urls": "\n".join(urls),
            "msk_date": now.strftime("%d-%m-%Y"),
            "msk_date_iso": now.date().isoformat(),
            "details": json.dumps(
                {"fields": fields, "images": images}, ensure_ascii=False),
            "price": float(price or fields.get("price") or 0),
            "fish_type": fields.get("fishType", ""),
            "fish_qty": int(fields.get("fishQty") or 0),
            "ore_type": fields.get("oreType", ""),
            "m_iron": int(fields.get("iron") or 0),
            "m_silver": int(fields.get("silver") or 0),
            "m_copper": int(fields.get("copper") or 0),
            "m_tin": int(fields.get("tin") or 0),
            "m_gold": int(fields.get("gold") or 0),
            "goods_delivery": "YES" if str(fields.get("delivery", "")).lower() in ("да", "yes", "1", "true") else "",
            "goods_loading": "YES" if str(fields.get("loading", "")).lower() in ("да", "yes", "1", "true") else "",
            "atelier_total_uniforms": int(fields.get("totalUniforms") or 0),
            "marketplace_links_count": len(fields.get("links", [])),
            "wn_category": fields.get("wnCategory", ""),
            "wn_screenshots_count": len(attachments) if contract_type == "агитации-wn" else 0,
            "tuning_has_screenshot": "YES" if attachments else "",
            "status": "",
        }
        await insert_contract_if_new({**row, "guild_id": str(guild_id)})
        saved = await fetch_one(
            "SELECT id FROM contracts WHERE guild_id=? AND ts=? AND discord_id=? AND contract_type=?",
            (str(guild_id), row["ts"], row["discord_id"], contract_type),
        )
        return int(saved["id"]) if saved else 0


async def setup(bot):
    await bot.add_cog(ContractSubmit(bot))
