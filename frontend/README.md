# Frontend

React + TypeScript + Vite веб-панель для управления Discord ботом Melancholia.

## Установка

```bash
npm install
```

## Настройка

Создать `.env` файл:

```env
VITE_API_URL=http://localhost:8000/api
VITE_WS_URL=ws://localhost:8000/ws
```

Для production (Cloudflare Pages):

```env
VITE_API_URL=https://your-backend-url.railway.app/api
VITE_WS_URL=wss://your-backend-url.railway.app/ws
```

## Запуск

Development:
```bash
npm run dev
```

Build:
```bash
npm run build
```

Preview:
```bash
npm run preview
```

## Структура

```
frontend/
├── src/
│   ├── components/       # Переиспользуемые компоненты
│   ├── hooks/            # Custom hooks
│   ├── layouts/          # Layout компоненты
│   ├── lib/              # Утилиты (API, helpers)
│   ├── pages/            # Страницы
│   ├── store/            # Zustand stores
│   ├── App.tsx           # Главный компонент
│   ├── main.tsx          # Entry point
│   └── index.css         # Global styles
├── public/               # Статические файлы
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
└── tailwind.config.js
```

## Деплой на Cloudflare Pages

### Через GitHub (Рекомендуется)

1. Залить код в GitHub репозиторий
2. Перейти на https://dash.cloudflare.com/
3. Pages → Create a project → Connect to Git
4. Выбрать репозиторий
5. Build settings:
   - Build command: `npm run build`
   - Build output directory: `dist`
6. Environment variables:
   ```
   VITE_API_URL=https://your-backend.railway.app/api
   VITE_WS_URL=wss://your-backend.railway.app/ws
   ```
7. Save and Deploy

### Через CLI

```bash
# Установить Wrangler
npm install -g wrangler

# Авторизоваться
wrangler login

# Деплой
npm run build
wrangler pages deploy dist --project-name=melancholia-panel
```

## Доступные роли

### Owner
- Полный доступ ко всем серверам
- Управление серверами
- Глобальные настройки

### Admin
- Управление своим сервером
- Одобрение контрактов и отчетов
- Управление пользователями
- Настройки модулей

### User
- Просмотр своих контрактов
- Подача отчетов
- Просмотр своей статистики
- Просмотр профиля

## Авторизация

### Owner
Вход через email и пароль (настроен в backend .env)

### Discord Users
Вход через Discord OAuth2:
1. Клик "Войти через Discord"
2. Авторизация на Discord
3. Редирект обратно на сайт
4. Автоматическое определение роли по правам на сервере

## WebSocket

Real-time обновления через WebSocket:
- Новые контракты
- Изменения статусов
- Обновления модулей
- Уведомления

## Компоненты

Основные компоненты уже созданы:
- `LoginPage` - страница входа
- `DiscordCallbackPage` - обработка Discord OAuth2
- `OwnerLayout` - layout для Owner
- `AdminLayout` - layout для Admin
- `UserLayout` - layout для User
- `OwnerDashboard` - дашборд для Owner

## TODO

- [ ] Admin Dashboard (контракты, отчеты, пользователи)
- [ ] User Dashboard (мои контракты, отчеты, профиль)
- [ ] Страницы управления контрактами
- [ ] Страницы отчетов
- [ ] Настройки модулей
- [ ] Графики и статистика
- [ ] Dark mode toggle
- [ ] Уведомления (toast)
- [ ] Загрузка файлов

## Стек

- React 18
- TypeScript
- Vite
- TailwindCSS
- React Router
- React Query
- Zustand
- Axios
- Lucide Icons
- date-fns
- recharts
