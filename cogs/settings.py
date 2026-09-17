"""
Cog для настройки интеграций и параметров сервера
"""
import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

from database import get_setting, set_setting, fetch_one
import gspread
from gspread.exceptions import APIError, SpreadsheetNotFound


class SettingsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="setup_sheets",
        description="Настроить интеграцию с Google Sheets для импорта контрактов"
    )
    @app_commands.describe(
        sheet_id="ID Google таблицы (из URL)",
        enabled="Включить или выключить импорт из Google Sheets",
        credentials_path="Путь к credentials.json (например: credentials/123456789.json)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_sheets(
        self,
        interaction: discord.Interaction,
        sheet_id: Optional[str] = None,
        enabled: Optional[bool] = None,
        credentials_path: Optional[str] = None
    ):
        """Настройка Google Sheets интеграции для сервера"""
        await interaction.response.defer(ephemeral=True)

        guild_id = str(interaction.guild_id)

        # Если не указаны параметры, показать текущие настройки
        if sheet_id is None and enabled is None and credentials_path is None:
            current_sheet_id = await get_setting("sheet_id", guild_id)
            current_enabled = await get_setting("sheets_enabled", guild_id)
            current_credentials_path = await get_setting("credentials_path", guild_id)

            embed = discord.Embed(
                title="⚙️ Настройки Google Sheets",
                color=discord.Color.blue()
            )

            embed.add_field(
                name="Sheet ID",
                value=f"`{current_sheet_id or 'Не настроено'}`",
                inline=False
            )
            embed.add_field(
                name="Статус",
                value="✅ Включено" if current_enabled == "true" else "❌ Выключено",
                inline=False
            )
            embed.add_field(
                name="Credentials",
                value=f"`{current_credentials_path or 'credentials.json'}`",
                inline=False
            )

            embed.add_field(
                name="📝 Как использовать",
                value=(
                    "**Установить Sheet ID:**\n"
                    "`/setup_sheets sheet_id:YOUR_SHEET_ID`\n\n"
                    "**Установить credentials:**\n"
                    f"`/setup_sheets credentials_path:credentials/{guild_id}.json`\n\n"
                    "**Включить импорт:**\n"
                    "`/setup_sheets enabled:True`\n\n"
                    "**Выключить импорт:**\n"
                    "`/setup_sheets enabled:False`"
                ),
                inline=False
            )

            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # Обновить credentials_path
        if credentials_path is not None:
            import os
            # Проверить что файл существует
            if not os.path.exists(credentials_path):
                await interaction.followup.send(
                    f"❌ Файл не найден: `{credentials_path}`\n\n"
                    f"💡 Подсказка: Поместите credentials файл в папку `credentials/` и назовите его `{guild_id}.json`",
                    ephemeral=True
                )
                return

            await set_setting("credentials_path", credentials_path, guild_id)

            embed = discord.Embed(
                title="✅ Credentials путь обновлен",
                description=f"Путь: `{credentials_path}`",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

        # Обновить sheet_id
        if sheet_id is not None:
            # Валидация: проверить что можем подключиться
            creds_path = await get_setting("credentials_path", guild_id) or "credentials.json"

            try:
                gc = gspread.service_account(filename=creds_path)
                sh = gc.open_by_key(sheet_id)

                # Попробовать получить список листов для проверки доступа
                worksheets = sh.worksheets()

                await set_setting("sheet_id", sheet_id, guild_id)

                embed = discord.Embed(
                    title="✅ Sheet ID обновлен",
                    description=f"**Таблица:** `{sh.title}`\n**Листы:** {len(worksheets)}",
                    color=discord.Color.green()
                )

                # Показать список листов
                sheet_names = [ws.title for ws in worksheets[:5]]
                if len(worksheets) > 5:
                    sheet_names.append(f"... и еще {len(worksheets) - 5}")
                embed.add_field(
                    name="Найденные листы",
                    value="\n".join(f"• {name}" for name in sheet_names),
                    inline=False
                )

                await interaction.followup.send(embed=embed, ephemeral=True)

            except FileNotFoundError:
                await interaction.followup.send(
                    f"❌ Ошибка: файл credentials не найден: `{creds_path}`\n\n"
                    "Убедитесь что credentials.json существует и доступен.",
                    ephemeral=True
                )
                return
            except SpreadsheetNotFound:
                await interaction.followup.send(
                    f"❌ Ошибка: таблица с ID `{sheet_id}` не найдена.\n\n"
                    "Проверьте:\n"
                    "• Правильность Sheet ID\n"
                    "• Что Service Account имеет доступ к таблице",
                    ephemeral=True
                )
                return
            except APIError as e:
                await interaction.followup.send(
                    f"❌ Ошибка Google API: {e}\n\n"
                    "Проверьте что Google Sheets API включен в проекте.",
                    ephemeral=True
                )
                return
            except Exception as e:
                await interaction.followup.send(
                    f"❌ Неожиданная ошибка: {e}",
                    ephemeral=True
                )
                return

        # Обновить enabled статус
        if enabled is not None:
            new_value = "true" if enabled else "false"
            await set_setting("sheets_enabled", new_value, guild_id)

            status_text = "включен ✅" if enabled else "выключен ❌"

            embed = discord.Embed(
                title=f"⚙️ Импорт из Google Sheets {status_text}",
                color=discord.Color.green() if enabled else discord.Color.orange()
            )

            if enabled:
                # Проверить что sheet_id настроен
                current_sheet_id = await get_setting("sheet_id", guild_id)
                if not current_sheet_id:
                    embed.add_field(
                        name="⚠️ Внимание",
                        value="Sheet ID не настроен! Используйте `/setup_sheets sheet_id:...`",
                        inline=False
                    )

            await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(
        name="setup_channels",
        description="Настроить каналы и роли для бота"
    )
    @app_commands.describe(
        admin_contracts_channel="Канал для админских контрактов",
        pending_counter_channel="Канал для счетчика ожидающих контрактов",
        pending_ping_role="Роль для пинга при новых контрактах"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_channels(
        self,
        interaction: discord.Interaction,
        admin_contracts_channel: Optional[discord.TextChannel] = None,
        pending_counter_channel: Optional[discord.TextChannel] = None,
        pending_ping_role: Optional[discord.Role] = None
    ):
        """Настройка каналов и ролей для сервера"""
        await interaction.response.defer(ephemeral=True)

        guild_id = str(interaction.guild_id)

        # Если не указаны параметры, показать текущие настройки
        if all(x is None for x in [admin_contracts_channel, pending_counter_channel, pending_ping_role]):
            admin_ch = await get_setting("admin_contracts_channel_id", guild_id)
            counter_ch = await get_setting("pending_counter_channel_id", guild_id)
            ping_role = await get_setting("pending_ping_role_id", guild_id)

            embed = discord.Embed(
                title="⚙️ Настройки каналов и ролей",
                color=discord.Color.blue()
            )

            # Admin contracts channel
            if admin_ch:
                try:
                    ch = interaction.guild.get_channel(int(admin_ch))
                    embed.add_field(
                        name="Канал админских контрактов",
                        value=ch.mention if ch else f"❌ Канал {admin_ch} не найден",
                        inline=False
                    )
                except:
                    embed.add_field(
                        name="Канал админских контрактов",
                        value=f"`{admin_ch}` (не найден)",
                        inline=False
                    )
            else:
                embed.add_field(
                    name="Канал админских контрактов",
                    value="❌ Не настроено",
                    inline=False
                )

            # Pending counter channel
            if counter_ch:
                try:
                    ch = interaction.guild.get_channel(int(counter_ch))
                    embed.add_field(
                        name="Канал счетчика ожидающих",
                        value=ch.mention if ch else f"❌ Канал {counter_ch} не найден",
                        inline=False
                    )
                except:
                    embed.add_field(
                        name="Канал счетчика ожидающих",
                        value=f"`{counter_ch}` (не найден)",
                        inline=False
                    )
            else:
                embed.add_field(
                    name="Канал счетчика ожидающих",
                    value="❌ Не настроено",
                    inline=False
                )

            # Ping role
            if ping_role and ping_role != "0":
                try:
                    role = interaction.guild.get_role(int(ping_role))
                    embed.add_field(
                        name="Роль для пинга",
                        value=role.mention if role else f"❌ Роль {ping_role} не найдена",
                        inline=False
                    )
                except:
                    embed.add_field(
                        name="Роль для пинга",
                        value=f"`{ping_role}` (не найдена)",
                        inline=False
                    )
            else:
                embed.add_field(
                    name="Роль для пинга",
                    value="❌ Не настроено (пинги отключены)",
                    inline=False
                )

            embed.add_field(
                name="📝 Как использовать",
                value=(
                    "**Установить каналы и роль:**\n"
                    "`/setup_channels admin_contracts_channel:#канал pending_ping_role:@роль`"
                ),
                inline=False
            )

            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        changes = []

        # Обновить настройки
        if admin_contracts_channel:
            await set_setting("admin_contracts_channel_id", str(admin_contracts_channel.id), guild_id)
            changes.append(f"• Канал админских контрактов: {admin_contracts_channel.mention}")

        if pending_counter_channel:
            await set_setting("pending_counter_channel_id", str(pending_counter_channel.id), guild_id)
            changes.append(f"• Канал счетчика ожидающих: {pending_counter_channel.mention}")

        if pending_ping_role:
            await set_setting("pending_ping_role_id", str(pending_ping_role.id), guild_id)
            changes.append(f"• Роль для пинга: {pending_ping_role.mention}")

        embed = discord.Embed(
            title="✅ Настройки обновлены",
            description="\n".join(changes),
            color=discord.Color.green()
        )

        await interaction.followup.send(embed=embed, ephemeral=True)

    @setup_sheets.error
    @setup_channels.error
    async def settings_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """Обработка ошибок команд настройки"""
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "❌ У вас нет прав администратора для использования этой команды.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"❌ Произошла ошибка: {error}",
                ephemeral=True
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(SettingsCog(bot))
