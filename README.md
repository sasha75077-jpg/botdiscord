# 🤖 Melancholia Bot - Мультисерверный режим

Версия 2.0 - Полная поддержка работы на нескольких Discord серверах одновременно.

## 🌟 Возможности

- ✅ **Автоматическая регистрация серверов** - бот автоматически добавляет новые серверы в БД
- ✅ **Изоляция данных** - каждый сервер имеет свои контракты, пользователей, настройки
- ✅ **Независимые настройки** - каждый сервер настраивается отдельно
- ✅ **Модульная система** - включайте/выключайте функции для каждого сервера
- ✅ **Отдельные Google Sheets** - каждый сервер может иметь свою таблицу
- ✅ **Команды настройки** - администраторы настраивают бота через Discord
- ✅ **Web-панель управления** - FastAPI backend для управления через браузер

## 🚀 Быстрый старт

### 1. Установка и настройка

```bash
# Клонировать репозиторий
git clone <your-repo>
cd "BOT Melancholia Now"

# Установить зависимости
pip install -r requirements.txt

# Создать .env файл
cp .env.example .env
```

### 2. Настроить .env

```env
# Discord Bot Token
DISCORD_TOKEN=your_bot_token

# Multi-guild поддержка (опционально)
# Оставьте пустым для работы на всех серверах
GUILD_IDS=

# Google Sheets (опционально, настраивается для каждого сервера)
SHEET_ID=
SHEET_CREDENTIALS=credentials.json

# Интервалы опроса (секунды)
POLLING_INTERVAL=60
PENDING_PING_INTERVAL_SEC=300
```

### 3. Инициализировать базу данных

```bash
# Создать новую БД с мультисервером
python -c "import asyncio; from database import init_db, migrate_db; asyncio.run(init_db()); asyncio.run(migrate_db())"

# Или мигрировать со старой версии
python migrate_to_v2.py
```

### 4. Запустить бота

```bash
python main.py
```

## 📋 Первоначальная настройка сервера

После добавления бота на ваш сервер:

### 1. Настроить каналы и роли

```
/setup_channels 
  admin_contracts_channel: #админ-контракты
  pending_counter_channel: #счетчик-контрактов
  pending_ping_role: @Роль для пинга
```

### 2. Настроить Google Sheets (опционально)

```bash
# Поместить credentials.json в папку credentials/
cp your-credentials.json credentials/YOUR_GUILD_ID.json
```

```
/setup_sheets 
  credentials_path: credentials/YOUR_GUILD_ID.json
  sheet_id: YOUR_SHEET_ID
  enabled: True
```

### 3. Проверить настройки

```
/setup_channels    # Показать настройки каналов
/setup_sheets      # Показать настройки Google Sheets
```

## 🔧 Настройки

### Настройки хранятся в таблице `guild_settings`

| Ключ | Описание | Пример |
|------|----------|--------|
| `sheet_id` | ID Google таблицы | `1BxiMVs0XRA5nFMd...` |
| `credentials_path` | Путь к credentials | `credentials/123.json` |
| `sheets_enabled` | Импорт из Sheets | `true` / `false` |
| `admin_contracts_channel_id` | Канал контрактов | `123456789` |
| `pending_counter_channel_id` | Канал счетчика | `123456789` |
| `pending_ping_role_id` | Роль для пинга | `987654321` |

### Модули (`guild_modules`)

Каждый сервер может включать/выключать модули:

- `contracts` - Система контрактов
- `user_panel` - Панель пользователя
- `admin_panel` - Панель администратора
- `bonus_reports` - Отчеты на бонусы
- `promotion_reports` - Отчеты на повышение

## 📚 Миграция существующего бота

### Шаг 1: Мигрировать схему БД

```bash
python migrate_to_v2.py
```

Это создаст:
- Таблицу `guilds` для серверов
- Таблицу `guild_settings` для настроек
- Таблицу `guild_modules` для модулей
- Добавит `guild_id` во все таблицы

### Шаг 2: Перенести настройки Google Sheets

```bash
python migrate_add_sheets_settings.py
```

Добавит настройки `sheet_id`, `credentials_path`, `sheets_enabled` для каждого сервера.

### Шаг 3: Перенести настройки каналов

```bash
python migrate_add_channel_settings.py
```

Добавит настройки каналов и ролей для каждого сервера.

### Шаг 4: Настроить credentials (опционально)

```bash
# Автоматически скопировать credentials.json для всех серверов
python setup_credentials.py

# Или вручную для конкретного сервера
cp credentials.json credentials/YOUR_GUILD_ID.json
```

## 🔐 Google Sheets интеграция

### Получение credentials

1. Перейти на https://console.cloud.google.com/
2. Создать проект или выбрать существующий
3. Включить Google Sheets API
4. Создать Service Account
5. Создать ключ JSON для Service Account
6. Скачать файл (это ваш credentials.json)

### Предоставить доступ к таблице

1. Открыть credentials.json
2. Найти поле `client_email`
3. Открыть Google Sheets таблицу
4. Нажать "Поделиться"
5. Добавить `client_email` с правами "Редактор"

### Получить Sheet ID

