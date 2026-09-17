# Архитектура системы Bot Melancholia Now

## Обзор
Модернизация Discord бота с веб-панелью управления на Cloudflare для поддержки нескольких серверов.

## Компоненты системы

### 1. Discord Bot (Python)
- **Текущее состояние**: Монолитный бот для одного сервера
- **Цель**: Multi-guild бот с оптимизированной архитектурой
- **Стек**: discord.py, aiosqlite, asyncio
- **Изменения**:
  - Поддержка нескольких серверов Discord
  - Изоляция данных по guild_id
  - Оптимизация cogs и database слоя
  - WebSocket/REST API клиент для связи с панелью

### 2. REST API Backend (Python)
- **Стек**: FastAPI (рекомендуется) или Flask
- **Функции**:
  - CRUD операции для контрактов, отчетов, пользователей
  - Управление настройками серверов
  - Авторизация и аутентификация
  - WebSocket для real-time обновлений
- **Деплой**: VPS/Railway/Fly.io (нужен постоянный процесс)

### 3. Web Panel (Frontend)
- **Стек**: React + TypeScript + Tailwind CSS (или Next.js)
- **Деплой**: Cloudflare Pages
- **Функции**:
  - Owner Dashboard
  - Admin Dashboard
  - User Dashboard
  - Управление серверами
  - Отчеты и аналитика

### 4. База данных
- **Текущая**: SQLite (bot.db)
- **Рекомендация**: 
  - **Вариант A**: PostgreSQL (для production, масштабируемость)
  - **Вариант B**: Cloudflare D1 (SQLite в облаке, интеграция с Workers)
  - **Вариант C**: Оставить SQLite + добавить Cloudflare KV для кеша
- **Изменения**:
  - Добавить таблицу `guilds` (серверы Discord)
  - Добавить таблицу `guild_settings` (настройки по серверам)
  - Добавить таблицу `permissions` (права доступа)
  - Добавить `guild_id` во все существующие таблицы

## Уровни доступа

### Owner (Ты)
- **Авторизация**: Email + Password (только ты)
- **Права**:
  - ✅ Полный доступ ко всем серверам
  - ✅ Управление API ключами
  - ✅ Просмотр логов всех серверов
  - ✅ Управление администраторами
  - ✅ Глобальные настройки бота
  - ✅ Статистика и аналитика всех серверов
  - ✅ Backup и restore базы данных

### Administrator (Админ сервера Discord)
- **Авторизация**: Discord OAuth2 (проверка роли на сервере)
- **Права** (только для своего сервера):
  - ✅ Настройки функций бота (включение/выключение модулей)
  - ✅ Управление контрактами
  - ✅ Просмотр и одобрение отчетов пользователей
  - ✅ Настройка каналов и ролей
  - ✅ Управление ценами и бонусами
  - ✅ Статистика сервера
  - ❌ Доступ к другим серверам
  - ❌ Глобальные настройки

### User (Обычный пользователь)
- **Авторизация**: Discord OAuth2
- **Права**:
  - ✅ Просмотр своих контрактов
  - ✅ Подача отчетов о бонусах
  - ✅ Просмотр своей статистики
  - ✅ Просмотр своего профиля и ранга
  - ❌ Доступ к админ функциям
  - ❌ Просмотр данных других пользователей

## Схема взаимодействия

```
┌─────────────────────────────────────────────────────────────┐
│                     Cloudflare Pages                         │
│  ┌───────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Owner Panel   │  │ Admin Panel  │  │ User Panel   │     │
│  │ (Login/Pass)  │  │ (OAuth2)     │  │ (OAuth2)     │     │
│  └───────────────┘  └──────────────┘  └──────────────┘     │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTPS REST API
                         │
┌────────────────────────▼────────────────────────────────────┐
│                    FastAPI Backend                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Auth Service │  │ API Routes   │  │ WebSocket    │     │
│  │ (JWT/OAuth2) │  │ (/api/...)   │  │ (real-time)  │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│         │                   │                   │           │
│         └───────────────────┼───────────────────┘           │
└─────────────────────────────┼─────────────────────────────────┘
                              │
                    ┌─────────▼──────────┐
                    │   PostgreSQL/D1    │
                    │   (Multi-guild DB) │
                    └─────────┬──────────┘
                              │
┌─────────────────────────────▼─────────────────────────────────┐
│                     Discord Bot (Python)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ Cogs         │  │ Event Handler│  │ API Client   │       │
│  │ (Commands)   │  │ (Guild Events)│  │ (to Backend) │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
└───────────────────────────────────────────────────────────────┘
                              │
                              ▼
                     ┌─────────────────┐
                     │ Discord Servers │
                     │ (Multiple)      │
                     └─────────────────┘
```

## API Endpoints (примерная структура)

### Authentication
- `POST /api/auth/owner/login` - Owner логин (email/password)
- `POST /api/auth/discord/callback` - Discord OAuth2 callback
- `POST /api/auth/refresh` - Обновление JWT токена
- `GET /api/auth/me` - Получение текущего пользователя

