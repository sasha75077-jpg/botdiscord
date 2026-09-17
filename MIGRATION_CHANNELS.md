# Миграция настроек каналов и ролей

## ✅ Что сделано

### 1. Создана миграция `migrate_add_channel_settings.py`
Переносит настройки каналов и ролей из `.env` в `guild_settings`:
- `admin_contracts_channel_id` - канал для админских контрактов
- `pending_ping_role_id` - роль для пинга при новых контрактах  
- `pending_counter_channel_id` - канал для счетчика ожидающих

### 2. Обновлен `services/pending_counter.py`
- Добавлен параметр `guild_id` в функцию `upsert_pending_counter_message()`
- Настройки канала теперь читаются из `guild_settings` для каждого сервера
- Улучшена обработка ошибок с логированием guild_id

### 3. Обновлен `main.py`
- Убран импорт `PENDING_PING_ROLE_ID` из config
- В `pending_counter_task()` роль для пинга читается из БД для каждого сервера
- Добавлена проверка на пустые/нулевые значения роли

### 4. Обновлен `config.py`
- Добавлены комментарии о deprecated переменных
- Указано что новые серверы должны использовать `guild_settings`
- Переменные оставлены для обратной совместимости

## 🚀 Как применить

```bash
# Запустить миграцию
cd "C:\Users\USER\Desktop\BOT Melancholia Now"
python migrate_add_channel_settings.py
```

Миграция автоматически:
1. Прочитает значения из `.env` файла
2. Добавит настройки для всех активных серверов в БД
3. Использует значения из `.env` как defaults

## 📋 После миграции

### Опционально: очистить `.env`
Можете удалить эти строки из `.env` (но это не обязательно):
```
ADMIN_CONTRACTS_CHANNEL_ID=...
PENDING_PING_ROLE_ID=...
```

### Настроить каналы для конкретного сервера
```sql
-- Через SQL
sqlite3 bot.db "UPDATE guild_settings SET setting_value='YOUR_CHANNEL_ID' WHERE guild_id='YOUR_GUILD_ID' AND setting_key='admin_contracts_channel_id';"

-- Или через команду /setup_channels (задача #5)
```

## 🔍 Проверка настроек

```sql
-- Посмотреть настройки сервера
sqlite3 bot.db "SELECT * FROM guild_settings WHERE guild_id='YOUR_GUILD_ID';"

-- Посмотреть все настройки каналов
sqlite3 bot.db "SELECT guild_id, setting_key, setting_value FROM guild_settings WHERE setting_key LIKE '%channel%' OR setting_key LIKE '%role%';"
```

## ⚠️ Важно

- Настройки применяются **per-server**, каждый сервер имеет свои каналы
- Если настройка не указана, бот выведет предупреждение в лог
- Значения `0` или пустые строки считаются "не настроено"
- Для `pending_ping_role_id`: если не настроено, пинги не отправляются

## 📝 Следующие шаги

- [ ] Создать команду `/setup_channels` для настройки через Discord (задача #5)
- [ ] Добавить UI в веб-панель для настройки каналов
- [ ] Обновить документацию для новых серверов
