# 🚀 Настройка бота с нуля - Пошаговая инструкция для чайников

**Время: ~1 час**  
**Сложность: Легко (все команды готовы, просто копируй)**

---

## 📋 Что получится в итоге

✅ Бот работает на твоем компьютере 24/7  
✅ База данных SQLite настроена и мигрирована  
✅ Все функции работают (контракты, ранги, бонусы, Google Sheets)  
✅ Бот готов к подключению на несколько Discord серверов  
✅ Веб-панель (потом) для управления через браузер  

---

## ⚙️ Часть 1: Подготовка (10 минут)

### Шаг 1: Проверить Python

Открой PowerShell (Win+X → Windows PowerShell) и выполни:

```powershell
python --version
```

**Что должно быть:**
```
Python 3.10.x или выше
```

**Если Python не установлен:**
1. Скачай с https://www.python.org/downloads/
2. При установке **ОБЯЗАТЕЛЬНО** поставь галочку "Add Python to PATH"
3. Перезагрузи компьютер
4. Проверь снова командой выше

---

### Шаг 2: Установить зависимости

```powershell
# Перейти в папку бота
cd "C:\Users\User\Desktop\BOT Melancholia Now"

# Установить все библиотеки (займет 2-3 минуты)
pip install -r requirements.txt
```

**Что происходит:**  
Устанавливаются все библиотеки которые нужны боту (discord.py, aiosqlite, gspread, и т.д.)

**Если ошибка "pip не найден":**
```powershell
python -m pip install -r requirements.txt
```

---

## 🗄️ Часть 2: Настройка базы данных (15 минут)

### Шаг 1: Понять что такое база данных

**База данных = Excel файл на стероидах**

В боте используется SQLite - это файл `bot.db` который хранит:
- Контракты пользователей
- Ранги и повышения
- Бонусы и отчеты
- Настройки для каждого сервера

**Где лежит база:** `C:\Users\User\Desktop\BOT Melancholia Now\bot.db`

---

### Шаг 2: Проверить старую базу

```powershell
# Посмотреть есть ли старая база
ls bot.db
```

**Если файл bot.db существует:**
У тебя есть старые данные! Нужна миграция (обновление структуры).

**Если файла нет:**
База создастся автоматически при первом запуске бота.

---

### Шаг 3: Миграция базы для мультисервера

**Что такое миграция:**  
Это обновление старой базы данных чтобы она поддерживала несколько Discord серверов.

**Что изменится:**
- ❌ Старая база: работает только на 1 сервере
- ✅ Новая база: работает на любом количестве серверов
- ✅ Все твои данные сохранятся!

**Выполни миграцию:**

```powershell
# Создать бэкап (на всякий случай)
Copy-Item bot.db bot_backup_$(Get-Date -Format 'yyyy-MM-dd').db

# Запустить миграцию
python migrate_to_v2.py
```

**Что увидишь:**

```
🔍 Checking database version...
📊 Current database version: 1
🎯 Target database version: 2

🔄 Starting migration...
✅ Backup created: bot_backup_2026-09-10.db
✅ Schema updated
✅ Data migrated: 150 contracts, 45 users, 200 bonus records
✅ Migration completed successfully!

🎉 Database is now ready for multi-guild support!
```

**Если ошибка:**
```powershell
# Восстановить из бэкапа
Copy-Item bot_backup_2026-09-10.db bot.db

# Написать мне что за ошибка показалась
```

---

### Шаг 4: Проверить структуру базы (опционально)

Хочешь посмотреть что внутри базы? Установи DB Browser:

1. Скачай https://sqlitebrowser.org/dl/
2. Установи
3. Открой `bot.db`
4. Увидишь таблицы: `guilds`, `contracts`, `ranks`, `bonus_reports`, и т.д.

**Не обязательно!** Это просто для любопытства.

---

## 🤖 Часть 3: Настройка Discord бота (15 минут)

### Шаг 1: Создать приложение Discord

1. Открыть https://discord.com/developers/applications
2. Нажать **New Application**
3. Ввести имя: `Melancholia Now`
4. Нажать **Create**

---

### Шаг 2: Получить Bot Token

1. В левом меню: **Bot**
2. Нажать **Reset Token** → **Yes, do it!**
3. **СКОПИРОВАТЬ TOKEN** (показывается один раз!)
   ```
   Пример: MTMzMDc0MzU3NjQ1MTIyMzYzNQ.XXXXXX.XXXXXXXXXXXXXXXXXXXXXXX
   ```
