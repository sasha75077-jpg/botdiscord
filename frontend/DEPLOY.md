# 🚀 Быстрый старт деплоя

## Локальная разработка

```bash
cd frontend
npm install
npm run dev
```

Откройте http://localhost:3000

## Деплой на Cloudflare Pages

### Вариант 1: Через Dashboard (проще)

1. Зайдите на https://dash.cloudflare.com/
2. Pages → Create a project → Connect to Git
3. Выберите репозиторий
4. Настройки сборки:
   - Build command: `npm run build`
   - Build output directory: `dist`
   - Root directory: `frontend`
5. Environment variables:
   - `VITE_API_URL` = `https://your-backend-api.com/api`
6. Save and Deploy

### Вариант 2: Через CLI

```bash
# Установите Wrangler
npm install -g wrangler

# Логин
wrangler login

# Деплой
cd frontend
npm run build
wrangler pages publish dist --project-name=melancholia-bot-panel
```

## После деплоя

1. **Обновите CORS на backend**
   Добавьте URL Cloudflare Pages в `ALLOWED_ORIGINS`

2. **Обновите Discord OAuth**
   Добавьте в Discord Developer Portal:
   ```
   https://your-project.pages.dev/auth/callback
   ```

3. **Проверьте работу**
   - Логин через Discord
   - API запросы
   - Роутинг

Полная инструкция: [CLOUDFLARE_DEPLOY.md](../CLOUDFLARE_DEPLOY.md)
