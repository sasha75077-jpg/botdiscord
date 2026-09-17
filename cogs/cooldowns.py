from datetime import datetime, timedelta, timezone
import sqlite3
import discord
from discord.ext import commands, tasks

from database import execute, fetch_one, fetch_all, get_setting


UTC = timezone.utc

SET_CD_NOTIFY_CHANNEL = "contracts_cd_notify_channel_id"
SET_CD_NOTIFY_ROLE = "contracts_cd_notify_role_id"

GLOBAL_COOLDOWNS = {
    "sea": {"title": "Дары моря", "default_seconds": 24 * 3600},
    "plane_goods": {"title": "Товары с самолета", "default_seconds": 24 * 3600},
    "atelier": {"title": "Ателье", "default_seconds": 24 * 3600},
    "metallurgy_delivery": {"title": "Металлургия сдача", "default_seconds": 24 * 3600},
}

TUNING_TITLE = "Тюнинг"
TUNING_DEFAULT_SECONDS = 6 * 3600


def utc_now() -> datetime:
    return datetime.now(UTC)


def to_iso(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat()


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(UTC)
    except:
        return None


def fmt_dt(dt: datetime | None) -> str:
    if not dt:
        return "—"
    return dt.strftime("%d.%m.%Y %H:%M:%S UTC")


def fmt_remaining(seconds: int) -> str:
    if seconds <= 0:
        return "Готово"

    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)

    parts = []
    if h:
        parts.append(f"{h}ч")
    if m:
        parts.append(f"{m}м")
    if s or not parts:
        parts.append(f"{s}с")
    return " ".join(parts)


def global_cd_key(code: str) -> str:
    return f"global:{code}"


def tuning_cd_key(discord_id: int | str) -> str:
    return f"user:{discord_id}:tuning"


async def ensure_cooldowns_table():
    await execute(
        """
        CREATE TABLE IF NOT EXISTS contract_cooldowns (
            cooldown_key TEXT PRIMARY KEY,
            cooldown_type TEXT NOT NULL,
            owner_discord_id TEXT,
            started_by TEXT,
            started_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            note TEXT,
            notified_done INTEGER NOT NULL DEFAULT 0
        )
        """,
        ()
    )


async def set_cooldown(
    cooldown_key: str,
    cooldown_type: str,
    duration_seconds: int,
    owner_discord_id: str | None = None,
    started_by: str | None = None,
    note: str | None = None,
):
    now = utc_now()
    expires = now + timedelta(seconds=int(duration_seconds))

    await execute(
        """
        INSERT INTO contract_cooldowns
            (cooldown_key, cooldown_type, owner_discord_id, started_by, started_at, expires_at, note, notified_done)
        VALUES (?, ?, ?, ?, ?, ?, ?, 0)
        ON CONFLICT(cooldown_key) DO UPDATE SET
            cooldown_type=excluded.cooldown_type,
            owner_discord_id=excluded.owner_discord_id,
            started_by=excluded.started_by,
            started_at=excluded.started_at,
            expires_at=excluded.expires_at,
            note=excluded.note,
            notified_done=0
        """,
        (
            str(cooldown_key),
            str(cooldown_type),
            str(owner_discord_id) if owner_discord_id is not None else None,
            str(started_by) if started_by is not None else None,
            to_iso(now),
            to_iso(expires),
            note,
        ),
    )


async def clear_cooldown(cooldown_key: str):
    await execute("DELETE FROM contract_cooldowns WHERE cooldown_key = ?", (str(cooldown_key),))


async def get_cooldown(cooldown_key: str):
    row = await fetch_one(
        "SELECT * FROM contract_cooldowns WHERE cooldown_key = ?",
        (str(cooldown_key),)
    )
    if not row:
        return None

    row = dict(row)
    started_dt = parse_dt(row.get("started_at"))
    expires_dt = parse_dt(row.get("expires_at"))
    now = utc_now()
    seconds_left = int((expires_dt - now).total_seconds()) if expires_dt else 0

    row["started_dt"] = started_dt
    row["expires_dt"] = expires_dt
    row["seconds_left"] = seconds_left
    row["is_active"] = seconds_left > 0
    row["remaining_text"] = fmt_remaining(seconds_left)
    return row


async def mark_notified(cooldown_key: str):
    await execute(
        "UPDATE contract_cooldowns SET notified_done = 1 WHERE cooldown_key = ?",
        (str(cooldown_key),)
    )


async def get_expired_unnotified():
    now_iso = to_iso(utc_now())
    rows = await fetch_all(
        """
        SELECT *
        FROM contract_cooldowns
        WHERE expires_at <= ?
          AND notified_done = 0
        """,
        (now_iso,)
    )
    return rows or []