Sheet ID находится в URL таблицы:
```
https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMd.../edit
                                       ^^^^^^^^^^^^^^^^^^^
                                          Это Sheet ID
```

### Настроить импорт

```
/setup_sheets 
  sheet_id: 1BxiMVs0XRA5nFMd...
  credentials_path: credentials/YOUR_GUILD_ID.json
  enabled: True
```

Подробнее: [GOOGLE_SHEETS_SETUP.md](GOOGLE_SHEETS_SETUP.md)

## 🛠️ Команды администратора

### `/setup_sheets` - Настройка Google Sheets

```
/setup_sheets                          # Показать настройки
/setup_sheets sheet_id:...             # Установить таблицу
/setup_sheets enabled:True             # Включить импорт
/setup_sheets credentials_path:...     # Установить credentials
```

### `/setup_channels` - Настройка каналов

```
/setup_channels                        # Показать настройки
/setup_channels admin_contracts_channel:#канал
/setup_channels pending_counter_channel:#канал
/setup_channels pending_ping_role:@роль
```

## 🏗️ Структура проекта

```
BOT Melancholia Now/
├── main.py                      # Точка входа бота
├── config.py                    # Конфигурация
├── database.py                  # Работа с БД
├── sheets_sync.py               # Импорт из Google Sheets
│
├── cogs/                        # Discord команды
│   ├── admin_panel.py           # Админ панель
│   ├── user_panel.py            # Панель пользователя
│   ├── settings.py              # Настройки сервера
│   └── ...
│
├── services/                    # Бизнес логика
│   ├── pending_counter.py       # Счетчик контрактов
│   └── ...
│
├── models/                      # Схемы БД
│   ├── schema.sql               # Старая схема
│   └── schema_v2_multiguild.sql # Новая схема
│
├── credentials/                 # Credentials файлы
│   ├── README.md
│   ├── .gitignore
│   └── GUILD_ID.json           # Per-server credentials
│
├── backend/                     # FastAPI Web-панель
│   └── app/
│       ├── main.py
│       ├── api/routes/
│       └── ...
│
├── frontend/                    # React фронтенд
│   └── src/
│
└── migrations/                  # Скрипты миграций
    ├── migrate_to_v2.py
    ├── migrate_add_sheets_settings.py
    ├── migrate_add_channel_settings.py
    └── setup_credentials.py
```

## 🐛 Troubleshooting

### Бот не видит сервер

**Проблема:** Сервер не появляется в БД после добавления бота.

**Решение:**
1. Перезапустить бота
2. Проверить что бот онлайн на сервере
3. Проверить БД: `SELECT * FROM guilds;`

### Импорт из Google Sheets не работает

**Проблема:** Контракты не импортируются из таблицы.

**Решение:**
1. Проверить настройки: `/setup_sheets`
2. Убедиться что `sheets_enabled = true`
3. Проверить что `sheet_id` настроен
4. Проверить доступ Service Account к таблице
5. Посмотреть логи бота на ошибки

### Счетчик контрактов не обновляется

**Проблема:** Сообщение со счетчиком не появляется.

**Решение:**
1. Настроить канал: `/setup_channels pending_counter_channel:#канал`
2. Проверить что модуль `contracts` включен
3. Проверить права бота на отправку сообщений в канал

### Credentials файл не найден

**Проблема:** Ошибка при импорте: "credentials файл не найден".

**Решение:**
1. Поместить credentials.json в папку `credentials/`
2. Переименовать в `GUILD_ID.json`
3. Настроить путь: `/setup_sheets credentials_path:credentials/GUILD_ID.json`

## 📖 Документация

- [GOOGLE_SHEETS_SETUP.md](GOOGLE_SHEETS_SETUP.md) - Настройка Google Sheets
- [MIGRATION_CHANNELS.md](MIGRATION_CHANNELS.md) - Миграция настроек каналов
- [backend/README.md](backend/README.md) - Web-панель управления

## 🔒 Безопасность

### Credentials файлы

- ❌ НЕ добавляйте `credentials/` в git
- ❌ НЕ публикуйте credentials файлы
- ✅ Убедитесь что `.gitignore` содержит `credentials/`
- ✅ Каждый сервер имеет свой credentials файл

### База данных

- Все данные изолированы по `guild_id`
- Один сервер не может видеть данные другого
- Каскадное удаление при удалении сервера

### Права доступа

- Команды настройки требуют права администратора
- Web-панель требует авторизацию через Discord OAuth2
- Owner аккаунт имеет доступ ко всем серверам

## 🤝 Поддержка

При возникновении проблем:

1. Проверьте раздел [Troubleshooting](#-troubleshooting)
2. Посмотрите логи бота
3. Проверьте настройки в БД
4. Откройте issue с описанием проблемы

## 📝 Changelog

### v2.0 (2026-09-17)

- ✨ Полная поддержка мультисервера
- ✨ Автоматическая регистрация серверов
- ✨ Изоляция данных per-server
- ✨ Независимые настройки Google Sheets
- ✨ Команды `/setup_sheets` и `/setup_channels`
- ✨ Изолированные credentials файлы
- ✨ Модульная система
- ✨ Миграция со старой версии
- 🐛 Исправлена ошибка с guild_id в импорте

### v1.0

- Базовая функциональность для одного сервера