### Guilds (Owner только)
- `GET /api/guilds` - Список всех серверов
- `GET /api/guilds/:id` - Информация о сервере
- `PUT /api/guilds/:id/settings` - Глобальные настройки сервера

### Contracts (Admin, Owner)
- `GET /api/guilds/:guild_id/contracts` - Список контрактов
- `GET /api/guilds/:guild_id/contracts/:id` - Детали контракта
- `PUT /api/guilds/:guild_id/contracts/:id` - Обновление статуса
- `DELETE /api/guilds/:guild_id/contracts/:id` - Удаление контракта

### Reports (User, Admin, Owner)
- `GET /api/guilds/:guild_id/reports/my` - Мои отчеты (User)
- `POST /api/guilds/:guild_id/reports` - Создание отчета
- `GET /api/guilds/:guild_id/reports` - Все отчеты (Admin)
- `PUT /api/guilds/:guild_id/reports/:id/approve` - Одобрение (Admin)

### Users
- `GET /api/guilds/:guild_id/users/me` - Мой профиль
- `GET /api/guilds/:guild_id/users/:id` - Профиль пользователя (Admin)
- `GET /api/guilds/:guild_id/users/:id/stats` - Статистика пользователя

### Settings (Admin, Owner)
- `GET /api/guilds/:guild_id/settings` - Настройки сервера
- `PUT /api/guilds/:guild_id/settings` - Обновление настроек
- `GET /api/guilds/:guild_id/settings/modules` - Включенные модули
- `PUT /api/guilds/:guild_id/settings/modules/:name` - Вкл/выкл модуль

## Новая структура базы данных

### Новые таблицы

```sql
-- Серверы Discord
CREATE TABLE guilds (
    guild_id TEXT PRIMARY KEY,
    guild_name TEXT NOT NULL,
    owner_id TEXT,
    added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1
);

-- Настройки серверов
CREATE TABLE guild_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id TEXT NOT NULL,
    setting_key TEXT NOT NULL,
    setting_value TEXT,
    FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE,
    UNIQUE(guild_id, setting_key)
);

-- Права доступа
CREATE TABLE permissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id TEXT NOT NULL,
    discord_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('owner', 'admin', 'user')),
    granted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    granted_by TEXT,
    FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE,
    UNIQUE(guild_id, discord_id)
);

-- Owner аккаунт (для веб-панели)
CREATE TABLE owner_account (
    id INTEGER PRIMARY KEY CHECK(id = 1),
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Изменения существующих таблиц

Добавить `guild_id TEXT` в:
- `contracts`
- `users`
- `bonus_reports`
- `applications`
- `settings` (или заменить на guild_settings)

## Стек технологий

### Backend
- **FastAPI** - современный, быстрый, async
- **SQLAlchemy** - ORM для работы с БД
- **Alembic** - миграции БД
- **python-jose** - JWT токены
- **passlib** - хеширование паролей
- **httpx** - async HTTP клиент

### Frontend
- **React 18** + **TypeScript**
- **Vite** - быстрый сборщик
- **Tailwind CSS** - стилизация
- **React Query** - кеширование запросов
- **Zustand** - state management
- **React Router** - роутинг

### DevOps
- **Cloudflare Pages** - frontend hosting
- **Railway/Fly.io** - backend hosting (или VPS)
- **GitHub Actions** - CI/CD
- **Docker** - контейнеризация

## План миграции

### Этап 1: Подготовка (1-2 дня)
1. Backup текущей базы данных
2. Создание новой схемы БД
3. Миграция данных с добавлением guild_id

### Этап 2: Backend API (3-5 дней)
1. Настройка FastAPI проекта
2. Реализация авторизации (OAuth2 + JWT)
3. Создание CRUD эндпоинтов
4. Интеграция с Discord API

### Этап 3: Рефакторинг бота (2-3 дня)
1. Оптимизация существующих cogs
2. Добавление поддержки multi-guild
3. Интеграция с Backend API
4. Кеширование и производительность

### Этап 4: Frontend (4-6 дней)
1. Настройка React проекта
2. Реализация OAuth2 flow
3. Создание Owner/Admin/User панелей
4. Интеграция с Backend API

### Этап 5: Деплой (1-2 дня)
1. Настройка Cloudflare Pages
2. Деплой backend
3. Настройка DNS и SSL
4. Тестирование

## Вопросы для принятия решений

1. **База данных**: PostgreSQL (масштабируемость) или Cloudflare D1 (интеграция)?
2. **Backend хостинг**: Railway, Fly.io или VPS?
3. **Нужен ли WebSocket** для real-time обновлений или достаточно polling?
4. **Google Sheets**: оставить интеграцию или полностью перейти на веб-панель?
5. **Дизайн**: использовать готовый UI kit (Tailwind UI, shadcn/ui) или кастомный?

## Следующие шаги

Что делаем первым делом?
1. Создаю схему новой базы данных и миграцию
2. Начинаю с FastAPI backend структуры
3. Оптимизирую существующий код бота
4. Начинаю с frontend (React + Cloudflare Pages)