async def build_global_cooldowns_embed() -> discord.Embed:
    embed = discord.Embed(
        title="⏱ КД контрактов",
        description="Выберите нужный глобальный контракт.",
        color=0x9B7BFF,
    )

    for code, meta in GLOBAL_COOLDOWNS.items():
        row = await get_cooldown(global_cd_key(code))
        if row and row["is_active"]:
            text = f"⏳ Осталось: {row['remaining_text']}"
            if row.get("started_by"):
                text += f"\nЗапустил: <@{row['started_by']}>"
            if row.get("expires_dt"):
                text += f"\nДо: {fmt_dt(row['expires_dt'])}"
        else:
            text = "✅ Готово"

        embed.add_field(name=meta["title"], value=text, inline=False)

    return embed


async def build_global_cd_detail_embed(code: str) -> discord.Embed:
    meta = GLOBAL_COOLDOWNS[code]
    row = await get_cooldown(global_cd_key(code))

    embed = discord.Embed(
        title=f"⏱ {meta['title']}",
        color=0x9B7BFF,
    )

    if row and row["is_active"]:
        embed.description = "Таймер активен."
        embed.add_field(name="Статус", value=f"⏳ Осталось: {row['remaining_text']}", inline=False)
        embed.add_field(
            name="Запустил",
            value=f"<@{row['started_by']}>" if row.get("started_by") else "—",
            inline=True
        )
        embed.add_field(name="До", value=fmt_dt(row.get("expires_dt")), inline=True)
    else:
        embed.description = "Таймер не активен."
        embed.add_field(name="Статус", value="✅ Готово", inline=False)

    embed.set_footer(text="Кнопка 'Запустить' всегда ставит новый таймер от текущего времени.")
    return embed


async def build_personal_tuning_embed(discord_id: str) -> discord.Embed:
    row = await get_cooldown(tuning_cd_key(discord_id))

    embed = discord.Embed(
        title="🕓 Личные откаты",
        description="Здесь отображается ваш личный откат на контракт \"Тюнинг\".",
        color=0x9B7BFF,
    )

    if row and row["is_active"]:
        embed.add_field(name="Тюнинг", value=f"⏳ Осталось: {row['remaining_text']}", inline=False)
        embed.add_field(name="До", value=fmt_dt(row.get("expires_dt")), inline=False)
    else:
        embed.add_field(name="Тюнинг", value="✅ Готово", inline=False)

    return embed


class CooldownTimeModal(discord.ui.Modal):
    def __init__(self, title: str, after_submit):
        super().__init__(title=title)
        self.after_submit = after_submit

        self.hours = discord.ui.TextInput(
            label="Часы",
            placeholder="Например: 24",
            default="0",
            required=False,
            max_length=5,
        )
        self.minutes = discord.ui.TextInput(
            label="Минуты",
            placeholder="Например: 0",
            default="0",
            required=False,
            max_length=5,
        )
        self.seconds = discord.ui.TextInput(
            label="Секунды",
            placeholder="Например: 0",
            default="0",
            required=False,
            max_length=5,
        )

        self.add_item(self.hours)
        self.add_item(self.minutes)
        self.add_item(self.seconds)

    async def on_submit(self, interaction: discord.Interaction):
        def parse_num(v: str) -> int:
            v = (v or "").strip()
            if v == "":
                return 0
            if not v.isdigit():
                raise ValueError("Нужно вводить только целые неотрицательные числа.")
            return int(v)

        try:
            h = parse_num(str(self.hours))
            m = parse_num(str(self.minutes))
            s = parse_num(str(self.seconds))
            total = h * 3600 + m * 60 + s
            if total <= 0:
                await interaction.response.send_message("❌ Время должно быть больше 0 секунд.", ephemeral=True)
                return
        except ValueError as e:
            await interaction.response.send_message(f"❌ {e}", ephemeral=True)
            return

        await self.after_submit(interaction, total)


class ConfirmResetView(discord.ui.View):
    def __init__(self, on_confirm, on_cancel):
        super().__init__(timeout=120)
        self.on_confirm = on_confirm
        self.on_cancel = on_cancel

    @discord.ui.button(label="✅ Подтвердить", style=discord.ButtonStyle.danger)
    async def confirm_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.on_confirm(interaction)

    @discord.ui.button(label="❌ Отмена", style=discord.ButtonStyle.secondary)
    async def cancel_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.on_cancel(interaction)


