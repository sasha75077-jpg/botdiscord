# Workers API — деплой и эксплуатация

Hono API на Cloudflare Workers + D1 (`melancholia-db`). R2 и KV **не используются** (закомментированы в `wrangler.toml`).

## Первичная настройка (уже выполнена, для справки)

```bash
cd workers/api
npx wrangler login
npx wrangler d1 create melancholia-db   # database_id уже в wrangler.toml
```

Миграции лежат в `migrations/` и применяются по порядку (сейчас `0001`–`0011`):

```bash
npx wrangler d1 execute melancholia-db --remote --yes --file=migrations/0001_initial_schema.sql
```

Секреты (все уже заданы, команды на случай ротации):

```bash
npx wrangler secret put DISCORD_CLIENT_ID
npx wrangler secret put DISCORD_CLIENT_SECRET
npx wrangler secret put DISCORD_BOT_TOKEN
npx wrangler secret put SECRET_KEY
npx wrangler secret put OWNER_EMAIL
npx wrangler secret put OWNER_PASSWORD
npx wrangler secret put SYNC_SECRET   # ключ бота (он же PANEL_SYNC_SECRET в .env бота)
```

## Деплой

```bash
cd workers/api
npx wrangler deploy
# → https://melancholia-api.sasha75077.workers.dev
```

## Связки, которые легко сломать

* `VITE_API_URL` на Pages — **без `/api`** на конце.
* Discord Developer Portal → OAuth2 → Redirects: `https://botdiscord-87a.pages.dev/auth/callback` (редирект идет на **фронт**, не на API).
* CORS разрешает только прод-домен и `localhost:5173` (`src/index.ts`).
* Токены: access 1ч, refresh 7d. Протухший access — **401** (фронт обновляет), а не 403.

## Диагностика

```bash
npx wrangler tail --format pretty
npx wrangler d1 execute melancholia-db --remote --command="SELECT COUNT(*) FROM contracts;"
curl https://melancholia-api.sasha75077.workers.dev/health
```

## Роуты (префикс — корень, без /api)

`/auth/*` (url, callback, owner/login, refresh, switch, me), `/guilds/*` (+ contracts/users/permissions/applications внутри), `/contracts/*`, `/users/*`, `/permissions/*`, `/prices`, `/showcase`, `/panels/*`.

Запись требует JWT (ролевые проверки внутри) или `SYNC_SECRET` (бот). GET в основном открытые.
