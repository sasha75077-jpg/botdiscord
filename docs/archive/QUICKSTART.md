# 🚀 Быстрый старт - Шпаргалка

## Первый запуск

```bash
# 1. Установка
pip install -r requirements.txt

# 2. Настройка .env
cp .env.example .env
# Отредактировать .env (добавить DISCORD_TOKEN)

# 3. Инициализация БД
python -c "import asyncio; from database import init_db, migrate_db; asyncio.run(init_db()); asyncio.run(migrate_db())"

# 4. Запуск
python main.py
```

## Настройка нового сервера

```
/setup_channels admin_contracts_channel:#канал pending_ping_role:@роль
/setup_sheets sheet_id:YOUR_SHEET_ID enabled:True
```

## Миграция со старой версии

```bash
python migrate_to_v2.py                    # Схема БД
python migrate_add_sheets_settings.py      # Google Sheets настройки
python migrate_add_channel_settings.py     # Каналы и роли
python setup_credentials.py                # Credentials файлы
```

## Основные команды

| Команда | Описание |
|---------|----------|
| `/setup_sheets` | Настройка Google Sheets |
| `/setup_channels` | Настройка каналов и ролей |

## Структура папок

```
BOT Melancholia Now/
├── main.py              # Точка входа
├── config.py            # Конфигурация
├── database.py          # БД
├── bot.db              # SQLite база
├── credentials/        # Google credentials
│   └── GUILD_ID.json
├── cogs/               # Discord команды
└── backend/            # Web-панель
```

## Настройки в БД

```sql
-- Просмотр настроек сервера
SELECT * FROM guild_settings WHERE guild_id='YOUR_GUILD_ID';

-- Просмотр модулей
SELECT * FROM guild_modules WHERE guild_id='YOUR_GUILD_ID';

-- Установка настройки
INSERT OR REPLACE INTO guild_settings (guild_id, setting_key, setting_value) 
VALUES ('GUILD_ID', 'sheet_id', 'YOUR_SHEET_ID');
```

## Проверка статуса

```bash
# Просмотр серверов
sqlite3 bot.db "SELECT guild_id, guild_name, is_active FROM guilds;"

# Просмотр настроек Google Sheets
sqlite3 bot.db "SELECT guild_id, setting_key, setting_value FROM guild_settings WHERE setting_key LIKE '%sheet%';"

# Просмотр модулей
sqlite3 bot.db "SELECT guild_id, module_name, is_enabled FROM guild_modules;"
```

## Частые проблемы

| Проблема | Решение |
|----------|---------|
| Контракты не импортируются | `/setup_sheets` → проверить enabled=True |
| Credentials не найден | `cp credentials.json credentials/GUILD_ID.json` |
| Счетчик не работает | `/setup_channels pending_counter_channel:#канал` |
| Команды не работают | Перезапустить бота |

## Google Sheets

```bash
# 1. Получить credentials.json из Google Cloud Console
# 2. Поместить в credentials/
cp credentials.json credentials/123456789.json

# 3. Настроить
/setup_sheets credentials_path:credentials/123456789.json
/setup_sheets sheet_id:1BxiMVs...
/setup_sheets enabled:True

# 4. Предоставить доступ
# В credentials.json найти client_email
# В Google Sheets → Поделиться → добавить client_email
```

## Логи

```bash
# Просмотр логов (если бот запущен)
# Логи выводятся в консоль

# Ключевые маркеры:
# [LOADED] - модуль загружен
# [SYNCED] - команды синхронизированы
# [Guild 123] - лог для конкретного сервера
# [ERROR] - ошибка
```

## Полезные ссылки

- [README.md](README.md) - Полная документация
- [FAQ.md](FAQ.md) - Часто задаваемые вопросы
- [GOOGLE_SHEETS_SETUP.md](GOOGLE_SHEETS_SETUP.md) - Настройка Google Sheets
- [backend/README.md](backend/README.md) - Web-панель

## Контакты

- GitHub Issues: для багов и вопросов
- Документация: в папке проекта
