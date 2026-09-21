# 🔄 Инструкция по завершению рефакторинга cogs

## ✅ Что уже обновлено

### Core файлы (100%)
- ✅ `config.py` - multi-guild support
- ✅ `database.py` - все функции обновлены
- ✅ `main.py` - автоматическая регистрация серверов
- ✅ `.env` - новые переменные

### Cogs (40%)
- ✅ `cogs/ranks.py` - полностью обновлен
- ✅ `cogs/bonus.py` - полностью обновлен
- ⏳ `cogs/admin_panel.py` - требует обновления
- ⏳ `cogs/user_panel.py` - требует обновления
- ⏳ `cogs/applications.py` - требует обновления
- ⏳ `cogs/cooldowns.py` - требует обновления
- ⏳ `cogs/bonus_reminder.py` - требует обновления

### Services
- ⏳ `services/pending_counter.py` - требует обновления
- ⏳ `sheets_sync.py` - требует обновления

---

## 📝 Паттерн обновления cogs

Все оставшиеся cogs нужно обновить по одному паттерну:

### 1. Добавить `guild_id` в параметры функций

**Было:**
```python
@app_commands.command(name="mycommand")
async def my_command(self, interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    # ...
```

**Стало:**
```python
@app_commands.command(name="mycommand")
async def my_command(self, interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    guild_id = str(interaction.guild_id)  # ДОБАВИТЬ
    # ...
```

### 2. Обновить все запросы к БД

**Было:**
```python
user = await fetch_one(
    "SELECT * FROM users WHERE discord_id = ?",
    (user_id,)
)
```

**Стало:**
```python
user = await fetch_one(
    "SELECT * FROM users WHERE guild_id = ? AND discord_id = ?",
    (guild_id, user_id)
)
```

### 3. Обновить INSERT запросы

**Было:**
```python
await execute(
    "INSERT INTO contracts (discord_id, contract_type, ...) VALUES (?, ?, ...)",
    (user_id, contract_type, ...)
)
```

**Стало:**
```python
await execute(
    "INSERT INTO contracts (guild_id, discord_id, contract_type, ...) VALUES (?, ?, ?, ...)",
    (guild_id, user_id, contract_type, ...)
)
```

### 4. Обновить вызовы функций из других модулей

**Было:**
```python
from cogs.ranks import ensure_user
user = await ensure_user(user_id)
```

**Стало:**
```python
from cogs.ranks import ensure_user
user = await ensure_user(user_id, guild_id)
```

### 5. Обновить вызовы функций из bonus.py

**Было:**
```python
from cogs.bonus import calc_bonus_for_user_week
result = await calc_bonus_for_user_week(user_id)
```

**Стало:**
```python
from cogs.bonus import calc_bonus_for_user_week
result = await calc_bonus_for_user_week(user_id, guild_id)
```

---

## 🎯 Конкретные изменения для каждого файла

### `cogs/admin_panel.py` (~194KB)

**Основные изменения:**

1. **Все команды slash-команд:**
   ```python
   guild_id = str(interaction.guild_id)
   ```

2. **Все запросы к contracts:**
   ```python
   # Было:
   "SELECT * FROM contracts WHERE confirm_status = 'PENDING'"
   
   # Стало:
   "SELECT * FROM contracts WHERE guild_id = ? AND confirm_status = 'PENDING'", (guild_id,)
   ```

3. **Все запросы к bonus_reports:**
   ```python
   # Было:
   "SELECT * FROM bonus_reports WHERE status = 'NEW'"
   
   # Стало:
   "SELECT * FROM bonus_reports WHERE guild_id = ? AND status = 'NEW'", (guild_id,)
   ```

4. **Все запросы к promotion_reports:**
   ```python
   # Было:
   "SELECT * FROM promotion_reports WHERE status = 'NEW'"
   
   # Стало:
   "SELECT * FROM promotion_reports WHERE guild_id = ? AND status = 'NEW'", (guild_id,)
   ```

5. **Все запросы к users:**
   ```python
   # Было:
   "SELECT * FROM users WHERE discord_id = ?"
   
   # Стало:
   "SELECT * FROM users WHERE guild_id = ? AND discord_id = ?", (guild_id, user_id)
   ```

6. **Настройки:**
   ```python
   # Было:
   value = await get_setting("key")
   await set_setting("key", "value")
   
   # Стало:
   value = await get_setting("key", guild_id)
   await set_setting("key", "value", guild_id)
   ```

### `cogs/user_panel.py` (~42KB)

Аналогичные изменения как в admin_panel.py:
- Добавить `guild_id` в каждую команду
- Обновить все запросы к БД
- Обновить вызовы `ensure_user(user_id, guild_id)`
- Обновить вызовы функций из `bonus.py` и `ranks.py`

