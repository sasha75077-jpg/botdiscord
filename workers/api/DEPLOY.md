# Деплой на Cloudflare - Пошаговая инструкция

## 1. Установка Wrangler CLI

```bash
cd workers/api
npm install
```

## 2. Авторизация в Cloudflare

```bash
npx wrangler login
```

## 3. Создание D1 базы данных

```bash
# Создать D1 базу
npx wrangler d1 create melancholia-db

# Скопировать database_id из вывода и вставить в wrangler.toml
```

Обновите `wrangler.toml`:
```toml
[[d1_databases]]
binding = "DB"
database_name = "melancholia-db"
database_id = "ВАШ_DATABASE_ID_ЗДЕСЬ"
```

## 4. Применить миграции D1

```bash
# Применить миграцию локально (для тестирования)
npx wrangler d1 execute melancholia-db --local --file=./migrations/0001_initial_schema.sql

# Применить миграцию в production
npx wrangler d1 execute melancholia-db --remote --file=./migrations/0001_initial_schema.sql
```

## 5. Создание R2 bucket для credentials

```bash
npx wrangler r2 bucket create melancholia-credentials
```

## 6. Создание KV namespace для кэша

```bash
# Production KV
npx wrangler kv:namespace create CACHE

# Скопировать id и вставить в wrangler.toml
```

Обновите `wrangler.toml`:
```toml
[[kv_namespaces]]
binding = "CACHE"
id = "ВАШ_KV_ID_ЗДЕСЬ"
```

## 7. Установка секретов

```bash
npx wrangler secret put DISCORD_CLIENT_ID
# Введите: 1330743576451223635

npx wrangler secret put DISCORD_CLIENT_SECRET
# Введите: oYeVafZ3Rdgi-IHBLTODh-OMzFALpQeD

npx wrangler secret put DISCORD_BOT_TOKEN
# Введите ваш Discord Bot Token

npx wrangler secret put SECRET_KEY
# Введите секретный ключ для JWT (любая длинная строка)

npx wrangler secret put OWNER_EMAIL
# Введите email владельца

npx wrangler secret put OWNER_PASSWORD
# Введите пароль владельца
```

## 8. Деплой API Worker

```bash
npx wrangler deploy
```

После деплоя вы получите URL вида: `https://melancholia-api.YOUR-SUBDOMAIN.workers.dev`

## 9. Обновить frontend

В настройках Cloudflare Pages добавьте переменную окружения:
- **Ключ:** `VITE_API_URL`
- **Значение:** `https://melancholia-api.YOUR-SUBDOMAIN.workers.dev`

## 10. Обновить Discord OAuth Redirect URI

В Discord Developer Portal → OAuth2 → Redirects добавьте:
```
https://melancholia-api.YOUR-SUBDOMAIN.workers.dev/auth/callback
```

## 11. Проверка деплоя

```bash
# Просмотр логов
npx wrangler tail

# Проверка health endpoint
curl https://melancholia-api.YOUR-SUBDOMAIN.workers.dev/health
```

## Локальная разработка

```bash
# Запуск локального dev сервера с локальной D1
npx wrangler dev --local
```

---

**Готово!** Теперь весь проект работает на Cloudflare без необходимости VPN.
