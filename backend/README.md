# Backend API

FastAPI backend для управления Discord ботом Melancholia.

## Установка

1. Создать виртуальное окружение:
```bash
python -m venv venv
.\venv\Scripts\Activate  # Windows
source venv/bin/activate  # Linux/Mac
```

2. Установить зависимости:
```bash
pip install -r requirements.txt
```

3. Создать `.env` файл на основе `.env.example`:
```bash
cp .env.example .env
```

4. Настроить `.env`:
   - Изменить `SECRET_KEY` (сгенерировать: `openssl rand -hex 32`)
   - Добавить Discord Client ID и Secret (из Discord Developer Portal)
   - Настроить Owner email/password
   - Добавить URL Cloudflare Pages в ALLOWED_ORIGINS

## Discord OAuth2 настройка

1. Перейти на https://discord.com/developers/applications
2. Выбрать приложение бота
3. Во вкладке "OAuth2" добавить Redirect URI:
   - Development: `http://localhost:3000/auth/callback`
   - Production: `https://your-app.pages.dev/auth/callback`

## Запуск

Development:
```bash
python run.py
```

Production (с gunicorn):
```bash
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## API Documentation

После запуска сервера:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Endpoints

### Authentication
- `POST /api/auth/owner/login` - Owner логин
- `POST /api/auth/discord/login` - Получить Discord OAuth2 URL
- `POST /api/auth/discord/callback` - Discord OAuth2 callback
- `POST /api/auth/refresh` - Обновить токен
- `GET /api/auth/me` - Текущий пользователь

### Guilds
- `GET /api/guilds` - Список серверов (Owner)
- `GET /api/guilds/{guild_id}` - Детали сервера
- `GET /api/guilds/{guild_id}/settings` - Настройки сервера
- `PUT /api/guilds/{guild_id}/settings` - Обновить настройки
- `GET /api/guilds/{guild_id}/modules` - Модули сервера
- `PUT /api/guilds/{guild_id}/modules/{module_name}` - Включить/выключить модуль

### Contracts
- `GET /api/guilds/{guild_id}/contracts` - Список контрактов
- `GET /api/guilds/{guild_id}/contracts/{id}` - Детали контракта
- `PUT /api/guilds/{guild_id}/contracts/{id}` - Обновить контракт
- `DELETE /api/guilds/{guild_id}/contracts/{id}` - Удалить контракт
- `GET /api/guilds/{guild_id}/contracts/stats` - Статистика контрактов

### Users
- `GET /api/guilds/{guild_id}/users/me` - Мой профиль
- `GET /api/guilds/{guild_id}/users/{discord_id}` - Профиль пользователя
- `GET /api/guilds/{guild_id}/users/{discord_id}/stats` - Статистика пользователя
- `GET /api/guilds/{guild_id}/users` - Список пользователей

### Reports
- `GET /api/guilds/{guild_id}/reports/bonus` - Отчеты на бонусы
- `GET /api/guilds/{guild_id}/reports/bonus/{id}` - Детали отчета
- `PUT /api/guilds/{guild_id}/reports/bonus/{id}/approve` - Одобрить/отклонить
- `GET /api/guilds/{guild_id}/reports/promotion` - Отчеты на повышение

### WebSocket
- `WS /ws/{guild_id}` - Real-time обновления

## WebSocket Events

Клиент получает события:
```json
{
  "type": "contract_update",
  "contract_id": 123,
  "status": "APPROVED"
}

{
  "type": "module_update",
  "module": "bonus_reports",
  "is_enabled": true
}

{
  "type": "bonus_report_update",
  "report_id": 456,
  "status": "APPROVED"
}
```

## Деплой на Railway

1. Создать проект на Railway.app
2. Подключить GitHub репозиторий
3. Добавить PostgreSQL addon (опционально, можно оставить SQLite)
4. Настроить переменные окружения (Environment Variables)
5. Railway автоматически обнаружит Dockerfile или можно использовать Nixpacks

### Railway Environment Variables
```
DATABASE_URL=sqlite+aiosqlite:///../../bot.db
SECRET_KEY=<generated-secret-key>
DISCORD_CLIENT_ID=<your-client-id>
DISCORD_CLIENT_SECRET=<your-client-secret>
DISCORD_REDIRECT_URI=https://your-app.pages.dev/auth/callback
DISCORD_BOT_TOKEN=<your-bot-token>
OWNER_EMAIL=admin@example.com
OWNER_PASSWORD=<strong-password>
ALLOWED_ORIGINS=https://your-app.pages.dev
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=False
```

## Структура

```
backend/
├── app/
│   ├── api/
│   │   ├── routes/
│   │   │   ├── auth.py       # Авторизация
│   │   │   ├── guilds.py     # Серверы
│   │   │   ├── contracts.py  # Контракты
│   │   │   ├── users.py      # Пользователи
│   │   │   └── reports.py    # Отчеты
│   │   └── dependencies.py   # Зависимости
│   ├── core/
│   │   ├── config.py         # Конфигурация
│   │   ├── database.py       # База данных
│   │   └── security.py       # Безопасность (JWT, пароли)
│   ├── models/               # SQLAlchemy модели (если нужно)
│   ├── schemas/              # Pydantic схемы
│   │   └── __init__.py
│   └── main.py               # FastAPI приложение
├── .env.example
├── requirements.txt
├── run.py
└── README.md
```

## Тестирование

```bash
# Установить pytest
pip install pytest pytest-asyncio httpx

# Запустить тесты
pytest
```

## Troubleshooting

### Проблемы с CORS
Убедитесь что URL фронтенда добавлен в `ALLOWED_ORIGINS` в `.env`.

### Проблемы с Discord OAuth2
- Проверьте что Redirect URI совпадает в Discord Developer Portal и `.env`
- Проверьте что Client ID и Secret верные
- Убедитесь что у приложения есть scope `identify` и `guilds`

### Проблемы с базой данных
- Для SQLite убедитесь что путь к `bot.db` правильный
- Для PostgreSQL проверьте `DATABASE_URL` формат: `postgresql+asyncpg://user:pass@host/db`
