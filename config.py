import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# Multi-guild support: можно указать несколько серверов через запятую
# Если не указано, бот будет работать на всех серверах где он есть
GUILD_IDS = os.getenv("GUILD_IDS", "")  # Например: "123456789,987654321"
GUILD_IDS_LIST = [int(gid.strip()) for gid in GUILD_IDS.split(",") if gid.strip()]

# Для обратной совместимости со старым кодом
GUILD_ID = GUILD_IDS_LIST[0] if GUILD_IDS_LIST else 0

# Google Sheets (опциональная интеграция, настраивается для каждого сервера)
SHEET_ID = os.getenv("SHEET_ID", "")
SHEET_CREDENTIALS = os.getenv("SHEET_CREDENTIALS", "credentials.json")
CONTRACTS_SHEET = "Contracts"
CHANNELS_SHEET = "Channels"

# Интервал polling для Google Sheets (секунды)
POLLING_INTERVAL = 60

# SQLite
DB_PATH = "bot.db"

# Настройки по умолчанию (DEPRECATED - используются только для обратной совместимости)
# Новые серверы должны настраивать каналы/роли через guild_settings
# Используйте миграцию: python migrate_add_channel_settings.py
ADMIN_CONTRACTS_CHANNEL_ID = int(os.getenv("ADMIN_CONTRACTS_CHANNEL_ID", 0))
PENDING_PING_INTERVAL_SEC = int(os.getenv("PENDING_PING_INTERVAL_SEC", 300))
PENDING_PING_ROLE_ID = int(os.getenv("PENDING_PING_ROLE_ID", 0))
