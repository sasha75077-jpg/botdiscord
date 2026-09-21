import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button
from typing import Optional
from utils.week import week_range_msk
from database import get_setting
from services.profile_panel import open_profile_panel

from config import GUILD_ID, GUILD_IDS_LIST

GUILD_OBJECTS = [discord.Object(id=g) for g in GUILD_IDS_LIST] or [discord.Object(id=GUILD_ID)]
from database import fetch_one, execute, fetch_all

from utils.week import week_range_msk
 

from cogs.ranks import (
    ensure_user,
    promotion_status,
    create_promo_report,
    SYSTEM_MAIN,
    SYSTEM_ALT,
)
from cogs.bonus import create_bonus_report_for_week
from cogs.admin_panel import update_bonus_audit_message

from cogs.cooldowns import show_personal_tuning_cooldown

# Построение общей статистики эмбед

async def build_stats_embed(uid: str) -> discord.Embed:
    rows = await fetch_all(
        "SELECT * FROM contracts WHERE discord_id = ? AND confirm_status = 'APPROVED'",
        (uid,)
    )

    activations = 0
    fish_times = 0
    atelier_uniforms = 0
    ore_totals = {}
    mining_totals = {"iron": 0, "silver": 0, "copper": 0, "tin": 0, "gold": 0}
    goods_loading = 0
    goods_delivery = 0
    mp_links = 0
    wn_green = 0
    wn_notify = 0
    tuning_count = 0

    for r in rows:
        ct = r.get("contract_type", "")

        if ct == "активация":
            activations += 1

        elif ct == "дары-моря":
            fish_times += 1

        elif ct == "ателье":
            atelier_uniforms += int(r.get("atelier_total_uniforms") or 0)

        elif ct == "металлургия-сдача":
            ore = r.get("ore_type") or "неизвестно"
            ore_totals[ore] = ore_totals.get(ore, 0) + 1

        elif ct == "металлургия-добыча":
            mining_totals["iron"]   += int(r.get("m_iron") or 0)
            mining_totals["silver"] += int(r.get("m_silver") or 0)
            mining_totals["copper"] += int(r.get("m_copper") or 0)
            mining_totals["tin"]    += int(r.get("m_tin") or 0)
            mining_totals["gold"]   += int(r.get("m_gold") or 0)

        elif ct == "товары":
            if r.get("goods_loading"):
                goods_loading += 1
            if r.get("goods_delivery"):
                goods_delivery += 1

        elif ct == "агитации-маркетплейс":
            mp_links += int(r.get("marketplace_links_count") or 0)

        elif ct == "агитации-wn":
            cat = r.get("wn_category") or ""
            cnt = int(r.get("wn_screenshots_count") or 0)
            if "Зеленка" in cat:
                wn_green += cnt
            else:
                wn_notify += cnt

        elif ct == "тюнинг":
            tuning_count += 1

    embed = discord.Embed(title="📊 Моя статистика контрактов", color=0x9B7BFF)
    embed.description = "Все одобренные контракты за всё время"

    embed.add_field(name="🔑 Активация", value=f"{activations} раз", inline=True)
    embed.add_field(name="🐟 Дары моря", value=f"{fish_times} раз", inline=True)
    embed.add_field(name="🧵 Ателье", value=f"{atelier_uniforms} форм", inline=True)

    ore_str = "\n".join(f"{ore}: {cnt} раз" for ore, cnt in ore_totals.items()) if ore_totals else "0"
    embed.add_field(name="⛏️ Металлургия сдача", value=ore_str, inline=False)

    mining_str = (
        f"Железо: {mining_totals['iron']}\n"
        f"Серебро: {mining_totals['silver']}\n"
        f"Медь: {mining_totals['copper']}\n"
        f"Олово: {mining_totals['tin']}\n"
        f"Золото: {mining_totals['gold']}"
    )
    embed.add_field(name="🪨 Металлургия добыча", value=mining_str, inline=False)

    embed.add_field(
        name="✈️ Товары с самолёта",
        value=f"Погрузок: {goods_loading}\nСдач: {goods_delivery}",
        inline=True
    )
    embed.add_field(
        name="📢 Агитации маркетплейс",
        value=f"{mp_links} ссылок",
        inline=True
    )
    embed.add_field(
        name="🎮 Агитации WN",
        value=f"Зелёнок(чат): {wn_green}\nУведомлений: {wn_notify}",
        inline=True
    )
    embed.add_field(name="🏍️ Тюнинг", value=f"{tuning_count} раз", inline=True)

    return embed

class StatsBackView(View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="⬅️ Назад", style=discord.ButtonStyle.secondary)
    async def back_btn(self, interaction: discord.Interaction, button: Button):
        embed = await build_profile_embed(str(interaction.user.id))
        await interaction.response.edit_message(embed=embed, view=MainPanelView())


# ---- helpers ----

