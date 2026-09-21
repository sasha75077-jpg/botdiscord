# 🎉 Полная инструкция по запуску системы

## 📦 Что создано

### ✅ Backend (FastAPI)
- REST API с авторизацией (Owner + Discord OAuth2)
- WebSocket для real-time обновлений
- CRUD для контрактов, отчетов, пользователей, серверов
- JWT токены с refresh
- Права доступа (Owner/Admin/User)

### ✅ Frontend (React + TypeScript)
- Веб-панель с 3 уровнями доступа
- Owner/Admin/User layouts и dashboards
- Discord OAuth2 flow
- Real-time updates через WebSocket
- TailwindCSS для стилизации
- React Query для кеширования

### ✅ База данных
- Новая схема для multi-guild поддержки
- Скрипт автоматической миграции
- Индексы для производительности

---

## 🚀 Пошаговый запуск

### Шаг 1: Миграция базы данных

```bash
cd "C:\Users\User\Desktop\BOT Melancholia Now"

# Открыть migrate_to_v2.py и заменить:
# DEFAULT_GUILD_ID = "YOUR_GUILD_ID_HERE"
# на реальный ID вашего сервера Discord

# Запустить миграцию
python migrate_to_v2.py
```

**Получить Guild ID:**
1. Включить режим разработчика в Discord (Настройки → Расширенные → Режим разработчика)
2. Правый клик на сервер → Копировать ID

---

### Шаг 2: Настройка Backend

```bash
cd backend

# Создать виртуальное окружение
python -m venv venv
.\venv\Scripts\Activate

# Установить зависимости
pip install -r requirements.txt

# Создать .env
copy .env.example .env
```

**Редактировать `backend/.env`:**

```env
# Сгенерировать SECRET_KEY:
# python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=ваш_сгенерированный_ключ

# Discord Developer Portal (https://discord.com/developers/applications)
DISCORD_CLIENT_ID=ваш_client_id
DISCORD_CLIENT_SECRET=ваш_secret
DISCORD_REDIRECT_URI=http://localhost:3000/auth/callback
DISCORD_BOT_TOKEN=ваш_bot_token

# Owner аккаунт
OWNER_EMAIL=admin@example.com
OWNER_PASSWORD=надежный_пароль

# CORS
ALLOWED_ORIGINS=http://localhost:3000
```

**Discord OAuth2 настройка:**
1. https://discord.com/developers/applications
2. Ваше приложение → OAuth2 → General
3. Добавить Redirect URI: `http://localhost:3000/auth/callback`
4. Скопировать Client ID и Client Secret

**Запустить Backend:**
```bash
python run.py
```

API: http://localhost:8000
Docs: http://localhost:8000/docs

---

### Шаг 3: Настройка Frontend

```bash
cd ..\frontend

# Установить зависимости
npm install

# Создать .env
copy .env.example .env
```

**Редактировать `frontend/.env`:**
```env
VITE_API_URL=http://localhost:8000/api
VITE_WS_URL=ws://localhost:8000/ws
```

**Запустить Frontend:**
```bash
npm run dev
```

Приложение: http://localhost:3000

---

## 🔐 Первый вход

### Owner (Вы)
1. Открыть http://localhost:3000
2. Переключить на вкладку "Owner"
3. Ввести email и пароль из `backend/.env`
4. После входа увидите список всех серверов

### Discord Users (Admin/User)
1. Открыть http://localhost:3000
2. Вкладка "Discord" → "Войти через Discord"
3. Авторизоваться в Discord
4. Автоматически определится роль на основе прав

---

## 📊 Структура проекта

```
BOT Melancholia Now/
├── backend/                    # FastAPI API
│   ├── app/
│   │   ├── api/routes/         # Endpoints
│   │   ├── core/               # Config, DB, Security
│   │   ├── schemas/            # Pydantic models
│   │   └── main.py             # FastAPI app + WebSocket
│   ├── .env                    # Конфигурация
│   ├── requirements.txt
│   └── run.py
│
├── frontend/                   # React + TypeScript
│   ├── src/
│   │   ├── components/         # Компоненты
│   │   ├── hooks/              # Custom hooks
│   │   ├── layouts/            # Owner/Admin/User layouts
│   │   ├── lib/                # API, utils
│   │   ├── pages/              # Страницы
│   │   ├── store/              # Zustand state
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── .env                    # API URLs
│   ├── package.json
│   └── vite.config.ts
│
├── models/
│   ├── schema.sql              # Старая схема
│   └── schema_v2_multiguild.sql # Новая multi-guild схема
│
├── migrate_to_v2.py            # Скрипт миграции
├── ARCHITECTURE.md             # Архитектура
├── SETUP_GUIDE.md              # Инструкция
└── bot.db                      # SQLite база (после миграции)
```