4. **ВАЖНО:** Никому не показывай этот токен!

---

### Шаг 3: Настроить права бота

В той же странице **Bot**:

**Privileged Gateway Intents** (включить все 3):
- ✅ Presence Intent
- ✅ Server Members Intent
- ✅ Message Content Intent

Нажать **Save Changes**

---

### Шаг 4: Получить Client ID и Client Secret

1. В левом меню: **OAuth2** → **General**
2. **Client ID:** скопировать (например: `1330743576451223635`)
3. **Client Secret:** нажать **Reset Secret** → скопировать

---

### Шаг 5: Добавить бота на сервер

1. В левом меню: **OAuth2** → **URL Generator**
2. **Scopes** выбрать:
   - ✅ `bot`
   - ✅ `applications.commands`
3. **Bot Permissions** выбрать:
   - ✅ Administrator (или выбрать конкретные права)
4. Скопировать **Generated URL** внизу страницы
5. Открыть URL в браузере
6. Выбрать свой Discord сервер
7. Нажать **Authorize**

**Бот появится на сервере в оффлайне** (мы его еще не запустили)

---

## 📝 Часть 4: Настройка .env файла (10 минут)

### Шаг 1: Открыть .env файл

Файл находится: `C:\Users\User\Desktop\BOT Melancholia Now\.env`

Открой его в Блокноте или любом редакторе.

---

### Шаг 2: Заполнить Discord настройки

```env
# === Discord Bot ===
DISCORD_TOKEN=MTMzMDc0MzU3NjQ1MTIyMzYzNQ.G3hHMx...  # ⬅️ Вставить твой Bot Token
GUILD_IDS=880440495233454080  # ⬅️ ID твоего сервера (см. ниже как найти)

# Discord OAuth2 (для веб-панели потом)
DISCORD_CLIENT_ID=1330743576451223635  # ⬅️ Client ID из Discord
DISCORD_CLIENT_SECRET=your_secret_here  # ⬅️ Client Secret из Discord
DISCORD_REDIRECT_URI=http://localhost:3000/auth/callback  # Пока не трогай
```

---

### Шаг 3: Как найти Guild ID (ID сервера)

**В Discord:**
1. Открыть Discord
2. Настройки → **Advanced** (Расширенные)
3. Включить **Developer Mode** (Режим разработчика)
4. Закрыть настройки
5. ПКМ на иконке сервера → **Copy Server ID**
6. Вставить в `.env` файл в `GUILD_IDS=`

**Для нескольких серверов:**
```env
GUILD_IDS=880440495233454080,123456789012345678,987654321098765432
```
(через запятую без пробелов)

---

### Шаг 4: Настроить каналы и роли

**Найти ID канала:**
1. ПКМ на канале → **Copy Channel ID**

**Найти ID роли:**
1. Настройки сервера → Роли
2. ПКМ на роли → **Copy Role ID**

**Заполнить в .env:**

```env
# === Channels ===
ADMIN_CONTRACTS_CHANNEL_ID=1470997095656849498  # ⬅️ Канал для отчетов админа
LOG_CHANNEL_ID=your_channel_id  # ⬅️ Канал для логов бота (опционально)

# === Roles ===
PENDING_PING_ROLE_ID=1470997335176773806  # ⬅️ Роль для пинга при новых контрактах
```

---

### Шаг 5: Google Sheets (опционально)

**Если НЕ используешь Google Sheets:**
```env
USE_GOOGLE_SHEETS=False
```

**Если используешь Google Sheets:**

1. Перейти в Google Cloud Console: https://console.cloud.google.com/
2. Создать проект
3. Включить Google Sheets API
4. Создать Service Account
5. Скачать JSON ключ
6. Положить файл в папку бота: `google_credentials.json`

```env
USE_GOOGLE_SHEETS=True
GOOGLE_CREDENTIALS_FILE=google_credentials.json
SPREADSHEET_ID=твой_spreadsheet_id  # из URL таблицы
WORKSHEET_NAME=Sheet1  # Имя листа
```

**Не обязательно!** Можно настроить потом.

---

### Шаг 6: Проверить остальные настройки

