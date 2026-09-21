from __future__ import annotations

from services.public_panel_embed import build_public_panel_embed
from views.public_profile_panel import PublicProfilePanelView

from services.prices import get_prices_where, set_price_db

import discord
import json
import io

from services.audit import audit_contracts, audit_promotions, audit_bonus_log

from datetime import datetime
from typing import Literal

from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput

from config import GUILD_ID, GUILD_IDS_LIST

GUILD_OBJECTS = [discord.Object(id=g) for g in GUILD_IDS_LIST] or [discord.Object(id=GUILD_ID)]
from database import fetch_all, execute, fetch_one, get_setting, set_setting

from utils.week import week_range_msk, prev_week_range_msk
from cogs.bonus import create_bonus_report_for_week, delete_bonus_report
from services.pending_counter import upsert_pending_counter_message

from datetime import datetime
import re

from cogs.cooldowns import show_global_cooldowns

USER_MENTION_RE = re.compile(r"^<@!?(?P<id>\d+)>$")


import discord

SET_ACCEPT_ROLES_KEY = "app_accept_roles"
SET_REJECT_ROLES_KEY = "app_reject_remove_roles"


def _role_ids_to_csv(role_ids: list[int]) -> str:
    return ",".join(str(x) for x in role_ids)


def _csv_to_role_ids(s: str | None) -> list[int]:
    if not s:
        return []
    out: list[int] = []
    for p in s.split(","):
        p = p.strip()
        if p.isdigit():
            out.append(int(p))
    return out


class ApplicationsRolesView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.accept_role_ids: list[int] = []
        self.reject_remove_role_ids: list[int] = []

    async def _load(self):
        self.accept_role_ids = _csv_to_role_ids(await get_setting(SET_ACCEPT_ROLES_KEY))
        self.reject_remove_role_ids = _csv_to_role_ids(await get_setting(SET_REJECT_ROLES_KEY))

    def build_embed(self) -> discord.Embed:
        e = discord.Embed(
            title="🎭 Роли заявок",
            description=(
                "Настрой роли, которые выдаются при принятии заявки, и роли, которые снимаются при отказе.\n"
                "Сохраняется в settings и используется cog `applications.py`."
            ),
            color=0x5865F2
        )
        a = ", ".join(f"<@&{rid}>" for rid in self.accept_role_ids) or "—"
        r = ", ".join(f"<@&{rid}>" for rid in self.reject_remove_role_ids) or "—"
        e.add_field(name="✅ Выдать при принятии", value=a, inline=False)
        e.add_field(name="❌ Снять при отказе", value=r, inline=False)
        return e

    async def open_edit(self, interaction: discord.Interaction):
        await self._load()
        await interaction.response.edit_message(content=None, embed=self.build_embed(), view=self)

    async def open_msg_edit(self, message: discord.Message):
        await self._load()
        await message.edit(content=None, embed=self.build_embed(), view=self)

    @discord.ui.button(label="✅ Выдать при принятии (выбор)", style=discord.ButtonStyle.success)
    async def pick_accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.guild:
            return await interaction.response.send_message("❌ Только на сервере.", ephemeral=True)

        await self._load()
        v = PickRolesOnceView(
            mode="accept",
            parent=self,
            preselected_ids=self.accept_role_ids,
        )
        await interaction.response.edit_message(
            content="Выбери роли, которые нужно выдавать при принятии заявки:",
            embed=None,
            view=v
        )

    @discord.ui.button(label="❌ Снять при отказе (выбор)", style=discord.ButtonStyle.danger)
    async def pick_reject_remove(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.guild:
            return await interaction.response.send_message("❌ Только на сервере.", ephemeral=True)

        await self._load()
        v = PickRolesOnceView(
            mode="reject_remove",
            parent=self,
            preselected_ids=self.reject_remove_role_ids,
        )
        await interaction.response.edit_message(
            content="Выбери роли, которые нужно снимать при отказе:",
            embed=None,
            view=v
        )

    @discord.ui.button(label="🧹 Очистить", style=discord.ButtonStyle.secondary)
    async def clear_all(self, interaction: discord.Interaction, button: discord.ui.Button):
        await set_setting(SET_ACCEPT_ROLES_KEY, "")
        await set_setting(SET_REJECT_ROLES_KEY, "")
        await self.open_edit(interaction)

    @discord.ui.button(label="⬅️ Назад", style=discord.ButtonStyle.secondary)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="⚙️ Настройки", description="Выберите раздел:", color=0x9B7BFF)
        await interaction.response.edit_message(content=None, embed=embed, view=AdminSettingsView())