### `cogs/applications.py` (~27KB)

1. Добавить `guild_id` в команды
2. Обновить запросы к `promotion_reports` и `bonus_reports`
3. Обновить запросы к `users`

### `cogs/cooldowns.py` (~28KB)

1. Добавить `guild_id` в команды
2. Обновить запросы к `contracts`
3. Обновить проверки cooldown (если используется БД)

### `cogs/bonus_reminder.py` (~3KB)

1. Обновить задачу для multi-guild:
   ```python
   for guild in bot.guilds:
       guild_id = str(guild.id)
       # проверить модуль
       if not await is_module_enabled(guild_id, "bonus_reports"):
           continue
       # выполнить логику
   ```

---

## 🛠️ Services

### `services/pending_counter.py`

**Было:**
```python
async def upsert_pending_counter_message(bot, content):
    setting_key = "pending_counter_channel_id"
    ch_id = await get_setting(setting_key)
    # ...
```

**Стало:**
```python
async def upsert_pending_counter_message(bot, content, guild_id: str):
    setting_key = "pending_counter_channel_id"
    ch_id = await get_setting(setting_key, guild_id)
    # ...
```

### `sheets_sync.py`

**Было:**
```python
def poll_contracts():
    # импорт контрактов
    insert_contract_if_new_sync({"ts": ..., "discord_id": ...})
```

**Стало:**
```python
def poll_contracts(guild_id: str):
    # импорт контрактов
    insert_contract_if_new_sync({
        "guild_id": guild_id,
        "ts": ...,
        "discord_id": ...
    })
```

---

## 🔍 Проверка после обновления

После обновления каждого файла проверьте:

1. **Импорты:** все функции из `ranks.py` и `bonus.py` вызываются с `guild_id`
2. **SQL запросы:** все таблицы с `guild_id` фильтруются
3. **Вызовы `get_setting/set_setting`:** передается `guild_id`
4. **Interaction handlers:** извлекается `guild_id = str(interaction.guild_id)`

### Автоматическая проверка

Можно использовать поиск для проверки:

```bash
# Найти все запросы к contracts без guild_id
grep -n "FROM contracts" cogs/*.py | grep -v "guild_id"

# Найти все запросы к users без guild_id
grep -n "FROM users" cogs/*.py | grep -v "guild_id"

# Найти все вызовы ensure_user без guild_id
grep -n "ensure_user(" cogs/*.py
```

---

## 📦 Быстрый способ обновления

Для ускорения процесса можно использовать find-and-replace в редакторе:

### Типовые замены:

1. **users таблица:**
   ```
   FROM users WHERE discord_id = ?
   →
   FROM users WHERE guild_id = ? AND discord_id = ?
   ```

2. **contracts таблица:**
   ```
   FROM contracts WHERE
   →
   FROM contracts WHERE guild_id = ? AND
   ```

3. **bonus_reports таблица:**
   ```
   FROM bonus_reports WHERE
   →
   FROM bonus_reports WHERE guild_id = ? AND
   ```

4. **Добавление guild_id в начало:**
   ```python
   guild_id = str(interaction.guild_id)
   ```
   
   Вставить после каждого:
   ```python
   async def command_name(self, interaction: discord.Interaction):
   ```

---

## ⚠️ Важные замечания

1. **JOIN запросы:** при JOIN с ranks убедитесь что тоже добавлен guild_id:
   ```sql
   FROM users u
   JOIN ranks r ON u.guild_id = r.guild_id AND u.current_rank_id = r.rank_id
   ```

2. **Подсчеты:** при COUNT тоже добавить guild_id:
   ```sql
   SELECT COUNT(*) FROM contracts WHERE guild_id = ? AND confirm_status = 'PENDING'
   ```

3. **ORDER BY и GROUP BY:** работают без изменений

4. **Views (v_contract_value):** если используются view, может потребоваться пересоздание

---

## 🚀 После завершения

После обновления всех cogs:

1. **Запустить миграцию:**
   ```bash
   python migrate_to_v2.py
   ```

2. **Запустить бота:**
   ```bash
   python main.py
   ```

3. **Проверить логи:**
   - Должно быть: `✅ Обнаружена новая схема БД (multi-guild)`
   - Должно быть: `✅ Сервер зарегистрирован: ...`
   - Все cogs загружены без ошибок

4. **Протестировать команды:**
   - Команды пользователя
   - Команды админа
   - Импорт из Google Sheets
   - Создание отчетов

---

## 📞 Помощь

Если нужна помощь с конкретным файлом - дай знать, обновлю его!

**Дата создания:** 9 сентября 2026
**Статус:** ranks.py ✅ | bonus.py ✅ | остальные ⏳