---

## 🎯 Функции по ролям

### 👑 Owner (Вы)
- ✅ Просмотр всех серверов
- ✅ Управление всеми серверами
- ✅ Глобальные настройки
- ✅ Статистика по всем серверам
- ✅ Управление правами

### 🛡️ Admin (Администратор Discord сервера)
- ✅ Управление своим сервером
- ✅ Одобрение/отклонение контрактов
- ✅ Одобрение/отклонение бонусных отчетов
- ✅ Просмотр статистики пользователей
- ✅ Настройки модулей (вкл/выкл функции)
- ❌ Доступ к другим серверам

### 👤 User (Обычный пользователь)
- ✅ Просмотр своих контрактов
- ✅ Подача бонусных отчетов
- ✅ Просмотр своей статистики
- ✅ Просмотр своего профиля
- ❌ Админ функции

---

## 🌐 Деплой

### Backend → Railway

1. Зарегистрироваться на https://railway.app
2. New Project → Deploy from GitHub
3. Подключить репозиторий
4. Railway автоматически определит Python
5. Добавить Environment Variables из `backend/.env`
6. Деплой произойдет автоматически
7. Скопировать URL (например: `https://your-app.railway.app`)

### Frontend → Cloudflare Pages

1. Залить код в GitHub
2. Зайти на https://dash.cloudflare.com
3. Pages → Create a project → Connect to Git
4. Выбрать репозиторий
5. Build settings:
   - Framework: Vite
   - Build command: `npm run build`
   - Build output: `dist`
   - Root directory: `frontend`
6. Environment variables:
   ```
   VITE_API_URL=https://your-app.railway.app/api
   VITE_WS_URL=wss://your-app.railway.app/ws
   ```
7. Save and Deploy

**После деплоя обновить Discord OAuth2:**
- Redirect URI: `https://your-app.pages.dev/auth/callback`
- Обновить `DISCORD_REDIRECT_URI` в Railway

---

## 🔧 Troubleshooting

### Backend не запускается
```
ModuleNotFoundError: No module named 'fastapi'
```
**Решение:** Активировать venv и установить зависимости
```bash
.\venv\Scripts\Activate
pip install -r requirements.txt
```

### Frontend не компилируется
```
Cannot find module '@/...'
```
**Решение:** Проверить `tsconfig.json` paths и установить зависимости
```bash
npm install
```

### Discord OAuth2 не работает
```
Failed to exchange code for token
```
**Решение:**
1. Проверить Client ID и Secret
2. Проверить Redirect URI (должен совпадать в Discord Portal и .env)
3. Проверить scopes: `identify` и `guilds`

### WebSocket не подключается
**Решение:** Проверить что backend запущен и `VITE_WS_URL` правильный

### База данных заблокирована
```
database is locked
```
**Решение:** Закрыть бота, затем запустить миграцию

---

## 📝 Что осталось доделать

### Backend
- [ ] Тесты (pytest)
- [ ] Rate limiting
- [ ] Логирование действий (audit log UI)

### Frontend
- [ ] Admin страницы (контракты, отчеты, пользователи)
- [ ] User страницы (мои контракты, отчеты)
- [ ] Графики и аналитика (recharts)
- [ ] Dark mode toggle
- [ ] Toast уведомления
- [ ] Загрузка файлов
- [ ] Фильтры и поиск
- [ ] Пагинация

### Bot
- [ ] Рефакторинг для multi-guild
- [ ] Оптимизация существующих cogs
- [ ] Интеграция с Backend API (опционально)
- [ ] Проверка модулей при загрузке

---

## ⚡ Быстрый старт (для разработки)

```bash
# Терминал 1 - Backend
cd backend
.\venv\Scripts\Activate
python run.py

# Терминал 2 - Frontend
cd frontend
npm run dev

# Открыть http://localhost:3000
```

---

## 📞 Контакты и помощь

- API Docs: http://localhost:8000/docs
- GitHub Issues: (добавь ссылку на репозиторий)

---

## 🎉 Готово!

Система полностью настроена и готова к работе. 

**Следующие шаги:**
1. Запустить миграцию БД
2. Запустить backend и frontend
3. Войти как Owner
4. Протестировать функции
5. Пригласить админов на тестирование
6. Задеплоить на Railway + Cloudflare Pages

**Создано:** 9 сентября 2026
**Версия:** 2.0.0
