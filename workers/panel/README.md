# Панель на Workers (обход блокировки *.pages.dev в РФ)

Фронт раздается как Workers Static Assets с `workers.dev`-домена,
который в РФ открывается (в отличие от `*.pages.dev`).

## Деплой

```bash
cd frontend
$env:VITE_API_URL="https://melancholia-api.sasha75077.workers.dev"; npm run build
# Workers Static Assets не переваривает Pages-правило /* /index.html (ругается на цикл):
Remove-Item dist/_redirects
cd ../workers/panel
npx wrangler deploy
# → https://melancholia-panel.sasha75077.workers.dev
```

SPA-фолбэк дает `not_found_handling = "single-page-application"`.
Воркер без `main` (чистые ассеты): со stub-скриптом несопоставленные
роуты падали в заглушку вместо `index.html`.

`public/_redirects` оставлен для Pages-зеркала — перед деплоем на воркер
его копия в `dist/` удаляется (см. выше).

## Связки

- CORS API (`workers/api/src/index.ts`) должен содержать URL панели.
- `FRONTEND_URL` API = URL панели (Discord OAuth `redirect_uri`).
- Discord Developer Portal → OAuth2 → Redirects: добавить
  `https://melancholia-panel.sasha75077.workers.dev/auth/callback`.
- Pages (`botdiscord-87a.pages.dev`) оставлен как запасное зеркало.
