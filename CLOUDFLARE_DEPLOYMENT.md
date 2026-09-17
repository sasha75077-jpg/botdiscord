# 🚀 Деплой на Cloudflare Pages + Railway

## 📦 Что куда деплоим

- **Frontend** → Cloudflare Pages (React приложение)
- **Backend** → Railway (FastAPI нужен постоянный процесс)
- **Bot** → Твой компьютер или VPS (Discord бот должен работать 24/7)

> **Почему backend не на Cloudflare Workers?**
> Cloudflare Workers не поддерживают постоянные WebSocket соединения и SQLite файлы. Railway лучше подходит для FastAPI + SQLite.

---

## 1️⃣ Frontend на Cloudflare Pages

### Способ A: Через GitHub (Рекомендуется)

**Шаг 1: Создать Git репозиторий**

```bash
cd "C:\Users\User\Desktop\BOT Melancholia Now"

# Инициализировать git
git init

# Добавить .gitignore если его нет
# (он уже создан в frontend/.gitignore)

# Добавить все файлы
git add .
git commit -m "Initial commit: Melancholia v2.0"

# Создать репозиторий на GitHub и подключить
git remote add origin https://github.com/ВАШ_USERNAME/melancholia-bot.git
git branch -M main
git push -u origin main
```

**Шаг 2: Подключить к Cloudflare Pages**

1. Перейти на https://dash.cloudflare.com/
2. Слева выбрать **Workers & Pages**
3. Нажать **Create application** → **Pages** → **Connect to Git**
4. Выбрать репозиторий **melancholia-bot**
5. Настройки сборки:
   ```
   Project name: melancholia-panel
   Production branch: main
   Framework preset: Vite
   Build command: npm run build
   Build output directory: dist
   Root directory: frontend
   ```

6. **Environment variables (Production):**
   ```
   VITE_API_URL=https://your-backend.up.railway.app/api
   VITE_WS_URL=wss://your-backend.up.railway.app/ws
   ```
   (Railway URL получишь после деплоя backend)

7. Нажать **Save and Deploy**

**Результат:** 
- URL: `https://melancholia-panel.pages.dev`
- Автоматический деплой при каждом push в main

---

### Способ B: Через Wrangler CLI (Быстрый)

```bash
cd frontend

# Установить Wrangler глобально
npm install -g wrangler

# Авторизоваться в Cloudflare
wrangler login

# Создать .env.production
echo VITE_API_URL=https://your-backend.railway.app/api > .env.production
echo VITE_WS_URL=wss://your-backend.railway.app/ws >> .env.production

# Собрать production билд
npm run build

# Задеплоить
wrangler pages deploy dist --project-name=melancholia-panel
```

---

## 2️⃣ Backend на Railway

Railway предоставляет бесплатный tier и отлично подходит для Python приложений.

**Шаг 1: Создать аккаунт**

1. Перейти на https://railway.app
2. Sign up with GitHub
3. Верифицировать email

**Шаг 2: Задеплоить backend**

### Вариант A: Через GitHub (автоматический деплой)

1. В Railway: **New Project** → **Deploy from GitHub repo**
2. Выбрать репозиторий `melancholia-bot`
3. Railway автоматически определит Python
4. **Root directory:** указать `backend`

### Вариант B: Через Railway CLI

```bash
# Установить Railway CLI
npm install -g @railway/cli

# Войти в Railway
railway login

# Перейти в папку backend
cd backend

# Инициализировать проект
railway init

# Задеплоить
railway up
```

**Шаг 3: Настроить Environment Variables**

В Railway проекте → **Variables** добавить:

```env
DATABASE_URL=sqlite+aiosqlite:///./bot.db
SECRET_KEY=<сгенерировать: python -c "import secrets; print(secrets.token_hex(32))">
DISCORD_CLIENT_ID=<твой_client_id>
DISCORD_CLIENT_SECRET=<твой_client_secret>
DISCORD_REDIRECT_URI=https://melancholia-panel.pages.dev/auth/callback
DISCORD_BOT_TOKEN=<твой_bot_token>
OWNER_EMAIL=admin@example.com
OWNER_PASSWORD=<надежный_пароль>
ALLOWED_ORIGINS=https://melancholia-panel.pages.dev
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=False
```

**Шаг 4: Получить Railway URL**

После деплоя Railway даст URL типа:
```
https://melancholia-backend-production-XXXX.up.railway.app
```

Скопировать этот URL и обновить в Cloudflare Pages:
```
VITE_API_URL=https://melancholia-backend-production-XXXX.up.railway.app/api
VITE_WS_URL=wss://melancholia-backend-production-XXXX.up.railway.app/ws
```

**Шаг 5: Redeploy Frontend**

После обновления env переменных в Cloudflare Pages:
- Перейти в **Deployments**
- Нажать **Retry deployment** на последнем деплое
- Или сделать новый commit и push

