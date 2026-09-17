# Инструкция по настройке и запуску системы

## ✅ Что уже готово

### 1. Архитектура системы
- Полная документация в `ARCHITECTURE.md`
- 3 уровня доступа: Owner, Admin, User
- Multi-guild поддержка

### 2. База данных
- Новая схема в `models/schema_v2_multiguild.sql`
- Скрипт миграции `migrate_to_v2.py`
- Поддержка нескольких серверов Discord

### 3. Backend API (FastAPI)
- ✅ Авторизация (Owner + Discord OAuth2)
- ✅ JWT токены (access + refresh)
- ✅ CRUD для контрактов
- ✅ CRUD для отчетов (бонусы, повышения)
- ✅ Управление пользователями
- ✅ Управление серверами и настройками
- ✅ WebSocket для real-time обновлений
- ✅ Права доступа (Owner/Admin/User)

## 🚀 Пошаговая установка

### Шаг 1: Миграция базы данных

```bash
cd "C:\Users\User\Desktop\BOT Melancholia Now"

# 1. Откройте migrate_to_v2.py и замените DEFAULT_GUILD_ID на реальный ID вашего сервера
# Чтобы узнать ID: правый клик на сервер в Discord → Копировать ID (нужен режим разработчика)

# 2. Запустите миграцию
python migrate_to_v2.py
```

**ВАЖНО:** Миграция создаст резервную копию БД перед изменениями!

### Шаг 2: Настройка Backend API

```bash
cd backend

# 1. Создать виртуальное окружение
python -m venv venv
.\venv\Scripts\Activate

# 2. Установить зависимости
pip install -r requirements.txt

# 3. Скопировать .env.example в .env
copy .env.example .env

# 4. Настроить .env (откройте в редакторе)
```

**Настройка .env:**

```env
# Генерировать SECRET_KEY:
# python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=сгенерированный_ключ

# Discord OAuth2 (создать на https://discord.com/developers/applications)
DISCORD_CLIENT_ID=ваш_client_id
DISCORD_CLIENT_SECRET=ваш_client_secret
DISCORD_REDIRECT_URI=http://localhost:3000/auth/callback
DISCORD_BOT_TOKEN=ваш_bot_token

# Owner аккаунт
OWNER_EMAIL=ваш_email@example.com
OWNER_PASSWORD=надежный_пароль

# CORS (добавить URL фронтенда после деплоя)
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
```

**Discord OAuth2 настройка:**

1. Перейти на https://discord.com/developers/applications
2. Выбрать ваше приложение (или создать новое)
3. Перейти в "OAuth2" → "General"
4. Добавить Redirect URI: `http://localhost:3000/auth/callback`
5. Скопировать Client ID и Client Secret в .env

### Шаг 3: Запуск Backend

```bash
# Находясь в папке backend с активированным venv
python run.py
```

API будет доступен на: http://localhost:8000
Документация: http://localhost:8000/docs

### Шаг 4: Обновление кода бота (следующий этап)

Нужно обновить код бота для работы с новой схемой БД. Список изменений:

1. **config.py** - добавить GUILD_ID
2. **database.py** - обновить все запросы (добавить guild_id)
3. **Все cogs** - добавить guild_id в запросы
4. **main.py** - добавить проверку модулей при загрузке

## 📋 Что осталось сделать

### Backend (текущий этап)
- [x] Миграция БД
- [x] FastAPI структура
- [x] Авторизация (Owner + Discord OAuth2)
- [x] API endpoints (contracts, users, reports, guilds)
- [x] WebSocket для real-time
- [ ] Тесты

### Frontend (следующий этап)
- [ ] React + TypeScript проект
- [ ] Авторизация (Owner + Discord OAuth2 flow)
- [ ] Owner Dashboard
- [ ] Admin Dashboard
- [ ] User Dashboard
- [ ] Real-time обновления (WebSocket)
- [ ] Деплой на Cloudflare Pages

### Bot (рефакторинг)
- [ ] Обновить database.py для multi-guild
- [ ] Обновить все cogs
- [ ] Добавить проверку модулей
- [ ] Оптимизация кода

### Деплой
- [ ] Backend на Railway
- [ ] Frontend на Cloudflare Pages
- [ ] Настроить DNS и SSL
- [ ] Тестирование

## 🔧 Troubleshooting

### Ошибка миграции БД
```
❌ Установите DEFAULT_GUILD_ID перед запуском миграции!
```
**Решение:** Откройте `migrate_to_v2.py` и замените `YOUR_GUILD_ID_HERE` на реальный ID сервера.

### Backend не запускается
```
ModuleNotFoundError: No module named 'fastapi'
```
**Решение:** Активируйте venv и установите зависимости:
```bash
.\venv\Scripts\Activate
pip install -r requirements.txt
```

### Discord OAuth2 не работает
```
Failed to exchange code for token
```
**Решение:** 
1. Проверьте что Client ID и Secret правильные
2. Проверьте что Redirect URI совпадает в Discord Developer Portal и .env
3. Убедитесь что добавлены scopes: `identify` и `guilds`

## 📞 Следующие шаги

**Хочешь продолжить с:**
1. **Frontend (React + Cloudflare Pages)** - создать веб-интерфейс
2. **Рефакторинг бота** - обновить существующий код для multi-guild
3. **Тестирование backend** - проверить что API работает
4. **Деплой** - настроить Railway и Cloudflare

Что делаем дальше?