```env
# === Pending System ===
PENDING_PING_INTERVAL_SEC=300  # Проверка каждые 5 минут
PENDING_CHECK_ENABLED=True

# === Database ===
DATABASE_URL=sqlite+aiosqlite:///./bot.db  # Путь к базе (не трогай)

# === API (для веб-панели потом) ===
API_HOST=0.0.0.0
API_PORT=8000
SECRET_KEY=your-secret-key-here  # Сгенерируется автоматически
DEBUG=True
```

---

## 🎮 Часть 5: Запуск бота (5 минут)

### Шаг 1: Первый запуск

```powershell
# Находясь в папке бота
python main.py
```

**Что увидишь:**

```
2026-09-10 12:00:00 INFO     discord.client logging in using static token
2026-09-10 12:00:01 INFO     discord.gateway Shard ID None has connected to Gateway

🤖 Bot is ready!
👤 Logged in as: Melancholia Now#1234
🆔 Bot ID: 1330743576451223635
📊 Connected to 1 guild(s)

✅ Guild registered: Your Server Name (880440495233454080)

🔄 Background tasks started:
  ✅ Pending contracts checker
  ✅ Google Sheets sync (disabled)
  ✅ Bonus reminders

🎉 All systems operational!
```

**Бот теперь онлайн на твоем сервере!**

---

### Шаг 2: Проверить что бот работает

**В Discord:**

1. Найти бота в списке участников (должен быть онлайн)
2. Написать команду: `/help`
3. Должен появиться список команд

**Если бот не отвечает:**
- Проверь что Bot Token правильный в `.env`
- Проверь что все 3 Intents включены в Discord Developer Portal
- Проверь логи в PowerShell окне

---

### Шаг 3: Остановить бота

В PowerShell окне нажми **Ctrl+C**

```
🛑 Shutting down...
✅ Bot stopped successfully
```

---

## 🔧 Часть 6: Настройка функций бота (10 минут)

### Шаг 1: Проверить доступные модули

Запусти бота и выполни в Discord:

```
/modules list
```

**Увидишь:**

```
📦 Available Modules:
✅ contracts - Contract management system
✅ ranks - Rank progression system
✅ bonus - Bonus calculation system
✅ applications - Application forms
✅ pending - Pending contracts checker
✅ sheets_sync - Google Sheets integration
```

---

### Шаг 2: Включить/выключить модули для сервера

```
/modules enable contracts
/modules enable ranks
/modules enable bonus
```

```
/modules disable sheets_sync  # Если не используешь Google Sheets
```

**Это настраивается для каждого сервера отдельно!**

---

### Шаг 3: Настроить настройки сервера

```
/settings set key:contracts_channel value:1234567890
/settings set key:min_contract_amount value:1000000
/settings set key:max_contract_amount value:50000000
```

**Посмотреть все настройки:**
```
/settings list
```

---

## 🌐 Часть 7: Добавить бота на другие серверы (5 минут)

### Шаг 1: Добавить Guild ID в .env

```env
# Добавить через запятую
GUILD_IDS=880440495233454080,123456789012345678
```

### Шаг 2: Перезапустить бота

```powershell
# Остановить: Ctrl+C
# Запустить снова:
python main.py
```

**Увидишь:**

```
📊 Connected to 2 guild(s)

✅ Guild registered: Server 1 (880440495233454080)
✅ Guild registered: Server 2 (123456789012345678)
```

### Шаг 3: Настроить модули для нового сервера

Каждый сервер настраивается отдельно!

**На Server 2:**
```
/modules enable contracts
/modules enable ranks
/modules disable sheets_sync  # Этот сервер без Google Sheets
```

**Разные настройки для разных серверов - это нормально!**

---

## ✅ Часть 8: Проверка что все работает (5 минут)

### Тест 1: Создать контракт

```
/contract add user:@Username amount:5000000 type:Cargo
```

**Должно:**
- ✅ Добавить контракт в базу
- ✅ Отправить сообщение в `ADMIN_CONTRACTS_CHANNEL_ID`
- ✅ Обновить Google Sheets (если включено)

---

### Тест 2: Проверить ранги

```
/rank check user:@Username
```

**Должно показать:**
- Текущий ранг
- Прогресс до следующего ранга
- Выполненные требования

---

### Тест 3: Рассчитать бонус

```
/bonus calculate user:@Username
```

