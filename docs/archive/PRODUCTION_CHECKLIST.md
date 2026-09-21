# Checklist для Production деплоя

## Backend

- [ ] Backend API развернут и доступен (Railway/VPS/другое)
- [ ] База данных настроена и миграции выполнены
  ```bash
  python migrate_add_recruiter_role.py
  ```
- [ ] Discord Bot токен настроен в `.env`
- [ ] Discord OAuth настроен:
  - Client ID и Secret в `.env`
  - Redirect URI добавлен в Discord Developer Portal
- [ ] Google Sheets credentials загружены для каждого сервера
- [ ] CORS настроен для frontend URL
  ```python
  ALLOWED_ORIGINS="https://your-frontend.pages.dev"
  ```
- [ ] Environment variables установлены на сервере
- [ ] Бот запущен и работает
  ```bash
  python main.py
  ```

## Frontend

- [ ] Код в Git репозитории (GitHub/GitLab)
- [ ] `.env.example` создан с правильными переменными
- [ ] `public/_redirects` и `public/_headers` на месте
- [ ] Build проходит без ошибок локально
  ```bash
  cd frontend && npm run build
  ```
- [ ] Cloudflare Pages проект создан
- [ ] Environment variables установлены:
  - `VITE_API_URL` = URL вашего backend
- [ ] Деплой успешно завершен
- [ ] Кастомный домен настроен (если используется)

## Discord Configuration

- [ ] Bot добавлен на тестовый сервер
- [ ] OAuth2 Redirect URIs обновлены:
  - [ ] `https://your-frontend.pages.dev/auth/callback`
  - [ ] `https://your-domain.com/auth/callback` (если есть)
- [ ] Bot Permissions настроены:
  - Send Messages
  - Embed Links
  - Attach Files
  - Read Message History
  - Manage Messages
  - Use Slash Commands

## Database

- [ ] Таблица `permissions` обновлена с ролью 'recruiter'
- [ ] Тестовые данные очищены (если нужно)
- [ ] Бэкап создан перед production запуском
- [ ] Owner аккаунт создан в `owner_account` таблице

## Google Sheets

- [ ] Service Account создан в Google Cloud Console
- [ ] Credentials.json скачан
- [ ] Credentials загружен для каждого сервера через:
  - Discord команду `/setup_sheets` или
  - Веб-панель Admin → Google Sheets Settings
- [ ] Таблица Google Sheets создана с нужными листами
- [ ] Service Account email добавлен в права доступа таблицы
- [ ] Импорт контрактов работает

## Testing

- [ ] Авторизация через Discord работает
- [ ] Owner может видеть все серверы
- [ ] Admin может управлять своим сервером
- [ ] Recruiter может отправлять только агитации
- [ ] User может отправлять контракты и заявки
- [ ] Google Sheets импорт работает
- [ ] Формы отправки контрактов работают
- [ ] Форма заявки в семью работает
- [ ] Роутинг работает на всех страницах
- [ ] Mobile версия выглядит нормально

## Security

- [ ] Security headers настроены (`_headers` файл)
- [ ] CORS строго ограничен на backend
- [ ] Environment variables не коммитятся в Git
- [ ] Credentials файлы в `.gitignore`
- [ ] JWT токены используют секретный ключ
- [ ] Discord Bot Token не светится в коде

## Monitoring

- [ ] Cloudflare Pages Analytics включена
- [ ] Backend логи настроены
- [ ] Discord Bot логи мониторятся
- [ ] Ошибки отслеживаются

## Documentation

- [ ] README.md обновлен с production URL
- [ ] Инструкции для администраторов серверов написаны
- [ ] FAQ обновлен
- [ ] Контакты для поддержки указаны

## Post-Launch

- [ ] Уведомить пользователей о запуске панели
- [ ] Обучить администраторов работе с панелью
- [ ] Создать тестовые контракты/заявки
- [ ] Мониторить ошибки первые 24 часа

---

## Быстрая проверка

```bash
# Backend health
curl https://your-backend-api.com/health

# Frontend доступен
curl -I https://your-frontend.pages.dev

# API работает
curl https://your-backend-api.com/api/guilds/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

Дата последней проверки: __________
Проверил: __________