async def fetch_week_contracts(uid: str, week_start: str, week_end: str, limit: int = 40):
    return await fetch_all(
        """
        SELECT
          id,
          contract_type,
          COALESCE(calc_price, 0) AS calc_price,
          msk_date_iso
        FROM v_contract_value
        WHERE confirm_status = 'APPROVED'
          AND discord_id = ?
          AND date(msk_date_iso) >= date(?)
          AND date(msk_date_iso) <= date(?)
        ORDER BY date(msk_date_iso) DESC, id DESC
        LIMIT ?
        """,
        (uid, week_start, week_end, limit)
    )

async def fetch_week_contracts_page(
    uid: str,
    week_start: str,
    week_end: str,
    page: int,
    per_page: int = 10
):
    page = max(0, int(page))
    per_page = max(1, min(int(per_page), 15))

    rows = await fetch_all(
        """
        SELECT
          id,
          contract_type,
          COALESCE(calc_price, 0) AS calc_price,
          msk_date_iso
        FROM v_contract_value
        WHERE confirm_status = 'APPROVED'
          AND discord_id = ?
          AND date(msk_date_iso) >= date(?)
          AND date(msk_date_iso) <= date(?)
        ORDER BY date(msk_date_iso) DESC, id DESC
        LIMIT ? OFFSET ?
        """,
        (uid, week_start, week_end, per_page, page * per_page)
    )

    total_row = await fetch_one(
        """
        SELECT COUNT(*) AS cnt
        FROM v_contract_value
        WHERE confirm_status = 'APPROVED'
          AND discord_id = ?
          AND date(msk_date_iso) >= date(?)
          AND date(msk_date_iso) <= date(?)
        """,
        (uid, week_start, week_end)
    )
    total = int(total_row["cnt"] or 0) if total_row else 0
    return rows, total

def _contracts_page_text(rows) -> str:
    if not rows:
        return "—"
    lines = []
    for c in rows:
        price = float(c.get("calc_price") or 0)
        ctype = (c.get("contract_type") or "—")
        day = (c.get("msk_date_iso") or "")[:10]
        lines.append(f"`{c['id']}` {day} • {ctype} • {round(price, 2)}")
    text = "\n".join(lines)
    return text[:1000] + "…" if len(text) > 1000 else text