---

## 3️⃣ Обновить Discord OAuth2

После деплоя обновить Redirect URI в Discord Developer Portal:

1. https://discord.com/developers/applications
2. Твое приложение → **OAuth2** → **General**
3. **Redirects** добавить:
   ```
   https://melancholia-panel.pages.dev/auth/callback
   ```
4. **Save Changes**

---

## 4️⃣ Проверка деплоя

### Проверить Backend

```bash
# Открыть в браузере
https://your-backend.railway.app/docs

# Должен открыться Swagger UI
```

### Проверить Frontend

```bash
# Открыть в браузере
https://melancholia-panel.pages.dev

# Должна открыться страница входа
```

### Проверить OAuth2

1. На странице входа нажать "Войти через Discord"
2. Должен перенаправить на Discord
3. После авторизации вернуть обратно

---

## 5️⃣ Настройка кастомного домена (опционально)

### Cloudflare Pages

1. В проекте Pages → **Custom domains**
2. Добавить свой домен (например: `panel.melancholia.bot`)
3. Cloudflare автоматически настроит SSL

### Railway

1. В проекте → **Settings** → **Domains**
2. Добавить кастомный домен
3. Настроить CNAME в DNS

---

## 📁 Структура файлов для деплоя

Убедись что эти файлы на месте:

```
BOT Melancholia Now/
├── frontend/
│   ├── package.json           ✅ Нужен для Cloudflare
│   ├── vite.config.ts         ✅ Настройки сборки
│   ├── .env.production        ✅ Production переменные
│   └── dist/                  (создастся при build)
│
└── backend/
    ├── requirements.txt       ✅ Нужен для Railway
    ├── run.py                 ✅ Entry point
    ├── Procfile              ⚠️ Создадим сейчас
    └── railway.json          ⚠️ Создадим сейчас
```

---

## 🔧 Файлы для Railway

### Создать `backend/Procfile`

```
web: python run.py
```

### Создать `backend/railway.json`

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "python run.py",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

---

## 💰 Стоимость

- **Cloudflare Pages:** Бесплатно (500 сборок/месяц)
- **Railway:** 
  - Free tier: $5 кредитов/месяц
  - Хватит на ~500 часов работы
  - После этого $5/месяц за дополнительные ресурсы

---

## 🔒 Безопасность

### Backend

1. **SECRET_KEY:** Сгенерировать уникальный
2. **OWNER_PASSWORD:** Использовать надежный пароль
3. **DEBUG:** Установить в `False` для production

### Frontend

1. **HTTPS:** Cloudflare автоматически использует SSL
2. **Environment variables:** Хранятся безопасно в Cloudflare

### Discord

1. **Client Secret:** Никогда не коммитить в git
2. **Bot Token:** Хранить только в переменных окружения

---

## 🚨 Troubleshooting

### Frontend не загружается

```bash
# Проверить env переменные
# В Cloudflare Pages → Settings → Environment variables
# Должны быть VITE_API_URL и VITE_WS_URL

# Пересобрать
# Deployments → Retry deployment
```

### Backend не отвечает

```bash
# Проверить логи в Railway
# Project → Deployments → View logs

# Проверить что все env переменные установлены
# Project → Variables
```

### OAuth2 не работает

```bash
# Проверить Redirect URI
# Discord Developer Portal → OAuth2
# Должен быть: https://melancholia-panel.pages.dev/auth/callback

# Проверить что в Railway установлен
# DISCORD_REDIRECT_URI=https://melancholia-panel.pages.dev/auth/callback
```

### WebSocket не подключается

```bash
# Проверить что URL начинается с wss:// а не ws://
VITE_WS_URL=wss://your-backend.railway.app/ws

# Проверить CORS в backend
# ALLOWED_ORIGINS должен включать URL frontend
```

---

## 📊 Мониторинг

### Cloudflare Pages

- Analytics встроен
- Можно смотреть количество посещений
- Pages → Analytics

### Railway

- Metrics встроены
- CPU, Memory, Network
- Project → Metrics

---

## 🔄 CI/CD (Автоматический деплой)

После настройки через GitHub:

1. **Сделать изменения** в коде
2. **Commit и push**:
   ```bash
   git add .
   git commit -m "Update feature"
   git push
   ```
3. **Cloudflare и Railway автоматически задеплоят** новую версию

---

## 📞 Следующие шаги

1. ✅ Создать GitHub репозиторий
2. ✅ Задеплоить backend на Railway
3. ✅ Задеплоить frontend на Cloudflare Pages
4. ✅ Обновить Discord OAuth2 Redirect URI
5. ✅ Протестировать вход и функции
6. ✅ Настроить кастомный домен (опционально)

**Хочешь чтобы я создал эти файлы (`Procfile`, `railway.json`, `.env.production`) прямо сейчас?**
