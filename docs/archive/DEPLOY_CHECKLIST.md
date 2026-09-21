# 📋 Checklist - Быстрая проверка перед деплоем

Пройдись по этому чеклисту перед деплоем:

## ✅ Подготовка файлов

- [x] `backend/Procfile` создан
- [x] `backend/railway.json` создан
- [x] `frontend/.env.production` создан
- [ ] `frontend/.env.production` обновлен с реальными URLs (после деплоя backend)

## ✅ Discord Developer Portal

- [ ] Приложение создано на https://discord.com/developers/applications
- [ ] Client ID скопирован
- [ ] Client Secret скопирован
- [ ] Bot Token скопирован
- [ ] OAuth2 Redirect URI добавлен (обновить после деплоя frontend)

## ✅ Railway (Backend)

- [ ] Аккаунт создан на https://railway.app
- [ ] Проект создан
- [ ] Backend задеплоен
- [ ] Environment variables настроены (11 переменных)
- [ ] Railway URL скопирован
- [ ] Backend API работает (открывается /docs)

## ✅ Cloudflare (Frontend)

- [ ] Аккаунт создан на https://dash.cloudflare.com
- [ ] Wrangler установлен (`npm install -g wrangler`)
- [ ] `frontend/.env.production` обновлен с Railway URL
- [ ] `npm install` выполнен в frontend
- [ ] `npm run build` работает без ошибок
- [ ] Frontend задеплоен
- [ ] Cloudflare URL скопирован
- [ ] Frontend загружается в браузере

## ✅ Финальная настройка

- [ ] Discord Redirect URI обновлен с Cloudflare URL
- [ ] Railway DISCORD_REDIRECT_URI обновлен с Cloudflare URL
- [ ] Railway ALLOWED_ORIGINS обновлен с Cloudflare URL
- [ ] Backend перезапущен после обновления переменных

## ✅ Тестирование

- [ ] Owner вход работает
- [ ] Discord OAuth2 работает
- [ ] WebSocket подключается (нет ошибок в консоли)
- [ ] Owner Dashboard показывает данные

## 🎯 Если что-то не работает

Открой `DEPLOY_NOW.md` секция **Troubleshooting** или `CLOUDFLARE_DEPLOYMENT.md`.

---

**Статус:** ⏳ Не задеплоено | ✅ Задеплоено успешно
**Дата последней проверки:** _________________