async def build_bonus_preview_embed(
    uid: str,
    report_id: int,
    week_start: str,
    week_end: str,
    page: int,
    per_page: int = 10
) -> discord.Embed:
    embed = await build_profile_embed(uid)

    sums = await calc_live_sums(uid, week_start, week_end)
    contracts_sum = float(sums.get("base_sum") or 0)
    rank_bonus_sum = float(sums.get("rank_bonus_sum") or 0)
    tuning_rank_bonus_sum = float(sums.get("tuning_rank_bonus_sum") or 0)

    sea = 0.0
    total = float(contracts_sum + rank_bonus_sum + tuning_rank_bonus_sum + sea)

    rows, total_cnt = await fetch_week_contracts_page(uid, week_start, week_end, page, per_page)
    max_page = max(0, (total_cnt - 1) // per_page) if total_cnt else 0

    embed.description = (
        f"💰 Предпросмотр премии за **{week_start} — {week_end}**\n"
        f"Отчёт: **#{report_id}**\n"
        f"Контракты: страница **{page+1}/{max_page+1}** (всего {total_cnt})"
    )

    embed.add_field(name="Контракты (база)", value=str(round(contracts_sum, 2)), inline=True)
    embed.add_field(name="Надбавка (ранг)", value=str(round(rank_bonus_sum, 2)), inline=True)
    embed.add_field(name="Надбавка (тюнинг)", value=str(round(tuning_rank_bonus_sum, 2)), inline=True)
    embed.add_field(name="Дары моря", value=str(round(sea, 2)), inline=True)
    embed.add_field(name="Итого", value=str(round(total, 2)), inline=True)

    embed.add_field(
        name=f"Список контрактов (показано {len(rows)})",
        value=_contracts_page_text(rows),
        inline=False
    )

    return embed



async def calc_live_sums(discord_id: str, week_start: str, week_end: str) -> dict:
    row = await fetch_one(
        """
        SELECT
          COALESCE(SUM(base_price), 0) AS base_sum,
          COALESCE(SUM(rank_bonus), 0) AS rank_bonus_sum,
          COALESCE(SUM(tuning_rank_bonus), 0) AS tuning_rank_bonus_sum,
          COALESCE(SUM(calc_price), 0) AS total_sum
        FROM v_contract_value
        WHERE discord_id = ?
          AND date(msk_date_iso) >= date(?)
          AND date(msk_date_iso) <= date(?)
        """,
        (discord_id, week_start, week_end)
    )
    return {
        "base_sum": float(row["base_sum"] or 0),
        "rank_bonus_sum": float(row["rank_bonus_sum"] or 0),
        "tuning_rank_bonus_sum": float(row["tuning_rank_bonus_sum"] or 0),
        "total_sum": float(row["total_sum"] or 0),
    }


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


async def get_user_rank_row(discord_id: str):
    return await fetch_one(
        "SELECT r.id AS rank_id, r.name AS rank_name, r.role_id AS role_id "
        "FROM users u "
        "LEFT JOIN ranks r ON r.id = u.current_rank_id "
        "WHERE u.discord_id = ?",
        (discord_id,),
    )


async def get_current_rank_name(discord_id: int) -> str:
    row = await get_user_rank_row(str(discord_id))
    if not row:
        return "—"
    # row может быть dict-like или tuple, но у тебя чаще dict/Row
    name = row.get("rank_name") if hasattr(row, "get") else row[1]
    return name or "—"



async def ensure_user_row(discord_id: str) -> None:
    """Создаёт строку users, если её нет (snake_case: users.discord_id)."""
    user = await fetch_one(
        "SELECT discord_id FROM users WHERE discord_id = ?",
        (discord_id,),
    )
    if user:
        return

    await execute(
        "INSERT INTO users (discord_id, current_rank_id, family_total, tuning_total) "
        "VALUES (?, NULL, 0, 0)",
        (discord_id,),
    )


async def require_static(interaction: discord.Interaction) -> Optional[str]:
    """Возвращает users.static или показывает ошибку и возвращает None."""
    uid = str(interaction.user.id)

    row = await fetch_one(
        "SELECT static FROM users WHERE discord_id = ?",
        (uid,)
    )

    static = row["static"] if row and row["static"] else None
    if static:
        return static

    embed = discord.Embed(title="Профиль", color=0xE74C3C)
    embed.description = "❌ Сначала укажи static (без него нельзя подать премию)."

    # Если interaction уже был acknowledged (defer/ответ), редактируем original response.
    if interaction.response.is_done():
        await interaction.edit_original_response(embed=embed, view=MainPanelView())
    else:
        # На случай, если вызвали require_static без defer.
        await interaction.response.edit_message(embed=embed, view=MainPanelView())

    return None

def build_promo_embed(rep: dict) -> discord.Embed:
    status = (rep.get("status") or "NEW").upper()

    colors = {
        "NEW": 0x3498DB,
        "TAKEN": 0xF39C12,
        "APPROVED": 0x2ECC71,
        "REJECTED": 0xE74C3C,
    }
    color = colors.get(status, 0x95A5A6)

    report_id = rep.get("report_id")
    user_id = str(rep.get("discord_id") or "")
    user_mention = f"<@{user_id}>" if user_id.isdigit() else user_id

    e = discord.Embed(title=f"Повышение #{report_id}", color=color)

    e.add_field(name="Пользователь", value=f"{user_mention}\n`{user_id}`", inline=True)
    e.add_field(name="Откуда", value=str(rep.get("from_rank_name") or "—"), inline=True)
    e.add_field(name="Куда", value=str(rep.get("to_rank_name") or "—"), inline=True)

    systemtype = rep.get("system_type")
    if systemtype:
        e.add_field(name="Система", value=str(systemtype), inline=True)

    takenby = str(rep.get("taken_by") or "")
    if takenby.isdigit():
        e.add_field(name="Взял", value=f"<@{takenby}>\n`{takenby}`", inline=True)

    reviewedby = str(rep.get("reviewed_by") or "")
    if reviewedby.isdigit():
        e.add_field(name="Решение", value=f"{status}\n<@{reviewedby}>", inline=True)
    else:
        e.add_field(name="Статус", value=status, inline=True)

    if status == "REJECTED" and rep.get("reason"):
        e.add_field(name="Причина", value=str(rep["reason"])[:1000], inline=False)

    reviewedat = rep.get("reviewed_at")
    if reviewedat:
        e.set_footer(text=f"reviewed_at: {reviewedat}")

    return e




async def build_profile_embed(user_id: str, guild_id: str | None = None) -> discord.Embed:
    if guild_id:
        await ensure_user(user_id, guild_id)

    row = await fetch_one(
        """
        SELECT
            u.discord_id,
            u.surname_changed,
            u.family_total,
            u.tuning_total,
            u.static,
            r.name AS rank_name
        FROM users u
        LEFT JOIN ranks r ON r.id = u.current_rank_id
        WHERE u.discord_id = ?
        """,
        (user_id,),
    )

    family_total = int(row["family_total"] or 0) if row else 0
    tuning_total = int(row["tuning_total"] or 0) if row else 0
    static_val = (row["static"] or "").strip() if row else ""
    rank_name = (row["rank_name"] if row and row["rank_name"] else "—")

    embed = discord.Embed(title="Профиль", color=0x32D3C5)
    embed.add_field(name="Пользователь", value=f"<@{user_id}>", inline=True)
    embed.add_field(name="Ранг", value=rank_name, inline=True)
    embed.add_field(
        name="Static",
        value=(f"`{static_val}`" if static_val else "❌ Не задан"),
        inline=False,
    )
    embed.add_field(name="Семейные (всего)", value=str(family_total), inline=True)
    embed.add_field(name="Тюнинг (всего)", value=str(tuning_total), inline=True)
    embed.set_footer(text="Выбери действие кнопками ниже.")
    return embed



async def has_active_promo_report(discord_id: str, system_type: str) -> bool:
    row = await fetch_one(
        "SELECT report_id FROM promotion_reports "
        "WHERE discord_id = ? AND system_type = ? AND status IN ('NEW','TAKEN') "
        "LIMIT 1",
        (discord_id, system_type),
    )
    return bool(row)

async def get_rank_name_from_discord(member: discord.Member) -> str:
    role_ids = [r.id for r in member.roles if r.id != member.guild.default_role.id]
    if not role_ids:
        return "—"

    placeholders = ",".join(["?"] * len(role_ids))
    row = await fetch_one(
        f"""
        SELECT name
        FROM ranks
        WHERE role_id IN ({placeholders})
        ORDER BY sort_order DESC
        LIMIT 1
        """,
        tuple(role_ids),
    )
    return row["name"] if row and row["name"] else "—"


async def update_user_rank_id_from_discord(member: discord.Member) -> int | None:
    uid = str(member.id)
    await ensure_user(uid)

    role_ids = [r.id for r in member.roles if r.id != member.guild.default_role.id]
    if not role_ids:
        await execute("UPDATE users SET current_rank_id = NULL WHERE discord_id = ?", (uid,))
        return None

    placeholders = ",".join(["?"] * len(role_ids))
    row = await fetch_one(
        f"""
        SELECT id
        FROM ranks
        WHERE role_id IN ({placeholders})
        ORDER BY sort_order DESC
        LIMIT 1
        """,
        tuple(role_ids),
    )

    rank_id = int(row["id"]) if row and row["id"] is not None else None
    await execute("UPDATE users SET current_rank_id = ? WHERE discord_id = ?", (rank_id, uid))
    return rank_id


async def get_user_rank_name(uid: str) -> str:
    row = await fetch_one(
        """
        SELECT r.name AS rank_name
        FROM users u
        LEFT JOIN ranks r ON r.id = u.current_rank_id
        WHERE u.discord_id = ?
        """,
        (uid,)
    )
    return (row["rank_name"] or "—") if row else "—"



# ---- UI ----

class BonusPreviewPagerView(discord.ui.View):
    def __init__(self, uid: str, report_id: int, week_start: str, week_end: str, page: int = 0, per_page: int = 10):
        super().__init__(timeout=300)
        self.uid = str(uid)
        self.report_id = int(report_id)
        self.week_start = week_start
        self.week_end = week_end
        self.page = int(page)
        self.per_page = int(per_page)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if str(interaction.user.id) != self.uid:
            await interaction.response.send_message("❌ Это меню не для вас.", ephemeral=True)
            return False
        return True

    async def _refresh(self, interaction: discord.Interaction):
        embed = await build_bonus_preview_embed(
            self.uid, self.report_id, self.week_start, self.week_end, self.page, self.per_page
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary, custom_id="bonus_prev_page")
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = max(0, self.page - 1)
        await self._refresh(interaction)

    @discord.ui.button(label="▶", style=discord.ButtonStyle.secondary, custom_id="bonus_next_page")
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page += 1
        # ограничение по максимуму страницы:
        _, total_cnt = await fetch_week_contracts_page(self.uid, self.week_start, self.week_end, 0, 1)
        max_page = max(0, (total_cnt - 1) // self.per_page) if total_cnt else 0
        self.page = min(self.page, max_page)
        await self._refresh(interaction)

    @discord.ui.button(label="✅ Отправить", style=discord.ButtonStyle.success, custom_id="bonus_pager_send_review")
    async def send_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
    
        row = await fetch_one(
            "SELECT status FROM bonus_reports WHERE report_id=? AND discord_id=?",
            (self.report_id, self.uid)
        )
        if not row:
            await interaction.edit_original_response(content="❌ Отчёт не найден.", embed=None, view=MainPanelView())
            return
    
        st = (row["status"] or "").upper()
    
        # уже отправлен / в работе / решён — повторно не отправляем
        if st in ("NEW", "TAKEN", "APPROVED"):
            embed = await build_profile_embed(self.uid)
            embed.description = f"❌ Отчёт уже активен (статус: **{st}**). Повторно отправить нельзя."
            await interaction.edit_original_response(embed=embed, view=MainPanelView())
            return
    
        # если отклонён — пусть сначала создастся новый DRAFT через кнопку "Премия"
        if st == "REJECTED":
            embed = await build_profile_embed(self.uid)
            embed.description = "❌ Отчёт отклонён. Нажмите «Премия» заново, чтобы пересоздать предпросмотр."
            await interaction.edit_original_response(embed=embed, view=MainPanelView())
            return
    
        # ожидаем, что сейчас DRAFT
        if st != "DRAFT":
            embed = await build_profile_embed(self.uid)
            embed.description = f"❌ Нельзя отправить отчёт из статуса **{st}**."
            await interaction.edit_original_response(embed=embed, view=MainPanelView())
            return
    
    

        sums = await calc_live_sums(self.uid, self.week_start, self.week_end)
        contracts_sum = float(sums.get("base_sum") or 0)
        rank_bonus_sum = float(sums.get("rank_bonus_sum") or 0)
        tuning_rank_bonus_sum = float(sums.get("tuning_rank_bonus_sum") or 0)

        sea = 0.0
        total = float(contracts_sum + rank_bonus_sum + tuning_rank_bonus_sum + sea)

        await execute(
            "UPDATE bonus_reports SET total_amount=?, status='NEW' WHERE report_id=?",
            (float(total), self.report_id)
        )

        raw = await get_setting("log_bonus")
        if raw:
            try:
                log_ch_id = int(raw)
                ch = interaction.client.get_channel(log_ch_id) or await interaction.client.fetch_channel(log_ch_id)

                audit_embed = discord.Embed(title=f"💰 Премия #{self.report_id}", color=0x3498DB)
                audit_embed.add_field(name="Пользователь", value=f"<@{self.uid}>", inline=True)
                audit_embed.add_field(name="Неделя", value=f"{self.week_start} — {self.week_end} (МСК)", inline=True)
                audit_embed.add_field(name="Контракты (live)", value=str(round(contracts_sum, 2)), inline=True)
                audit_embed.add_field(name="Надбавка (ранг)", value=str(round(rank_bonus_sum, 2)), inline=True)
                audit_embed.add_field(name="Надбавка (тюнинг)", value=str(round(tuning_rank_bonus_sum, 2)), inline=True)
                audit_embed.add_field(name="Дары моря", value=str(round(sea, 2)), inline=True)
                audit_embed.add_field(name="Сумма (итог)", value=str(round(total, 2)), inline=True)
                audit_embed.add_field(name="Статус", value="NEW", inline=True)

                msg = await ch.send(embed=audit_embed)

                await execute(
                    "UPDATE bonus_reports SET audit_channel_id=?, audit_msg_id=? WHERE report_id=?",
                    (str(msg.channel.id), str(msg.id), self.report_id),
                )
                await update_bonus_audit_message(interaction.client, self.report_id)
            except Exception as e:
                print(f"Audit log failed for report {self.report_id}: {e}")

        embed = await build_profile_embed(self.uid)
        embed.description = (
            f"✅ Отчёт на премию отправлен на рассмотрение (ID {self.report_id}).\n"
            f"Контракты: {round(contracts_sum, 2)}; "
            f"Надбавка (ранг): {round(rank_bonus_sum, 2)}; "
            f"Надбавка (тюнинг): {round(tuning_rank_bonus_sum, 2)}; "
            f"Итого: {round(total, 2)}"
        )
        await interaction.edit_original_response(embed=embed, view=MainPanelView())

    @discord.ui.button(label="⬅️ Назад", style=discord.ButtonStyle.secondary, custom_id="bonus_back")
    async def back_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = await build_profile_embed(self.uid)
        embed.description = "Выберите действие:"
        await interaction.response.edit_message(embed=embed, view=MainPanelView())


class SetStaticModal(discord.ui.Modal, title="Указать static"):
    static = discord.ui.TextInput(
        label="Static",
        placeholder="3..64 символа",
        min_length=3,
        max_length=64,
        required=True,
    )

    async def on_submit(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        val = self.static.value.strip()

        await ensure_user(uid)

        row = await fetch_one("SELECT static FROM users WHERE discord_id = ?", (uid,))
        if row and (row["static"] or "").strip():
            await interaction.response.send_message(
                "❌ Static уже задан. Если нужно изменить — попроси администратора.",
                ephemeral=True,
            )
            return

        await execute("UPDATE users SET static = ? WHERE discord_id = ?", (val, uid))
        embed = await build_profile_embed(uid)
        await interaction.response.edit_message(embed=embed, view=MainPanelView())


class UserPanel(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="profile", description="Открыть мейн панель")
    @app_commands.guilds(*GUILD_OBJECTS)
    async def profile(self, interaction: discord.Interaction):
        await open_profile_panel(interaction)

        guild = interaction.guild

        member = interaction.user if isinstance(interaction.user, discord.Member) else guild.get_member(interaction.user.id)
        if member is None:
            member = await guild.fetch_member(interaction.user.id)

        rank_name = await get_rank_name_from_discord(member)

        embed = await build_profile_embed(str(member.id))
        
        # Обновляем поле "Ранг", как у тебя было
        for i, f in enumerate(embed.fields):
            if f.name == "Ранг":
                embed.set_field_at(i, name="Ранг", value=rank_name, inline=True)
                break
        else:
            embed.add_field(name="Ранг", value=rank_name, inline=True)
        
        # --- аккуратно добавляем Discord ID в конец блока ---
        
        # Проверяем, нет ли уже такого поля
        if not any(f.name == "Discord ID" for f in embed.fields):
            embed.add_field(
                name="Discord ID",
                value=f"`{member.id}`",
                inline=False,
            )
            
        await interaction.edit_original_response(embed=embed, view=MainPanelView(), content=None)

    @app_commands.command(name="set_static", description="Указать static для премий (один раз)")
    @app_commands.guilds(*GUILD_OBJECTS)
    async def set_static(self, interaction: discord.Interaction, static: str):
        static = static.strip()
        if len(static) < 3 or len(static) > 64:
            await interaction.response.send_message("❌ Static должен быть 3..64 символа.", ephemeral=True)
            return

        uid = str(interaction.user.id)
        await ensure_user(uid)

        row = await fetch_one("SELECT static FROM users WHERE discord_id = ?", (uid,))
        if row and (row["static"] or "").strip():
            await interaction.response.send_message(
                "❌ Static уже задан. Если нужно изменить — попроси администратора.",
                ephemeral=True,
            )
            return

        await execute("UPDATE users SET static = ? WHERE discord_id = ?", (static, uid))
        await interaction.response.send_message(f"✅ Static сохранён: `{static}`", ephemeral=True)


class MainPanelView(View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="💻Указать static", style=discord.ButtonStyle.secondary)
    async def set_static_btn(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(SetStaticModal())

    @discord.ui.button(label="📈Система повышения", style=discord.ButtonStyle.primary)
    async def promo_info(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
    
        guild = interaction.guild
        if guild is None:
            await interaction.followup.send("❌ Команда доступна только на сервере.", ephemeral=True)
            return
    
        member = interaction.user if isinstance(interaction.user, discord.Member) else guild.get_member(interaction.user.id)
        if member is None:
            member = await guild.fetch_member(interaction.user.id)
    
        uid = str(interaction.user.id)
        cur_name = await get_user_rank_name(uid)
        main = await promotion_status(uid, SYSTEM_MAIN)
        alt = await promotion_status(uid, SYSTEM_ALT)
    
        embed = discord.Embed(title="📈Система повышения", color=0x9B7BFF)
        embed.add_field(name="Текущий ранг", value=cur_name, inline=False)
    
        if main.get("data"):
            d = main["data"]
            embed.add_field(
                name=f"Основная: {d['from']} → {d['to']}",
                value=f"Семейные: {d['family_have']}/{d['family_need']}",
                inline=False,
            )
    
        if alt.get("data"):
            d = alt["data"]
            extra = [
                f"Семейные: {d['family_have']}/{d['family_need']}",
                f"Тюнинг: {d['tuning_have']}/{d['tuning_need']}",
            ]
            embed.add_field(
                name=f"Альтернатива: {d['from']} → {d['to']}",
                value="\n".join(extra),
                inline=False,
            )
    
        await interaction.edit_original_response(embed=embed, view=PromoSubmitView())

    @discord.ui.button(label="💰Премия", style=discord.ButtonStyle.success)
    async def bonus_btn(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)
    
        uid = str(interaction.user.id)
    
        st = await require_static(interaction)
        if not st:
            return
    
        week_start, week_end = week_range_msk()
    
        res = await create_bonus_report_for_week(uid, week_start, week_end)
    
        if not res.get("ok"):
            embed = await build_profile_embed(uid)
            reason = res.get("reason")
    
            if reason == "no_contracts":
                embed.description = "❌ За неделю нет одобренных контрактов (база = 0)."
            elif reason == "no_static":
                embed.description = "❌ Не задан static."
            elif reason == "already_exists":
                embed.description = "❌ Отчёт за эту неделю уже существует."
            else:
                embed.description = f"❌ {reason or 'Не удалось создать отчёт.'}"
    
            await interaction.edit_original_response(embed=embed, view=MainPanelView())
            return
    
        report_id = int(res["report_id"])
    
        # первичный пересчёт суммы (чтобы в БД не лежал мусор)
        sums = await calc_live_sums(uid, week_start, week_end)
        contracts_sum = float(sums.get("base_sum") or 0)
        rank_bonus_sum = float(sums.get("rank_bonus_sum") or 0)
        tuning_rank_bonus_sum = float(sums.get("tuning_rank_bonus_sum") or 0)
        sea = 0.0
        total = float(contracts_sum + rank_bonus_sum + tuning_rank_bonus_sum + sea)
    
        await execute(
            "UPDATE bonus_reports SET total_amount=? WHERE report_id=?",
            (float(total), report_id)
        )
    
        embed = await build_bonus_preview_embed(uid, report_id, week_start, week_end, page=0, per_page=10)
        await interaction.edit_original_response(
            embed=embed,
            view=BonusPreviewPagerView(uid, report_id, week_start, week_end, page=0, per_page=10)
        )

    @discord.ui.button(label="🕓 Личные откаты", style=discord.ButtonStyle.secondary)
    async def personal_cooldowns_btn(self, interaction: discord.Interaction, button: Button):
        await show_personal_tuning_cooldown(interaction, MainPanelView, build_profile_embed)

    @discord.ui.button(label="💲 Выплаты", style=discord.ButtonStyle.secondary)
    async def payouts_btn(self, interaction: discord.Interaction, button: Button):
        from cogs.admin_panel import build_prices_embed
        embed = await build_prices_embed()
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="📝 Контракт", style=discord.ButtonStyle.primary)
    async def contract_btn(self, interaction: discord.Interaction, button: Button):
        embed = discord.Embed(
            title="📝 Отправить контракт",
            description="В Discord: команда `/контракт` (тип + скриншоты).\n"
                        "На сайте: панель → Контракты → Отправить (со скриншотами).",
            color=0x3498DB,
        )
        embed.add_field(
            name="Сайт",
            value="https://botdiscord-87a.pages.dev/contracts/new",
            inline=False,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="📊 Моя статистика", style=discord.ButtonStyle.secondary)
    async def my_stats_btn(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        uid = str(interaction.user.id)
        embed = await build_stats_embed(uid)
        await interaction.edit_original_response(embed=embed, view=StatsBackView())
        
class PromoSubmitView(View):
    def __init__(self):
        super().__init__(timeout=120)

    async def update_promo_report_message(client: discord.Client, report_id: int):
        rep = await fetch_one(
            "SELECT pr.*, r1.name AS from_rank_name, r2.name AS to_rank_name "
            "FROM promotion_reports pr "
            "LEFT JOIN ranks r1 ON pr.from_rank_id = r1.id "
            "LEFT JOIN ranks r2 ON pr.to_rank_id = r2.id "
            "WHERE pr.report_id = ?",
            (int(report_id),),
        )
        if not rep:
            return
    
        ch_id = rep["msg_channel_id"]
        msg_id = rep["msg_id"]
        if not ch_id or not msg_id:
            return
    
        try:
            channel = client.get_channel(int(ch_id)) or await client.fetch_channel(int(ch_id))
            msg = await channel.fetch_message(int(msg_id))
        except Exception:
            return
    
        user_id = rep["discord_id"]
        from_name = rep["from_rank_name"] or "?"
        to_name = rep["to_rank_name"] or "?"
    
        u = await fetch_one(
            "SELECT family_total, tuning_total, surname_changed FROM users WHERE discord_id = ?",
            (user_id,),
        )
        fam = int(u["family_total"] or 0) if u else 0
        tun = int(u["tuning_total"] or 0) if u else 0
        sur = bool(int(u["surname_changed"] or 0)) if u else False
    
        system_type = (rep["system_type"] or "").lower()
        sys_name = "Основная" if system_type == "main" else "Альтернативная"
    
        status = (rep["status"] or "NEW").upper()
        color = 0x00BCD4
        if status == "TAKEN":
            color = 0xF39C12
        elif status == "APPROVED":
            color = 0x2ECC71
        elif status == "REJECTED":
            color = 0xE74C3C
    
        embed = discord.Embed(title=f"Отчёт на повышение #{rep['report_id']}", color=color)
        embed.add_field(name="Пользователь", value=f"<@{user_id}>\n`{user_id}`", inline=True)
        embed.add_field(name="Система", value=sys_name, inline=True)
        embed.add_field(name="Статус", value=status, inline=True)
    
        embed.add_field(name="С ранга", value=from_name, inline=True)
        embed.add_field(name="На ранг", value=to_name, inline=True)
    
        embed.add_field(name="Семейных (всего)", value=str(fam), inline=True)
        embed.add_field(name="Тюнинг (всего)", value=str(tun), inline=True)
    
        if rep["taken_by"]:
            embed.add_field(name="Взял в работу", value=f"<@{rep['taken_by']}>", inline=True)
    
        if rep["reviewed_by"]:
            embed.add_field(name="Решение принял", value=f"<@{rep['reviewed_by']}>", inline=True)
    
        if status == "REJECTED" and rep["reason"]:
            embed.add_field(name="Причина", value=str(rep["reason"])[:1000], inline=False)
    
        if rep["submitted_at"]:
            embed.set_footer(text=f"submitted_at: {rep['submitted_at']}")
    
        # Главное: редактируем сообщение и убираем любые кнопки/вью
        await msg.edit(embed=embed, view=None)



    async def _send_report_to_channel(self, interaction: discord.Interaction, report_id: int, system_type: str):
        rep = await fetch_one(
            "SELECT pr.*, r1.name AS from_rank_name, r2.name AS to_rank_name "
            "FROM promotion_reports pr "
            "LEFT JOIN ranks r1 ON pr.from_rank_id = r1.id "
            "LEFT JOIN ranks r2 ON pr.to_rank_id = r2.id "
            "WHERE pr.report_id = ?",
            (report_id,),
        )
        if not rep:
            return

        user_id = rep["discord_id"]
        from_name = rep["from_rank_name"] or "?"
        to_name = rep["to_rank_name"] or "?"

        s = await fetch_one("SELECT value FROM settings WHERE key = 'promotion_channel_id'", ())
        channel_id = int(s["value"]) if s and s["value"] else None
        if not channel_id:
            return

        channel = interaction.client.get_channel(channel_id)
        if channel is None:
            try:
                channel = await interaction.client.fetch_channel(channel_id)
            except Exception:
                return

        sys_name = "Основная" if system_type == SYSTEM_MAIN else "Альтернативная"

        u = await fetch_one(
            "SELECT family_total, tuning_total, surname_changed FROM users WHERE discord_id = ?",
            (user_id,),
        )
        fam = int(u["family_total"] or 0) if u else 0
        tun = int(u["tuning_total"] or 0) if u else 0
        sur = bool(int(u["surname_changed"] or 0)) if u else False

        status = (rep["status"] or "NEW").upper()
        taken_by = rep["taken_by"]
        reviewed_by = rep["reviewed_by"]
        reason = rep["reason"]
        
        color = 0x00BCD4
        if status == "TAKEN":
            color = 0xF39C12
        elif status == "APPROVED":
            color = 0x2ECC71
        elif status == "REJECTED":
            color = 0xE74C3C
        
        embed = discord.Embed(title=f"Отчёт на повышение #{report_id}", color=color)
        embed.add_field(name="Пользователь", value=f"<@{user_id}>\n`{user_id}`", inline=True)
        embed.add_field(name="Система", value=sys_name, inline=True)
        embed.add_field(name="Статус", value=status, inline=True)
        
        embed.add_field(name="С ранга", value=from_name, inline=True)
        embed.add_field(name="На ранг", value=to_name, inline=True)
        
        embed.add_field(name="Семейных (всего)", value=str(fam), inline=True)
        embed.add_field(name="Тюнинг (всего)", value=str(tun), inline=True)
        
        if taken_by:
            embed.add_field(name="Взял", value=f"<@{taken_by}>", inline=True)
        
        if reviewed_by:
            embed.add_field(name="Решение принял", value=f"<@{reviewed_by}>", inline=True)
        
        if status == "REJECTED" and reason:
            embed.add_field(name="Причина", value=str(reason)[:1000], inline=False)
        
        msg = await channel.send(embed=embed)
        
        await execute(
            "UPDATE promotion_reports SET msg_channel_id = ?, msg_id = ? WHERE report_id = ?",
            (str(channel.id), str(msg.id), int(report_id)),
        )

    @discord.ui.button(label="Подать (Основная)", style=discord.ButtonStyle.primary)
    async def submit_main(self, interaction: discord.Interaction, button: Button):
        uid = str(interaction.user.id)

        if await has_active_promo_report(uid, SYSTEM_MAIN):
            await interaction.response.edit_message(
                embed=discord.Embed(
                    title="Отчёт на повышение",
                    description="❌ У тебя уже есть активный отчёт (NEW/TAKEN).",
                    color=0xE74C3C,
                ),
                view=MainPanelView(),
            )
            return

        res = await create_promo_report(uid, SYSTEM_MAIN)
        if not res["ok"]:
            await interaction.response.edit_message(
                embed=discord.Embed(title="Ошибка", description=f"❌ {res['reason']}", color=0xE74C3C),
                view=MainPanelView(),
            )
            return

        await self._send_report_to_channel(interaction, res["report_id"], SYSTEM_MAIN)

        embed = await build_profile_embed(uid)
        await interaction.response.edit_message(embed=embed, view=MainPanelView())

    @discord.ui.button(label="Подать (Альтернативная)", style=discord.ButtonStyle.primary)
    async def submit_alt(self, interaction: discord.Interaction, button: Button):
        uid = str(interaction.user.id)

        if await has_active_promo_report(uid, SYSTEM_ALT):
            await interaction.response.edit_message(
                embed=discord.Embed(
                    title="Отчёт на повышение",
                    description="❌ У тебя уже есть активный отчёт (NEW/TAKEN).",
                    color=0xE74C3C,
                ),
                view=MainPanelView(),
            )
            return

        res = await create_promo_report(uid, SYSTEM_ALT)
        if not res["ok"]:
            await interaction.response.edit_message(
                embed=discord.Embed(title="Ошибка", description=f"❌ {res['reason']}", color=0xE74C3C),
                view=MainPanelView(),
            )
            return

        await self._send_report_to_channel(interaction, res["report_id"], SYSTEM_ALT)

        embed = await build_profile_embed(uid)
        await interaction.response.edit_message(embed=embed, view=MainPanelView())

    @discord.ui.button(label="Назад", style=discord.ButtonStyle.secondary)
    async def back_btn(self, interaction: discord.Interaction, button: Button):
        uid = str(interaction.user.id)
        embed = await build_profile_embed(uid)
        await interaction.response.edit_message(embed=embed, view=MainPanelView())


async def setup(bot):
    await bot.add_cog(UserPanel(bot))