**Должно:**
- Посчитать бонус за текущую неделю
- Показать детальный расчет

---

## 🔄 Часть 9: Автозапуск бота (опционально)

### Вариант 1: Скрипт автозапуска (Windows)

Создай файл `start_bot.bat`:

```batch
@echo off
cd "C:\Users\User\Desktop\BOT Melancholia Now"
python main.py
pause
```

Теперь просто двойной клик по `start_bot.bat` чтобы запустить бота.

---

### Вариант 2: Автозапуск при старте Windows

1. Win+R → `shell:startup` → Enter
2. Скопировать туда `start_bot.bat`
3. Бот будет запускаться при включении компьютера

**НО:** Компьютер должен быть включен 24/7 чтобы бот работал!

---

### Вариант 3: VPS/Cloud сервер (рекомендуется)

Для 24/7 работы лучше использовать VPS:

**Популярные варианты:**
- Railway (https://railway.app) - $5/месяц
- DigitalOcean (https://digitalocean.com) - $6/месяц
- Heroku (https://heroku.com) - бесплатный план убрали
- Oracle Cloud (https://oracle.com/cloud) - бесплатный forever tier

**Инструкция для VPS:**
1. Создать сервер Ubuntu
2. Установить Python
3. Загрузить код бота
4. Настроить systemd service (автозапуск)

Могу сделать отдельную инструкцию если нужно!

---

## 🎉 Готово!

### Что получилось:

✅ **База данных**
- SQLite база настроена
- Миграция на multi-guild выполнена
- Все данные сохранены

✅ **Discord бот**
- Бот создан и добавлен на серверы
- Все права настроены
- Команды работают

✅ **Мульти-сервер**
- Бот работает на нескольких серверах одновременно
- Каждый сервер со своими настройками
- Модули включаются/выключаются отдельно

✅ **Функции**
- Контракты
- Ранги и повышения
- Бонусы
- Google Sheets (опционально)
- Pending система
- Веб-панель (готова, деплой потом)

---

## 🆘 Частые проблемы

### Бот не запускается

```
ModuleNotFoundError: No module named 'discord'
```

**Решение:**
```powershell
pip install -r requirements.txt
```

---

### Бот оффлайн в Discord

**Проверь:**
1. Token правильный в `.env`?
2. Все 3 Intents включены?
3. Есть ошибки в PowerShell окне?

---

### Команды не работают

```
Application did not respond
```

**Решение:**
```powershell
# В коде бота убедись что команды зарегистрированы
# Перезапусти бота и подожди 1-2 минуты
```

---

### База данных не найдена

```
sqlite3.OperationalError: no such table: contracts
```

**Решение:**
```powershell
# Удалить старую базу и создать новую
Remove-Item bot.db
python migrate_to_v2.py
```

---

### Google Sheets не работает

```
gspread.exceptions.APIError
```

**Решение:**
1. Проверь что Service Account создан
2. Файл `google_credentials.json` в папке бота
3. Таблица расшарена на email Service Account
4. В `.env`: `USE_GOOGLE_SHEETS=True`

---

## 📚 Следующие шаги

### 1. Настроить веб-панель

Открой `DEPLOY_NOW.md` для инструкций по деплою веб-панели на Cloudflare.

**Что даст веб-панель:**
- Вход через Discord для пользователей
- Админ-панель для управления сервером
- Owner-панель для глобальных настроек
- Отчеты и статистика в реальном времени
- WebSocket обновления

---

### 2. Дополнительные функции

Можешь добавить:
- Систему заявок (applications)
- Напоминания о бонусах
- Кастомные роли за ранги
- Интеграцию с другими API

---

### 3. Мониторинг и логи

Настроить:
- LOG_CHANNEL_ID для логов в Discord
- Внешний мониторинг (UptimeRobot)
- Backup базы данных

---

## 📞 Нужна помощь?

**Что можно спросить:**
- Как настроить конкретную функцию
- Как добавить кастомную команду
- Как деплоить на VPS
- Как настроить автоматический backup
- Любые ошибки которые возникают

**Просто опиши проблему и скопируй ошибку из PowerShell!**

---

**Создано: 2026-09-10**  
**Версия: 2.0 (Multi-Guild)**  
**Время настройки: ~1 час**  
**Сложность: ⭐⭐☆☆☆**