class PickRolesOnceView(discord.ui.View):
    def __init__(self, mode: str, parent: ApplicationsRolesView, preselected_ids: list[int]):
        super().__init__(timeout=180)
        self.mode = mode  # "accept" | "reject_remove"
        self.parent = parent
        self.selected_ids: list[int] = list(preselected_ids or [])

        self.add_item(RoleMultiSelect(set(preselected_ids or [])))

    @discord.ui.button(label="💾 Сохранить", style=discord.ButtonStyle.primary)
    async def save(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.mode == "accept":
            await set_setting(SET_ACCEPT_ROLES_KEY, _role_ids_to_csv(self.selected_ids))
        elif self.mode == "reject_remove":
            await set_setting(SET_REJECT_ROLES_KEY, _role_ids_to_csv(self.selected_ids))
        else:
            return await interaction.response.edit_message(content="❌ Unknown mode.", view=self)

        # ВАЖНО: отвечаем ОДИН раз на interaction — редактируем текущее сообщение обратно в панель
        await self.parent._load()
        await interaction.response.edit_message(
            content="✅ Сохранено.",
            embed=self.parent.build_embed(),
            view=self.parent
        )

    @discord.ui.button(label="Отмена", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.parent._load()
        await interaction.response.edit_message(
            content=None,
            embed=self.parent.build_embed(),
            view=self.parent
        )


class RoleMultiSelect(discord.ui.RoleSelect):
    def __init__(self, preselected_ids: set[int]):
        super().__init__(
            placeholder="Выбери роли…",
            min_values=0,
            max_values=25
        )
        self.preselected_ids = preselected_ids

    async def callback(self, interaction: discord.Interaction):
        view: PickRolesOnceView = self.view  # type: ignore
        view.selected_ids = [r.id for r in self.values]
        # Тут тоже не defer: просто “ack” редактированием не нужен, можно быстро подтвердить defer,
        # но тогда нельзя будет response.edit_message в save. Поэтому просто тихо отвечаем defer НЕ делая.
        await interaction.response.defer()


async def get_admin_role_ids() -> list[int]:
    """
    Читает admin_role_ids из настроек и возвращает список int.
    В БД хранится JSON-строка вида "[123, 456]".
    """
    raw = await get_setting("admin_role_ids")
    if not raw:
        return []

    try:
        arr = json.loads(raw)
    except Exception:
        return []

    if not isinstance(arr, list):
        return []

    ids: list[int] = []
    for x in arr:
        try:
            ids.append(int(x))
        except Exception:
            continue
    return ids


async def count_admins_online(guild: discord.Guild) -> tuple[int, int]:
    """
    Возвращает (всего_админов, админов_онлайн) по ролям из admin_role_ids.
    """
    role_ids = await get_admin_role_ids()
    if not role_ids:
        return 0, 0

    admins: set[discord.Member] = set()
    for rid in role_ids:
        role = guild.get_role(rid)
        if role:
            admins.update(role.members)

    online = 0
    for m in admins:
        if m.status in (discord.Status.online, discord.Status.idle, discord.Status.dnd):
            online += 1

    return len(admins), online



async def count_pending_contracts(guild_id: str | None = None) -> int:
    row = await fetch_one(
        "SELECT COUNT(*) AS cnt FROM contracts WHERE confirm_status = 'PENDING' AND (? IS NULL OR guild_id = ?)",
        (guild_id, guild_id)
    )
    return int(row["cnt"] or 0) if row else 0


async def count_pending_promos(guild_id: str | None = None) -> int:
    row = await fetch_one(
        "SELECT COUNT(*) AS cnt FROM promotion_reports WHERE status IN ('NEW','TAKEN') AND (? IS NULL OR guild_id = ? OR guild_id IS NULL)",
        (guild_id, guild_id)
    )
    return int(row["cnt"] or 0) if row else 0


async def count_pending_bonus(guild_id: str | None = None) -> int:
    row = await fetch_one(
        "SELECT COUNT(*) AS cnt FROM bonus_reports WHERE status IN ('NEW','TAKEN') AND (? IS NULL OR guild_id = ?)",
        (guild_id, guild_id)
    )
    return int(row["cnt"] or 0) if row else 0




async def build_admin_hub_embed(guild: discord.Guild) -> discord.Embed:
    gid = str(guild.id)
    c1 = await count_pending_contracts(gid)
    c2 = await count_pending_promos(gid)
    c3 = await count_pending_bonus(gid)

    admins_total, admins_online = await count_admins_online(guild)

    e = discord.Embed(title="🔧 Админ-панель", color=0x9B7BFF)
    e.description = "Открыть панель можно кнопкой ниже (панель будет видна только вам). Автообновление панели каждые 5 минут!"

    e.add_field(
        name="👮 Админы",
        value=f"В сети: **{admins_online}** / **{admins_total}**",
        inline=True
    )
    e.add_field(
        name="📌 В очереди",
        value=(
            f"📝Контракты: **{c1}**\n"
            f"📈Повышения: **{c2}**\n"
            f"💰Премии: **{c3}**"
        ),
        inline=True
    )
    return e




async def preview_sync_all_ranks(guild: discord.Guild, sample_limit: int = 5) -> dict:
    rank_rows = await fetch_all(
        "SELECT id, role_id, COALESCE(sort_order, 0) AS sort_order FROM ranks WHERE role_id IS NOT NULL AND guild_id = ?",
        (str(guild.id),)
    )
    role_to_rank = {int(r["role_id"]): (int(r["id"]), int(r["sort_order"])) for r in rank_rows}

    would_set = 0
    no_rank_role = 0
    samples = []

    async for member in guild.fetch_members(limit=None):
        best_rank_id = None
        best_so = -10**9

        for role in member.roles:
            hit = role_to_rank.get(role.id)
            if not hit:
                continue
            rank_id, so = hit
            if so > best_so:
                best_so = so
                best_rank_id = rank_id

        if best_rank_id is None:
            no_rank_role += 1
            continue

        would_set += 1
        if len(samples) < sample_limit:
            samples.append((str(member.id), best_rank_id, best_so))

    return {"would_set": would_set, "no_rank_role": no_rank_role, "samples": samples}

async def sync_all_ranks_db_only(guild: discord.Guild) -> dict:
    rank_rows = await fetch_all(
        "SELECT id, role_id, COALESCE(sort_order, 0) AS sort_order FROM ranks WHERE role_id IS NOT NULL AND guild_id = ?",
        (str(guild.id),)
    )
    role_to_rank = {int(r["role_id"]): (int(r["id"]), int(r["sort_order"])) for r in rank_rows}

    synced = 0
    no_rank_role = 0

    async for member in guild.fetch_members(limit=None):
        best_rank_id = None
        best_so = -10**9

        for role in member.roles:
            hit = role_to_rank.get(role.id)
            if not hit:
                continue
            rank_id, so = hit
            if so > best_so:
                best_so = so
                best_rank_id = rank_id

        if best_rank_id is None:
            no_rank_role += 1
            continue

        await execute(
            """
            INSERT INTO users(discord_id, current_rank_id)
            VALUES(?, ?)
            ON CONFLICT(discord_id) DO UPDATE SET current_rank_id=excluded.current_rank_id
            """,
            (str(member.id), int(best_rank_id))
        )
        synced += 1

    return {"synced": synced, "no_rank_role": no_rank_role}


async def void_contract_by_id(contract_id: int, moderator_id: int, reason: str) -> bool:
    row = await fetch_one(
        "SELECT id FROM contracts WHERE id=? AND COALESCE(voided,0)=0",
        (contract_id,)
    )
    if not row:
        return False

    await execute("""
        UPDATE contracts
        SET voided=1,
            voided_by=?,
            voided_reason=?,
            voided_at=datetime('now')
        WHERE id=? AND COALESCE(voided,0)=0
    """, (str(moderator_id), reason, contract_id))
    return True



async def get_setting(key: str, default=None):
    row = await fetch_one("SELECT value FROM settings WHERE key = ?", (key,))
    return (row["value"] if row else default)

async def log_void_contract(interaction: discord.Interaction, contract_id: int, reason: str):
    audit_id = await get_setting("log_promo")
    if not audit_id:
        print("log_promo is not set in settings")
        return

    try:
        audit_id = int(audit_id)
    except ValueError:
        print("log_promo is not int:", audit_id)
        return

    ch = interaction.client.get_channel(audit_id)
    if ch is None:
        try:
            ch = await interaction.client.fetch_channel(audit_id)  # fallback [web:216]
        except Exception as e:
            print("Cannot fetch audit channel:", e)
            return

    e = discord.Embed(title="🗑️ Контракт списан (voided)", color=0xE74C3C)
    e.add_field(name="Contract ID", value=str(contract_id), inline=True)
    e.add_field(name="Кто", value=interaction.user.mention, inline=True)
    e.add_field(name="Причина", value=(reason or "—")[:1024], inline=False)

    try:
        await ch.send(embed=e)
    except Exception as ex:
        print("Failed to send void log:", ex)



class VoidByIdModal(discord.ui.Modal, title="Списать контракт по Contract ID"):
    contract_id = discord.ui.TextInput(
        label="Contract ID",
        required=True,
        max_length=20
    )
    reason = discord.ui.TextInput(
        label="Причина списания",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=500
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            cid = int(str(self.contract_id.value).strip())
        except ValueError:
            await interaction.response.send_message("❌ Contract ID должен быть числом.", ephemeral=True)
            return

        reason = str(self.reason.value).strip()
        ok = await void_contract_by_id(cid, interaction.user.id, reason)
        if not ok:
            await interaction.response.send_message("❌ Контракт не найден или уже списан.", ephemeral=True)
            return

        await log_void_contract(interaction, cid, reason)
        await interaction.response.send_message("✅ Контракт списан: в премии больше не учитывается.", ephemeral=True)



async def void_promo_credits_by_contract(contract_id: int, moderator_id: int, reason: str) -> int:
    row = await fetch_one(
        "SELECT COUNT(*) AS n FROM promo_credits WHERE contract_id=? AND voided=0",
        (contract_id,)
    )
    n = int((row or {}).get("n", 0))
    if n == 0:
        return 0

    await execute("""
        UPDATE promo_credits
        SET voided=1,
            voided_by=?,
            voided_reason=?,
            voided_at=datetime('now')
        WHERE contract_id=? AND voided=0
    """, (str(moderator_id), reason, contract_id))

    return n





async def calc_live_base_sum(discord_id: str, week_start: str, week_end: str) -> float:
    row = await fetch_one(
        """
        SELECT COALESCE(SUM(calc_price), 0) AS base_sum
        FROM v_contract_value
        WHERE discord_id = ?
          AND confirm_status = 'APPROVED'
          AND date(msk_date_iso) >= date(?)
          AND date(msk_date_iso) <= date(?)
        """,
        (discord_id, week_start, week_end)
    )
    return float((row["base_sum"] if row else 0) or 0.0)



PRICE_LABELS = {
    "agit:wn_green": "Агитации WN: зелёная",
    "agit:wn_notice": "Агитации WN: объявление",
    "agit:marketplace_link": "Агитации: маркетплейс",
    "atelier.uniform": "Ателье: форма",
    "goods.delivery": "Товары: доставка",
    "goods.loading": "Товары: погрузка",
    "ore.delivery.copper": "Руда: сдача Медь",
    "ore.delivery.gold": "Руда: сдача Золото",
    "ore.delivery.iron": "Руда: сдача Железо",
    "ore.delivery.silver": "Руда: Сдача Серебро",
    "ore.delivery.tin": "Руда: Сдача Олово",
    "tuning:with_screenshot": "Тюнинг: со скриншотом",
    "courier:delivery": "Курьер еды",
    "ore_unit:copper": "Добыча руды: Медь",
    "ore_unit:gold": "Добыча руды: Золото",
    "ore_unit:iron": "Добыча руды: Железо",
    "ore_unit:silver": "Добыча руды: Серебро",
    "ore_unit:tin": "Добыча руды: Олово",
}

CATEGORY_ORDER = ["Агитации", "Товары", "Ателье", "Тюнинг", "Курьер", "Руда (доставка)", "Руда (добыча)"]

CATEGORY_QUERIES = {
    "Агитации": "item_key LIKE 'agit:%'",
    "Товары": "item_key LIKE 'goods.%'",
    "Ателье": "item_key LIKE 'atelier.%'",
    "Тюнинг": "item_key LIKE 'tuning:%'",
    "Курьер": "item_key LIKE 'courier:%'",
    "Руда (доставка)": "item_key LIKE 'ore.delivery.%'",
    "Руда (добыча)": "item_key LIKE 'ore_unit:%'",
}

def fmt_price(p: float) -> str:
    return f"{p:,.0f}".replace(",", " ")



async def build_prices_embed() -> discord.Embed:
    embed = discord.Embed(
        title="💰 Выплаты по контрактам",
        description="Сколько платим за каждый контракт. Цены меняет администрация.",
        color=0x2ECC71,
    )

    cat_emoji = {
        "Агитации": "📣",
        "Товары": "📦",
        "Ателье": "🧵",
        "Тюнинг": "🔧",
        "Курьер": "🛵",
        "Руда (доставка)": "⛏️",
        "Руда (добыча)": "💎",
    }

    for cat in CATEGORY_ORDER:
        rows = await get_prices_where(CATEGORY_QUERIES[cat])
        if not rows:
            continue

        lines = []
        for r in rows:
            k = r["item_key"]
            p = float(r["price"] or 0)
            name = PRICE_LABELS.get(k, k)
            lines.append(f"▪️ {name} — **{fmt_price(p)}**")

        emoji = cat_emoji.get(cat, "📌")
        embed.add_field(name=f"{emoji} {cat}", value="\n".join(lines), inline=False)

    embed.set_footer(text="Обновляется автоматически • /prices_ui для правок (админ)")
    return embed


class EditPriceModal(discord.ui.Modal, title="Изменить цену"):
    new_price = discord.ui.TextInput(label="Новая цена", placeholder="например 12000", required=True)

    def __init__(self, view, item_key: str):
        super().__init__()
        self.view = view
        self.item_key = item_key

    async def on_submit(self, interaction: discord.Interaction):
        raw = str(self.new_price.value).strip().replace(" ", "").replace(",", ".")
        try:
            price = float(raw)
        except ValueError:
            return await interaction.response.send_message("❌ Введи число.", ephemeral=True)

        if price < 0:
            return await interaction.response.send_message("❌ Цена не может быть отрицательной.", ephemeral=True)

        await set_price_db(self.item_key, price)
        await interaction.response.send_message("✅ Обновлено.", ephemeral=True)

        embed = await self.view.build_embed()
        await self.view.message.edit(embed=embed, view=self.view)


class PricesCategoriesView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=600)
        self.category = "Агитации"
        self.selected_key = None
        self.message = None

        self.category_select.options = [
            discord.SelectOption(label=name, value=name)
            for name in CATEGORY_QUERIES.keys()
        ]

    async def build_embed(self):
        rows = await get_prices_where(CATEGORY_QUERIES[self.category])

        # options второго select (до 25)
        opts = []
        for r in rows[:25]:
            k = r["item_key"]
            p = float(r["price"] or 0)
            label = PRICE_LABELS.get(k, k)
            opts.append(discord.SelectOption(label=label[:100], value=k, description=fmt_price(p)[:100]))

        self.item_select.options = opts
        if opts and self.selected_key not in [o.value for o in opts]:
            self.selected_key = opts[0].value
        if not opts:
            self.selected_key = None

        lines = []
        for r in rows:
            k = r["item_key"]
            p = float(r["price"] or 0)
            name = PRICE_LABELS.get(k, k)
            lines.append(f"{name} — {fmt_price(p)}")

        desc = "\n".join(lines) if lines else "Пусто."
        return discord.Embed(title=f"Цены: {self.category}", description=desc, color=0x95A5A6)

    @discord.ui.select(placeholder="Категория", row=0)
    async def category_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.category = select.values[0]
        embed = await self.build_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.select(placeholder="Пункт", row=1)
    async def item_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.selected_key = select.values[0]
        await interaction.response.send_message(f"Выбрано: `{self.selected_key}`", ephemeral=True)

    @discord.ui.button(label="Изменить цену", style=discord.ButtonStyle.primary, row=2)
    async def edit_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.selected_key:
            return await interaction.response.send_message("Сначала выбери пункт.", ephemeral=True)
        await interaction.response.send_modal(EditPriceModal(self, self.selected_key))



async def update_bonus_audit_message(client: discord.Client, report_id: int):
    r = await fetch_one("SELECT * FROM bonus_reports WHERE report_id = ?", (int(report_id),))
    if not r:
        return

    ch_id = r.get("audit_channel_id")
    msg_id = r.get("audit_msg_id")
    if not ch_id or not msg_id:
        return

    try:
        ch = client.get_channel(int(ch_id)) or await client.fetch_channel(int(ch_id))
        msg = await ch.fetch_message(int(msg_id))
    except Exception:
        return

    status = (r.get("status") or "NEW").upper()
    decision = (r.get("decision") or "").upper()

    # live суммы из view за неделю
    sums = await calc_live_sums(str(r["discord_id"]), str(r["week_start"]), str(r["week_end"]))
    contracts_sum = float(sums["contracts_sum"])
    rank_bonus_sum = float(sums["rank_bonus_sum"])
    live_base_total = float(sums["live_total"])  # контракты+надбавка

    sea = float(r.get("sea_amount") or 0.0)
    total = live_base_total + sea

    # синхронизируем total_amount в БД с тем, что показываем
    try:
        await execute(
            "UPDATE bonus_reports SET total_amount = ? WHERE report_id = ?",
            (float(total), int(report_id))
        )
    except Exception:
        pass

    color = 0x3498DB
    if status == "APPROVED" or decision == "APPROVED":
        color = 0x2ECC71
    elif status == "REJECTED" or decision == "REJECTED":
        color = 0xE74C3C
    elif status == "TAKEN":
        color = 0xF1C40F

    e = discord.Embed(title=f"💰 Премия #{r['report_id']}", color=color)
    e.add_field(name="Пользователь", value=f"<@{r['discord_id']}>", inline=True)
    e.add_field(name="Неделя", value=f"{r['week_start']} — {r['week_end']} (МСК)", inline=True)
    e.add_field(name="Статус", value=status, inline=True)

    e.add_field(name="Контракты (live)", value=str(round(contracts_sum, 2)), inline=True)
    e.add_field(name="Надбавка за ранг", value=str(round(rank_bonus_sum, 2)), inline=True)
    e.add_field(name="Дары моря", value=str(round(sea, 2)), inline=True)
    e.add_field(name="Сумма (итог)", value=str(round(total, 2)), inline=False)

    if r.get("taken_by"):
        e.add_field(name="Взял", value=f"<@{r['taken_by']}>", inline=True)
    if r.get("reviewed_by"):
        e.add_field(name="Рассмотрел", value=f"<@{r['reviewed_by']}>", inline=True)
    if status == "REJECTED" and r.get("reason"):
        e.add_field(name="Причина", value=str(r["reason"])[:1000], inline=False)

    await msg.edit(embed=e)




def escape_like(s: str, esc: str = "\\") -> str:
    return (s.replace(esc, esc + esc)
             .replace("%", esc + "%")
             .replace("_", esc + "_"))


def parse_user_id(s: str) -> int | None:
    s = (s or "").strip()
    if s.isdigit():
        return int(s)

    m = USER_MENTION_RE.match(s)
    if m:
        return int(m.group("id"))

    return None


def parse_admin_role_ids(raw: str) -> list[int]:
    raw = (raw or "").strip()
    if not raw:
        return []

    i = raw.find("[")
    if i != -1:
        raw = raw[i:]  # отрезали префикс вроде "admin_role_ids"

    if raw.startswith("[") and raw.endswith("]"):
        try:
            arr = json.loads(raw)
            return [int(x) for x in arr]
        except Exception:
            return []

    parts = raw.replace(",", " ").split()
    return [int(p) for p in parts if p.isdigit()]

def dump_admin_role_ids(ids: set[int]) -> str:
    return json.dumps(sorted(ids), ensure_ascii=False)

def admin_roles_check(get_setting):
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.guild is None:
            return False

        raw = await get_setting("admin_role_ids")
        role_ids = parse_admin_role_ids(str(raw or ""))
        if not role_ids:
            return False

        # 1) если Discord уже дал Member — используем
        if isinstance(interaction.user, discord.Member):
            member = interaction.user
        else:
            # 2) пробуем из кэша
            member = interaction.guild.get_member(interaction.user.id)
            # 3) если нет в кэше — тянем с API
            if member is None:
                member = await interaction.guild.fetch_member(interaction.user.id)

        return any(member.get_role(rid) is not None for rid in role_ids)

    return app_commands.check(predicate)


# ====== SETTINGS MODALS / VIEW ======

async def create_promo_report_and_post(
    interaction: discord.Interaction,
    discord_id: str,
    from_rank_id: int,
    to_rank_id: int,
    system_type: str,
    embed: discord.Embed,
):
    # 1) создаём репорт
    await execute(
        """
        INSERT INTO promotion_reports(guild_id, discord_id, from_rank_id, to_rank_id, system_type, submitted_at, status)
        VALUES (?, ?, ?, ?, ?, datetime('now'), 'NEW')
        """,
        (str(interaction.guild.id) if interaction.guild else None, str(discord_id), int(from_rank_id), int(to_rank_id), str(system_type)),
    )

    rep = await fetch_one(
        "SELECT report_id FROM promotion_reports WHERE discord_id = ? ORDER BY report_id DESC LIMIT 1",
        (str(discord_id),),
    )
    report_id = int(rep["report_id"])
    try:
        from services.api_sync import queue_promo_sync
        queue_promo_sync(str(interaction.guild.id), report_id, str(discord_id),
                         from_rank=from_rank_id, to_rank=to_rank_id, status="NEW")
    except Exception as e:
        print(f"[api_sync] warn: {e}")

    # 2) куда постить
    raw = await get_setting("promo_channel_id")
    if not raw:
        raise RuntimeError("Не задан promo_channel_id (задай в /admin → Settings).")
    channel_id = int(raw)

    ch = interaction.client.get_channel(channel_id)
    if ch is None:
        ch = await interaction.client.fetch_channel(channel_id)

    # 3) постим сообщение и сохраняем ids
    msg = await ch.send(embed=embed, view=PromoActionView(report_id))
    await execute(
        "UPDATE promotion_reports SET msg_channel_id=?, msg_id=? WHERE report_id=?",
        (str(msg.channel.id), str(msg.id), report_id),
    )

    return {"ok": True, "report_id": report_id}



class SetJsonRoleIdsModal(discord.ui.Modal, title="admin_role_ids (JSON)"):
    value = discord.ui.TextInput(
        label="JSON массив role_id",
        placeholder='[123, 456]',
        style=discord.TextStyle.long,
        required=True,
        max_length=1000,
    )

    async def on_submit(self, interaction: discord.Interaction):
        raw = self.value.value.strip()
        ids = parse_admin_role_ids(raw)
        if not ids:
            await interaction.response.send_message("❌ JSON невалидный или пустой список.", ephemeral=True)
            return
        await set_setting("admin_role_ids", dump_admin_role_ids(ids))
        await interaction.response.send_message(f"✅ admin_role_ids = {dump_admin_role_ids(ids)}", ephemeral=True)


class SetChannelIdModal(discord.ui.Modal):
    def __init__(self, key: str, title: str):
        super().__init__(title=title)
        self.key = key
        self.value = discord.ui.TextInput(
            label="ID канала (число)",
            placeholder="123456789012345678",
            required=True,
            max_length=32,
        )
        self.add_item(self.value)

    async def on_submit(self, interaction: discord.Interaction):
        s = self.value.value.strip()
        if not s.isdigit():
            await interaction.response.send_message("❌ Нужно число (channel_id).", ephemeral=True)
            return
        await set_setting(self.key, s)
        await interaction.response.send_message(f"✅ {self.key} = {s}", ephemeral=True)


class SetRoleIdModal(discord.ui.Modal):
    def __init__(self, key: str, title: str):
        super().__init__(title=title)
        self.key = key
        self.value = discord.ui.TextInput(
            label="ID роли (число)",
            placeholder="123456789012345678",
            required=True,
            max_length=32,
        )
        self.add_item(self.value)

    async def on_submit(self, interaction: discord.Interaction):
        s = self.value.value.strip()
        if not s.isdigit():
            await interaction.response.send_message("❌ Нужно число (role_id).", ephemeral=True)
            return
        await set_setting(self.key, s)
        await interaction.response.send_message(f"✅ {self.key} = {s}", ephemeral=True)


# ====== RANKS HELPERS ======

async def fetch_rank_requirements_rows(guild_id: str | None = None):
    return await fetch_all(
        """
        SELECT
          r1.id AS rank_from_id,
          r1.name AS rank_from_name,
          r1.sort_order AS sort_order,

          rm.rank_to AS main_rank_to_id,
          r2m.name AS main_rank_to_name,
          COALESCE(rm.family_contracts, 0) AS main_family,

          ra.rank_to AS alt_rank_to_id,
          r2a.name AS alt_rank_to_name,
          COALESCE(ra.family_contracts, 0) AS alt_family,
          COALESCE(ra.tuning_contracts, 0) AS alt_tuning

        FROM ranks r1
        LEFT JOIN rank_requirements_main rm ON rm.rank_from = r1.id
        LEFT JOIN ranks r2m ON r2m.id = rm.rank_to

        LEFT JOIN rank_requirements_alt ra ON ra.rank_from = r1.id
        LEFT JOIN ranks r2a ON r2a.id = ra.rank_to
        WHERE (? IS NULL OR r1.guild_id = ?)
        ORDER BY r1.sort_order ASC
        """,
        (guild_id, guild_id)
    )


async def get_user_approved_contracts_cnt(discord_id: int, guild_id: str | None = None) -> int:
    row = await fetch_one(
        "SELECT COUNT(*) AS cnt FROM contracts WHERE discord_id = ? AND confirm_status='APPROVED' AND (? IS NULL OR guild_id = ?)",
        (str(discord_id), guild_id, guild_id)  # contracts.discord_id = TEXT
    )
    return int(row["cnt"] or 0)


async def pick_rank_for_cnt(cnt: int, guild_id: str | None = None):
    return await fetch_one(
        """
        SELECT id, name, role_id, min_contracts, sort_order
        FROM ranks
        WHERE min_contracts <= ? AND (? IS NULL OR guild_id = ?)
        ORDER BY min_contracts DESC, sort_order DESC
        LIMIT 1
        """,
        (cnt, guild_id, guild_id)
    )


async def get_all_rank_role_ids(guild_id: str | None = None) -> list[int]:
    rows = await fetch_all(
        "SELECT role_id FROM ranks WHERE (? IS NULL OR guild_id = ?)", (guild_id, guild_id))
    return [int(r["role_id"]) for r in rows]


async def apply_rank_to_member(guild: discord.Guild, member: discord.Member) -> dict:
    gid = str(guild.id)
    cnt = await get_user_approved_contracts_cnt(member.id, gid)
    rank = await pick_rank_for_cnt(cnt, gid)
    if not rank:
        return {"ok": False, "reason": "no_ranks_in_db", "cnt": cnt}

    target_role = guild.get_role(int(rank["role_id"]))
    if not target_role:
        return {"ok": False, "reason": "role_not_found", "rank": dict(rank), "cnt": cnt}

    all_rank_role_ids = set(await get_all_rank_role_ids(gid))
    to_remove = [r for r in member.roles if r.id in all_rank_role_ids and r.id != target_role.id]

    try:
        if to_remove:
            await member.remove_roles(*to_remove, reason="Rank recalculation")
        if target_role not in member.roles:
            await member.add_roles(target_role, reason="Rank recalculation")
    except discord.Forbidden:
        return {"ok": False, "reason": "forbidden_manage_roles", "rank": dict(rank), "cnt": cnt}

    return {"ok": True, "rank": dict(rank), "cnt": cnt}


async def fetch_ranks(guild_id: str | None = None):
    return await fetch_all(
        "SELECT id, name, role_id, min_contracts, sort_order FROM ranks WHERE (? IS NULL OR guild_id = ?) ORDER BY min_contracts ASC, sort_order ASC",
        (guild_id, guild_id)
    )

async def update_promo_report_message(client: discord.Client, report_id: int):
    r = await fetch_one(
        """
        SELECT pr.*,
               r1.name AS from_rank_name,
               r2.name AS to_rank_name
        FROM promotion_reports pr
        LEFT JOIN ranks r1 ON pr.from_rank_id = r1.id
        LEFT JOIN ranks r2 ON pr.to_rank_id = r2.id
        WHERE pr.report_id = ?
        """,
        (int(report_id),),
    )
    if not r:
        return

    if not r.get("msg_channel_id") or not r.get("msg_id"):
        return

    channel_id = int(r["msg_channel_id"])
    msg_id = int(r["msg_id"])

    ch = client.get_channel(channel_id)
    if ch is None:
        ch = await client.fetch_channel(channel_id)

    msg = await ch.fetch_message(msg_id)

    status = (r.get("status") or "NEW").upper()
    color = 0x00BCD4
    if status == "APPROVED":
        color = 0x2ECC71
    elif status == "REJECTED":
        color = 0xE74C3C
    elif status == "TAKEN":
        color = 0xF1C40F

    e = discord.Embed(title=f"Отчет на повышения №{r['report_id']}", color=color)
    e.add_field(name="Пользователь", value=f"<@{r['discord_id']}> (`{r['discord_id']}`)", inline=False)
    e.add_field(name="Ранг прошлый", value=str(r.get("from_rank_name") or r.get("from_rank_id") or "?"), inline=True)
    e.add_field(name="Повышение на ранг", value=str(r.get("to_rank_name") or r.get("to_rank_id") or "?"), inline=True)
    e.add_field(name="Статус", value=status, inline=True)


    if r.get("reviewed_by"):
        e.add_field(name="Проверил", value=f"<@{r['reviewed_by']}>", inline=True)
    if status == "REJECTED" and r.get("reason"):
        e.add_field(name="Причина", value=str(r["reason"])[:1000], inline=False)

    # Если финальный статус — кнопки убираем
    view = None if status in ("APPROVED", "REJECTED") else PromoActionView(int(report_id))

    await msg.edit(embed=e, view=view)

def ranks_embed(rows):
    if not rows:
        return discord.Embed(title="🏷️ Ранги", description="Ранги не настроены.", color=0x808080)

    lines = []
    for i, r in enumerate(rows, start=1):
        lines.append(
            f"{i}. {r['name']} | role_id={r['role_id']} | min={r['min_contracts']} | order={r['sort_order']}"
        )

    return discord.Embed(title="🏷️ Ранги", description="```" + "\n".join(lines) + "```", color=0x808080)


class RankLinearRequirementsModal(discord.ui.Modal, title="Требования повышения (линейно)"):
    rank_name = discord.ui.TextInput(
        label="Текущий ранг (name)",
        placeholder="Newbie",
        max_length=50
    )
    main_family = discord.ui.TextInput(
        label="MAIN: family_contracts",
        placeholder="15",
        max_length=10
    )
    alt_family = discord.ui.TextInput(
        label="ALT: family_contracts",
        placeholder="10",
        max_length=10
    )
    alt_tuning = discord.ui.TextInput(
        label="ALT: tuning_contracts",
        placeholder="3",
        max_length=10
    )

    async def on_submit(self, interaction: discord.Interaction):
        name = self.rank_name.value.strip()
        if not name:
            return await interaction.response.send_message("❌ Название ранга пустое.", ephemeral=True)

        if not self.main_family.value.strip().isdigit():
            return await interaction.response.send_message("❌ MAIN family_contracts должен быть числом.", ephemeral=True)
        if not self.alt_family.value.strip().isdigit():
            return await interaction.response.send_message("❌ ALT family_contracts должен быть числом.", ephemeral=True)
        if not self.alt_tuning.value.strip().isdigit():
            return await interaction.response.send_message("❌ ALT tuning_contracts должен быть числом.", ephemeral=True)

        main_f = int(self.main_family.value.strip())
        alt_f = int(self.alt_family.value.strip())
        alt_t = int(self.alt_tuning.value.strip())

        # 1) найти rank_from и его sort_order
        _gid = str(interaction.guild.id) if interaction.guild else None
        r1 = await fetch_one("SELECT id, sort_order FROM ranks WHERE name=? AND (? IS NULL OR guild_id = ?) LIMIT 1", (name, _gid, _gid))
        if not r1:
            return await interaction.response.send_message(f"❌ Ранг '{name}' не найден.", ephemeral=True)

        rf = int(r1["id"])
        so = int(r1["sort_order"] or 0)

        # 2) найти следующий ранг по sort_order
        r2 = await fetch_one("SELECT id, name FROM ranks WHERE sort_order=? AND (? IS NULL OR guild_id = ?) LIMIT 1", (so + 1, _gid, _gid))
        if not r2:
            return await interaction.response.send_message(
                f"❌ Для ранга '{name}' не найден следующий (sort_order={so+1}).",
                ephemeral=True
            )

        rt = int(r2["id"])
        next_name = r2["name"]

        # 3) сохранить как "одна строка на rank_from"
        await execute("DELETE FROM rank_requirements_main WHERE rank_from=?", (rf,))
        await execute(
            "INSERT INTO rank_requirements_main(rank_from, rank_to, family_contracts) VALUES(?,?,?)",
            (rf, rt, main_f),
        )

        await execute("DELETE FROM rank_requirements_alt WHERE rank_from=?", (rf,))
        await execute(
            "INSERT INTO rank_requirements_alt(rank_from, rank_to, family_contracts, tuning_contracts) VALUES(?,?,?,?)",
            (rf, rt, alt_f, alt_t),
        )

        await interaction.response.send_message(
            f"✅ {name} → {next_name}: MAIN family={main_f}; ALT family={alt_f}, tuning={alt_t}.",
            ephemeral=True
        )


class RankAddModal(discord.ui.Modal, title="Добавить ранг"):
    name = discord.ui.TextInput(label="Название ранга", max_length=50)
    role_id = discord.ui.TextInput(label="Discord role_id", placeholder="123456789012345678", max_length=32)
    sort_order = discord.ui.TextInput(label="Порядок (sort_order)", placeholder="0", max_length=10, required=False)

    async def on_submit(self, interaction: discord.Interaction):
        n = self.name.value.strip()
        if not n:
            return await interaction.response.send_message("❌ Пустое название.", ephemeral=True)

        role_raw = self.role_id.value.strip()
        if not role_raw.isdigit():
            return await interaction.response.send_message("❌ role_id должен быть числом.", ephemeral=True)
        role_id = int(role_raw)

        so_raw = self.sort_order.value.strip()
        so = int(so_raw) if so_raw.lstrip("-").isdigit() else 0

        await execute(
            "INSERT INTO ranks(name, role_id, min_contracts, sort_order, guild_id) VALUES(?, ?, 0, ?, ?)",
            (n, role_id, so, str(interaction.guild.id) if interaction.guild else None)
        )
      
        await interaction.response.send_message("✅ Ранг добавлен.", ephemeral=True)

class RankEditModal(discord.ui.Modal, title="Изменить ранг"):
    def __init__(self, rank_row: dict):
        super().__init__(timeout=300)
        self.rank_row = rank_row

        # поля с дефолтами из БД
        self.name = discord.ui.TextInput(
            label="Название ранга",
            max_length=50,
            default=str(rank_row["name"] or "")
        )
        self.role_id = discord.ui.TextInput(
            label="Discord role_id",
            placeholder="123456789012345678",
            max_length=32,
            default=str(rank_row["role_id"] or "")
        )
        self.sort_order = discord.ui.TextInput(
            label="Порядок (sort_order)",
            placeholder="0",
            max_length=10,
            required=False,
            default=str(rank_row["sort_order"] or 0)
        )

        # важно: регистрировать children
        self.add_item(self.name)
        self.add_item(self.role_id)
        self.add_item(self.sort_order)

    async def on_submit(self, interaction: discord.Interaction):
        n = self.name.value.strip()
        if not n:
            return await interaction.response.send_message("❌ Пустое название.", ephemeral=True)

        role_raw = self.role_id.value.strip()
        if role_raw and not role_raw.isdigit():
            return await interaction.response.send_message("❌ role_id должен быть числом.", ephemeral=True)
        role_id = int(role_raw) if role_raw else None

        so_raw = self.sort_order.value.strip()
        so = int(so_raw) if so_raw.lstrip("-").isdigit() else 0

        rid = int(self.rank_row["id"])

        # UPDATE нескольких колонок по id
        await execute(
            """
            UPDATE ranks
            SET name = ?, role_id = ?, sort_order = ?
            WHERE id = ?
            """,
            (n, role_id, so, rid)
        )

        await interaction.response.send_message(
            f"✅ Ранг обновлён: id={rid}, name='{n}', role_id={role_id}, sort_order={so}",
            ephemeral=True
        )

class RankReqNumbersModal(discord.ui.Modal, title="Требования повышения"):
    def __init__(self, req_row: dict):
        super().__init__(timeout=300)
        self.req_row = req_row  # содержит *_family/*_tuning и main_rank_to_id и т.д.

        self.main_family = discord.ui.TextInput(
            label="MAIN: family_contracts",
            max_length=10,
            default=str(req_row.get("main_family", 0) or 0),
        )
        self.alt_family = discord.ui.TextInput(
            label="ALT: family_contracts",
            max_length=10,
            default=str(req_row.get("alt_family", 0) or 0),
        )
        self.alt_tuning = discord.ui.TextInput(
            label="ALT: tuning_contracts",
            max_length=10,
            default=str(req_row.get("alt_tuning", 0) or 0),
        )

        self.add_item(self.main_family)
        self.add_item(self.alt_family)
        self.add_item(self.alt_tuning)

    async def on_submit(self, interaction: discord.Interaction):
        if not self.main_family.value.strip().isdigit():
            return await interaction.response.send_message("❌ MAIN family должен быть числом.", ephemeral=True)
        if not self.alt_family.value.strip().isdigit():
            return await interaction.response.send_message("❌ ALT family должен быть числом.", ephemeral=True)
        if not self.alt_tuning.value.strip().isdigit():
            return await interaction.response.send_message("❌ ALT tuning должен быть числом.", ephemeral=True)

        main_f = int(self.main_family.value.strip())
        alt_f  = int(self.alt_family.value.strip())
        alt_t  = int(self.alt_tuning.value.strip())

        rf = int(self.req_row["rank_from_id"])

        # rank_to берём из MAIN rank_to; если его ещё нет — считаем линейно по sort_order
        rt = self.req_row.get("main_rank_to_id")
        if rt:
            rt = int(rt)
        else:
            so = int(self.req_row.get("sort_order") or 0)
            _gid2 = str(interaction.guild.id) if interaction.guild else None
            nxt = await fetch_one("SELECT id FROM ranks WHERE sort_order=? AND (? IS NULL OR guild_id = ?) LIMIT 1", (so + 1, _gid2, _gid2))
            if not nxt:
                return await interaction.response.send_message("❌ Не найден следующий ранг (sort_order+1).", ephemeral=True)
            rt = int(nxt["id"])

        # перезаписываем правило для rank_from
        await execute("DELETE FROM rank_requirements_main WHERE rank_from=?", (rf,))
        await execute(
            "INSERT INTO rank_requirements_main(rank_from, rank_to, family_contracts) VALUES(?,?,?)",
            (rf, rt, main_f),
        )

        await execute("DELETE FROM rank_requirements_alt WHERE rank_from=?", (rf,))
        await execute(
            "INSERT INTO rank_requirements_alt(rank_from, rank_to, family_contracts, tuning_contracts) VALUES(?,?,?,?)",
            (rf, rt, alt_f, alt_t),
        )

        from_name = self.req_row.get("rank_from_name") or "?"
        to_name = self.req_row.get("main_rank_to_name") or "следующий"
        await interaction.response.send_message(
            f"✅ {from_name} → {to_name}: MAIN fam={main_f}; ALT fam={alt_f}, tun={alt_t}.",
            ephemeral=True
        )

class RankReqSelect(discord.ui.Select):
    def __init__(self, rows):
        self.rows_by_id = {str(r["rank_from_id"]): r for r in rows}


        options = []
        for i, r in enumerate(rows[:25], start=1):
            to_name = r.get("main_rank_to_name") or "—"
            label = f"{i}. {r.get('rank_from_name','?')} → {to_name}"


            desc = f"MAIN fam={r.get('main_family',0)} | ALT fam={r.get('alt_family',0)} tun={r.get('alt_tuning',0)}"
            options.append(discord.SelectOption(
                label=label[:100],
                description=desc[:100],
                value=str(r["rank_from_id"])
            ))


        super().__init__(placeholder="Выбери ранг…", min_values=1, max_values=1, options=options)


    async def callback(self, interaction: discord.Interaction):
        rid = self.values[0]
        row = self.rows_by_id.get(rid)
        if not row:
            return await interaction.response.send_message("❌ Ранг не найден.", ephemeral=True)


        await interaction.response.send_modal(RankReqNumbersModal(row))

class RankSelect(discord.ui.Select):
    def __init__(self, rows, action: str):
        self.rows_by_id = {str(r["id"]): r for r in rows}
        self.action = action

        options = []
        for i, r in enumerate(rows[:25], start=1):
            label = f"{i}. {r['name']}"
            desc = f"min={r['min_contracts']} order={r['sort_order']}"
            options.append(discord.SelectOption(label=label[:100], description=desc[:100], value=str(r["id"])))


        super().__init__(placeholder="Выбери ранг…", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        rid = self.values[0]
        row = self.rows_by_id.get(rid)
        if not row:
            await interaction.response.send_message("❌ Ранг не найден.", ephemeral=True)
            return

        if self.action == "edit":
            await interaction.response.send_modal(RankEditModal(row))
            return

        if self.action == "delete":
            _todel = await fetch_one("SELECT guild_id FROM ranks WHERE id = ?", (int(row["id"]),))
            if interaction.guild and _todel and _todel.get("guild_id") and str(_todel["guild_id"]) != str(interaction.guild.id):
                return await interaction.response.send_message("❌ Этот ранг с другого сервера.", ephemeral=True)
            await execute("DELETE FROM ranks WHERE id = ?", (int(row["id"]),))
            rows = await fetch_ranks(str(interaction.guild.id) if interaction.guild else None)
            await interaction.response.edit_message(embed=ranks_embed(rows), view=RanksView())
            return
        


class RanksView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="🔄 Обновить", style=discord.ButtonStyle.secondary)
    async def refreshbtn(self, interaction: discord.Interaction, button: discord.ui.Button):
        rows = await fetch_ranks(str(interaction.guild.id) if interaction.guild else None)
        await interaction.response.edit_message(embed=ranks_embed(rows), view=RanksView())

    @discord.ui.button(label="➕ Добавить", style=discord.ButtonStyle.success)
    async def addbtn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RankAddModal())

    @discord.ui.button(label="📈 Требования", style=discord.ButtonStyle.primary)
    async def reqbtn(self, interaction: discord.Interaction, button: discord.ui.Button):
        rows = await fetch_rank_requirements_rows(str(interaction.guild.id) if interaction.guild else None)
        if not rows:
            return await interaction.response.send_message("Ранги пустые.", ephemeral=True)
    
        v = discord.ui.View(timeout=300)
        v.add_item(RankReqSelect(rows))
        await interaction.response.edit_message(embed=ranks_embed(await fetch_ranks(str(interaction.guild.id) if interaction.guild else None)), view=v)

    @discord.ui.button(label="✏️ Изменить", style=discord.ButtonStyle.primary)
    async def editbtn(self, interaction: discord.Interaction, button: discord.ui.Button):
        rows = await fetch_ranks(str(interaction.guild.id) if interaction.guild else None)
        if not rows:
            await interaction.response.send_message("Ранги пустые.", ephemeral=True)
            return
        v = discord.ui.View(timeout=300)
        v.add_item(RankSelect(rows, action="edit"))
        await interaction.response.edit_message(embed=ranks_embed(rows), view=v)

    @discord.ui.button(label="🗑 Удалить", style=discord.ButtonStyle.danger)
    async def delbtn(self, interaction: discord.Interaction, button: discord.ui.Button):
        rows = await fetch_ranks(str(interaction.guild.id) if interaction.guild else None)
        if not rows:
            await interaction.response.send_message("Ранги пустые.", ephemeral=True)
            return
        v = discord.ui.View(timeout=300)
        v.add_item(RankSelect(rows, action="delete"))
        await interaction.response.edit_message(embed=ranks_embed(rows), view=v)

    @discord.ui.button(label="🔄 Ранг вручную", style=discord.ButtonStyle.primary)
    async def manualrankbtn(self, interaction: discord.Interaction, button: discord.ui.Button):
        rows = await fetch_ranks(str(interaction.guild.id) if interaction.guild else None)  # у тебя уже есть helper [file:934]
        v = ManualRankSetView(rows)
        await interaction.response.edit_message(embed=v.build_embed(), view=v)

    @discord.ui.button(label="⬅️ Назад", style=discord.ButtonStyle.secondary)
    async def backbtn(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="⚙️ Настройки", description="Выбери что поменять:", color=0x808080)
        await interaction.response.edit_message(embed=embed, view=AdminSettingsView())



class RankApplyOneModal(discord.ui.Modal, title="Применить ранг одному"):
    user_id = discord.ui.TextInput(
        label="Пользователь (ID или @упоминание)",
        placeholder="123... или <@123...>",
        max_length=64
    )


class SetStaticModal(discord.ui.Modal, title="Установить статик"):
    userid = discord.ui.TextInput(label="Discord ID или @упоминание", placeholder="123... или @user", required=True, max_length=64)
    static = discord.ui.TextInput(label="Static", placeholder="например: 12345", required=True, max_length=64)

    async def on_submit(self, interaction: discord.Interaction):
        uid = parse_user_id(self.userid.value)  # у тебя уже есть parseuserid/parseuserids в файле [file:1469]
        if not uid:
            await interaction.response.send_message("Не смог распарсить пользователя.", ephemeral=True)
            return

        st = (self.static.value or "").strip()
        if not st:
            await interaction.response.send_message("Статик не должен быть пустым.", ephemeral=True)
            return
        _sgid = str(interaction.guild.id) if interaction.guild else None

        row = await fetch_one("SELECT static FROM users WHERE discord_id = ? AND (? IS NULL OR guild_id = ?)", (str(uid), _sgid, _sgid))
        old = (row["static"] if row and "static" in row.keys() else (row[0] if row else None))
        old = (old or "").strip()

        if row:
            await execute("UPDATE users SET static = ? WHERE discord_id = ? AND (? IS NULL OR guild_id = ?)", (st, str(uid), _sgid, _sgid))
        else:
            await execute("INSERT INTO users (discord_id, guild_id, static) VALUES (?, ?, ?)", (str(uid), _sgid or "", st))

        if old:
            await interaction.response.send_message(f"Готово. `{uid}`: `{old}` → `{st}`", ephemeral=True)
        else:
            await interaction.response.send_message(f"Готово. `{uid}` static = `{st}`", ephemeral=True)



    async def on_submit(self, interaction: discord.Interaction):
        uid = parse_user_id(self.user_id.value)
        if not uid:
            await interaction.response.send_message("❌ Введи ID или @упоминание пользователя.", ephemeral=True)
            return
        if not interaction.guild:
            await interaction.response.send_message("❌ Команда доступна только на сервере.", ephemeral=True)
            return

        member = interaction.guild.get_member(uid)
        if not member:
            try:
                member = await interaction.guild.fetch_member(uid)
            except discord.NotFound:
                member = None
            except discord.Forbidden:
                await interaction.response.send_message("❌ Нет прав fetch_member.", ephemeral=True)
                return

        if not member:
            await interaction.response.send_message("❌ Пользователь не найден на сервере.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        res = await apply_rank_to_member(interaction.guild, member)
        if not res["ok"]:
            await interaction.followup.send(f"❌ Не применилось: {res}", ephemeral=True)
            return

        await interaction.followup.send(
            f"✅ {member.mention}: contracts={res['cnt']}, rank={res['rank']['name']}",
            ephemeral=True
        )

async def get_user_rank_row(discord_id: str):
    return await fetch_one(
        "SELECT r.id AS rankid, r.name AS rankname, r.role_id AS role_id "
        "FROM users u "
        "LEFT JOIN ranks r ON r.id = u.current_rank_id "
        "WHERE u.discord_id = ?",
        (discord_id,),
    )



async def sync_member_rank_role(guild: discord.Guild, member: discord.Member):
    uid = str(member.id)

    rank = await fetch_one(
        """
        SELECT r.name AS rank_name, r.role_id AS role_id
        FROM users u
        LEFT JOIN ranks r ON r.id = u.current_rank_id
        WHERE u.discord_id = ?
        """,
        (uid,),
    )
    if not rank or not rank["role_id"]:
        return

    target_role_id = int(rank["role_id"])
    target_role = guild.get_role(target_role_id)
    if target_role is None:
        return

    rows = await fetch_all("SELECT role_id FROM ranks WHERE role_id IS NOT NULL", ())
    rank_role_ids = {int(x["role_id"]) for x in rows}

    to_remove = [r for r in member.roles if r.id in rank_role_ids and r.id != target_role.id]
    if to_remove:
        await member.remove_roles(*to_remove, reason="Rank sync from DB")

    if target_role not in member.roles:
        await member.add_roles(target_role, reason="Rank sync from DB")

    
    
    
# ====== PRICES (SMART SEARCH + PAGINATION) ======
    
async def fetch_prices():
    return await fetch_all(
        "SELECT item_key, price FROM prices ORDER BY item_key ASC",
        ()
    )


def prices_embed(rows):
    if not rows:
        return discord.Embed(title="💲 Цены", description="Прайс пуст.", color=0x808080)

    lines = [f"{r['item_key']} = {r['price']}" for r in rows]
    text = "\n".join(lines)
    if len(text) > 3500:
        text = text[:3500] + "\n..."
    return discord.Embed(title="💲 Цены", description="```" + text + "```", color=0x808080)


class PriceUpsertModal(discord.ui.Modal, title="Установить цену"):
    item_key = discord.ui.TextInput(label="item_key", placeholder="например: goods_loading", max_length=100)
    price = discord.ui.TextInput(label="price", placeholder="например: 123.45", max_length=32)

    async def on_submit(self, interaction: discord.Interaction):
        k = self.item_key.value.strip()
        if not k:
            await interaction.response.send_message("❌ item_key пустой.", ephemeral=True)
            return

        p_raw = self.price.value.strip().replace(",", ".")
        try:
            p = float(p_raw)
        except ValueError:
            await interaction.response.send_message("❌ price должно быть числом.", ephemeral=True)
            return
        if p < 0:
            await interaction.response.send_message("❌ price не может быть отрицательной.", ephemeral=True)
            return

        await execute(
            "INSERT OR REPLACE INTO prices(item_key, price) VALUES(?, ?)",
            (k, p)
        )

        rows = await fetch_prices()
        await interaction.response.edit_message(embed=prices_embed(rows), view=PricesView())


class PriceEditModal(discord.ui.Modal):
    def __init__(self, item_key: str, old_price):
        super().__init__(title=f"Изменить цену: {item_key}")
        self.item_key_val = item_key
        self.price = discord.ui.TextInput(label="Новая цена", default=str(old_price), max_length=32)
        self.add_item(self.price)

    async def on_submit(self, interaction: discord.Interaction):
        p_raw = self.price.value.strip().replace(",", ".")
        try:
            p = float(p_raw)
        except ValueError:
            await interaction.response.send_message("❌ price должно быть числом.", ephemeral=True)
            return
        if p < 0:
            await interaction.response.send_message("❌ price не может быть отрицательной.", ephemeral=True)
            return

        await execute(
            "UPDATE prices SET price=? WHERE item_key=?",
            (p, self.item_key_val)
        )

        rows = await fetch_prices()
        await interaction.response.edit_message(embed=prices_embed(rows), view=PricesView())


class PriceActionsView(discord.ui.View):
    def __init__(self, item_key: str, price):
        super().__init__(timeout=300)
        self.item_key = item_key
        self.price = price

    @discord.ui.button(label="✏️ Изменить", style=discord.ButtonStyle.primary)
    async def edit_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(PriceEditModal(self.item_key, self.price))

    @discord.ui.button(label="🗑 Удалить", style=discord.ButtonStyle.danger)
    async def del_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await execute("DELETE FROM prices WHERE item_key = ?", (self.item_key,))
        rows = await fetch_prices()
        await interaction.response.edit_message(embed=prices_embed(rows), view=PricesView())

    @discord.ui.button(label="⬅️ Назад", style=discord.ButtonStyle.secondary)
    async def back_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        rows = await fetch_prices()
        await interaction.response.edit_message(embed=prices_embed(rows), view=PricesView())


PAGE_SIZE = 25  # select limit [web:1148]


async def count_prices_smart(q: str) -> int:
    q = (q or "").strip()
    if not q:
        return 0
    q_esc = escape_like(q)
    contains = f"%{q_esc}%"
    row = await fetch_one(
        "SELECT COUNT(*) AS cnt FROM prices WHERE item_key LIKE ? ESCAPE '\\'",
        (contains,)
    )
    return int(row["cnt"] or 0)


async def search_prices_page(q: str, page: int):
    q = (q or "").strip()
    if not q:
        return []

    q_esc = escape_like(q)
    exact = q
    prefix = f"{q_esc}%"
    contains = f"%{q_esc}%"
    offset = max(0, int(page)) * PAGE_SIZE

    sql = """
    SELECT item_key, price
    FROM prices
    WHERE item_key LIKE ? ESCAPE '\\'
    ORDER BY
      CASE
        WHEN item_key = ? THEN 0
        WHEN item_key LIKE ? ESCAPE '\\' THEN 1
        ELSE 2
      END,
      LENGTH(item_key) ASC,
      item_key ASC
    LIMIT ? OFFSET ?;
    """
    return await fetch_all(sql, (contains, exact, prefix, PAGE_SIZE, offset))


class PriceSearchSelect(discord.ui.Select):
    def __init__(self, rows):
        self.by_key = {r["item_key"]: r for r in rows}

        options = []
        for r in rows[:25]:
            label = r["item_key"]
            desc = f"price={r['price']}"
            options.append(discord.SelectOption(label=str(label)[:100], description=str(desc)[:100], value=str(label)))

        super().__init__(placeholder="Выбери позицию…", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        key = self.values[0]
        row = self.by_key.get(key)
        if not row:
            await interaction.response.send_message("❌ Позиция не найдена.", ephemeral=True)
            return

        embed = discord.Embed(
            title="💲 Цена: выбранная позиция",
            description=f"`{key}` = **{row['price']}**\nВыбери действие:",
            color=0x808080
        )
        await interaction.response.edit_message(embed=embed, view=PriceActionsView(key, row["price"]))


class PriceSearchResultsView(discord.ui.View):
    def __init__(self, query: str, page: int, total: int, rows):
        super().__init__(timeout=300)
        self.query = query
        self.page = page
        self.total = total

        self.add_item(PriceSearchSelect(rows))

        last_page = max(0, (total - 1) // PAGE_SIZE)
        self.first_btn.disabled = (page <= 0)
        self.prev_btn.disabled = (page <= 0)
        self.next_btn.disabled = (page >= last_page)
        self.last_btn.disabled = (page >= last_page)

    async def _go(self, interaction: discord.Interaction, new_page: int):
        new_page = max(0, int(new_page))
        rows = await search_prices_page(self.query, new_page)
        pages = max(1, (self.total + PAGE_SIZE - 1) // PAGE_SIZE)

        embed = prices_embed(rows)
        embed.title = f"🔎 '{self.query}' — стр. {new_page+1}/{pages} (всего: {self.total})"
        await interaction.response.edit_message(
            embed=embed,
            view=PriceSearchResultsView(self.query, new_page, self.total, rows)
        )

    @discord.ui.button(label="⏮️", style=discord.ButtonStyle.secondary)
    async def first_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._go(interaction, 0)

    @discord.ui.button(label="⬅️", style=discord.ButtonStyle.secondary)
    async def prev_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._go(interaction, self.page - 1)

    @discord.ui.button(label="➡️", style=discord.ButtonStyle.secondary)
    async def next_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._go(interaction, self.page + 1)

    @discord.ui.button(label="⏭️", style=discord.ButtonStyle.secondary)
    async def last_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        last_page = max(0, (self.total - 1) // PAGE_SIZE)
        await self._go(interaction, last_page)

    @discord.ui.button(label="⬅️ Назад", style=discord.ButtonStyle.secondary)
    async def back_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        rows = await fetch_prices()
        await interaction.response.edit_message(embed=prices_embed(rows), view=PricesView())


class PriceSearchModal(discord.ui.Modal, title="Поиск по item_key"):
    query = discord.ui.TextInput(
        label="Часть item_key",
        placeholder="минимум 2 символа, например: ore_",
        max_length=100,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        q = (self.query.value or "").strip()
        if len(q) < 2:
            await interaction.response.send_message("Введи минимум 2 символа.", ephemeral=True)
            return

        total = await count_prices_smart(q)
        if total <= 0:
            await interaction.response.send_message("Ничего не найдено.", ephemeral=True)
            return

        page = 0
        rows = await search_prices_page(q, page)

        pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        embed = prices_embed(rows)
        embed.title = f"🔎 '{q}' — стр. 1/{pages} (всего: {total})"

        await interaction.response.edit_message(
            embed=embed,
            view=PriceSearchResultsView(q, page, total, rows)
        )


class PricesView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="🔄 Обновить", style=discord.ButtonStyle.secondary)
    async def refresh_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        rows = await fetch_prices()
        await interaction.response.edit_message(embed=prices_embed(rows), view=PricesView())

    @discord.ui.button(label="➕ Добавить/обновить", style=discord.ButtonStyle.success)
    async def upsert_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(PriceUpsertModal())

    @discord.ui.button(label="🔎 Поиск", style=discord.ButtonStyle.secondary)
    async def search_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(PriceSearchModal())

    @discord.ui.button(label="⬅️ Назад", style=discord.ButtonStyle.secondary)
    async def back_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="⚙️ Настройки", description="Выбери что поменять:", color=0x808080)
        await interaction.response.edit_message(embed=embed, view=AdminSettingsView())


class SetStaticValueModal(discord.ui.Modal, title="Static"):
    static = discord.ui.TextInput(label="Static", placeholder="например: 12345", required=True, max_length=64)

    def __init__(self, parent_view: "SetStaticView"):
        super().__init__()
        self.parent_view = parent_view

    async def on_submit(self, interaction: discord.Interaction):
        st = (self.static.value or "").strip()
        if not st:
            await interaction.response.send_message("Статик не должен быть пустым.", ephemeral=True)
            return

        self.parent_view.static_value = st
        await interaction.response.edit_message(embed=self.parent_view.build_embed(), view=self.parent_view)


class SetStaticView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.selected_user_id: int | None = None
        self.static_value: str | None = None

        self.user_select = discord.ui.UserSelect(placeholder="Выбери пользователя", min_values=1, max_values=1)
        self.user_select.callback = self.on_user_selected
        self.add_item(self.user_select)

    def build_embed(self) -> discord.Embed:
        e = discord.Embed(title="Установить static", color=0x808080)
        e.add_field(name="User", value=str(self.selected_user_id) if self.selected_user_id else "Не выбран", inline=False)
        e.add_field(name="Static", value=self.static_value if self.static_value else "Не задан", inline=False)
        return e

    async def on_user_selected(self, interaction: discord.Interaction):
        self.selected_user_id = self.user_select.values[0].id
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="Ввести static", style=discord.ButtonStyle.primary)
    async def enter_static(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SetStaticValueModal(self))

    @discord.ui.button(label="Сохранить", style=discord.ButtonStyle.success)
    async def save(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.selected_user_id:
            await interaction.response.send_message("Сначала выбери пользователя.", ephemeral=True)
            return
        st = (self.static_value or "").strip()
        if not st:
            await interaction.response.send_message("Сначала задай static.", ephemeral=True)
            return
        _sg = str(interaction.guild.id) if interaction.guild else None

        row = await fetch_one("SELECT static FROM users WHERE discord_id = ? AND (? IS NULL OR guild_id = ?)", (str(self.selected_user_id), _sg, _sg))
        old = None
        if row:
            # подстрой под то, что возвращает твой fetch_one (dict/tuple)
            old = (row.get("static") if hasattr(row, "get") else row[0])
            old = (old or "").strip()

        if row:
            await execute("UPDATE users SET static = ? WHERE discord_id = ? AND (? IS NULL OR guild_id = ?)", (st, str(self.selected_user_id), _sg, _sg))
        else:
            await execute("INSERT INTO users (discord_id, guild_id, static) VALUES (?, ?, ?)", (str(self.selected_user_id), _sg or "", st))

        if old:
            await interaction.response.send_message(f"Готово: `{old}` → `{st}`", ephemeral=True)
        else:
            await interaction.response.send_message(f"Готово: `{st}`", ephemeral=True)

    @discord.ui.button(label="Назад", style=discord.ButtonStyle.secondary)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="Настройки", description="...", color=0x808080)
        await interaction.response.edit_message(embed=embed, view=AdminSettingsView())


class StaticPickUserModal(discord.ui.Modal, title="Пользователь"):
    user = discord.ui.TextInput(label="Discord ID или @упоминание", required=True, max_length=64)

    def __init__(self, parent: "SetStaticScreen"):
        super().__init__()
        self.parent = parent

    async def on_submit(self, interaction: discord.Interaction):
        uid = parse_user_id(self.user.value)  # твой helper через _
        if not uid:
            await interaction.response.send_message("Не смог распарсить пользователя.", ephemeral=True)
            return
        self.parent.user_id = uid
        await interaction.response.edit_message(embed=self.parent.embed(), view=self.parent)


class StaticValueModal(discord.ui.Modal, title="Static"):
    static = discord.ui.TextInput(label="Static", required=True, max_length=64)

    def __init__(self, parent: "SetStaticScreen"):
        super().__init__()
        self.parent = parent

    async def on_submit(self, interaction: discord.Interaction):
        st = (self.static.value or "").strip()
        if not st:
            await interaction.response.send_message("Статик не должен быть пустым.", ephemeral=True)
            return
        self.parent.static_value = st
        await interaction.response.edit_message(embed=self.parent.embed(), view=self.parent)


class SetStaticScreen(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.user_id: int | None = None
        self.static_value: str | None = None

    def embed(self):
        e = discord.Embed(title="Установить static", color=0x808080)
        e.add_field(name="User", value=str(self.user_id) if self.user_id else "Не выбран", inline=False)
        e.add_field(name="Static", value=self.static_value or "Не задан", inline=False)
        return e

    @discord.ui.button(label="Выбрать пользователя", style=discord.ButtonStyle.secondary)
    async def pick_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(StaticPickUserModal(self))

    @discord.ui.button(label="Ввести static", style=discord.ButtonStyle.primary)
    async def pick_static(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(StaticValueModal(self))

    @discord.ui.button(label="Сохранить", style=discord.ButtonStyle.success)
    async def save(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.user_id:
            await interaction.response.send_message("Сначала выбери пользователя.", ephemeral=True)
            return
        st = (self.static_value or "").strip()
        if not st:
            await interaction.response.send_message("Сначала задай static.", ephemeral=True)
            return
        _sg2 = str(interaction.guild.id) if interaction.guild else None

        row = await fetch_one("SELECT static FROM users WHERE discord_id = ? AND (? IS NULL OR guild_id = ?)", (str(self.user_id), _sg2, _sg2))
        old = ""
        if row:
            old = (row.get("static") if hasattr(row, "get") else row[0]) or ""
            old = old.strip()

        if row:
            await execute("UPDATE users SET static = ? WHERE discord_id = ? AND (? IS NULL OR guild_id = ?)", (st, str(self.user_id), _sg2, _sg2))
        else:
            await execute("INSERT INTO users (discord_id, guild_id, static) VALUES (?, ?, ?)", (str(self.user_id), _sg2 or "", st))

        msg = f"Готово. `{self.user_id}`: `{old}` → `{st}`" if old else f"Готово. `{self.user_id}` static = `{st}`"
        await interaction.response.send_message(msg, ephemeral=True)


class ManualRankSetView(discord.ui.View):
    def __init__(self, rank_rows: list[dict]):
        super().__init__(timeout=300)

        self.selected_user_id: int | None = None
        self.selected_rank_id: int | None = None

        def _so(r: dict) -> int:
            return int(r.get("sortorder") or r.get("sort_order") or 0)

        # 1) сортировка + кэши
        self.rank_rows = sorted(rank_rows, key=lambda r: (_so(r), int(r.get("id") or 0)))
        self.rank_by_id = {str(r["id"]): r for r in self.rank_rows}

        # 2) options ДЕЛАЕМ ОДИН РАЗ + display map (1..N)
        self.display_by_id: dict[str, str] = {}
        options: list[discord.SelectOption] = []

        for idx, r in enumerate(self.rank_rows[:25], start=1):
            rid = str(r["id"])
            disp = f"{idx}. {r['name']}"
            self.display_by_id[rid] = disp

            options.append(
                discord.SelectOption(
                    label=disp,  # <-- вот это увидишь в списке
                    value=rid,   # <-- это уйдёт в on_rank (id)
                    description=f"min={r.get('mincontracts', 0)} db_order={_so(r)}"[:100],
                )
            )

        # 3) UserSelect
        self.user_select = discord.ui.UserSelect(
            placeholder="Выбери пользователя",
            min_values=1,
            max_values=1
        )
        self.user_select.callback = self.on_user
        self.add_item(self.user_select)

        # 4) Rank Select (ВАЖНО: НЕ пересоздаём options ещё раз)
        self.rank_select = discord.ui.Select(
            placeholder="Выбери ранг",
            min_values=1,
            max_values=1,
            options=options
        )
        self.rank_select.callback = self.on_rank
        self.add_item(self.rank_select)

    def build_embed(self) -> discord.Embed:
        e = discord.Embed(title="Изменение ранга вручную", color=0x3498DB)

        e.add_field(
            name="Пользователь",
            value=(f"<@{self.selected_user_id}>" if self.selected_user_id else "—"),
            inline=True
        )

        if self.selected_rank_id:
            rid = str(self.selected_rank_id)
            rank_text = self.display_by_id.get(rid, rid)  # <-- 1..N + name (как в меню)
        else:
            rank_text = "—"

        e.add_field(name="Ранг", value=rank_text, inline=True)
        return e

    async def on_user(self, interaction: discord.Interaction):
        self.selected_user_id = self.user_select.values[0].id
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    async def on_rank(self, interaction: discord.Interaction):
        self.selected_rank_id = int(self.rank_select.values[0])

        rid = str(self.selected_rank_id)
        self.rank_select.placeholder = f"Выбран: {self.display_by_id.get(rid, rid)}"

        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="Применить", style=discord.ButtonStyle.success)
    async def apply(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.guild:
            await interaction.response.send_message("❌ Сервер недоступен.", ephemeral=True)
            return
        if not self.selected_user_id or not self.selected_rank_id:
            await interaction.response.send_message("❌ Выбери пользователя и ранг.", ephemeral=True)
            return
        _mgg = str(interaction.guild.id)

        await interaction.response.defer(ephemeral=True)

        old = await fetch_one(
            "SELECT u.current_rank_id AS rank_id, r.name AS rank_name "
            "FROM users u LEFT JOIN ranks r ON r.id = u.current_rank_id "
            "WHERE u.discord_id = ? AND (? IS NULL OR u.guild_id = ?)",
            (str(self.selected_user_id), _mgg, _mgg),
        )
        old_name = (old["rank_name"] if old and old.get("rank_name") else "—")

        await execute(
            "UPDATE users SET current_rank_id=? WHERE discord_id=? AND (? IS NULL OR guild_id = ?)",
            (int(self.selected_rank_id), str(self.selected_user_id), _mgg, _mgg),
        )

        member = interaction.guild.get_member(self.selected_user_id) or await interaction.guild.fetch_member(self.selected_user_id)

        rank_roles = []
        for r in self.rank_rows:
            rid = r.get("role_id") or r.get("roleid")
            if rid:
                rank_roles.append(int(rid))

        to_remove = [role for role in member.roles if role.id in set(rank_roles)]
        if to_remove:
            await member.remove_roles(*to_remove, reason="Ранг изменён вручную (admin panel)")

        new_rank = self.rank_by_id.get(str(self.selected_rank_id))
        new_role_id = None
        if new_rank:
            new_role_id = new_rank.get("role_id") or new_rank.get("roleid")

        if new_role_id:
            new_role = interaction.guild.get_role(int(new_role_id))
            if new_role and new_role not in member.roles:
                await member.add_roles(new_role, reason="Ранг изменён вручную (admin panel)")

        new_name = (new_rank["name"] if new_rank and new_rank.get("name") else str(self.selected_rank_id))

        log = discord.Embed(title="📝 Ранг изменён вручную", color=0x9B59B6)
        log.add_field(name="Пользователь", value=f"<@{self.selected_user_id}>\n`{self.selected_user_id}`", inline=True)
        log.add_field(name="Админ", value=f"<@{interaction.user.id}>\n`{interaction.user.id}`", inline=True)
        log.add_field(name="Было", value=old_name, inline=True)
        log.add_field(name="Стало", value=new_name, inline=True)

        await audit_promotions(interaction.client, log)

        await interaction.followup.send(f"✅ Готово: ранг обновлён на **{new_name}**.", ephemeral=True)

    @discord.ui.button(label="Назад", style=discord.ButtonStyle.secondary)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        rows = await fetch_ranks(str(interaction.guild.id) if interaction.guild else None)
        await interaction.response.edit_message(embed=ranks_embed(rows), view=RanksView())

ADMIN_HUB_CH_KEY = "admin_hub_channel_id"
ADMIN_HUB_MSG_KEY = "admin_hub_message_id"


class AdminPanel(commands.Cog):
    PANEL_CH_KEY = "profile_panel_channel_id"
    PANEL_MSG_KEY = "profile_panel_message_id"

    def __init__(self, bot):
        self.bot = bot
        # Регистрируем persistent view для админ-хаба
        self.bot.add_view(AdminHubView())

    def cog_unload(self):
        pass


    @app_commands.command(name="admin", description="Открыть админ-панель")
    @app_commands.guilds(*GUILD_OBJECTS)
    @admin_roles_check(get_setting)
    async def admin_panel(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        view = AdminMainView()
        embed = discord.Embed(title="🔧 Админ-панель", color=0x9B7BFF)
        embed.description = "Выберите раздел:"
        await interaction.edit_original_response(embed=embed, view=view, content=None)

    @app_commands.command(name="admin_hub", description="Создать сообщение админ-панели в канале")
    @app_commands.guilds(*GUILD_OBJECTS)
    @admin_roles_check(get_setting)
    async def admin_hub(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)

        embed = await build_admin_hub_embed(interaction.guild)
        msg = await channel.send(embed=embed, view=AdminHubView())

        # Сохраняем id для автообновления
        await set_setting(ADMIN_HUB_CH_KEY, str(channel.id))
        await set_setting(ADMIN_HUB_MSG_KEY, str(msg.id))

        await interaction.edit_original_response(
            content=f"✅ Хаб создан: {msg.jump_url}",
            embed=None,
            view=None
        )


    @app_commands.command(name="profile_panel", description="Создать/обновить общую панель профиля")
    @app_commands.guilds(*GUILD_OBJECTS)
    @admin_roles_check(get_setting)
    async def profile_panel(self, interaction: discord.Interaction, channel: discord.TextChannel | None = None):
        await interaction.response.defer(ephemeral=True)

        if channel is None:
            channel = interaction.channel

        embed = await build_public_panel_embed(interaction.guild)
        view = PublicProfilePanelView()

        msg_id = await get_setting(self.PANEL_MSG_KEY)
        if msg_id:
            try:
                msg = await channel.fetch_message(int(msg_id))
                await msg.edit(embed=embed, view=view)
                await set_setting(self.PANEL_CH_KEY, str(channel.id))
                await interaction.edit_original_response(content="Панель обновлена.")
                return
            except discord.NotFound:
                pass

        msg = await channel.send(embed=embed, view=view)
        await set_setting(self.PANEL_CH_KEY, str(channel.id))
        await set_setting(self.PANEL_MSG_KEY, str(msg.id))
        await interaction.edit_original_response(content="Панель создана и сохранена.")

    @app_commands.command(name="prices_ui", description="Интерактивные цены по категориям")
    @app_commands.guilds(*GUILD_OBJECTS)
    @admin_roles_check(get_setting)
    async def prices_ui(self, interaction: discord.Interaction):
        view = PricesCategoriesView()
        embed = await view.build_embed()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        view.message = await interaction.original_response()
    
    @app_commands.command(name="post_prices", description="Опубликовать прайс-эмбед в этот канал")
    @app_commands.guilds(*GUILD_OBJECTS)
    @admin_roles_check(get_setting)
    async def post_prices(self, interaction: discord.Interaction):
        from services.prices_panel import ensure_panel, CH_KEY
        from database import set_setting as db_set_setting
        guild = interaction.guild
        if guild is None:
            return await interaction.response.send_message("❌ Только на сервере.", ephemeral=True)
        await db_set_setting(CH_KEY, str(interaction.channel.id), str(guild.id))
        status = await ensure_panel(interaction.client, guild, build_prices_embed)
        await interaction.response.send_message(
            f"✅ Панель: {status}. Дальше обновляется сама.", ephemeral=True)
    

    @app_commands.command(name="refresh_prices", description="Обновить ранее опубликованный прайс-эмбед")
    @app_commands.guilds(*GUILD_OBJECTS)
    @admin_roles_check(get_setting)
    async def refresh_prices(self, interaction: discord.Interaction):
        from services.prices_panel import ensure_panel
        guild = interaction.guild
        if guild is None:
            return await interaction.response.send_message("❌ Только на сервере.", ephemeral=True)
        status = await ensure_panel(interaction.client, guild, build_prices_embed)
        await interaction.response.send_message(f"✅ Панель: {status}.", ephemeral=True)


    @app_commands.command(name="set_price", description="Установить цену: item_key -> price")
    @app_commands.guilds(*GUILD_OBJECTS)
    @app_commands.checks.has_permissions(administrator=True)
    async def set_price(self, interaction: discord.Interaction, item_key: str, price: float):
        item_key = item_key.strip()
        if not item_key:
            await interaction.response.send_message("❌ item_key пустой.", ephemeral=True)
            return
        if price < 0:
            await interaction.response.send_message("❌ price не может быть отрицательной.", ephemeral=True)
            return

        await execute(
            "INSERT OR REPLACE INTO prices(item_key, price) VALUES(?, ?)",
            (item_key, float(price))
        )
        await interaction.response.send_message(f"✅ Цена установлена: `{item_key}` = **{price}**", ephemeral=True)

    @app_commands.command(name="prices", description="Показать все цены")
    @app_commands.guilds(*GUILD_OBJECTS)
    @admin_roles_check(get_setting)
    async def prices(self, interaction: discord.Interaction):
        rows = await fetch_all("SELECT item_key, price FROM prices ORDER BY item_key ASC", ())
        if not rows:
            await interaction.response.send_message("Прайс пуст. Используй `/set_price`.", ephemeral=True)
            return

        lines = [f"{r['item_key']} = {r['price']}" for r in rows]
        text = "\n".join(lines)

        if len(text) <= 1800:
            embed = discord.Embed(title="Цены", description=f"```{text}```", color=0x95A5A6)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        cut = text[:1800]
        embed = discord.Embed(title="Цены (часть списка)", description=f"```{cut}```", color=0x95A5A6)
        embed.set_footer(text="Список длинный — позже сделаем пагинацию кнопками.")
        await interaction.response.send_message(embed=embed, ephemeral=True)


    @app_commands.command(name="promo_submit", description="Подать отчёт на повышение (main/alt)")
    @app_commands.guilds(*GUILD_OBJECTS)
    async def promo_submit(self, interaction: discord.Interaction, system: str):
        system = (system or "").lower().strip()
        if system not in ("main", "alt"):
            await interaction.response.send_message("system должен быть main или alt", ephemeral=True)
            return
    
        await interaction.response.defer(ephemeral=True)
    
        discord_id = str(interaction.user.id)
    
        res = await create_promo_report_and_post(discord_id, system)
        if not res.get("ok"):
            await interaction.followup.send(res.get("reason", "Ошибка"), ephemeral=True)
            return
    
        report_id = int(res["report_id"])
        postres = await post_promo_report_message(interaction.client, report_id)
        if not postres.get("ok"):
            await interaction.followup.send(f"Репорт создан #{report_id}, но не смог запостить в канал: {postres['reason']}", ephemeral=True)
            return
    
        await interaction.followup.send(f"✅ Репорт создан #{report_id} и отправлен в канал.", ephemeral=True)

    @app_commands.command(name="set_log_contracts", description="Канал логов контрактов")
    @app_commands.guilds(*GUILD_OBJECTS)
    @app_commands.checks.has_permissions(administrator=True)
    async def set_log_contracts(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)
        await set_setting("log_contracts", str(channel.id))
        await interaction.followup.send(f"✅ Логи контрактов: {channel.mention}", ephemeral=True)
    
    @app_commands.command(name="set_log_bonus", description="Канал логов бонусов")
    @app_commands.guilds(*GUILD_OBJECTS)
    @app_commands.checks.has_permissions(administrator=True)
    async def set_log_bonus(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)
        await set_setting("log_bonus", str(channel.id))
        await interaction.followup.send(f"✅ Логи бонусов: {channel.mention}", ephemeral=True)
    
    @app_commands.command(name="set_log_promo", description="Канал логов промо")
    @app_commands.guilds(*GUILD_OBJECTS)
    @app_commands.checks.has_permissions(administrator=True)
    async def set_log_promo(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)
        await set_setting("log_promo", str(channel.id))
        await interaction.followup.send(f"✅ Логи промо: {channel.mention}", ephemeral=True)
    

    @app_commands.command(name="bonus_export", description="Экспорт одобренных премий за неделю (TXT)")
    @app_commands.guilds(*GUILD_OBJECTS)
    @app_commands.choices(week=[
        app_commands.Choice(name="Текущая неделя", value="current"),
        app_commands.Choice(name="Прошлая неделя", value="previous")
    ])
    @admin_roles_check(get_setting)
    async def bonus_export(self, interaction: discord.Interaction, week: str = "current"):
        await self.bonus_export_impl(interaction, week=week)
    
    
    async def bonus_export_impl(self, interaction: discord.Interaction, week: str = "current"):
        if week == "previous":
            week_start, week_end = prev_week_range_msk()
        else:
            week_start, week_end = week_range_msk()
        
        rows = await fetch_all(
            """
            SELECT
              br.discord_id,
              (COALESCE(live.base_sum, 0) + COALESCE(br.sea_amount, 0)) AS total_amount,
              u.static
            FROM bonus_reports br
            LEFT JOIN users u ON u.discord_id = br.discord_id
            LEFT JOIN (
              SELECT
                discord_id,
                COALESCE(SUM(calc_price), 0) AS base_sum
              FROM v_contract_value
              WHERE confirm_status = 'APPROVED'
                AND date(msk_date_iso) >= date(?)
                AND date(msk_date_iso) <= date(?)
              GROUP BY discord_id
            ) live ON live.discord_id = br.discord_id
            WHERE br.status = 'APPROVED'
              AND br.week_start = ?
              AND br.week_end = ?
            ORDER BY total_amount DESC
            """,
            (week_start, week_end, week_start, week_end)
        )
        
        if not rows:
            await interaction.response.send_message(
                f"Нет одобренных премий за неделю {week_start} — {week_end}.",
                ephemeral=True
            )
            return
        
        total_sum = 0
        missing_static = 0
        lines = []
        
        for r in rows:
            st = (r["static"] or "").strip()
            if not st:
                st = "NO_STATIC"
                missing_static += 1
            
            amount = float(r["total_amount"] or 0)
            amount_int = int(round(amount))  # округляем до целого
            total_sum += amount_int
            lines.append(f"{st};{amount_int};{week_start}-{week_end}")
        
        # 1. статик;общая сумма;СУММА_ЗА_НЕДЕЛЮ (целое число)
        # 2. Премия за неделю ДАТА_НАЧАЛА — ДАТА_КОНЦА  
        # 3. ПУСТАЯ_СТРОКА
        header = [
            f"statik;общая сумма;{total_sum}",  # ← ЦЕЛОЕ число
            f"Премия за неделю {week_start} — {week_end}",
            ""
        ]
        
        content = "\n".join(header + lines)
        data = io.BytesIO(content.encode("utf-8"))
        filename = f"bonus_{week_start}_to_{week_end}.txt"
        
        await interaction.response.send_message(
            content=f"Готово: {len(rows)} человек, общая сумма **{total_sum}**. Без static: {missing_static}.",
            file=discord.File(fp=data, filename=filename),
            ephemeral=True
        )


    @app_commands.command(name="bonus_generate", description="Сформировать премии за неделю (для всех)")
    @app_commands.guilds(*GUILD_OBJECTS)
    @admin_roles_check(get_setting)
    async def bonus_generate(self, interaction: discord.Interaction, week: Literal["current", "previous"] = "current"):
        if week == "previous":
            week_start, week_end = prev_week_range_msk()
        else:
            week_start, week_end = week_range_msk()

        gid = str(interaction.guild.id) if interaction.guild else None
        ch_val = (await get_setting("bonus_log_channel_id", gid)) or ""
        if not ch_val:
            brow = await fetch_one("SELECT value FROM settings WHERE key = 'bonus_channel_id'", ())
            ch_val = ((brow or {}).get("value")) or ""
        channel_id = int(ch_val) if str(ch_val).strip().isdigit() else None
        if not channel_id:
            await interaction.response.send_message("❌ Не задан канал премий.", ephemeral=True)
            return

        channel = interaction.client.get_channel(channel_id)
        if not channel:
            await interaction.response.send_message("❌ Канал премий не найден.", ephemeral=True)
            return

        candidates = await fetch_all(
            """
            SELECT discord_id
            FROM v_contract_value
            WHERE date(msk_date_iso) >= date(?)
              AND date(msk_date_iso) <= date(?)
            GROUP BY discord_id
            HAVING COALESCE(SUM(calc_price), 0) > 0
            """,
            (week_start, week_end)
        )
        # v_contract_value без guild_id: оставляем только участников текущего сервера
        if interaction.guild is not None:
            try:
                member_ids = {str(m.id) for m in interaction.guild.members}
                candidates = [r for r in candidates if str(r["discord_id"]) in member_ids]
            except Exception:
                pass
    
        created = 0
        updated = 0
        skipped_exists = 0
        skipped_empty = 0
        skipped_no_static = 0
    
        await interaction.response.send_message(
            f"Старт генерации премий за {week_start} — {week_end}. Кандидатов: {len(candidates)}",
            ephemeral=True
        )
    
        for row in candidates:
            uid = row["discord_id"]
            res = await create_bonus_report_for_week(uid, gid, week_start, week_end)
    
            if not res.get("ok"):
                reason = res.get("reason")
    
                if reason == "already_exists":
                    skipped_exists += 1
                    continue
    
                if reason == "no_contracts":
                    skipped_empty += 1
                    continue
    
                if reason == "no_static":
                    skipped_no_static += 1
                    continue
    
                continue
    
            # Если отчёт был обновлён (статус NEW) — НЕ шлём новый эмбед (чтобы не спамить канал)
            if res.get("updated"):
                updated += 1
                continue
    
            created += 1
            report_id = res["report_id"]
            calc = res["calc"]
    
            embed = discord.Embed(title=f"Отчёт на премию #{report_id}", color=0x2ECC71)
            embed.add_field(name="Пользователь", value=f"<@{uid}>", inline=True)
            embed.add_field(name="Неделя", value=f"{week_start} — {week_end} (МСК)", inline=True)
            embed.add_field(name="Сумма (без 'Дары моря')", value=str(round(calc["total"], 2)), inline=False)
            embed.set_footer(
                text="В Админ панели: возьмите в работу и одобрите/отклоните. "
                     "Сумма за выплату контракта 'Дары моря' добавляются вручную."
            )
    
            await channel.send(embed=embed)
    
        await interaction.followup.send(
            f"Готово. Создано новых: {created}. Обновлено NEW: {updated}. "
            f"Пропущено (уже было/в работе): {skipped_exists}. "
            f"Пропущено (пусто): {skipped_empty}. Пропущено (нет static): {skipped_no_static}.",
            ephemeral=True
        )


    @app_commands.command(name="bonus_delete", description="Удалить отчёт премии по report_id")
    @app_commands.guilds(*GUILD_OBJECTS)
    @admin_roles_check(get_setting)
    async def bonus_delete(self, interaction: discord.Interaction, report_id: int):
        res = await delete_bonus_report(report_id)
        if not res["ok"]:
            await interaction.response.send_message("❌ Не найден report_id.", ephemeral=True)
            return
        await interaction.response.send_message(f"✅ Отчёт премии #{report_id} удалён.", ephemeral=True)

    @app_commands.command(name="pending_now", description="Обновить счётчик PENDING сейчас")
    @app_commands.guilds(*GUILD_OBJECTS)
    @admin_roles_check(get_setting)
    async def pending_now(self, interaction: discord.Interaction):
        row = await fetch_one(
            "SELECT COUNT(*) AS cnt FROM contracts WHERE confirm_status='PENDING'",
            ()
        )
        cnt = int(row["cnt"] or 0)

        content = f"⏳ Не рассмотренных контрактов: {cnt}"
        await upsert_pending_counter_message(self.bot, content)

        await interaction.response.send_message("✅ Счётчик обновлён.", ephemeral=True)

    @app_commands.command(name="set_pending_channel", description="Задать канал для счётчика PENDING")
    @app_commands.guilds(*GUILD_OBJECTS)
    @app_commands.checks.has_permissions(administrator=True)
    async def set_pending_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await set_setting("pending_channel_id", str(channel.id))
        await execute("DELETE FROM settings WHERE key = ?", ("pending_counter_message_id",))
        await interaction.response.send_message(f"✅ Канал счётчика: {channel.mention}", ephemeral=True)

    @app_commands.command(name="set_pending_role", description="Задать роль для пинга PENDING (если нужно)")
    @app_commands.guilds(*GUILD_OBJECTS)
    @app_commands.checks.has_permissions(administrator=True)
    async def set_pending_role(self, interaction: discord.Interaction, role: discord.Role):
        await set_setting("pending_ping_role_id", str(role.id))
        await interaction.response.send_message(f"✅ Роль пинга: {role.mention}", ephemeral=True)

    @app_commands.command(name="pending_settings", description="Показать настройки PENDING")
    @app_commands.guilds(*GUILD_OBJECTS)
    @admin_roles_check(get_setting)
    async def pending_settings(self, interaction: discord.Interaction):
        ch = await get_setting("pending_channel_id")
        rr = await get_setting("pending_ping_role_id")
        await interaction.response.send_message(
            f"pending_channel_id: {ch}\npending_ping_role_id: {rr}",
            ephemeral=True
        )

    @app_commands.command(name="clear_pending_role", description="Выключить роль пинга для PENDING")
    @app_commands.guilds(*GUILD_OBJECTS)
    @app_commands.checks.has_permissions(administrator=True)
    async def clear_pending_role(self, interaction: discord.Interaction):
        await execute("DELETE FROM settings WHERE key = ?", ("pending_ping_role_id",))
        await interaction.response.send_message("✅ Роль пинга отключена.", ephemeral=True)

    @app_commands.command(name="set_audit_channel", description="Установить канал логов")
    @app_commands.guilds(*GUILD_OBJECTS)
    @app_commands.checks.has_permissions(administrator=True)
    async def set_audit_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await interaction.response.defer(ephemeral=True)
        await set_setting("audit_log_channel_id", str(channel.id))
        await interaction.followup.send(f"✅ Канал логов: {channel.mention}", ephemeral=True)

    @app_commands.command(name="sync", description="Синхронизировать slash-команды (owner)")
    @app_commands.guilds(*GUILD_OBJECTS)
    async def sync_slash(self, interaction: discord.Interaction):
        if interaction.user.id != 335065897398042626 :
            await interaction.response.send_message("Нет прав.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        guild = discord.Object(id=GUILD_ID)
        synced = await self.bot.tree.sync(guild=guild)
        await interaction.followup.send(f"✅ Synced: {len(synced)}", ephemeral=True)
        
    @app_commands.command(name="admin_roles", description="Показать разрешённые админ-роли")
    @app_commands.guilds(*GUILD_OBJECTS)
    @admin_roles_check(get_setting)
    async def admin_roles(self, interaction: discord.Interaction):
        raw = await get_setting("admin_role_ids")
        await interaction.response.send_message(f"admin_role_ids = {raw}", ephemeral=True)


    @app_commands.command(name="add_admin_role")
    @app_commands.checks.has_permissions(administrator=True)
    async def add_admin_role(self, interaction: discord.Interaction, role: discord.Role):
        raw = await get_setting("admin_role_ids")
        ids = parse_admin_role_ids(str(raw or "[]"))
        ids.add(role.id)
        await set_setting("admin_role_ids", dump_admin_role_ids(ids))
        await interaction.response.send_message(f"✅ Добавил {role.mention}", ephemeral=True)
    
    @app_commands.command(name="remove_admin_role")
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_admin_role(self, interaction: discord.Interaction, role: discord.Role):
        raw = await get_setting("admin_role_ids")
        ids = parse_admin_role_ids(str(raw or "[]"))
        ids.discard(role.id)
        await set_setting("admin_role_ids", dump_admin_role_ids(ids))
        await interaction.response.send_message(f"✅ Убрал {role.mention}", ephemeral=True)
        
        
    @app_commands.command(name="ranks", description="Показать ранги")
    @app_commands.guilds(*GUILD_OBJECTS)
    @admin_roles_check(get_setting)
    async def ranks_list(self, interaction: discord.Interaction):
        _gid = str(interaction.guild.id) if interaction.guild else None
        rows = await fetch_all(
            "SELECT id, name, role_id, min_contracts, sort_order FROM ranks WHERE (? IS NULL OR guild_id = ?) ORDER BY min_contracts ASC, sort_order ASC",
            (_gid, _gid)
        )
        if not rows:
            await interaction.response.send_message("Ранги пустые.", ephemeral=True)
            return
    
        lines = [f"{r['id']}. {r['name']} | role_id={r['role_id']} | min={r['min_contracts']} | order={r['sort_order']}" for r in rows]
        await interaction.response.send_message("```" + "\n".join(lines) + "```", ephemeral=True)

    @app_commands.command(name="rank_add", description="Добавить ранг")
    @app_commands.guilds(*GUILD_OBJECTS)
    @app_commands.checks.has_permissions(administrator=True)
    async def rank_add(self, interaction: discord.Interaction, name: str, role: discord.Role, min_contracts: int, sort_order: int = 0):
        name = name.strip()
        if not name:
            await interaction.response.send_message("❌ Пустое имя.", ephemeral=True)
            return
        if min_contracts < 0:
            await interaction.response.send_message("❌ min_contracts < 0.", ephemeral=True)
            return
    
        await execute(
            "INSERT INTO ranks(name, role_id, min_contracts, sort_order, guild_id) VALUES(?, ?, ?, ?, ?)",
            (name, int(role.id), int(min_contracts), int(sort_order),
             str(interaction.guild.id) if interaction.guild else None)
        )
        await interaction.response.send_message(f"✅ Ранг добавлен: {name} -> {role.mention}", ephemeral=True)
        
    @app_commands.command(name="rank_del", description="Удалить ранг по id")
    @app_commands.guilds(*GUILD_OBJECTS)
    @app_commands.checks.has_permissions(administrator=True)
    async def rank_del(self, interaction: discord.Interaction, rank_id: int):
        _todel = await fetch_one("SELECT guild_id FROM ranks WHERE id = ?", (int(rank_id),))
        if interaction.guild and _todel and _todel.get("guild_id") and str(_todel["guild_id"]) != str(interaction.guild.id):
            return await interaction.response.send_message("❌ Этот ранг с другого сервера.", ephemeral=True)
        await execute("DELETE FROM ranks WHERE id = ?", (int(rank_id),))
        await interaction.response.send_message(f"✅ Удалено: rank_id={rank_id}", ephemeral=True)
        
    @app_commands.command(name="rank_apply", description="Применить ранг пользователю (по контрактам)")
    @app_commands.guilds(*GUILD_OBJECTS)
    @app_commands.checks.has_permissions(administrator=True)
    async def rank_apply(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.defer(ephemeral=True)
        res = await apply_rank_to_member(interaction.guild, member)
        if not res["ok"]:
            await interaction.followup.send(f"❌ Не применилось: {res}", ephemeral=True)
            return
        await interaction.followup.send(f"✅ {member.mention}: contracts={res['cnt']}, rank={res['rank']['name']}", ephemeral=True)



    @app_commands.command(name="rank_apply_all", description="Применить ранги всем участникам (долго)")
    @app_commands.guilds(*GUILD_OBJECTS)
    @app_commands.checks.has_permissions(administrator=True)
    async def rank_apply_all(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
    
        ok = 0
        fail = 0
        for m in interaction.guild.members:
            if m.bot:
                continue
            res = await apply_rank_to_member(interaction.guild, m)
            if res["ok"]:
                ok += 1
            else:
                fail += 1
    
        await interaction.followup.send(f"✅ Готово. OK={ok}, FAIL={fail}", ephemeral=True)
        
    @app_commands.command(name="setstatic", description="Установить статик пользователю")
    @app_commands.guilds(*GUILD_OBJECTS)
    @admin_roles_check(get_setting)  # или твой декоратор
    async def setstatic(self, interaction: discord.Interaction, user: discord.Member, static: str):
        st = (static or "").strip()
        if not st:
            await interaction.response.send_message("Статик не должен быть пустым.", ephemeral=True)
            return
        _sg3 = str(interaction.guild.id) if interaction.guild else None

        row = await fetch_one(
            "SELECT static FROM users WHERE discord_id = ? AND (? IS NULL OR guild_id = ?)",
            (str(user.id), _sg3, _sg3),
        )
        old = (row["static"] if row and "static" in row.keys() else (row[0] if row else None))  # на случай dict/tuple
        old = (old or "").strip()

        if row:
            await execute("UPDATE users SET static = ? WHERE discord_id = ? AND (? IS NULL OR guild_id = ?)", (st, str(user.id), _sg3, _sg3))
        else:
            await execute("INSERT INTO users (discord_id, guild_id, static) VALUES (?, ?, ?)", (str(user.id), _sg3 or "", st))
        
        if old:
            msg = f"Ок. {user.mention} static: `{old}` → `{st}`"
        else:
            msg = f"Ок. {user.mention} static = `{st}`"
        
        await interaction.response.send_message(msg, ephemeral=True)

class AdminSyncRanksView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="🔎 Dry-run синк рангов", style=discord.ButtonStyle.secondary)
    async def preview_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.guild:
            return await interaction.response.send_message("❌ Сервер недоступен.", ephemeral=True)
        if not (isinstance(interaction.user, discord.Member) and interaction.user.guild_permissions.administrator):
            return await interaction.response.send_message("❌ Только админ.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        res = await preview_sync_all_ranks(interaction.guild)

        sample_txt = "\n".join([f"- <@{uid}> -> rank_id={rid} (so={so})" for uid, rid, so in res["samples"]]) or "—"
        await interaction.followup.send(
            f"Dry-run (без записи):\n"
            f"Будет записано/обновлено: {res['would_set']}\n"
            f"Без ранговых ролей: {res['no_rank_role']}\n"
            f"Примеры:\n{sample_txt}",
            ephemeral=True
        )

    @discord.ui.button(label="✅ Запустить синк (в БД)", style=discord.ButtonStyle.success)
    async def run_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.guild:
            return await interaction.response.send_message("❌ Сервер недоступен.", ephemeral=True)
        if not (isinstance(interaction.user, discord.Member) and interaction.user.guild_permissions.administrator):
            return await interaction.response.send_message("❌ Только админ.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        res = await sync_all_ranks_db_only(interaction.guild)

        await interaction.followup.send(
            f"✅ Готово.\n"
            f"Записано/обновлено: {res['synced']}\n"
            f"Без ранговых ролей: {res['no_rank_role']}",
            ephemeral=True
        )

    @discord.ui.button(label="⬅️ Назад в настройки", style=discord.ButtonStyle.secondary)
    async def back_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(view=AdminSettingsView())



class BonusMenuView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="📋 Рассмотрение премий", style=discord.ButtonStyle.secondary)
    async def review_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await show_bonus_reports(interaction)

    @discord.ui.button(label="⚙️ Инструменты (экспорт/генерация)", style=discord.ButtonStyle.success)
    async def tools_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="💰 Премии — инструменты", description="Выбери действие:", color=0x2ECC71)
        await interaction.response.edit_message(embed=embed, view=BonusToolsView())

    @discord.ui.button(label="⬅️ Назад", style=discord.ButtonStyle.secondary)
    async def back_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="🔧 Админ-панель", description="Выберите раздел:", color=0x9B7BFF)
        await interaction.response.edit_message(embed=embed, view=AdminMainView())


class BonusToolsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    def _get_admin_cog(self, interaction: discord.Interaction):
        return interaction.client.get_cog("AdminPanel")

    @discord.ui.button(label="⚙️ Генерация (текущая неделя)", style=discord.ButtonStyle.success)
    async def gen_current(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = self._get_admin_cog(interaction)
        if not cog:
            await interaction.response.send_message("❌ Cog AdminPanel не найден.", ephemeral=True)
            return
        await cog.bonus_generate.callback(cog, interaction, week="current")

    @discord.ui.button(label="⚙️ Генерация (прошлая неделя)", style=discord.ButtonStyle.success)
    async def gen_prev(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = self._get_admin_cog(interaction)
        if not cog:
            await interaction.response.send_message("❌ Cog AdminPanel не найден.", ephemeral=True)
            return
        await cog.bonus_generate.callback(cog, interaction, week="previous")

    @discord.ui.button(label="📤 Экспорт (текущая неделя)", style=discord.ButtonStyle.primary)
    async def export_current(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = self._get_admin_cog(interaction)
        if not cog:
            await interaction.response.send_message("❌ Cog AdminPanel не найден.", ephemeral=True)
            return
        await cog.bonus_export_impl(interaction, week="current")
    
    @discord.ui.button(label="📤 Экспорт (прошлая неделя)", style=discord.ButtonStyle.primary)
    async def export_prev(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = self._get_admin_cog(interaction)
        if not cog:
            await interaction.response.send_message("❌ Cog AdminPanel не найден.", ephemeral=True)
            return
        await cog.bonus_export_impl(interaction, week="previous")

    @discord.ui.button(label="⬅️ Назад", style=discord.ButtonStyle.secondary)
    async def back_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="💰 Премии", description="Выбери раздел:", color=0x2ECC71)
        await interaction.response.edit_message(embed=embed, view=BonusMenuView())


class AdminHubView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def has_admin_roles(self, member: discord.Member) -> bool:
        """Админ: Discord-админ, legacy admin_role_ids или панельная роль admin/owner."""
        if member.guild_permissions.administrator:
            return True
        role_ids = await get_admin_role_ids()  # твоя функция из services
        if role_ids:
            member_roles = {role.id for role in member.roles}
            if bool(member_roles & set(role_ids)):
                return True
        try:
            row = await fetch_one(
                "SELECT role FROM permissions WHERE guild_id = ? AND discord_id = ?",
                (str(member.guild.id), str(member.id)),
            )
            if row and row.get("role") in ("admin", "owner"):
                return True
        except Exception:
            pass
        return False

    @discord.ui.button(
        label="🔧 Открыть админ-панель",
        style=discord.ButtonStyle.primary,
        custom_id="admin_hub_open"
    )
    async def open_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message("❌ Только участники сервера.", ephemeral=True)

        if not await self.has_admin_roles(interaction.user):
            return await interaction.response.send_message("❌ У вас нет нужных ролей.", ephemeral=True)

        embed = discord.Embed(
            title="🔧 Админ-панель",
            description="Выберите раздел:",
            color=0x9B7BFF
        )

        await interaction.response.send_message(embed=embed, view=AdminMainView(), ephemeral=True)

    @discord.ui.button(
        label="🔄 Обновить счётчики",
        style=discord.ButtonStyle.secondary,
        custom_id="admin_hub_refresh"
    )
    async def refresh_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message("❌ Только участники сервера.", ephemeral=True)

        if not await self.has_admin_roles(interaction.user):
            return await interaction.response.send_message("❌ У вас нет нужных ролей.", ephemeral=True)

        embed = await build_admin_hub_embed(interaction.guild)
        await interaction.response.edit_message(embed=embed, view=self)


        
class AdminMainView(View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="📋 Подтверждение контрактов", style=discord.ButtonStyle.primary, custom_id="admin_contracts")
    async def confirm_contracts_btn(self, interaction: discord.Interaction, button: Button):
        await show_pending_contracts(interaction)

    @discord.ui.button(label="📊 Рассмотрение отчётов", style=discord.ButtonStyle.secondary, custom_id="admin_reports")
    async def review_reports_btn(self, interaction: discord.Interaction, button: Button):
        await show_promo_reports(interaction)
        
    @discord.ui.button(label="💰 Премии", style=discord.ButtonStyle.success, custom_id="admin_bonus")
    async def bonus_btn(self, interaction: discord.Interaction, button: Button):
        embed = discord.Embed(title="💰 Премии", description="Выбери раздел:", color=0x2ECC71)
        await interaction.response.edit_message(embed=embed, view=BonusMenuView())

    @discord.ui.button(label="⏱ КД контрактов", style=discord.ButtonStyle.primary, custom_id="admin_cooldowns")
    async def contract_cooldowns_btn(self, interaction: discord.Interaction, button: Button):
        await show_global_cooldowns(interaction, AdminMainView)

    @discord.ui.button(label="📣 Пинг контрактов", style=discord.ButtonStyle.primary)
    async def contracts_ping_btn(self, interaction: discord.Interaction, button: Button):
        from cogs.contracts_ping import show_contracts_ping
        await show_contracts_ping(interaction)

    @discord.ui.button(label="📕Списать по Contract ID", style=discord.ButtonStyle.danger)
    async def void_contract_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(VoidByIdModal())

    @discord.ui.button(label="⚙️ Настройки", style=discord.ButtonStyle.secondary, custom_id="admin_settings")
    async def settings_btn(self, interaction: discord.Interaction, button: Button):
        embed = discord.Embed(title="⚙️ Настройки", color=0x808080)
        embed.description = "Выбери что поменять:"
        await interaction.response.edit_message(embed=embed, view=AdminSettingsView())

class AdminSettingsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="🔑Роли админов", style=discord.ButtonStyle.primary)
    async def btn_admin_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not (isinstance(interaction.user, discord.Member) and interaction.user.guild_permissions.administrator):
            await interaction.response.send_message("❌ Только администратор Discord может менять роли админов.", ephemeral=True)
            return
    
        await interaction.response.send_modal(SetJsonRoleIdsModal())

    @discord.ui.button(label="📝Канал для отчетов на повышения", style=discord.ButtonStyle.secondary)
    async def btnpromoch(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SetChannelIdModal("promochannelid", "promochannelid"))

    @discord.ui.button(label="📗Канал логов", style=discord.ButtonStyle.secondary)
    async def btn_audit(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SetChannelIdModal("audit_log_channel_id", "audit_log_channel_id"))

    @discord.ui.button(label="📕Канал ожидания контрактов", style=discord.ButtonStyle.secondary)
    async def btn_pending_ch(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SetChannelIdModal("pending_channel_id", "pending_channel_id"))

    @discord.ui.button(label="🗒️Роль пинга для контрактов", style=discord.ButtonStyle.secondary)
    async def btn_pending_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SetRoleIdModal("pending_ping_role_id", "pending_ping_role_id"))

    @discord.ui.button(label="🏷️ Ранги", style=discord.ButtonStyle.secondary)
    async def btn_ranks(self, interaction: discord.Interaction, button: discord.ui.Button):
        rows = await fetch_ranks(str(interaction.guild.id) if interaction.guild else None)
        await interaction.response.edit_message(embed=ranks_embed(rows), view=RanksView())

    @discord.ui.button(label="💲 Цены", style=discord.ButtonStyle.secondary)
    async def btn_prices(self, interaction: discord.Interaction, button: discord.ui.Button):
        rows = await fetch_prices()
        await interaction.response.edit_message(embed=prices_embed(rows), view=PricesView())

    @discord.ui.button(label="👥Set static", style=discord.ButtonStyle.secondary)
    async def btn_set_static(self, interaction: discord.Interaction, button: discord.ui.Button):
        v = SetStaticView()
        await interaction.response.edit_message(embed=v.build_embed(), view=v)

    @discord.ui.button(label="🔄 Синк рангов из ролей", style=discord.ButtonStyle.secondary)
    async def btn_sync_ranks(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not (isinstance(interaction.user, discord.Member) and interaction.user.guild_permissions.administrator):
            return await interaction.response.send_message("❌ Только админ.", ephemeral=True)
    
        embed = discord.Embed(
            title="🔄 Синк рангов",
            description="Dry-run ничего не пишет. Запуск — обновит users.current_rank_id по ролям (max sort_order).",
            color=0x95A5A6
        )
        await interaction.response.edit_message(embed=embed, view=AdminSyncRanksView())

    @discord.ui.button(label="📨 Панель заявок", style=discord.ButtonStyle.success)
    async def btn_applications_panel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not (isinstance(interaction.user, discord.Member) and interaction.user.guild_permissions.administrator):
            await interaction.response.send_message("❌ Только админ.", ephemeral=True)
            return

        # 1) достаём URL сайта из settings
        row = await fetch_one("SELECT value FROM settings WHERE key=?", ("applications_apply_url",))
        apply_url = (row["value"] if row and row.get("value") else "").strip()
        if not apply_url.startswith("http"):
            await interaction.response.send_message(
                "❌ Не задан applications_apply_url. Сначала задай ссылку на сайт заявок.",
                ephemeral=True
            )
            return
    
        # 2) постим в канал подачи
        ch = interaction.guild.get_channel(1386755575592914974) or await interaction.guild.fetch_channel(1386755575592914974)
    
        e = discord.Embed(
            title="Заявка в семью",
            description="Нажми кнопку ниже, авторизуйся через Discord и заполни форму.",
            color=0x2ECC71
        )
    
        v = discord.ui.View(timeout=None)
        v.add_item(discord.ui.Button(label="Подать заявку", url=apply_url))
    
        await ch.send(embed=e, view=v)
        await interaction.response.send_message("✅ Панель заявок опубликована.", ephemeral=True)

    @discord.ui.button(label="🌐 Ссылка на сайт заявок", style=discord.ButtonStyle.secondary)
    async def btn_apply_url(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not (isinstance(interaction.user, discord.Member) and interaction.user.guild_permissions.administrator):
            await interaction.response.send_message("❌ Только админ.", ephemeral=True)
            return
        await interaction.response.send_modal(SetTextSettingModal("applications_apply_url", "URL сайта заявок"))

    @discord.ui.button(label="🎭 Роли заявок", style=discord.ButtonStyle.secondary)
    async def btn_app_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not (isinstance(interaction.user, discord.Member) and interaction.user.guild_permissions.administrator):
            await interaction.response.send_message("❌ Только админ.", ephemeral=True)
            return
    
        v = ApplicationsRolesView()
        await v._load()  # <-- ВАЖНО: загрузить из settings перед build_embed()
    
        await interaction.response.edit_message(
            content=None,
            embed=v.build_embed(),
            view=v
        )

    @discord.ui.button(label="📣 Роль пинга заявок", style=discord.ButtonStyle.secondary)
    async def btn_apps_ping_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SetRoleIdModal("applications_ping_role_id", "applications_ping_role_id"))

    @discord.ui.button(label="⏱️ Канал уведомлений КД", style=discord.ButtonStyle.secondary)
    async def btn_cd_notify_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(
            SetChannelIdModal("contracts_cd_notify_channel_id", "contracts_cd_notify_channel_id")
        )

    @discord.ui.button(label="🔔 Роль уведомлений КД", style=discord.ButtonStyle.secondary)
    async def btn_cd_notify_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(
            SetRoleIdModal("contracts_cd_notify_role_id", "contracts_cd_notify_role_id")
        )

    @discord.ui.button(label="📣 Канал пинга контрактов", style=discord.ButtonStyle.secondary)
    async def btn_contracts_ping_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(
            SetChannelIdModal("contracts_ping_channel_id", "contracts_ping_channel_id")
        )
    
    @discord.ui.button(label="📣 Роль пинга контрактов", style=discord.ButtonStyle.secondary)
    async def btn_contracts_ping_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(
            SetRoleIdModal("contracts_ping_role_id", "contracts_ping_role_id")
        )

    @discord.ui.button(label="⬅️ Назад", style=discord.ButtonStyle.secondary)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="🔧 Админ-панель", description="Выберите раздел:", color=0x9B7BFF)
        await interaction.response.edit_message(embed=embed, view=AdminMainView())


class SetTextSettingModal(discord.ui.Modal):
    def __init__(self, key: str, title: str):
        super().__init__(title=title)
        self.key = key
        self.val = discord.ui.TextInput(label="Значение", style=discord.TextStyle.short, max_length=300)
        self.add_item(self.val)

    async def on_submit(self, interaction: discord.Interaction):
        value = str(self.val.value).strip()
        await execute(
            "INSERT INTO settings(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (self.key, value),
        )
        await interaction.response.send_message(f"✅ Сохранено: {self.key}", ephemeral=True)


async def show_pending_contracts(interaction: discord.Interaction, page: int = 0):
    gid = str(interaction.guild.id) if interaction.guild else None
    contracts = await fetch_all(
        "SELECT * FROM contracts WHERE confirm_status = 'PENDING' AND (? IS NULL OR guild_id = ?) ORDER BY ts DESC LIMIT 10 OFFSET ?",
        (gid, gid, page * 10)
    )

    total = await fetch_one(
        "SELECT COUNT(*) as cnt FROM contracts WHERE confirm_status = 'PENDING' AND (? IS NULL OR guild_id = ?)",
        (gid, gid))
    total_count = int(total["cnt"] or 0) if total else 0

    embed = discord.Embed(title="📋 Подтверждение контрактов", color=0x00FF00)
    view = None

    if not contracts:
        embed.description = "✅ Нет контрактов, ожидающих подтверждения"
    else:
        embed = discord.Embed(title="📋 Подтверждение контрактов", color=0xFFA500)
        embed.description = f"Всего ожидает: **{total_count}**\n\nВыберите контракт для подтверждения:"

        view = PendingContractsView(contracts, page, total_count)

        for i, contract in enumerate(contracts, start=1):
            user_mention = f"<@{contract['discord_id']}>"
            contract_type = contract["contract_type"]
            date = contract["msk_date"] or contract["ts"][:10]

            details_preview = ""
            if contract_type == "активация":
                details_preview = f"Сумма: {contract['price']}"
            elif contract_type == "дары-моря":
                details_preview = f"{contract['fish_type']} x{contract['fish_qty']}"
            elif contract_type == "металлургия-сдача":
                details_preview = f"Руда: {contract['ore_type']}"
            elif contract_type == "металлургия-добыча":
                ores = []
                if contract["m_iron"]:
                    ores.append(f"Железо {contract['m_iron']}")
                if contract["m_silver"]:
                    ores.append(f"Серебро {contract['m_silver']}")
                if contract["m_copper"]:
                    ores.append(f"Медь {contract['m_copper']}")
                if contract["m_tin"]:
                    ores.append(f"Олово {contract['m_tin']}")
                if contract["m_gold"]:
                    ores.append(f"Золото {contract['m_gold']}")
                details_preview = ", ".join(ores) if ores else "—"
            elif contract_type == "товары":
                parts = []
                if contract["goods_delivery"]:
                    parts.append("Сдача")
                if contract["goods_loading"]:
                    parts.append("Погрузка")
                details_preview = " + ".join(parts) if parts else "—"
            elif contract_type == "ателье":
                details_preview = f"Форм: {contract['atelier_total_uniforms']}"
            elif contract_type == "агитации-маркетплейс":
                details_preview = f"Ссылок: {contract['marketplace_links_count']}"
            elif contract_type == "агитации-wn":
                wn_category = contract.get("wn_category") or "—"
                wn_screenshots_count = contract.get("wn_screenshots_count", 0) or 0
                details_preview = f"{wn_category} | Скринов: {wn_screenshots_count}"
            elif contract_type == "тюнинг":
                details_preview = "Скриншот: " + ("YES" if contract["tuning_has_screenshot"] else "—")

            embed.add_field(
                name=f"{i}. {contract_type.title()} | {date}",
                value=f"Пользователь: {user_mention}\n{details_preview}\nID: `{contract['id']}`",
                inline=False
            )

    if interaction.response.is_done():
        await interaction.message.edit(embed=embed, view=view)
    else:
        await interaction.response.edit_message(embed=embed, view=view)



class BackToAdminView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="⬅ Назад", style=discord.ButtonStyle.secondary, custom_id="back_admin_empty_reports")
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="Админ-панель", description="Выберите раздел:", color=0x9B7BFF)
        await interaction.response.edit_message(embed=embed, view=AdminMainView())



class PendingContractsView(View):
    def __init__(self, contracts, page, total_count):
        super().__init__(timeout=300)
        self.contracts = contracts
        self.page = page
        self.total_count = total_count
        
        
        options = []
        for contract in contracts[:25]:
            label = f"{contract['contract_type']} | {contract['msk_date'] or contract['ts'][:10]}"
            description = f"ID: {contract['id']} | User: {contract['discord_id'][:8]}..."
            options.append(discord.SelectOption(label=label[:100], description=description[:100], value=str(contract["id"])))

        self.select = discord.ui.Select(placeholder="Выберите контракт...", options=options, custom_id="select_contract")
        self.select.callback = self.on_select
        self.add_item(self.select)

        if page > 0:
            prev_btn = Button(label="◀️ Назад", style=discord.ButtonStyle.secondary, custom_id="prev_page")
            prev_btn.callback = self.prev_page
            self.add_item(prev_btn)

        if (page + 1) * 10 < total_count:
            next_btn = Button(label="Вперёд ▶️", style=discord.ButtonStyle.secondary, custom_id="next_page")
            next_btn.callback = self.next_page
            self.add_item(next_btn)

    @discord.ui.button(
        label="⬅  Админ панель",
        style=discord.ButtonStyle.secondary,
        custom_id="back_admin_from_contracts"
    )
    async def back_to_admin(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="Админ-панель", description="Выберите раздел:", color=0x9B7BFF)
        await interaction.response.edit_message(embed=embed, view=AdminMainView())


    async def on_select(self, interaction: discord.Interaction):
        contractid = int(self.select.values[0])
        await show_contract_detail(interaction, contractid, return_page=self.page)


    async def prev_page(self, interaction: discord.Interaction):
        await show_pending_contracts(interaction, self.page - 1)

    async def next_page(self, interaction: discord.Interaction):
        await show_pending_contracts(interaction, self.page + 1)


def _clip(text: str, limit: int) -> str:
    text = "" if text is None else str(text)
    return text if len(text) <= limit else (text[:limit-3] + "...")

def _split_for_embed_fields(text: str, limit: int = 1024):
    text = "" if text is None else str(text)
    for i in range(0, len(text), limit):
        yield text[i:i+limit]

async def show_contract_detail(interaction: discord.Interaction, contract_id: int, return_page: int = 0):
    contract = await fetch_one("SELECT * FROM contracts WHERE id = ?", (contract_id,))
    if not contract:
        await interaction.response.send_message("❌ Контракт не найден", ephemeral=True)
        return

    def pack_lines(lines, limit=1024):
        chunks = []
        cur = ""
        for line in lines:
            line = str(line)
            add = (("\n" if cur else "") + line)
            if len(cur) + len(add) > limit:
                if cur:
                    chunks.append(cur)
                    cur = line
                else:
                    # если одна строка сама длиннее 1024 — обрежем (бывает у очень длинных URL)
                    chunks.append(line[:limit - 3] + "...")
                    cur = ""
            else:
                cur += add
        if cur:
            chunks.append(cur)
        return chunks

    user_mention = f"<@{contract['discord_id']}>"
    embed = discord.Embed(title=f"📄 Контракт #{contract['id']}", color=0x3498DB)

    embed.add_field(name="Тип", value=_clip(contract.get("contract_type") or "—", 1024), inline=True)
    embed.add_field(name="Пользователь", value=user_mention, inline=True)

    date_val = contract.get("msk_date") or (contract.get("ts") or "")[:10] or "—"
    embed.add_field(name="Дата (МСК)", value=_clip(date_val, 1024), inline=True)

    ct = contract.get("contract_type")
    if ct == "активация":
        embed.add_field(name="Сумма", value=_clip(str(contract.get("price", "—")), 1024), inline=False)

    elif ct == "дары-моря":
        embed.add_field(name="Рыба", value=_clip(contract.get("fish_type") or "—", 1024), inline=True)
        embed.add_field(name="Количество", value=_clip(str(contract.get("fish_qty", "—")), 1024), inline=True)

    elif ct == "металлургия-сдача":
        embed.add_field(name="Руда", value=_clip(contract.get("ore_type") or "—", 1024), inline=False)

    elif ct == "металлургия-добыча":
        ores_text = (
            f"Железо: {contract.get('m_iron', 0)}\n"
            f"Серебро: {contract.get('m_silver', 0)}\n"
            f"Медь: {contract.get('m_copper', 0)}\n"
            f"Олово: {contract.get('m_tin', 0)}\n"
            f"Золото: {contract.get('m_gold', 0)}"
        )
        embed.add_field(name="Добыча", value=_clip(ores_text, 1024), inline=False)

    elif ct == "товары":
        parts = []
        if contract.get("goods_delivery"):
            parts.append("✅ Сдача")
        if contract.get("goods_loading"):
            parts.append("✅ Погрузка")
        embed.add_field(name="Тип", value=_clip("\n".join(parts) if parts else "—", 1024), inline=False)

    elif ct == "ателье":
        embed.add_field(name="Нашито форм", value=_clip(str(contract.get("atelier_total_uniforms", "—")), 1024), inline=False)

    elif ct == "агитации-маркетплейс":
        embed.add_field(name="Количество ссылок", value=_clip(str(contract.get("marketplace_links_count", "—")), 1024), inline=False)

    elif ct == "агитации-wn":
        embed.add_field(name="Категория", value=_clip(contract.get("wn_category") or "—", 1024), inline=False)

    elif ct == "тюнинг":
        embed.add_field(name="Скриншот", value=_clip(contract.get("tuning_has_screenshot") or "—", 1024), inline=False)

    # 📎 Вложения (не рвём ссылки)
    attachment_urls = (contract.get("attachment_urls") or "").strip()
    if attachment_urls:
        urls = [u.strip() for u in attachment_urls.split("\n") if u.strip()]
        links = [f"[Скриншот {i+1}]({url})" for i, url in enumerate(urls)]
        parts = pack_lines(links, 1024)

        # не превышаем 25 полей у embed
        available = 25 - len(embed.fields)
        parts = parts[:max(0, available)]

        for idx, part in enumerate(parts):
            name = "📎 Вложения" if idx == 0 else "📎 Вложения (продолжение)"
            embed.add_field(name=name, value=part, inline=False)

    # 🔗 Сообщение Discord
    if contract.get("discord_message_id"):
        channel_id = contract.get("channel_id")
        msg_id = contract.get("discord_message_id")
        if channel_id and msg_id:
            link = f"https://discord.com/channels/{GUILD_ID}/{channel_id}/{msg_id}"
            embed.add_field(name="🔗 Сообщение Discord", value=f"[Перейти]({link})", inline=False)

    embed.set_footer(text=_clip(f"Статус: {contract.get('confirm_status', '—')}", 2048))

    view = ContractActionView(contract_id, return_page=return_page)
    await interaction.response.edit_message(embed=embed, view=view)


class ContractActionView(View):
    def __init__(self, contract_id: int = 0, return_page: int = 0):
        super().__init__(timeout=None)
        self.contract_id = contract_id
        self.return_page = return_page

    def _resolve_id(self, interaction: discord.Interaction) -> int:
        if self.contract_id:
            return int(self.contract_id)
        try:
            title = (interaction.message.embeds[0].title if interaction.message and interaction.message.embeds else "") or ""
            import re as _re
            m = _re.search(r"#(\d+)", title)
            if m:
                return int(m.group(1))
        except Exception:
            pass
        return 0

    @discord.ui.button(label="🙋 Взять", style=discord.ButtonStyle.primary, custom_id="claim_contract")
    async def claim_btn(self, interaction: discord.Interaction, button: Button):
        rid = self._resolve_id(interaction)
        if not rid:
            return await interaction.response.send_message("❌ Не нашел контракт.", ephemeral=True)
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message("❌ Только на сервере.", ephemeral=True)
        try:
            from cogs.applications import is_staff_member
            if not await is_staff_member(interaction.user):
                return await interaction.response.send_message("❌ Только стафф.", ephemeral=True)
        except Exception:
            pass
        row = await fetch_one("SELECT * FROM contracts WHERE id = ?", (rid,))
        if not row or row["confirm_status"] != "PENDING":
            return await interaction.response.send_message("❌ Контракт уже обработан.", ephemeral=True)
        if interaction.guild and row.get("guild_id") and str(row["guild_id"]) != str(interaction.guild.id):
            return await interaction.response.send_message("❌ Этот контракт с другого сервера.", ephemeral=True)
        now = datetime.utcnow().isoformat()
        await execute(
            "UPDATE contracts SET claimed_by = ?, claimed_at = ?, nudged_at = NULL WHERE id = ?",
            (str(interaction.user.id), now, rid),
        )
        try:
            from services.api_sync import queue_contract_sync
            queue_contract_sync(
                str(row.get("guild_id") or interaction.guild.id), row.get("ts"),
                row["discord_id"], row["contract_type"],
                price=row.get("price", 0), status="PENDING",
                claimed_by=str(interaction.user.id), claimed_at=now,
            )
        except Exception as e:
            print(f"[api_sync] warn: {e}")
        try:
            await interaction.response.send_message(
                f"✅ Взял контракт #{rid}. Не забудь вынести решение.", ephemeral=True)
        except Exception:
            pass

    @discord.ui.button(label="✅ Принять", style=discord.ButtonStyle.success, custom_id="approve_contract")
    async def approve_btn(self, interaction: discord.Interaction, button: Button):
        rid = self._resolve_id(interaction)
        if not rid:
            return await interaction.response.send_message("❌ Не нашел контракт.", ephemeral=True)
        await approve_contract(interaction, rid)

    @discord.ui.button(label="❌ Отклонить", style=discord.ButtonStyle.danger, custom_id="reject_contract")
    async def reject_btn(self, interaction: discord.Interaction, button: Button):
        rid = self._resolve_id(interaction)
        if not rid:
            return await interaction.response.send_message("❌ Не нашел контракт.", ephemeral=True)
        modal = RejectReasonModal(rid)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="⬅️ Назад", style=discord.ButtonStyle.secondary, custom_id="back_to_list")
    async def back_to_list(self, interaction: discord.Interaction, button: Button):
        await show_pending_contracts(interaction, page=self.return_page)

PROMO_EXCLUDED_TYPES = {
    "активация",
    "металлургия добыча",
    "агитации маркетплейс",
    "агитации wn",
}

async def mark_contract_message(client, channel_id, message_id, accepted: bool, title: str, decider_id=None):
    """Проставить статус на сообщении ревью (embed + снять кнопки)."""
    try:
        if not channel_id or not message_id:
            return False
        ch = client.get_channel(int(channel_id))
        if ch is None:
            try:
                ch = await client.fetch_channel(int(channel_id))
            except Exception:
                return False
        try:
            msg = await ch.fetch_message(int(message_id))
        except Exception:
            return False
        emb = msg.embeds[0] if msg.embeds else discord.Embed(title=title)
        emb.color = 0x2ECC71 if accepted else 0xE74C3C
        emb.add_field(name="Статус", value="✅ Принят" if accepted else "❌ Отклонен", inline=False)
        await msg.edit(embed=emb, view=None)
        try:
            who = f"<@{decider_id}>" if decider_id else ""
            await ch.send(f"{'Одобрен' if accepted else 'Отклонен'}: {who}".strip())
        except Exception:
            pass
        return True
    except Exception as e:
        print(f"[contract-mark] warn: {e}")
        return False


async def approve_contract(interaction: discord.Interaction, contract_id: int):
    contract = await fetch_one("SELECT * FROM contracts WHERE id = ?", (contract_id,))
    if not contract or contract["confirm_status"] != "PENDING":
        if interaction.response.is_done():
            await interaction.message.edit(content="❌ Контракт уже обработан или не найден", embed=None, view=None)
        else:
            await interaction.response.send_message("❌ Контракт уже обработан или не найден", ephemeral=True)
        return
    if interaction.guild and contract.get("guild_id") and str(contract["guild_id"]) != str(interaction.guild.id):
        msg = "❌ Этот контракт с другого сервера."
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)
        return

    discord_id = contract["discord_id"]
    contract_type = contract["contract_type"]

    ct = (contract_type or "").strip().lower()
    excluded = ct in PROMO_EXCLUDED_TYPES
    is_tuning = (ct == "тюнинг")
    # Личные контракты (не семейные): тюнинг + курьер еды
    is_personal = ct in ("тюнинг", "курьер-еды")

    admin_id = str(interaction.user.id)
    now = datetime.utcnow().isoformat()

    # 1) подтверждаем контракт
    await execute(
        "UPDATE contracts SET confirm_status='APPROVED', confirmed_by=?, confirmed_at=? WHERE id=?",
        (admin_id, now, contract_id)
    )

    # 1.0) статус на сообщении ревью (только для зеркал с сайта)
    try:
        _review = await fetch_one(
            "SELECT channel_id, discord_message_id, site_id FROM contracts WHERE id = ?", (contract_id,))
        if _review and _review.get("site_id") and _review.get("discord_message_id"):
            await mark_contract_message(
                interaction.client, _review["channel_id"], _review["discord_message_id"],
                True, f"Контракт #{contract_id}", decider_id=str(interaction.user.id))
    except Exception as e:
        print(f"[contract-mark] warn: {e}")

    # 1.0) синхронизация с панелью
    try:
        from services.api_sync import queue_contract_sync
        queue_contract_sync(
            contract.get("guild_id"), contract.get("ts"),
            discord_id, contract_type,
            price=contract.get("price", 0), status="APPROVED",
        )
    except Exception as e:
        print(f"[api_sync] warn: {e}")

    # 1.1) обновляем счётчик ожидания
    row = await fetch_one("SELECT COUNT(*) AS cnt FROM contracts WHERE confirm_status='PENDING'", ())
    cnt = int(row["cnt"] or 0)
    await upsert_pending_counter_message(interaction.client, f"⏳ Ожидание проверки контрактов: {cnt}")

    # 2) ensure user
    _ag = str(interaction.guild.id) if interaction.guild else (contract.get("guild_id") or "")
    user = await fetch_one("SELECT 1 AS ok FROM users WHERE discord_id = ? AND guild_id = ?", (discord_id, _ag))
    if not user:
        await execute(
            "INSERT INTO users (discord_id, guild_id, current_rank_id, family_total, tuning_total) VALUES (?, ?, NULL, 0, 0)",
            (discord_id, _ag)
        )

    credit_day = (contract.get("msk_date_iso") or "").strip()
    counted_for_promo = False

    # 3) начисление в повышение + антидубль (личные: тюнинг/курьер - в свой котел)
    if (not excluded) and credit_day:
        credit_kind = "tuning" if is_personal else "family"
        _cg = str(interaction.guild.id) if interaction.guild else (contract.get("guild_id") or "")

        if is_personal:
            # ТЮНИНГ: удаляем старые за день и добавляем новую (обходит UNIQUE)
            await execute(
                "DELETE FROM promo_credits WHERE discord_id=? AND credit_day=? AND credit_kind=? AND contract_type=? AND (? = '' OR guild_id = ? OR guild_id IS NULL)",
                (str(discord_id), credit_day, credit_kind, ct, _cg, _cg)
            )
            await execute(
                "INSERT INTO promo_credits(discord_id, credit_day, credit_kind, contract_type, contract_id, guild_id) "
                "VALUES(?,?,?,?,?,?)",
                (str(discord_id), credit_day, credit_kind, ct, int(contract_id), _cg)
            )
            counted_for_promo = True
        else:
            # FAMILY: INSERT OR IGNORE (только раз в день)
            await execute(
                "INSERT OR IGNORE INTO promo_credits(discord_id, credit_day, credit_kind, contract_type, contract_id, guild_id) "
                "VALUES(?,?,?,?,?,?)",
                (str(discord_id), credit_day, credit_kind, ct, int(contract_id), _cg)
            )
            row = await fetch_one(
                "SELECT 1 AS ok FROM promo_credits "
                "WHERE discord_id=? AND credit_day=? AND credit_kind=? AND contract_type=? AND contract_id=? AND (? = '' OR guild_id = ? OR guild_id IS NULL)",
                (str(discord_id), credit_day, credit_kind, ct, int(contract_id), _cg, _cg)
            )
            counted_for_promo = bool(row)
    
        if counted_for_promo:
            if is_personal:
                await execute("UPDATE users SET tuning_total = tuning_total + 1 WHERE discord_id = ? AND guild_id = ?", (discord_id, _ag))
            else:
                await execute("UPDATE users SET family_total = family_total + 1 WHERE discord_id = ? AND guild_id = ?", (discord_id, _ag))
                
    # 4) текст (нужен для audit/DM)
    if excluded:
        gained_text = "Не засчитывается в повышение"
    else:
        gained_text = (
            ("+1 личный" if is_personal else "+1 семейный контракт")
            if counted_for_promo
            else "В повышение уже засчитан сегодня (повтор)"
        )

    # 5) ВОЗВРАТ В СПИСОК (без followup, чтобы не ловить Unknown Webhook)
    await show_pending_contracts(interaction, page=0)

    # 6) AUDIT LOG
    log = discord.Embed(title="✅ Контракт принят", color=0x2ECC71)
    log.add_field(name="Contract ID", value=str(contract_id), inline=True)
    log.add_field(name="Type", value=str(contract_type), inline=True)
    log.add_field(name="Promo", value=gained_text, inline=True)
    log.add_field(name="Admin", value=f"{interaction.user} ({interaction.user.id})", inline=False)
    log.add_field(name="User", value=f"<@{discord_id}> ({discord_id})", inline=False)

    if contract.get("channel_id") and contract.get("discord_message_id"):
        link = f"https://discord.com/channels/{GUILD_ID}/{contract['channel_id']}/{contract['discord_message_id']}"
        log.add_field(name="Source", value=f"[Открыть]({link})", inline=False)

    # было просто: await audit_contracts(...)
    try:
        await audit_contracts(interaction.client, log)
    except Exception as e:
        # не ломаем весь флоу, но даём модератору знать, что лог не ушёл
        text = f"⚠️ Контракт принят, но не смог отправить лог: {type(e).__name__}: {e}"
        if interaction.response.is_done():
            # уже редактировали сообщение — шлём отдельным эпхемеральным
            try:
                await interaction.followup.send(text, ephemeral=True)
            except:
                pass
        else:
            try:
                await interaction.response.send_message(text, ephemeral=True)
            except:
                pass


    # 7) DM пользователю
    try:
        user_obj = await interaction.client.fetch_user(int(discord_id))
        if excluded:
            await user_obj.send(
                f"✅ Ваш контракт **{contract_type}** был принят.\n"
                f"ℹ️ Он **не засчитывается** в повышение."
            )
        else:
            await user_obj.send(
                f"✅ Ваш контракт **{contract_type}** был принят.\n"
                f"🎯 Засчитано в повышение: **{gained_text}**."
            )
    except Exception:
        pass



class RejectReasonModal(Modal, title="Причина отклонения"):
    reason_input = TextInput(
        label="Укажите причину отклонения",
        style=discord.TextStyle.paragraph,
        placeholder="Например: неверный скриншот, недостаточно данных...",
        required=True,
        max_length=500
    )

    def __init__(self, contract_id: int):
        super().__init__()
        self.contract_id = contract_id

    async def on_submit(self, interaction: discord.Interaction):
        reason = self.reason_input.value.strip()

        contract = await fetch_one("SELECT * FROM contracts WHERE id = ?", (self.contract_id,))
        if not contract or contract["confirm_status"] != "PENDING":
            if interaction.response.is_done():
                await interaction.message.edit(content="❌ Контракт уже обработан", embed=None, view=None)
            else:
                await interaction.response.send_message("❌ Контракт уже обработан", ephemeral=True)
            return

        admin_id = str(interaction.user.id)
        now = datetime.utcnow().isoformat()

        await execute(
            "UPDATE contracts SET confirm_status='REJECTED', confirmed_by=?, confirmed_at=?, reject_reason=? WHERE id=?",
            (admin_id, now, reason, self.contract_id)
        )

        # Статус на сообщении ревью (только для зеркал с сайта)
        try:
            _review = await fetch_one(
                "SELECT channel_id, discord_message_id, site_id FROM contracts WHERE id = ?", (self.contract_id,))
            if _review and _review.get("site_id") and _review.get("discord_message_id"):
                await mark_contract_message(
                    interaction.client, _review["channel_id"], _review["discord_message_id"],
                    False, f"Контракт #{self.contract_id}", decider_id=str(interaction.user.id))
        except Exception as e:
            print(f"[contract-mark] warn: {e}")

        # Синхронизация с панелью
        try:
            from services.api_sync import queue_contract_sync
            queue_contract_sync(
                contract.get("guild_id"), contract.get("ts"),
                contract["discord_id"], contract["contract_type"],
                price=contract.get("price", 0), status="REJECTED",
            )
        except Exception as e:
            print(f"[api_sync] warn: {e}")

        row = await fetch_one("SELECT COUNT(*) AS cnt FROM contracts WHERE confirm_status='PENDING'", ())
        cnt = int(row["cnt"] or 0)
        await upsert_pending_counter_message(interaction.client, f"⏳ Ожидание проверки контрактов: {cnt}")

        discord_id = contract["discord_id"]
        contract_type = contract["contract_type"]

        # Возврат в список (без followup)
        await show_pending_contracts(interaction, page=0)

        # AUDIT LOG
        log = discord.Embed(title="❌ Контракт отклонен", color=0xE74C3C)
        log.add_field(name="Contract ID", value=str(self.contract_id), inline=True)
        log.add_field(name="Type", value=str(contract_type), inline=True)
        log.add_field(name="Admin", value=f"{interaction.user} ({interaction.user.id})", inline=False)
        log.add_field(name="User", value=f"<@{discord_id}> ({discord_id})", inline=False)
        log.add_field(name="Reason", value=reason[:1000], inline=False)

        if contract.get("channel_id") and contract.get("discord_message_id"):
            link = f"https://discord.com/channels/{GUILD_ID}/{contract['channel_id']}/{contract['discord_message_id']}"
            log.add_field(name="Source", value=f"[Открыть]({link})", inline=False)

        await audit_contracts(interaction.client, log)

        try:
            user_obj = await interaction.client.fetch_user(int(discord_id))
            await user_obj.send(f"❌ Ваш контракт **{contract_type}** был отклонён.\nПричина: {reason}")
        except Exception:
            pass



# --- PROMO REPORTS (ниже твой код без изменений) ---


async def show_promo_reports(interaction: discord.Interaction, page: int = 0):
    gid = str(interaction.guild.id) if interaction.guild else None
    reports = await fetch_all(
        """SELECT pr.*, r1.name AS from_name, r2.name AS to_name
           FROM promotion_reports pr
           LEFT JOIN ranks r1 ON pr.from_rank_id = r1.id
           LEFT JOIN ranks r2 ON pr.to_rank_id = r2.id
           WHERE pr.status IN ('NEW','TAKEN')
             AND (? IS NULL OR pr.guild_id = ? OR pr.guild_id IS NULL)
           ORDER BY pr.report_id DESC
           LIMIT 10 OFFSET ?""",
        (gid, gid, page * 10)
    )
    total = await fetch_one(
        "SELECT COUNT(*) AS cnt FROM promotion_reports WHERE status IN ('NEW','TAKEN')"
        " AND (? IS NULL OR guild_id = ? OR guild_id IS NULL)",
        (gid, gid))
    total_count = total["cnt"] if total else 0

    if not reports:
        embed = discord.Embed(title="📊 Отчёты на повышение", color=0x00FF00)
        embed.description = "Нет отчётов, ожидающих рассмотрения."
        await interaction.response.edit_message(embed=embed, view=BackToAdminView())
        return


    embed = discord.Embed(title="📊 Отчёты на повышение", color=0x3498DB)
    embed.description = f"Всего в очереди: **{total_count}**"

    view = PromoReportsView(reports, page, total_count)

    for r in reports:
        user = f"<@{r['discord_id']}>"
        sys_name = "Основная" if r["system_type"] == "main" else "Альтернатива"
        status = r["status"]
        taken_by = f"<@{r['taken_by']}>" if r["taken_by"] else "—"
        embed.add_field(
            name=f"#{r['report_id']} | {r['from_name']} → {r['to_name']} | {sys_name}",
            value=f"Пользователь: {user}\nСтатус: **{status}**\nВзял в работу: {taken_by}",
            inline=False
        )

    await interaction.response.edit_message(embed=embed, view=view)





class PromoReportsView(View):
    def __init__(self, reports, page, total_count):
        super().__init__(timeout=300)
        self.reports = reports
        self.page = page
        self.total_count = total_count

        options = []
        for r in reports[:25]:
            label = f"#{r['report_id']} {r['from_name']}→{r['to_name']}"
            description = f"User: {r['discord_id']}"
            options.append(discord.SelectOption(label=label[:100], description=description[:100], value=str(r["report_id"])))
        self.select = discord.ui.Select(placeholder="Выберите отчёт...", options=options)
        self.select.callback = self.on_select
        self.add_item(self.select)

        if page > 0:
            prev_btn = Button(label="◀️ Назад", style=discord.ButtonStyle.secondary)
            prev_btn.callback = self.prev_page
            self.add_item(prev_btn)

        if (page + 1) * 10 < total_count:
            next_btn = Button(label="Вперёд ▶️", style=discord.ButtonStyle.secondary)
            next_btn.callback = self.next_page
            self.add_item(next_btn)

        back_btn = Button(label="⬅ Админ-панель", style=discord.ButtonStyle.secondary, custom_id="back_admin_from_reports")
        back_btn.callback = self.back_to_admin
        self.add_item(back_btn)

    async def back_to_admin(self, interaction: discord.Interaction):
        embed = discord.Embed(title="Админ-панель", description="Выберите раздел:", color=0x9B7BFF)
        await interaction.response.edit_message(embed=embed, view=AdminMainView())

    async def on_select(self, interaction: discord.Interaction):
        rep_id = int(self.select.values[0])
        await show_promo_detail(interaction, rep_id)

    async def prev_page(self, interaction: discord.Interaction):
        await show_promo_reports(interaction, self.page - 1)

    async def next_page(self, interaction: discord.Interaction):
        await show_promo_reports(interaction, self.page + 1)


async def show_promo_detail(interaction: discord.Interaction, report_id: int):
    r = await fetch_one(
        """SELECT pr.*, r1.name AS from_name, r2.name AS to_name
           FROM promotion_reports pr
           LEFT JOIN ranks r1 ON pr.from_rank_id = r1.id
           LEFT JOIN ranks r2 ON pr.to_rank_id = r2.id
           WHERE pr.report_id = ?""",
        (report_id,)
    )
    if not r:
        await interaction.response.send_message("❌ Отчёт не найден.", ephemeral=True)
        return

    user = f"<@{r['discord_id']}>"
    sys_name = "Основная" if r["system_type"] == "main" else "Альтернатива"

    embed = discord.Embed(title=f"Отчёт #{r['report_id']}", color=0x2980B9)
    embed.add_field(name="Пользователь", value=user, inline=True)
    embed.add_field(name="Система", value=sys_name, inline=True)
    embed.add_field(name="С ранга", value=r["from_name"], inline=True)
    embed.add_field(name="На ранг", value=r["to_name"], inline=True)
    embed.add_field(name="Статус", value=r["status"], inline=True)
    if r["taken_by"]:
        embed.add_field(name="Взял в работу", value=f"<@{r['taken_by']}>", inline=True)

    view = PromoActionView(report_id)
    await interaction.response.edit_message(embed=embed, view=view)


async def post_promo_report_message(client: discord.Client, report_id: int):
    r = await fetch_one(
        """
        SELECT pr.*,
               r1.name AS from_name,
               r2.name AS to_name
        FROM promotion_reports pr
        LEFT JOIN ranks r1 ON pr.from_rank_id = r1.id
        LEFT JOIN ranks r2 ON pr.to_rank_id = r2.id
        WHERE pr.report_id = ?
        """,
        (int(report_id),),
    )
    if not r:
        return {"ok": False, "reason": "report_not_found"}

    raw = await get_setting("promochannelid")
    try:
        _grow = await fetch_one("SELECT guild_id FROM promotion_reports WHERE report_id = ?", (int(report_id),))
        _gg = (_grow or {}).get("guild_id")
        if _gg:
            _per = await get_setting("promo_log_channel_id", str(_gg))
            if _per:
                raw = _per
    except Exception:
        pass
    if not raw:
        return {"ok": False, "reason": "promochannelid_not_set"}

    # Теги ролей на новые заявки
    _pings = ""
    try:
        _praw = None
        try:
            _grow2 = await fetch_one("SELECT guild_id FROM promotion_reports WHERE report_id = ?", (int(report_id),))
            _gg2 = (_grow2 or {}).get("guild_id")
            if _gg2:
                _praw = await get_setting("promo_ping_role_ids", str(_gg2))
        except Exception:
            pass
        _ids = [x.strip() for x in (_praw or "").split(",") if x.strip().isdigit()]
        if _ids:
            _pings = " ".join(f"<@&{i}>" for i in _ids)
    except Exception:
        pass

    channel_id = int(raw)
    ch = client.get_channel(channel_id)
    if ch is None:
        ch = await client.fetch_channel(channel_id)

    sysname = "MAIN" if (r["system_type"] or "") == "main" else "ALT"
    embed = discord.Embed(title=f"Отчет на повышение #{r['report_id']}", color=0x3498DB)
    embed.add_field(name="Пользователь", value=f"<@{r['discord_id']}> (`{r['discord_id']}`)", inline=False)
    embed.add_field(name="Система повышения", value=sysname, inline=True)
    embed.add_field(name="С ранга", value=str(r.get("from_name") or "?"), inline=True)
    embed.add_field(name="На ранг", value=str(r.get("to_name") or "?"), inline=True)
    embed.add_field(name="Статус", value=str(r.get("status") or "NEW"), inline=True)

    msg = await ch.send(content=_pings or None, embed=embed, view=PromoActionView(int(report_id)))

    await execute(
        "UPDATE promotion_reports SET msg_channel_id=?, msg_id=? WHERE report_id=?",
        (str(msg.channel.id), str(msg.id), int(report_id)),
    )

    return {"ok": True, "msg_id": msg.id, "channel_id": msg.channel.id}




class PromoActionView(View):
    def __init__(self, report_id: int = 0):
        super().__init__(timeout=None)
        self.report_id = int(report_id)

    def _resolve_id(self, interaction: discord.Interaction) -> int:
        if self.report_id:
            return int(self.report_id)
        try:
            title = (interaction.message.embeds[0].title if interaction.message and interaction.message.embeds else "") or ""
            import re as _re
            m = _re.search(r"#(\d+)", title)
            if m:
                return int(m.group(1))
        except Exception:
            pass
        return 0

    @discord.ui.button(label="Одобрить", style=discord.ButtonStyle.success, custom_id="promo:approve")
    async def approve_btn(self, interaction: discord.Interaction, button: Button):
        # defer сразу — до любых тяжёлых операций
        await interaction.response.defer(ephemeral=True)
        rid = self._resolve_id(interaction)
        if not rid:
            return await interaction.followup.send("❌ Не нашел отчет.", ephemeral=True)
        await approve_promotion(interaction, rid)

    @discord.ui.button(label="Отклонить", style=discord.ButtonStyle.danger, custom_id="promo:reject")
    async def reject_btn(self, interaction: discord.Interaction, button: Button):
        rid = self._resolve_id(interaction)
        if not rid:
            return await interaction.response.send_message("❌ Не нашел отчет.", ephemeral=True)
        modal = RejectPromoModal(rid)
        await interaction.response.send_modal(modal)


async def approve_promotion(interaction: discord.Interaction, report_id: int):
    r = await fetch_one("SELECT * FROM promotion_reports WHERE report_id = ?", (int(report_id),))
    if not r or r["status"] not in ("NEW", "TAKEN"):
        await interaction.followup.send("❌ Отчёт уже обработан.", ephemeral=True)
        return
    if interaction.guild and r.get("guild_id") and str(r["guild_id"]) != str(interaction.guild.id):
        await interaction.followup.send("❌ Этот отчет с другого сервера.", ephemeral=True)
        return

    guild = interaction.guild or interaction.client.get_guild(GUILD_ID)
    if guild is None:
        await interaction.followup.send("❌ Не удалось получить сервер.", ephemeral=True)
        return

    user_id = int(r["discord_id"])
    member = guild.get_member(user_id)
    if member is None:
        try:
            member = await guild.fetch_member(user_id)
        except Exception:
            member = None
    if member is None:
        await interaction.followup.send("❌ Не удалось найти участника на сервере.", ephemeral=True)
        return

    admin_id = str(interaction.user.id)

    # 1) фиксируем решение
    await execute("""
        UPDATE promotion_reports
        SET status='APPROVED',
            reviewed_by=?,
            reviewed_at=datetime('now'),
            decision='APPROVED'
        WHERE report_id=?
    """, (admin_id, int(report_id)))
    try:
        from services.api_sync import queue_promo_sync
        queue_promo_sync(str(guild.id), int(report_id), str(r["discord_id"]),
                         from_rank=r.get("from_rank_id"), to_rank=r.get("to_rank_id"),
                         status="APPROVED")
    except Exception as e:
        print(f"[api_sync] warn: {e}")

    # 2) current_rank_id пользователю
    _pg = str(guild.id)
    await execute(
        "UPDATE users SET current_rank_id=? WHERE discord_id=? AND (? IS NULL OR guild_id = ?)",
        (r["to_rank_id"], r["discord_id"], _pg, _pg),
    )

    # 3) списание контрактов
    need_fam = 0
    need_tun = 0

    if (r["system_type"] or "") == "main":
        req = await fetch_one(
            "SELECT family_contracts FROM rank_requirements_main WHERE rank_from=? AND rank_to=?",
            (r["from_rank_id"], r["to_rank_id"]),
        )
        need_fam = int(req["family_contracts"] or 0) if req else 0
    else:
        req = await fetch_one(
            "SELECT family_contracts, tuning_contracts FROM rank_requirements_alt WHERE rank_from=? AND rank_to=?",
            (r["from_rank_id"], r["to_rank_id"]),
        )
        need_fam = int(req["family_contracts"] or 0) if req else 0
        need_tun = int(req["tuning_contracts"] or 0) if req else 0

    await execute(
        """
        UPDATE users
        SET
          family_total = CASE WHEN family_total >= ? THEN family_total - ? ELSE 0 END,
          tuning_total = CASE WHEN tuning_total >= ? THEN tuning_total - ? ELSE 0 END
        WHERE discord_id = ?
        """,
        (need_fam, need_fam, need_tun, need_tun, r["discord_id"]),
    )

    # 4) роли
    from_rank = await fetch_one("SELECT id, name, role_id FROM ranks WHERE id = ?", (r["from_rank_id"],))
    to_rank = await fetch_one("SELECT id, name, role_id FROM ranks WHERE id = ?", (r["to_rank_id"],))

    if from_rank and from_rank.get("role_id"):
        old_role = guild.get_role(int(from_rank["role_id"]))
        if old_role and old_role in member.roles:
            await member.remove_roles(old_role, reason="Повышение ранга")

    if to_rank and to_rank.get("role_id"):
        new_role = guild.get_role(int(to_rank["role_id"]))
        if new_role:
            await member.add_roles(new_role, reason="Повышение ранга")

    # 5) обновляем исходное сообщение в промо-канале (убираем кнопки)
    await update_promo_report_message(interaction.client, int(report_id))

    # 6) лог
    from_name = (from_rank["name"] if from_rank and from_rank.get("name") else "?")
    to_name   = (to_rank["name"] if to_rank and to_rank.get("name") else "?")

    log_embed = discord.Embed(title="✅ Повышение одобрено", color=0x2ECC71)
    log_embed.description = (
        f"Повышение №{report_id}\n"
        f"Пользователь: <@{r['discord_id']}>\n"
        f"Админ: <@{interaction.user.id}>\n"
    )
    log_embed.add_field(name="С ранга", value=from_name, inline=True)
    log_embed.add_field(name="На ранг", value=to_name, inline=True)

    await audit_promotions(interaction.client, log_embed)

    # 7) ответ админу через followup (т.к. уже делали defer)
    f_name = (from_rank["name"] if from_rank and from_rank.get("name") else "?")
    t_name = (to_rank["name"] if to_rank and to_rank.get("name") else "?")
    embed = discord.Embed(title="✅ Повышение одобрено", color=0x2ECC71)
    embed.description = f"<@{r['discord_id']}> повышен с **{f_name}** до **{t_name}**."

    await interaction.followup.send(embed=embed, ephemeral=True)


async def reject_promotion(interaction: discord.Interaction, report_id: int, reason_text: str):
    r = await fetch_one("""
    SELECT pr.*,
           r1.name AS from_name,
           r2.name AS to_name
    FROM promotion_reports pr
    LEFT JOIN ranks r1 ON pr.from_rank_id = r1.id
    LEFT JOIN ranks r2 ON pr.to_rank_id   = r2.id
    WHERE pr.report_id = ?""", (int(report_id),))
    
    if not r or r["status"] not in ("NEW", "TAKEN"):
        await interaction.response.send_message("❌ Отчёт уже обработан.", ephemeral=True)
        return
    if interaction.guild and r.get("guild_id") and str(r["guild_id"]) != str(interaction.guild.id):
        await interaction.response.send_message("❌ Этот отчет с другого сервера.", ephemeral=True)
        return

    admin_id = str(interaction.user.id)

    await execute(
        """
        UPDATE promotion_reports
        SET status='REJECTED',
            reviewed_by=?,
            reviewed_at=datetime('now'),
            decision='REJECTED',
            reason=?
        WHERE report_id=?
        """,
        (admin_id, reason_text, int(report_id)),
    )
    try:
        from services.api_sync import queue_promo_sync
        queue_promo_sync(str(interaction.guild.id), int(report_id), str(r["discord_id"]),
                         from_rank=r.get("from_rank_id"), to_rank=r.get("to_rank_id"),
                         status="REJECTED", reason=reason_text)
    except Exception as e:
        print(f"[api_sync] warn: {e}")

    # обновляем исходное сообщение в промо-канале (убираем кнопки + reason)
    await update_promo_report_message(interaction.client, int(report_id))

    # лог
    from_name = str(r.get("from_name") or "?")
    to_name   = str(r.get("to_name") or "?")
    
    log_embed = discord.Embed(title="❌ Повышение отклонено", color=0xE74C3C)
    log_embed.add_field(name="С ранга", value=from_name, inline=True)
    log_embed.add_field(name="На ранг", value=to_name, inline=True)
    
    log_embed.description = (
        f"Повышение №{report_id}\n"
        f"Пользователь: <@{r['discord_id']}>\n"
        f"Админ: <@{interaction.user.id}>\n"
        f"Причина: {reason_text}"
    )

    await audit_promotions(interaction.client, log_embed)

    # ответ админу
    embed = discord.Embed(title="❌ Повышение отклонено", color=0xE74C3C)
    embed.description = f"Отчёт #{report_id} отклонён.\nПричина: {reason_text}"

    if interaction.response.is_done():
        await interaction.edit_original_response(embed=embed, view=None)
    else:
        await interaction.response.edit_message(embed=embed, view=None)




class RejectPromoModal(Modal, title="Причина отклонения повышения"):
    reason_input = TextInput(
        label="Причина",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=500
    )

    def __init__(self, report_id: int):
        super().__init__()
        self.report_id = report_id

    async def on_submit(self, interaction: discord.Interaction):
        reason_text = self.reason_input.value.strip()
        await reject_promotion(interaction, self.report_id, reason_text)



# --- BONUS REPORTS (ниже твой код почти без изменений) ---

async def calc_live_sums(discord_id: str, week_start: str, week_end: str) -> dict:
    row = await fetch_one(
        """
        SELECT
          COALESCE(SUM(base_price), 0) AS contracts_sum,
          COALESCE(SUM(rank_bonus), 0) AS rank_bonus_sum,
          COALESCE(SUM(tuning_rank_bonus), 0) AS tuning_rank_bonus_sum,
          COALESCE(SUM(calc_price), 0) AS live_total
        FROM v_contract_value
        WHERE discord_id = ?
          AND date(msk_date_iso) >= date(?)
          AND date(msk_date_iso) <= date(?)
        """,
        (discord_id, week_start, week_end)
    )
    return {
        "contracts_sum": float(row["contracts_sum"] or 0),
        "rank_bonus_sum": float(row["rank_bonus_sum"] or 0),
        "tuning_rank_bonus_sum": float(row["tuning_rank_bonus_sum"] or 0),
        "live_total": float(row["live_total"] or 0),
    }


async def show_bonus_reports(interaction: discord.Interaction, page: int = 0):
    week_start, week_end = week_range_msk()
    offset = page * 10
    gid = str(interaction.guild.id) if interaction.guild else None

    reports = await fetch_all(
        """
        SELECT
          br.report_id,
          br.discord_id,
          br.week_start,
          br.week_end,
          br.total_amount,
          br.sea_amount,
          br.status,
          br.taken_by,

          (
            SELECT COALESCE(SUM(vc.base_price), 0)
            FROM v_contract_value vc
            WHERE vc.discord_id = br.discord_id
              AND date(vc.msk_date_iso) >= date(br.week_start)
              AND date(vc.msk_date_iso) <= date(br.week_end)
          ) AS live_contracts,

          (
            SELECT COALESCE(SUM(vc.rank_bonus), 0)
            FROM v_contract_value vc
            WHERE vc.discord_id = br.discord_id
              AND date(vc.msk_date_iso) >= date(br.week_start)
              AND date(vc.msk_date_iso) <= date(br.week_end)
          ) AS live_rank_bonus,

          (
            SELECT COALESCE(SUM(vc.tuning_rank_bonus), 0)
            FROM v_contract_value vc
            WHERE vc.discord_id = br.discord_id
              AND date(vc.msk_date_iso) >= date(br.week_start)
              AND date(vc.msk_date_iso) <= date(br.week_end)
          ) AS live_tuning_rank_bonus,

          (
            SELECT COALESCE(SUM(vc.calc_price), 0)
            FROM v_contract_value vc
            WHERE vc.discord_id = br.discord_id
              AND date(vc.msk_date_iso) >= date(br.week_start)
              AND date(vc.msk_date_iso) <= date(br.week_end)
          ) AS live_base_total

        FROM bonus_reports br
        WHERE (br.status IN ('NEW','TAKEN')
           OR (br.status='APPROVED' AND br.week_start=? AND br.week_end=?))
          AND (? IS NULL OR br.guild_id = ?)
        ORDER BY br.report_id DESC
        LIMIT 10 OFFSET ?
        """,
        (week_start, week_end, gid, gid, offset)
    )

    total = await fetch_one(
        """
        SELECT COUNT(*) AS cnt
        FROM bonus_reports
        WHERE (status IN ('NEW','TAKEN')
           OR (status='APPROVED' AND week_start=? AND week_end=?))
          AND (? IS NULL OR guild_id = ?)
        """,
        (week_start, week_end, gid, gid)
    )

    total_count = int(total["cnt"] or 0) if total else 0

    if not reports:
        embed = discord.Embed(title="💰 Отчёты на премию", color=0x00FF00)
        embed.description = "Нет отчётов на премию, ожидающих рассмотрения."
        await interaction.response.edit_message(embed=embed, view=None)
        return

    embed = discord.Embed(title="💰 Отчёты на премию", color=0x2ECC71)
    embed.description = f"Всего в очереди: **{total_count}**"

    view = BonusReportsView(reports, page, total_count)

    for r in reports:
        user = f"<@{r['discord_id']}>"
        taken_by = f"<@{r['taken_by']}>" if r["taken_by"] else "—"

        contracts_sum = float(r["live_contracts"] or 0.0)
        rank_bonus_sum = float(r["live_rank_bonus"] or 0.0)
        tuning_rank_bonus_sum = float(r["live_tuning_rank_bonus"] or 0.0)
        sea = float(r["sea_amount"] or 0.0)

        live_base_total = float(r["live_base_total"] or 0.0)
        live_total = live_base_total + sea

        embed.add_field(
            name=f"#{r['report_id']} | {r['week_start']} — {r['week_end']}",
            value=(
                f"Пользователь: {user}\n"
                f"Контракты: {round(contracts_sum, 2)}\n"
                f"Надбавка за ранг: {round(rank_bonus_sum, 2)}\n"
                f"Надбавка за тюнинг: {round(tuning_rank_bonus_sum, 2)}\n"
                f"Дары моря: {round(sea, 2)}\n"
                f"Итого (live): **{round(live_total, 2)}**\n"
                f"Статус: **{r['status']}**\n"
                f"Взял: {taken_by}"
            ),
            inline=False
        )

    await interaction.response.edit_message(embed=embed, view=view)


class BonusReportsView(View):
    def __init__(self, reports, page, total_count):
        super().__init__(timeout=300)
        self.reports = reports
        self.page = page
        self.total_count = total_count

        options = []
        for r in reports[:25]:
            label = f"#{r['report_id']} {r['week_start']}—{r['week_end']}"
            desc = f"user {r['discord_id']}"
            options.append(discord.SelectOption(label=label[:100], description=desc[:100], value=str(r["report_id"])))

        self.select = discord.ui.Select(placeholder="Выберите отчёт на премию...", options=options)
        self.select.callback = self.on_select
        self.add_item(self.select)

        if page > 0:
            prev_btn = Button(label="◀️ Назад", style=discord.ButtonStyle.secondary)
            prev_btn.callback = self.prev_page
            self.add_item(prev_btn)

        if (page + 1) * 10 < total_count:
            next_btn = Button(label="Вперёд ▶️", style=discord.ButtonStyle.secondary)
            next_btn.callback = self.next_page
            self.add_item(next_btn)

    async def on_select(self, interaction: discord.Interaction):
        report_id = int(self.select.values[0])
        await show_bonus_detail(interaction, report_id)

    async def prev_page(self, interaction: discord.Interaction):
        await show_bonus_reports(interaction, self.page - 1)

    async def next_page(self, interaction: discord.Interaction):
        await show_bonus_reports(interaction, self.page + 1)


async def show_bonus_detail(interaction: discord.Interaction, report_id: int):
    r = await fetch_one("SELECT * FROM bonus_reports WHERE report_id = ?", (report_id,))
    if not r:
        await interaction.response.send_message("❌ Отчёт не найден.", ephemeral=True)
        return

    sums = await calc_live_sums(str(r["discord_id"]), str(r["week_start"]), str(r["week_end"]))
    contracts_sum = float(sums["contracts_sum"])
    rank_bonus_sum = float(sums["rank_bonus_sum"])
    tuning_rank_bonus_sum = float(sums["tuning_rank_bonus_sum"])
    live_base_total = float(sums["live_total"])

    sea_amount = float(r["sea_amount"] or 0.0)
    total = live_base_total + sea_amount

    user = f"<@{r['discord_id']}>"
    embed = discord.Embed(title=f"💰 Премия #{r['report_id']}", color=0x27AE60)
    embed.add_field(name="Пользователь", value=user, inline=True)
    embed.add_field(name="Неделя", value=f"{r['week_start']} — {r['week_end']} (МСК)", inline=True)

    embed.add_field(name="Контракты (live)", value=str(round(contracts_sum, 2)), inline=True)
    embed.add_field(name="Надбавка за ранг", value=str(round(rank_bonus_sum, 2)), inline=True)
    embed.add_field(name="Надбавка за тюнинг", value=str(round(tuning_rank_bonus_sum, 2)), inline=True)
    embed.add_field(name="Дары моря", value=str(round(sea_amount, 2)), inline=True)
    embed.add_field(name="Сумма (итог)", value=str(round(total, 2)), inline=False)

    embed.add_field(name="Статус", value=str(r["status"] or "—"), inline=True)
    if r.get("taken_by"):
        embed.add_field(name="Взял в работу", value=f"<@{r['taken_by']}>", inline=True)

    try:
        items = json.loads(r["contracts_json"] or "[]")
    except Exception:
        items = []

    if items:
        preview = []
        for it in items[:10]:
            preview.append(f"#{it.get('contract_id')} {it.get('contract_type')} = {it.get('amount')}")
        more = "" if len(items) <= 10 else f"\n...и ещё {len(items) - 10}"
        embed.add_field(name="Контракты (первые 10)", value="\n".join(preview) + more, inline=False)

    view = BonusActionView(report_id)
    await interaction.response.edit_message(embed=embed, view=view)


class BonusActionView(View):
    def __init__(self, report_id: int = 0):
        super().__init__(timeout=None)
        self.report_id = report_id

    def _resolve_id(self, interaction: discord.Interaction) -> int:
        if self.report_id:
            return int(self.report_id)
        try:
            title = (interaction.message.embeds[0].title if interaction.message and interaction.message.embeds else "") or ""
            import re as _re
            m = _re.search(r"#(\d+)", title)
            if m:
                return int(m.group(1))
        except Exception:
            pass
        return 0

    @discord.ui.button(label="Добавить сумму к итогу за 'Дары моря'", style=discord.ButtonStyle.secondary, custom_id="bonus:sea")
    async def add_sea_btn(self, interaction: discord.Interaction, button: Button):
        rid = self._resolve_id(interaction)
        if not rid:
            return await interaction.response.send_message("❌ Не нашел отчет.", ephemeral=True)
        await interaction.response.send_modal(
            AddSeaAmountModal(
                rid,
                channel_id=int(interaction.channel.id) if interaction.channel else 0,
                message_id=int(interaction.message.id) if interaction.message else 0
            )
        )

    @discord.ui.button(label="Одобрить", style=discord.ButtonStyle.success, custom_id="bonus:approve")
    async def approve_btn(self, interaction: discord.Interaction, button: Button):
        rid = self._resolve_id(interaction)
        if not rid:
            return await interaction.response.send_message("❌ Не нашел отчет.", ephemeral=True)
        await approve_bonus(interaction, rid)

    @discord.ui.button(label="Отклонить", style=discord.ButtonStyle.danger, custom_id="bonus:reject")
    async def rejectbtn(self, interaction: discord.Interaction, button: Button):
        rid = self._resolve_id(interaction)
        if not rid:
            return await interaction.response.send_message("❌ Не нашел отчет.", ephemeral=True)
        await interaction.response.send_modal(RejectBonusModal(rid))

    @discord.ui.button(label="← Назад к списку", style=discord.ButtonStyle.primary, custom_id="bonus:back")
    async def back_btn(self, interaction: discord.Interaction, button: Button):
        await show_bonus_reports(interaction, page=0)


async def fetch_bonus_report(report_id: int):
    return await fetch_one(
        """
        SELECT report_id, discord_id, week_start, week_end,
               total_amount, sea_amount, status, decision, reason,
               taken_by, reviewed_by, reviewed_at
        FROM bonus_reports
        WHERE report_id = ?
        """,
        (int(report_id),)
    )


class AddSeaAmountModal(discord.ui.Modal, title="Дары моря: сумма"):
    def __init__(self, report_id: int, channel_id: int = 0, message_id: int = 0):
        super().__init__()
        self.report_id = int(report_id)
        self.channel_id = int(channel_id or 0)
        self.message_id = int(message_id or 0)

        self.amount = discord.ui.TextInput(
            label="Сумма за 'Дары моря' (прибавится к итогу)",
            placeholder="Например: 5000",
            required=True,
            max_length=20
        )
        self.add_item(self.amount)

    async def on_submit(self, interaction: discord.Interaction):
        raw = (self.amount.value or "").strip().replace(",", ".")
        try:
            sea = float(raw)
        except ValueError:
            await interaction.response.send_message("❌ Введи число.", ephemeral=True)
            return

        if sea < 0:
            await interaction.response.send_message("❌ Сумма не может быть отрицательной.", ephemeral=True)
            return

        await execute(
            "UPDATE bonus_reports SET sea_amount = ? WHERE report_id = ?",
            (float(sea), self.report_id)
        )

        row = await fetch_bonus_report(self.report_id)
        if not row:
            await interaction.response.send_message("✅ 'Дары моря' обновлены.", ephemeral=True)
            return

        sums = await calc_live_sums(str(row["discord_id"]), str(row["week_start"]), str(row["week_end"]))
        contracts_sum = float(sums["contracts_sum"])
        rank_bonus_sum = float(sums["rank_bonus_sum"])
        tuning_rank_bonus_sum = float(sums["tuning_rank_bonus_sum"])
        live_base_total = float(sums["live_total"])

        sea_amount = float(row["sea_amount"] or 0.0)
        total = live_base_total + sea_amount

        await execute(
            "UPDATE bonus_reports SET total_amount = ? WHERE report_id = ?",
            (float(total), self.report_id)
        )

        embed = discord.Embed(title=f"💰 Премия #{self.report_id}", color=0x27AE60)
        embed.add_field(name="Пользователь", value=f"<@{row['discord_id']}>", inline=True)
        embed.add_field(name="Неделя", value=f"{row['week_start']} — {row['week_end']} (МСК)", inline=True)

        embed.add_field(name="Контракты (live)", value=str(round(contracts_sum, 2)), inline=True)
        embed.add_field(name="Надбавка за ранг", value=str(round(rank_bonus_sum, 2)), inline=True)
        embed.add_field(name="Надбавка за тюнинг", value=str(round(tuning_rank_bonus_sum, 2)), inline=True)
        embed.add_field(name="Дары моря", value=str(round(sea_amount, 2)), inline=True)
        embed.add_field(name="Сумма (итог)", value=str(round(total, 2)), inline=False)

        embed.add_field(name="Статус", value=str(row["status"] or "—"), inline=True)
        embed.set_footer(text="Live база считается автоматически, 'Дары моря' задаются вручную.")

        if self.channel_id and self.message_id and self.message_id != 0:
            try:
                ch = interaction.client.get_channel(self.channel_id) or await interaction.client.fetch_channel(self.channel_id)
                msg = await ch.fetch_message(self.message_id)
                await msg.edit(embed=embed, view=BonusActionView(self.report_id))
            except (discord.NotFound, discord.HTTPException):
                pass

        await interaction.response.send_message("✅ 'Дары моря' сохранены.", ephemeral=True)


async def approve_bonus(interaction: discord.Interaction, report_id: int):
    r = await fetch_one("SELECT * FROM bonus_reports WHERE report_id = ?", (report_id,))
    if not r:
        await interaction.response.send_message("❌ Отчёт не найден.", ephemeral=True)
        return
    if interaction.guild and r.get("guild_id") and str(r["guild_id"]) != str(interaction.guild.id):
        await interaction.response.send_message("❌ Этот отчет с другого сервера.", ephemeral=True)
        return
    if interaction.guild and r.get("guild_id") and str(r["guild_id"]) != str(interaction.guild.id):
        await interaction.response.send_message("❌ Этот отчет с другого сервера.", ephemeral=True)
        return

    from cogs.bonus import week_locked
    if week_locked(r.get("week_end") or ""):
        await interaction.response.send_message(
            "❌ Неделя закрыта: после понедельника принимать нельзя.", ephemeral=True)
        return

    sums = await calc_live_sums(str(r["discord_id"]), str(r["week_start"]), str(r["week_end"]))
    contracts_sum = float(sums["contracts_sum"])
    rank_bonus_sum = float(sums["rank_bonus_sum"])
    tuning_rank_bonus_sum = float(sums["tuning_rank_bonus_sum"])
    live_base_total = float(sums["live_total"])

    sea = float(r.get("sea_amount") or 0.0)
    total = live_base_total + sea

    admin_id = str(interaction.user.id)
    await execute(
        """
        UPDATE bonus_reports
        SET status='APPROVED',
            reviewed_by=?,
            reviewed_at=datetime('now'),
            decision='APPROVED',
            total_amount=?
        WHERE report_id=?
        """,
        (admin_id, float(total), report_id)
    )
    try:
        from services.api_sync import queue_bonus_sync
        queue_bonus_sync(str(interaction.guild.id), int(report_id), str(r["discord_id"]),
                         amount=float(total), status="APPROVED",
                         external_id=(f"site:{r['site_id']}" if r.get("site_id") else None))
    except Exception as e:
        print(f"[api_sync] warn: {e}")

    await update_bonus_audit_message(interaction.client, report_id)

    embed = discord.Embed(title=f"✅ Премия #{report_id} одобрена", color=0x2ECC71)
    embed.description = (
        f"Пользователь: <@{r['discord_id']}>\n"
        f"Контракты: {round(contracts_sum, 2)}\n"
        f"Надбавка за ранг: {round(rank_bonus_sum, 2)}\n"
        f"Надбавка за тюнинг: {round(tuning_rank_bonus_sum, 2)}\n"
        f"Море: {round(sea, 2)}\n"
        f"Итого: **{round(total, 2)}**"
    )
    await interaction.response.edit_message(embed=embed, view=None)

    log = discord.Embed(title="✅ Премия принята", color=0x2ECC71)
    log.add_field(name="Премия отчет", value=str(report_id), inline=True)
    log.add_field(name="Админ", value=f"{interaction.user} ({interaction.user.id})", inline=False)
    log.add_field(name="Пользователь", value=f"<@{r['discord_id']}> ({r['discord_id']})", inline=False)
    log.add_field(name="Контракты", value=str(round(contracts_sum, 2)), inline=True)
    log.add_field(name="Надбавка за ранг", value=str(round(rank_bonus_sum, 2)), inline=True)
    log.add_field(name="Надбавка за тюнинг", value=str(round(tuning_rank_bonus_sum, 2)), inline=True)
    log.add_field(name="Дары моря", value=str(round(sea, 2)), inline=True)
    log.add_field(name="Итого премии", value=str(round(total, 2)), inline=False)

    await audit_bonus_log(interaction.client, log)


class RejectBonusModal(discord.ui.Modal, title="Отклонение премии"):
    reason = discord.ui.TextInput(
        label="Причина",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=500
    )

    def __init__(self, report_id: int):
        super().__init__()
        self.report_id = int(report_id)

    async def on_submit(self, interaction: discord.Interaction):
        r = await fetch_one(
            """
            SELECT report_id, discord_id, week_start, week_end, status, sea_amount, site_id, guild_id
            FROM bonus_reports
            WHERE report_id=?
            """,
            (self.report_id,)
        )

        if not r:
            await interaction.response.send_message("Репорт не найден.", ephemeral=True)
            return
        if interaction.guild and r.get("guild_id") and str(r["guild_id"]) != str(interaction.guild.id):
            await interaction.response.send_message("❌ Этот отчет с другого сервера.", ephemeral=True)
            return

        st = (r["status"] or "").upper()

        if st == "APPROVED":
            cur_start, cur_end = week_range_msk()
            if str(r["week_start"]) != str(cur_start) or str(r["week_end"]) != str(cur_end):
                await interaction.response.send_message(
                    "Принятую премию можно отклонить только на этой неделе.",
                    ephemeral=True
                )
                return
        elif st not in ("NEW", "TAKEN"):
            await interaction.response.send_message("Нельзя отклонить в этом статусе.", ephemeral=True)
            return

        from cogs.bonus import week_locked
        if week_locked(r.get("week_end") or ""):
            await interaction.response.send_message(
                "❌ Неделя закрыта: после понедельника решать нельзя.", ephemeral=True)
            return

        admin_id = str(interaction.user.id)
        reason_text = (self.reason.value or "").strip()

        await execute(
            """
            UPDATE bonus_reports
            SET status='REJECTED',
                reviewed_by=?,
                reviewed_at=datetime('now'),
                decision='REJECTED',
                reason=?
            WHERE report_id=?
            """,
            (admin_id, reason_text, self.report_id)
        )

        await update_bonus_audit_message(interaction.client, self.report_id)

        await show_bonus_reports(interaction, page=0)
        await interaction.followup.send(f"Отклонено: #{self.report_id}", ephemeral=True)

        sums = await calc_live_sums(str(r["discord_id"]), str(r["week_start"]), str(r["week_end"]))
        contracts_sum = float(sums["contracts_sum"])
        rank_bonus_sum = float(sums["rank_bonus_sum"])
        tuning_rank_bonus_sum = float(sums["tuning_rank_bonus_sum"])
        live_base_total = float(sums["live_total"])

        sea = float(r.get("sea_amount") or 0.0)
        total = live_base_total + sea

        try:
            from services.api_sync import queue_bonus_sync
            queue_bonus_sync(str(interaction.guild.id), int(self.report_id), str(r["discord_id"]),
                             amount=float(total), status="REJECTED", reason=reason_text,
                             external_id=(f"site:{r['site_id']}" if r.get("site_id") else None))
        except Exception as e:
            print(f"[api_sync] warn: {e}")

        log = discord.Embed(title="❌ Премия отклонена", color=0xE74C3C)
        log.add_field(name="Премия отчет", value=str(self.report_id), inline=True)
        log.add_field(name="Админ", value=f"{interaction.user} ({interaction.user.id})", inline=False)
        log.add_field(name="Пользователь", value=f"<@{r['discord_id']}> ({r['discord_id']})", inline=False)
        log.add_field(name="Контракты", value=str(round(contracts_sum, 2)), inline=True)
        log.add_field(name="Надбавка за ранг", value=str(round(rank_bonus_sum, 2)), inline=True)
        log.add_field(name="Надбавка за тюнинг", value=str(round(tuning_rank_bonus_sum, 2)), inline=True)
        log.add_field(name="Дары Моря", value=str(round(sea, 2)), inline=True)
        log.add_field(name="Итого премии", value=str(round(total, 2)), inline=False)
        log.add_field(name="Причина", value=reason_text[:1000], inline=False)

        await audit_bonus_log(interaction.client, log)


ADMIN_PANEL_CH_KEY = "admin_panel_channel_id"
ADMIN_PANEL_MSG_KEY = "admin_panel_message_id"




async def setup(bot: commands.Bot):
    await bot.add_cog(AdminPanel(bot))
    bot.add_view(BonusActionView(0))
    bot.add_view(ContractActionView(0))
    bot.add_view(PromoActionView(0))
