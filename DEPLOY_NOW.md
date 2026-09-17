# 🚀 Быстрый деплой - Пошаговая инструкция

## Подготовка (5 минут)

### 1. Создать файлы для деплоя ✅

Уже созданы:
- ✅ `backend/Procfile` - для Railway
- ✅ `backend/railway.json` - конфигурация Railway
- ✅ `frontend/.env.production` - production переменные

---

## Деплой Backend на Railway (10 минут)

### Шаг 1: Создать аккаунт Railway

1. Открыть https://railway.app
2. Нажать **Start a New Project**
3. Войти через GitHub
4. Подтвердить email

### Шаг 2: Создать проект

**Вариант A: Без Git (быстро, для теста)**

```bash
# Установить Railway CLI
npm install -g @railway/cli

# Перейти в backend
cd "C:\Users\User\Desktop\BOT Melancholia Now\backend"

# Войти
railway login

# Создать проект
railway init

# Задеплоить
railway up

# Получить URL
railway domain
```

**Вариант B: Через GitHub (для production)**

1. Создать GitHub репозиторий (если еще не создан)
2. В Railway: **New Project** → **Deploy from GitHub repo**
3. Выбрать репозиторий
4. Railway автоматически определит Python

### Шаг 3: Настроить переменные окружения

В Railway проекте нажать **Variables** и добавить:

```env
# Database
DATABASE_URL=sqlite+aiosqlite:///./bot.db

# Security (ВАЖНО: сгенерировать новый SECRET_KEY)
SECRET_KEY=<нажми кнопку Generate>

# Discord OAuth2
DISCORD_CLIENT_ID=1330743576451223635
DISCORD_CLIENT_SECRET=<твой_secret_из_Discord_Developer_Portal>
DISCORD_REDIRECT_URI=https://melancholia-panel.pages.dev/auth/callback
DISCORD_BOT_TOKEN=<твой_бот_токен_из_Discord_Developer_Portal>

# Owner Account
OWNER_EMAIL=admin@example.com
OWNER_PASSWORD=<придумай_надежный_пароль>

# CORS (обновить после создания Cloudflare Pages)
ALLOWED_ORIGINS=https://melancholia-panel.pages.dev

# API Settings
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=False
```

### Шаг 4: Получить URL backend

После деплоя Railway покажет URL типа:
```
https://melancholia-backend-production-XXXX.up.railway.app
```

**СКОПИРУЙ ЭТОТ URL** - он нужен для следующего шага!

---

## Деплой Frontend на Cloudflare Pages (10 минут)

### Шаг 1: Обновить .env.production

Открыть `frontend/.env.production` и заменить на реальный Railway URL:

```env
VITE_API_URL=https://melancholia-backend-production-XXXX.up.railway.app/api
VITE_WS_URL=wss://melancholia-backend-production-XXXX.up.railway.app/ws
```

### Шаг 2: Создать аккаунт Cloudflare

1. Открыть https://dash.cloudflare.com/
2. Sign up (бесплатно)
3. Подтвердить email

### Шаг 3: Задеплоить через Wrangler CLI (быстро)

```bash
# Установить Wrangler
npm install -g wrangler

# Перейти в frontend
cd "C:\Users\User\Desktop\BOT Melancholia Now\frontend"

# Авторизоваться
wrangler login

# Установить зависимости (если еще не установлены)
npm install

# Собрать production билд
npm run build

# Задеплоить
wrangler pages deploy dist --project-name=melancholia-panel

# Скопировать URL который покажется
```

**ИЛИ**

### Шаг 3 (альтернатива): Через GitHub

1. Создать GitHub репозиторий
2. Запушить код:
   ```bash
   cd "C:\Users\User\Desktop\BOT Melancholia Now"
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/ВАШ_USERNAME/melancholia-bot.git
   git push -u origin main
   ```

3. В Cloudflare Dashboard:
   - **Workers & Pages** → **Create application** → **Pages**
   - **Connect to Git** → выбрать репозиторий
   - **Build settings:**
     ```
     Framework preset: Vite
     Build command: npm run build
     Build output directory: dist
     Root directory: frontend
     ```
   - **Environment variables:**
     ```
     VITE_API_URL=https://your-railway-url.up.railway.app/api
     VITE_WS_URL=wss://your-railway-url.up.railway.app/ws
     ```
   - **Save and Deploy**