class GlobalCooldownsListView(discord.ui.View):
    def __init__(self, admin_back_view_factory):
        super().__init__(timeout=300)
        self.admin_back_view_factory = admin_back_view_factory

    @discord.ui.button(label="🌊 Дары моря", style=discord.ButtonStyle.primary)
    async def sea_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await show_global_cd_detail(interaction, "sea", self.admin_back_view_factory)

    @discord.ui.button(label="✈️ Товары с самолета", style=discord.ButtonStyle.primary)
    async def plane_goods_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await show_global_cd_detail(interaction, "plane_goods", self.admin_back_view_factory)

    @discord.ui.button(label="🧵 Ателье", style=discord.ButtonStyle.primary)
    async def atelier_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await show_global_cd_detail(interaction, "atelier", self.admin_back_view_factory)

    @discord.ui.button(label="⛏️ Металлургия сдача", style=discord.ButtonStyle.primary)
    async def metallurgy_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await show_global_cd_detail(interaction, "metallurgy_delivery", self.admin_back_view_factory)

    @discord.ui.button(label="🔄 Обновить", style=discord.ButtonStyle.secondary)
    async def refresh_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = await build_global_cooldowns_embed()
        await interaction.response.edit_message(
            embed=embed,
            view=GlobalCooldownsListView(self.admin_back_view_factory)
        )

    @discord.ui.button(label="⬅️ Назад", style=discord.ButtonStyle.secondary)
    async def back_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="Админ-панель", description="Выберите раздел:", color=0x9B7BFF)
        await interaction.response.edit_message(embed=embed, view=self.admin_back_view_factory())


class GlobalCooldownDetailView(discord.ui.View):
    def __init__(self, code: str, admin_back_view_factory):
        super().__init__(timeout=300)
        self.code = code
        self.admin_back_view_factory = admin_back_view_factory

    async def redraw(self, interaction: discord.Interaction):
        embed = await build_global_cd_detail_embed(self.code)
        await interaction.response.edit_message(
            embed=embed,
            view=GlobalCooldownDetailView(self.code, self.admin_back_view_factory)
        )

    @discord.ui.button(label="▶️ Запустить", style=discord.ButtonStyle.success)
    async def start_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        meta = GLOBAL_COOLDOWNS[self.code]
        await set_cooldown(
            cooldown_key=global_cd_key(self.code),
            cooldown_type=self.code,
            duration_seconds=meta["default_seconds"],
            started_by=str(interaction.user.id),
        )
        await self.redraw(interaction)

    @discord.ui.button(label="🗑 Сбросить", style=discord.ButtonStyle.danger)
    async def reset_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        async def on_confirm(i: discord.Interaction):
            await clear_cooldown(global_cd_key(self.code))
            embed = await build_global_cd_detail_embed(self.code)
            await i.response.edit_message(
                embed=embed,
                view=GlobalCooldownDetailView(self.code, self.admin_back_view_factory)
            )

        async def on_cancel(i: discord.Interaction):
            embed = await build_global_cd_detail_embed(self.code)
            await i.response.edit_message(
                embed=embed,
                view=GlobalCooldownDetailView(self.code, self.admin_back_view_factory)
            )

        embed = discord.Embed(
            title="Подтверждение сброса",
            description=f"Сбросить КД для **{GLOBAL_COOLDOWNS[self.code]['title']}**?",
            color=0xE67E22
        )
        await interaction.response.edit_message(embed=embed, view=ConfirmResetView(on_confirm, on_cancel))

    @discord.ui.button(label="🕓 Изменить время", style=discord.ButtonStyle.primary)
    async def edit_time_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        source_message = interaction.message
        code = self.code
        admin_back_view_factory = self.admin_back_view_factory

        async def after_submit(modal_interaction: discord.Interaction, total_seconds: int):
            await modal_interaction.response.defer(ephemeral=True)
            await set_cooldown(
                cooldown_key=global_cd_key(code),
                cooldown_type=code,
                duration_seconds=total_seconds,
                started_by=str(modal_interaction.user.id),
                note="manual_time_set",
            )
            embed = await build_global_cd_detail_embed(code)
            try:
                await source_message.edit(
                    embed=embed,
                    view=GlobalCooldownDetailView(code, admin_back_view_factory)
                )
            except Exception as e:
                print("[Cooldowns] edit global detail after modal failed:", repr(e))

        await interaction.response.send_modal(
            CooldownTimeModal(
                title=f"Изменить время: {GLOBAL_COOLDOWNS[self.code]['title']}",
                after_submit=after_submit,
            )
        )

    @discord.ui.button(label="🔄 Обновить", style=discord.ButtonStyle.secondary)
    async def refresh_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.redraw(interaction)

    @discord.ui.button(label="⬅️ Назад", style=discord.ButtonStyle.secondary)
    async def back_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = await build_global_cooldowns_embed()
        await interaction.response.edit_message(
            embed=embed,
            view=GlobalCooldownsListView(self.admin_back_view_factory)
        )


