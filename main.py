import asyncio
import discord
from discord.ext import commands, tasks
from discord import app_commands
from gspread.exceptions import APIError


from config import (
    DISCORD_TOKEN, GUILD_IDS_LIST,
    POLLING_INTERVAL, PENDING_PING_INTERVAL_SEC
)

from database import (
    init_db, migrate_db, fetch_one, get_setting,
    register_guild, is_module_enabled
)
from sheets_sync import poll_contracts
from services.pending_counter import upsert_pending_counter_message

from services.public_panel_embed import build_public_panel_embed
from views.public_profile_panel import PublicProfilePanelView

from cogs.admin_panel import AdminHubView, build_admin_hub_embed


ADMIN_HUB_CH_KEY = "admin_hub_channel_id"
ADMIN_HUB_MSG_KEY = "admin_hub_message_id"
PANEL_CH_KEY = "profile_panel_channel_id"
PANEL_MSG_KEY = "profile_panel_message_id"


intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True


# Multi-guild поддержка
last_pending_cnt = {}  # {guild_id: count}
poll_lock = asyncio.Lock()


class MyBot(commands.Bot):
    async def setup_hook(self):
        await init_db()
        await migrate_db()

        # Загрузка cogs
        await self.load_extension("cogs.admin_panel")
        print("[LOADED] cogs.admin_panel")

        await self.load_extension("cogs.user_panel")
        print("[LOADED] cogs.user_panel")

        await self.load_extension("cogs.applications")
        print("[LOADED] cogs.applications")

        await self.load_extension("cogs.cooldowns")
        print("[LOADED] cogs.cooldowns")

        await self.load_extension("cogs.bonus_reminder")
        print("[LOADED] cogs.bonus_reminder")

        await self.load_extension("cogs.settings")
        print("[LOADED] cogs.settings")

        await self.load_extension("cogs.role_sync")
        print("[LOADED] cogs.role_sync")

        self.add_view(PublicProfilePanelView())

        # Multi-guild: синхронизировать команды для всех серверов
        if GUILD_IDS_LIST:
            for guild_id in GUILD_IDS_LIST:
                guild = discord.Object(id=guild_id)
                try:
                    # Глобальные команды (/заявка и др.) тоже копируем на серверы
                    self.tree.copy_global_to(guild=guild)
                    synced = await self.tree.sync(guild=guild)
                    print(f"[SYNCED] {len(synced)} commands to guild {guild_id}")
                except Exception as e:
                    print(f"[ERROR] Failed to sync to guild {guild_id}: {e}")
        else:
            # Глобальная синхронизация (все серверы)
            synced = await self.tree.sync()
            print(f"[SYNCED] {len(synced)} commands globally")

        # Запуск фоновых задач
        if not poll_contracts_task.is_running():
            poll_contracts_task.start()

        if not pending_counter_task.is_running():
            pending_counter_task.start()

        if not profile_panel_refresh_task.is_running():
            profile_panel_refresh_task.start()

        if not admin_hub_refresh_task.is_running():
            admin_hub_refresh_task.start()

    async def on_ready(self):
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        print(f"Connected to {len(self.guilds)} guilds")

        # Зарегистрировать все серверы в БД
        for guild in self.guilds:
            icon_url = guild.icon.url if guild.icon else None
            await register_guild(str(guild.id), guild.name, icon_url)

        print("[READY] Bot is ready!")

    async def on_guild_join(self, guild: discord.Guild):
        """Автоматически регистрировать новые серверы"""
        print(f"[GUILD JOIN] Joined new guild: {guild.name} ({guild.id})")
        icon_url = guild.icon.url if guild.icon else None
        await register_guild(str(guild.id), guild.name, icon_url)

    async def on_guild_update(self, before: discord.Guild, after: discord.Guild):
        """Обновлять информацию о сервере"""
        if before.name != after.name or before.icon != after.icon:
            icon_url = after.icon.url if after.icon else None
            await register_guild(str(after.id), after.name, icon_url)


bot = MyBot(command_prefix=".", intents=intents)


async def run_poll_contracts_with_retry(guild_id: str, sheet_id: str = None, credentials_path: str = None):
    """
    Запуск импорта контрактов с повторными попытками при ошибках 503

    Args:
        guild_id: ID Discord сервера
        sheet_id: ID Google таблицы (опционально)
        credentials_path: Путь к credentials файлу (опционально)
    """
    delays = [1, 2, 4, 8]

    for attempt, delay in enumerate(delays, start=1):
        try:
            return await asyncio.to_thread(poll_contracts, guild_id, sheet_id, credentials_path)
        except APIError as e:
            text = str(e)
            is_503 = (
                "[503]" in text
                or '"code": 503' in text
                or "service is currently unavailable" in text.lower()
            )

            if not is_503:
                raise

            if attempt == len(delays):
                raise

            print(f"[Guild {guild_id}] Google Sheets 503, retry {attempt}/{len(delays) - 1} in {delay}s")
            await asyncio.sleep(delay)


