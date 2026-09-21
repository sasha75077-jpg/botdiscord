# Frontend — веб-панель Melancholia

React + TypeScript + Vite. Бэкенд — Cloudflare Workers (`workers/api`), база — D1. Старого Railway/FastAPI-бэкенда больше нет.

## Настройка

```env
# .env.production (локально; в git не лежит)
VITE_API_URL=https://melancholia-api.<subdomain>.workers.dev
```

Важно: **без `/api` на конце** — воркер отдает `/auth`, `/guilds` и т.д. напрямую. WebSocket нет (опрос через React Query).

## Запуск

```bash
npm install
npm run dev      # http://localhost:3000 (прокси /api -> localhost:8000, legacy)
npm run build    # tsc + vite → dist/
```

## Деплой на Cloudflare Pages

Проект `botdiscord` (домен `botdiscord-87a.pages.dev`) привязан к Git — прод собирается сам при `git push`.

```bash
git add ... && git commit -m "..." && git push
# дашборд: Workers & Pages → botdiscord → Deployments → Success (2-3 мин)
```

Вручную (черновик для проверки):

```bash
npm run build
npx wrangler pages deploy dist --project-name=botdiscord
```

Переменная Pages (Dashboard → Settings → Environment Variables, Production + Preview):

```
VITE_API_URL=https://melancholia-api.<subdomain>.workers.dev
```

## Роли и маршруты

| Роль | Что видит |
|------|-----------|
| owner | Все серверы, витрина, цены, пользователи, настройки |
| admin | Свой сервер: контракты, заявки, премии, ранги, роли, пользователи, уведомления, панели, цены |
| recruiter | Свои + очередь заявок/контрактов (только агитации на отправку), таблица |
| user | Свои контракты/заявки/премии, таблица семьи, цены, профиль |
| stranger | Только витрина серверов |

Роль зашита в JWT при входе + тихо обновляется при загрузке (`App.tsx`). Протухший токен дает 401 (фронт обновляет), не 403.

## Темы

`darkMode: 'class'`. По умолчанию `auto` — следит за `prefers-color-scheme` + переключатель в шапке (`ThemeToggle`, хранит `localStorage.theme`). Инлайн-скрипт в `index.html` ставит класс до отрисовки.

## Структура

```
frontend/src/
├── components/   # ContractForm, ApplicationForm, GuildSwitcher, ThemeToggle, ...
├── layouts/      # OwnerLayout, AdminLayout, UserLayout
├── lib/api.ts    # axios + все API-клиенты
├── pages/        # owner/, admin/, user/, contracts/, applications/, ...
├── store/        # authStore (zustand persist)
├── App.tsx       # роуты по ролям
└── index.css     # tailwind + .btn/.card/.input
```

## Стек

React 18, TypeScript, Vite 5, TailwindCSS, React Router 6, React Query 5, Zustand 4, Axios, Lucide Icons.