class PersonalTuningCooldownView(discord.ui.View):
    def __init__(self, main_panel_view_factory, profile_embed_factory):
        super().__init__(timeout=300)
        self.main_panel_view_factory = main_panel_view_factory
        self.profile_embed_factory = profile_embed_factory

    async def redraw(self, interaction: discord.Interaction):
        embed = await build_personal_tuning_embed(str(interaction.user.id))
        await interaction.response.edit_message(
            embed=embed,
            view=PersonalTuningCooldownView(self.main_panel_view_factory, self.profile_embed_factory)
        )

    @discord.ui.button(label="▶️ Запустить", style=discord.ButtonStyle.success)
    async def start_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        uid = str(interaction.user.id)
        await set_cooldown(
            cooldown_key=tuning_cd_key(uid),
            cooldown_type="tuning",
            duration_seconds=TUNING_DEFAULT_SECONDS,
            owner_discord_id=uid,
            started_by=uid,
        )
        await self.redraw(interaction)

    @discord.ui.button(label="🗑 Сбросить", style=discord.ButtonStyle.danger)
    async def reset_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        uid = str(interaction.user.id)

        async def on_confirm(i: discord.Interaction):
            await clear_cooldown(tuning_cd_key(uid))
            embed = await build_personal_tuning_embed(uid)
            await i.response.edit_message(
                embed=embed,
                view=PersonalTuningCooldownView(self.main_panel_view_factory, self.profile_embed_factory)
            )

        async def on_cancel(i: discord.Interaction):
            embed = await build_personal_tuning_embed(uid)
            await i.response.edit_message(
                embed=embed,
                view=PersonalTuningCooldownView(self.main_panel_view_factory, self.profile_embed_factory)
            )

        embed = discord.Embed(
            title="Подтверждение сброса",
            description="Сбросить ваш личный КД на **Тюнинг**?",
            color=0xE67E22
        )
        await interaction.response.edit_message(embed=embed, view=ConfirmResetView(on_confirm, on_cancel))

    @discord.ui.button(label="🕓 Изменить время", style=discord.ButtonStyle.primary)
    async def edit_time_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        uid = str(interaction.user.id)
        source_message = interaction.message
        main_panel_view_factory = self.main_panel_view_factory
        profile_embed_factory = self.profile_embed_factory

        async def after_submit(modal_interaction: discord.Interaction, total_seconds: int):
            await modal_interaction.response.defer(ephemeral=True)
            await set_cooldown(
                cooldown_key=tuning_cd_key(uid),
                cooldown_type="tuning",
                duration_seconds=total_seconds,
                owner_discord_id=uid,
                started_by=uid,
                note="manual_time_set",
            )
            embed = await build_personal_tuning_embed(uid)
            try:
                await source_message.edit(
                    embed=embed,
                    view=PersonalTuningCooldownView(main_panel_view_factory, profile_embed_factory)
                )
            except Exception as e:
                print("[Cooldowns] edit personal tuning after modal failed:", repr(e))

        await interaction.response.send_modal(
            CooldownTimeModal(
                title="Изменить время: Тюнинг",
                after_submit=after_submit,
            )
        )

    @discord.ui.button(label="🔄 Обновить", style=discord.ButtonStyle.secondary)
    async def refresh_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.redraw(interaction)

    @discord.ui.button(label="⬅️ Назад", style=discord.ButtonStyle.secondary)
    async def back_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = await self.profile_embed_factory(str(interaction.user.id))
        await interaction.response.edit_message(
            embed=embed,
            view=self.main_panel_view_factory()
        )


async def show_global_cooldowns(interaction: discord.Interaction, admin_back_view_factory):
    embed = await build_global_cooldowns_embed()
    await interaction.response.edit_message(embed=embed, view=GlobalCooldownsListView(admin_back_view_factory))


async def show_global_cd_detail(interaction: discord.Interaction, code: str, admin_back_view_factory):
    embed = await build_global_cd_detail_embed(code)
    await interaction.response.edit_message(embed=embed, view=GlobalCooldownDetailView(code, admin_back_view_factory))


async def show_personal_tuning_cooldown(interaction: discord.Interaction, main_panel_view_factory, profile_embed_factory):
    embed = await build_personal_tuning_embed(str(interaction.user.id))
    await interaction.response.edit_message(
        embed=embed,
        view=PersonalTuningCooldownView(main_panel_view_factory, profile_embed_factory)
    )


class CooldownsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.cooldowns_notifier.start()

    def cog_unload(self):
        self.cooldowns_notifier.cancel()

    @tasks.loop(seconds=30)
    async def cooldowns_notifier(self):
        try:
            rows = await get_expired_unnotified()
            print(f"[CooldownsCog] expired rows: {len(rows)}")
        except sqlite3.OperationalError as e:
            print("[CooldownsCog] sqlite locked while reading expired rows:", repr(e))
            return
        except Exception as e:
            print("[CooldownsCog] failed to load expired rows:", repr(e))
            return

        for raw_row in rows:
            try:
                row = dict(raw_row)
                cd_type = row.get("cooldown_type")
                cd_key = row.get("cooldown_key")

                print(f"[CooldownsCog] processing key={cd_key}, type={cd_type}")

                if cd_type == "tuning":
                    owner_id = row.get("owner_discord_id")
                    print(f"[CooldownsCog] tuning owner_id={owner_id}")

                    if owner_id and str(owner_id).isdigit():
                        user = self.bot.get_user(int(owner_id))

                        if user is None:
                            try:
                                user = await self.bot.fetch_user(int(owner_id))
                            except Exception as e:
                                print("[CooldownsCog] fetch_user failed:", repr(e))
                                user = None

                        if user is not None:
                            try:
                                await user.send(
                                    "✅ Ваш контракт **Тюнинг** откатился. Вы можете взять новый личный контракт."
                                )
                                print(f"[CooldownsCog] DM sent to user {owner_id}")
                            except discord.Forbidden as e:
                                print(f"[CooldownsCog] DM forbidden for user {owner_id}: {repr(e)}")
                            except Exception as e:
                                print(f"[CooldownsCog] DM send failed for user {owner_id}: {repr(e)}")
                        else:
                            print(f"[CooldownsCog] user not found: {owner_id}")
                    else:
                        print(f"[CooldownsCog] invalid owner_discord_id: {owner_id}")

                elif cd_type in GLOBAL_COOLDOWNS:
                    channel_id = await get_setting(SET_CD_NOTIFY_CHANNEL)
                    role_id = await get_setting(SET_CD_NOTIFY_ROLE)

                    print(
                        f"[CooldownsCog] global notify settings: "
                        f"channel_id={channel_id}, role_id={role_id}"
                    )

                    channel = None
                    if channel_id and str(channel_id).isdigit():
                        channel = self.bot.get_channel(int(channel_id))

                        if channel is None:
                            try:
                                channel = await self.bot.fetch_channel(int(channel_id))
                            except Exception as e:
                                print("[CooldownsCog] fetch_channel failed:", repr(e))
                                channel = None

                    if channel is not None:
                        title = GLOBAL_COOLDOWNS[cd_type]["title"]
                        text = f"✅ Откат контракта **{title}** завершён."

                        if role_id and str(role_id).isdigit():
                            text = f"<@&{role_id}> {text}"

                        try:
                            await channel.send(
                                text,
                                allowed_mentions=discord.AllowedMentions(roles=True)
                            )
                            print(f"[CooldownsCog] channel notification sent for {cd_key}")
                        except discord.Forbidden as e:
                            print(f"[CooldownsCog] no permission to send in channel {channel_id}: {repr(e)}")
                        except Exception as e:
                            print(f"[CooldownsCog] channel send failed for {cd_key}: {repr(e)}")
                    else:
                        print(f"[CooldownsCog] notify channel not found: {channel_id}")

                else:
                    print(f"[CooldownsCog] unknown cooldown type: {cd_type}")

                try:
                    await mark_notified(cd_key)
                    print(f"[CooldownsCog] marked notified: {cd_key}")
                except sqlite3.OperationalError as e:
                    print(f"[CooldownsCog] sqlite locked on mark_notified for {cd_key}: {repr(e)}")
                except Exception as e:
                    print(f"[CooldownsCog] mark_notified failed for {cd_key}: {repr(e)}")

            except Exception as e:
                print("[CooldownsCog] notify row error:", repr(e))

    @cooldowns_notifier.before_loop
    async def before_cooldowns_notifier(self):
        await self.bot.wait_until_ready()
        try:
            await ensure_cooldowns_table()
            print("[CooldownsCog] notifier ready")
        except Exception as e:
            print("[CooldownsCog] ensure_cooldowns_table failed:", repr(e))


async def setup(bot: commands.Bot):
    await bot.add_cog(CooldownsCog(bot))