### Шаг 4: Получить URL frontend

Cloudflare покажет URL типа:
```
https://melancholia-panel.pages.dev
```

---

## Обновить Discord OAuth2 (5 минут)

### Шаг 1: Discord Developer Portal

1. Открыть https://discord.com/developers/applications
2. Выбрать свое приложение
3. Перейти в **OAuth2** → **General**

### Шаг 2: Добавить Redirect URI

В **Redirects** добавить:
```
https://melancholia-panel.pages.dev/auth/callback
```

Нажать **Save Changes**

### Шаг 3: Обновить Backend

Вернуться в Railway → **Variables** и обновить:
```env
DISCORD_REDIRECT_URI=https://melancholia-panel.pages.dev/auth/callback
ALLOWED_ORIGINS=https://melancholia-panel.pages.dev
```

Railway автоматически перезапустит backend.

---

## Проверка (5 минут)

### 1. Проверить Backend API

Открыть в браузере:
```
https://your-backend.railway.app/docs
```

Должен открыться Swagger UI с документацией API.

### 2. Проверить Frontend

Открыть в браузере:
```
https://melancholia-panel.pages.dev
```

Должна открыться страница входа.

### 3. Проверить Owner вход

1. Переключиться на вкладку **Owner**
2. Ввести email и пароль из Railway переменных
3. Должен войти и показать Owner Dashboard

### 4. Проверить Discord OAuth2

1. Переключиться на вкладку **Discord**
2. Нажать **Войти через Discord**
3. Авторизоваться в Discord
4. Должен вернуть на сайт и войти

---

## Troubleshooting

### Backend не отвечает

```bash
# Проверить логи в Railway
# Перейти в проект → Deployments → View Logs

# Проверить что все переменные установлены
# Variables → должны быть все из списка выше
```

### Frontend показывает ошибку API

```bash
# Проверить что VITE_API_URL правильный
# Должен заканчиваться на /api

# Проверить CORS в Railway
# ALLOWED_ORIGINS должен содержать URL frontend
```

### OAuth2 не работает

```bash
# Проверить Redirect URI в Discord
# Должен быть: https://melancholia-panel.pages.dev/auth/callback

# Проверить DISCORD_REDIRECT_URI в Railway
# Должен совпадать с Discord
```

---

## ✅ Чеклист деплоя

- [ ] Railway аккаунт создан
- [ ] Backend задеплоен на Railway
- [ ] Railway URL скопирован
- [ ] Environment variables настроены в Railway
- [ ] Cloudflare аккаунт создан
- [ ] Frontend задеплоен на Cloudflare Pages
- [ ] `.env.production` обновлен с Railway URL
- [ ] Discord Redirect URI обновлен
- [ ] Backend ALLOWED_ORIGINS обновлен
- [ ] Backend API работает (открывается /docs)
- [ ] Frontend загружается
- [ ] Owner вход работает
- [ ] Discord OAuth2 работает

---

## 🎉 Готово!

Теперь у тебя:
- ✅ Backend работает на Railway
- ✅ Frontend работает на Cloudflare Pages
- ✅ Автоматический SSL (HTTPS)
- ✅ Доступ из любой точки мира

**URLs:**
- Frontend: `https://melancholia-panel.pages.dev`
- Backend API: `https://your-backend.railway.app`
- API Docs: `https://your-backend.railway.app/docs`

---

## 🔄 Обновление после изменений

### Если меняешь Backend:

**Через Railway CLI:**
```bash
cd backend
railway up
```

**Через GitHub:**
```bash
git add .
git commit -m "Update backend"
git push
# Railway автоматически задеплоит
```

### Если меняешь Frontend:

**Через Wrangler:**
```bash
cd frontend
npm run build
wrangler pages deploy dist --project-name=melancholia-panel
```

**Через GitHub:**
```bash
git add .
git commit -m "Update frontend"
git push
# Cloudflare автоматически задеплоит
```

---

## 💡 Полезные команды

```bash
# Railway: посмотреть логи
railway logs

# Railway: открыть в браузере
railway open

# Wrangler: посмотреть проекты
wrangler pages project list

# Wrangler: логи
wrangler pages deployment tail
```

---

**Время выполнения: ~30 минут**
**Сложность: Легко**
**Стоимость: Бесплатно**
