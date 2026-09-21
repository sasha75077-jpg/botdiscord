# 🚀 Деплой на Cloudflare Pages

Полная инструкция по развертыванию веб-панели Melancholia Bot на Cloudflare Pages.

---

## 📋 Предварительные требования

1. **Аккаунт Cloudflare** - зарегистрируйтесь на [cloudflare.com](https://www.cloudflare.com/)
2. **GitHub репозиторий** - код должен быть в Git репозитории
3. **Backend API** - развернутый backend (Railway, VPS, или другой хостинг)

---

## 🔧 Шаг 1: Подготовка проекта

### 1.1 Проверьте структуру проекта

```
frontend/
├── src/
├── public/
│   ├── _redirects      # ✅ Уже создан
│   └── _headers        # ✅ Уже создан
├── package.json
├── vite.config.ts
├── tsconfig.json
└── .env.example
```

### 1.2 Создайте .env.example

```bash
cd frontend
cat > .env.example << 'EOF'
# Backend API URL
VITE_API_URL=https://your-backend-api.com/api

# Discord OAuth (optional, if using direct auth)
VITE_DISCORD_CLIENT_ID=your_discord_client_id
EOF
```

### 1.3 Обновите package.json scripts (если нужно)

Убедитесь что есть build команда:

```json
{
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview"
  }
}
```

---

## 🚀 Шаг 2: Деплой на Cloudflare Pages

### 2.1 Через Cloudflare Dashboard (рекомендуется)

1. **Войдите в Cloudflare Dashboard**
   - Откройте [dash.cloudflare.com](https://dash.cloudflare.com/)
   - Перейдите в **Pages** → **Create a project**

2. **Подключите GitHub репозиторий**
   - Нажмите **Connect to Git**
   - Авторизуйте Cloudflare в GitHub
   - Выберите ваш репозиторий

3. **Настройте параметры сборки**

   ```
   Project name: melancholia-bot-panel
   Production branch: main
   Build command: npm run build
   Build output directory: dist
   Root directory: frontend
   ```

4. **Добавьте переменные окружения**
   
   В разделе **Environment variables**:
   
   ```
   VITE_API_URL = https://your-backend-api.com/api
   ```

5. **Нажмите Deploy**

### 2.2 Через CLI (альтернатива)

```bash
# Установите Wrangler CLI
npm install -g wrangler

# Логин в Cloudflare
wrangler login

# Деплой из директории frontend
cd frontend
npm run build
wrangler pages publish dist --project-name=melancholia-bot-panel
```

---

## 🔗 Шаг 3: Настройка Backend CORS

После деплоя frontend будет доступен по адресу типа:
```
https://melancholia-bot-panel.pages.dev
```

### 3.1 Обновите CORS в backend

Откройте `backend/app/core/config.py`:

```python
class Settings(BaseSettings):
    # ...
    
    ALLOWED_ORIGINS: str = Field(
        default="http://localhost:5173,https://melancholia-bot-panel.pages.dev",
        env="ALLOWED_ORIGINS"
    )
    
    @property
    def origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]
```

Или через переменную окружения на сервере:

```bash
export ALLOWED_ORIGINS="http://localhost:5173,https://melancholia-bot-panel.pages.dev"
```

---

## 🔐 Шаг 4: Настройка Discord OAuth

### 4.1 Обновите Redirect URI в Discord Developer Portal

1. Откройте [discord.com/developers/applications](https://discord.com/developers/applications)
2. Выберите ваше приложение
3. Перейдите в **OAuth2** → **General**
4. Добавьте Redirect URI:

   ```
   https://melancholia-bot-panel.pages.dev/auth/callback
   ```

5. Сохраните изменения

### 4.2 Обновите backend Discord OAuth настройки

В `backend/.env`:

```bash
DISCORD_REDIRECT_URI=https://melancholia-bot-panel.pages.dev/auth/callback
```

---

## 📦 Шаг 5: Проверка деплоя

### 5.1 Откройте сайт

Перейдите на:
```
https://melancholia-bot-panel.pages.dev
```

### 5.2 Проверьте функционал

- ✅ Страница логина загружается
- ✅ Discord OAuth работает
- ✅ API запросы проходят (проверьте Network в DevTools)
- ✅ Роутинг работает (перейдите на разные страницы)

---

## 🔄 Шаг 6: Настройка автоматического деплоя

Cloudflare Pages автоматически деплоит при каждом push в `main` ветку.

### Workflow:

1. **Разработка**
   ```bash
   git checkout -b feature/my-feature
   # делаете изменения
   git commit -am "Add new feature"
   git push origin feature/my-feature
   ```

2. **Pull Request**
   - Создайте PR в GitHub
   - Cloudflare создаст **Preview deployment** с уникальным URL
   - Протестируйте изменения

3. **Production**
   ```bash
   git checkout main
   git merge feature/my-feature
   git push origin main
   ```
   - Cloudflare автоматически деплоит в **production**

---

## 🌐 Шаг 7: Настройка кастомного домена (опционально)

### 7.1 Добавьте домен в Cloudflare Pages

1. В Cloudflare Pages → Ваш проект → **Custom domains**
2. Нажмите **Set up a custom domain**
3. Введите домен: `panel.yourdomain.com`

### 7.2 Добавьте DNS записи

Cloudflare автоматически предложит добавить CNAME запись:

```
CNAME panel.yourdomain.com → melancholia-bot-panel.pages.dev
```

### 7.3 Обновите конфигурацию

После добавления домена обновите:

1. **Backend CORS**: добавьте `https://panel.yourdomain.com`
2. **Discord OAuth**: добавьте `https://panel.yourdomain.com/auth/callback`
3. **Frontend .env**: `VITE_API_URL` остается прежним

---

## 🔒 Безопасность

### Уже настроено в проекте:

- ✅ **Security headers** (`public/_headers`)
  - X-Frame-Options: DENY
  - X-Content-Type-Options: nosniff
  - X-XSS-Protection
  - Referrer-Policy
  - Permissions-Policy

- ✅ **SPA routing** (`public/_redirects`)
  - Все роуты перенаправляются на index.html
  - API проксируется на backend

### Дополнительные меры:

1. **HTTPs Only** - Cloudflare Pages автоматически использует HTTPS
2. **Environment Variables** - секреты хранятся в Cloudflare, не в коде
3. **CORS** - строгая настройка allowed origins на backend

---

## 🐛 Troubleshooting

### Проблема: API запросы не работают

**Решение:**
1. Проверьте `VITE_API_URL` в Environment Variables
2. Убедитесь что backend доступен
3. Проверьте CORS на backend
4. Откройте DevTools → Network и проверьте ошибки

### Проблема: Роутинг не работает (404 на /guilds/...)

**Решение:**
Убедитесь что файл `public/_redirects` существует с содержимым:
```
/*    /index.html   200
```

### Проблема: Discord OAuth не работает

**Решение:**
1. Проверьте Redirect URI в Discord Developer Portal
2. Убедитесь что `DISCORD_REDIRECT_URI` в backend `.env` совпадает
3. Проверьте что frontend правильно редиректит на `/auth/callback`

### Проблема: Build падает

**Решение:**
1. Проверьте логи сборки в Cloudflare Pages
2. Запустите `npm run build` локально
3. Исправьте TypeScript ошибки
4. Проверьте что все зависимости установлены

---

## 📊 Мониторинг

### Cloudflare Pages Analytics

Cloudflare автоматически собирает:
- Количество визитов
- География пользователей
- Производительность (Core Web Vitals)
- Ошибки

Доступно в: **Pages** → Ваш проект → **Analytics**

---

## 🚀 Production Checklist

Перед запуском в production:

- [ ] Backend API развернут и доступен
- [ ] CORS настроен правильно
- [ ] Discord OAuth Redirect URI добавлен
- [ ] Environment variables установлены в Cloudflare
- [ ] Кастомный домен настроен (если используется)
- [ ] Протестирована авторизация
- [ ] Протестированы все основные функции
- [ ] Security headers настроены
- [ ] Google Sheets credentials загружены на backend
- [ ] Database миграции выполнены

---

## 📚 Дополнительные ресурсы

- [Cloudflare Pages Docs](https://developers.cloudflare.com/pages/)
- [Vite Deployment Guide](https://vitejs.dev/guide/static-deploy.html)
- [Discord OAuth2 Docs](https://discord.com/developers/docs/topics/oauth2)

---

## 🎉 Готово!

После выполнения всех шагов ваша веб-панель будет доступна по адресу:

```
https://melancholia-bot-panel.pages.dev
```

Или на кастомном домене:

```
https://panel.yourdomain.com
```

---

## 🆘 Поддержка

Если возникли проблемы:
1. Проверьте логи в Cloudflare Pages
2. Проверьте логи backend
3. Откройте DevTools → Console для ошибок frontend
4. Создайте issue в GitHub репозитории