@tasks.loop(minutes=5)
async def profile_panel_refresh_task():
    """Обновление панели профиля для всех серверов"""
    for guild in bot.guilds:
        guild_id = str(guild.id)

        # Проверить включен ли модуль
        if not await is_module_enabled(guild_id, "user_panel"):
            continue

        try:
            ch_id = await get_setting(PANEL_CH_KEY, guild_id)
            msg_id = await get_setting(PANEL_MSG_KEY, guild_id)
            if not ch_id or not msg_id:
                continue

            channel = guild.get_channel(int(ch_id))
            if channel is None:
                continue

            msg = await channel.fetch_message(int(msg_id))
            embed = await build_public_panel_embed(guild)
            await msg.edit(embed=embed, view=PublicProfilePanelView())
        except discord.NotFound:
            continue
        except Exception as e:
            print(f"[profile_panel_refresh_task] guild {guild_id} error: {e}")


@profile_panel_refresh_task.before_loop
async def _before_profile_panel_refresh_task():
    await bot.wait_until_ready()


@tasks.loop(minutes=5)
async def admin_hub_refresh_task():
    """Обновление админ панели для всех серверов"""
    for guild in bot.guilds:
        guild_id = str(guild.id)

        # Проверить включен ли модуль
        if not await is_module_enabled(guild_id, "admin_panel"):
            continue

        try:
            ch_id = await get_setting(ADMIN_HUB_CH_KEY, guild_id)
            msg_id = await get_setting(ADMIN_HUB_MSG_KEY, guild_id)
            if not ch_id or not msg_id:
                continue

            channel = guild.get_channel(int(ch_id))
            if channel is None:
                continue

            msg = await channel.fetch_message(int(msg_id))
            embed = await build_admin_hub_embed(guild)
            await msg.edit(embed=embed)
        except discord.NotFound:
            continue
        except Exception as e:
            print(f"[admin_hub_refresh_task] guild {guild_id} error: {e}")


@admin_hub_refresh_task.before_loop
async def _before_admin_hub_refresh_task():
    await bot.wait_until_ready()


@tasks.loop(seconds=PENDING_PING_INTERVAL_SEC)
async def pending_counter_task():
    """Счетчик ожидающих контрактов для всех серверов"""
    global last_pending_cnt

    for guild in bot.guilds:
        guild_id = str(guild.id)

        # Проверить включен ли модуль
        if not await is_module_enabled(guild_id, "contracts"):
            continue

        try:
            row = await fetch_one(
                "SELECT COUNT(*) AS cnt FROM contracts WHERE guild_id=? AND confirm_status='PENDING'",
                (guild_id,)
            )
            cnt = int(row["cnt"] or 0)

            # Получить роль для пинга из настроек сервера
            pending_role_str = await get_setting("pending_ping_role_id", guild_id)
            pending_role_id = int(pending_role_str) if pending_role_str and pending_role_str != "0" else None

            prev_cnt = last_pending_cnt.get(guild_id)
            should_ping = (
                pending_role_id
                and prev_cnt is not None
                and cnt > prev_cnt
                and cnt > 0
            )

            ping = f"<@&{pending_role_id}> " if should_ping else ""
            content = f"{ping}⏳ Очередь контрактов: {cnt}"

            await upsert_pending_counter_message(bot, content, guild_id)
            last_pending_cnt[guild_id] = cnt
        except Exception as e:
            print(f"[pending_counter_task] guild {guild_id} error: {e}")


@pending_counter_task.before_loop
async def _before_pending_counter_task():
    await bot.wait_until_ready()


@tasks.loop(seconds=POLLING_INTERVAL)
async def poll_contracts_task():
    """Импорт контрактов из Google Sheets (если модуль включен)"""
    if poll_lock.locked():
        print("[poll_contracts_task] skipped: already running")
        return

    async with poll_lock:
        for guild in bot.guilds:
            guild_id = str(guild.id)

            # Проверить включен ли модуль и настройки Google Sheets
            if not await is_module_enabled(guild_id, "contracts"):
                continue

            # Проверить есть ли настройка sheets_enabled для этого сервера
            sheets_enabled = await get_setting("sheets_enabled", guild_id)
            if sheets_enabled == "false":
                continue

            # Получить настройки Google Sheets для этого сервера
            sheet_id = await get_setting("sheet_id", guild_id)
            credentials_path = await get_setting("credentials_path", guild_id)

            # Если настройки не указаны, используются значения по умолчанию из config.py
            try:
                count = await run_poll_contracts_with_retry(guild_id, sheet_id, credentials_path)
                if count > 0:
                    print(f"[Guild {guild_id}] Imported {count} new contracts from Sheets")
            except APIError as e:
                print(f"[poll_contracts_task] guild {guild_id} APIError: {e}")
            except Exception as e:
                print(f"[poll_contracts_task] guild {guild_id} error: {e!r}")


@poll_contracts_task.before_loop
async def _before_poll_contracts_task():
    await bot.wait_until_ready()


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CheckFailure):
        if interaction.response.is_done():
            await interaction.followup.send("❌ Нет прав.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Нет прав.", ephemeral=True)
        return
    raise error


bot.run(DISCORD_TOKEN)
