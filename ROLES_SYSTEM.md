# 🎭 Система ролей и доступа (4 уровня)

## 📊 Иерархия ролей

```
┌─────────────────────────────────────────┐
│          Owner (Владелец)               │  Вы
│  • Видит ВСЕ серверы                    │
│  • Глобальные настройки бота            │
│  • Управление любым сервером            │
│  • Назначение Admin/Recruiter           │
└─────────────────────────────────────────┘
                 │
        ┌────────┴────────┐
        ▼                 ▼
┌─────────────────┐  ┌──────────────────┐
│  Admin (Админ)  │  │ Recruiter        │
│  • Свой сервер  │  │ • Свой сервер    │
│  • Все настройки│  │ • Агитации       │
│  • Все контракты│  │  - маркетплейс   │
│  • Все заявки   │  │  - wn            │
│  • Назначение   │  │ • Заявки (чтение)│
│    Recruiter    │  └──────────────────┘
└─────────────────┘
        │
        ▼
┌─────────────────────────────────────────┐
│          User (Пользователь)            │
│  • Отправка своих контрактов            │
│  • Подача заявки в семью                │
│  • Просмотр своей статистики            │
└─────────────────────────────────────────┘
```

---

## 🔐 Таблица прав доступа

| Функция | Owner | Admin | Recruiter | User |
|---------|-------|-------|-----------|------|
| **Просмотр всех серверов** | ✅ | ❌ | ❌ | ❌ |
| **Глобальные настройки бота** | ✅ | ❌ | ❌ | ❌ |
| **Audit log всех серверов** | ✅ | ❌ | ❌ | ❌ |
| **Настройки своего сервера** | ✅ | ✅ | ❌ | ❌ |
| **Настройка Google Sheets** | ✅ | ✅ | ❌ | ❌ |
| **Настройка каналов/ролей** | ✅ | ✅ | ❌ | ❌ |
| **Включение/выключение модулей** | ✅ | ✅ | ❌ | ❌ |
| **Назначение Recruiter** | ✅ | ✅ | ❌ | ❌ |
| **Назначение Admin** | ✅ | ❌ | ❌ | ❌ |
| **Просмотр всех контрактов** | ✅ | ✅ | ❌ | ❌ |
| **Подтверждение/отклонение контрактов** | ✅ | ✅ | ❌ | ❌ |
| **Отправка агитаций (маркетплейс)** | ✅ | ✅ | ✅ | ❌ |
| **Отправка агитаций (WN)** | ✅ | ✅ | ✅ | ❌ |
| **Просмотр заявок** | ✅ | ✅ | ✅ (readonly) | ❌ |
| **Подтверждение/отклонение заявок** | ✅ | ✅ | ❌ | ❌ |
| **Отправка своих контрактов** | ✅ | ✅ | ✅ | ✅ |
| **Подача заявки в семью** | ✅ | ✅ | ✅ | ✅ |
| **Просмотр своей статистики** | ✅ | ✅ | ✅ | ✅ |

---

## 💾 Структура БД

### Таблица `permissions`

```sql
CREATE TABLE permissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id TEXT NOT NULL,
    discord_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('owner', 'admin', 'recruiter', 'user')),
    granted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    granted_by TEXT,  -- Discord ID того кто выдал роль
    FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE,
    UNIQUE(guild_id, discord_id)
);
```

**Пример данных:**
```
guild_id        | discord_id     | role      | granted_by
----------------|----------------|-----------|------------
123456789       | YOUR_ID        | owner     | NULL
123456789       | 111111111      | admin     | YOUR_ID
123456789       | 222222222      | recruiter | 111111111
123456789       | 333333333      | user      | NULL
```

---

## 🎯 Как определяется роль

### 1. **Owner (Владелец бота)**
```javascript
// Проверка через .env или БД
const OWNER_DISCORD_ID = "YOUR_DISCORD_ID";

function isOwner(discordId) {
  return discordId === OWNER_DISCORD_ID;
}
```

### 2. **Admin/Recruiter/User**
```javascript
async function getUserRole(discordId, guildId) {
  // Если Owner - всегда owner
  if (isOwner(discordId)) return 'owner';
  
  // Проверить в БД
  const row = await db.fetch_one(
    "SELECT role FROM permissions WHERE guild_id = ? AND discord_id = ?",
    [guildId, discordId]
  );
  
  if (row) return row.role;
  
  // По умолчанию - user
  return 'user';
}
```

---

## 📝 API Endpoints для управления ролями

### `GET /api/guilds/{guild_id}/permissions`
Список всех пользователей с ролями на сервере.

**Доступ:** Owner, Admin

**Response:**
```json
{
  "permissions": [
    {
      "discord_id": "111111111",
      "username": "AdminUser#1234",
      "avatar": "...",
      "role": "admin",
      "granted_at": "2026-09-17T00:00:00Z",
      "granted_by": "YOUR_ID"
    },
    {
      "discord_id": "222222222",
      "username": "RecruiterUser#5678",
      "avatar": "...",
      "role": "recruiter",
      "granted_at": "2026-09-17T01:00:00Z",
      "granted_by": "111111111"
    }
  ]
}
```

### `POST /api/guilds/{guild_id}/permissions`
Назначить роль пользователю.

**Доступ:** 
- Owner: может назначить любую роль
- Admin: может назначить только recruiter

**Request:**
```json
{
  "discord_id": "222222222",
  "role": "recruiter"
}
```

**Response:**
```json
{
  "ok": true,
  "message": "Role assigned"
}
```

### `DELETE /api/guilds/{guild_id}/permissions/{discord_id}`
Удалить роль пользователя.

**Доступ:** Owner, Admin (только если сам назначал)

---

## 🔨 Middleware для проверки прав

### Backend (FastAPI)

```python
from fastapi import Depends, HTTPException

async def require_role(
    min_role: str,  # 'owner', 'admin', 'recruiter', 'user'
    guild_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Проверить что у пользователя есть минимальная роль"""
    
    role_hierarchy = {
        'owner': 4,
        'admin': 3,
        'recruiter': 2,
        'user': 1
    }
    
    user_role = await get_user_role(current_user['discord_id'], guild_id)
    
    if role_hierarchy.get(user_role, 0) < role_hierarchy.get(min_role, 0):
        raise HTTPException(
            status_code=403,
            detail=f"Требуется роль {min_role} или выше"
        )
    
    return user_role
```

**Использование:**
```python
@router.post("/api/guilds/{guild_id}/settings")
async def update_settings(
    guild_id: str,
    settings: SettingsModel,
    role: str = Depends(lambda: require_role('admin', guild_id))
):
    # Только admin и owner могут изменять настройки
    ...
```

---

## 🎨 UI компоненты

### 1. **Страница управления ролями** `/guilds/{guild_id}/permissions`

```
┌────────────────────────────────────────────────┐
│  👥 Управление ролями - Server Name            │
├────────────────────────────────────────────────┤
│  [+ Добавить пользователя]                     │
│                                                │
│  Администраторы (1):                           │
│  ┌──────────────────────────────────────────┐  │
│  │ 👤 AdminUser#1234                        │  │
│  │    Discord ID: 111111111                 │  │
│  │    Назначен: 2026-09-17                  │  │
│  │    [Удалить роль]                        │  │
│  └──────────────────────────────────────────┘  │
│                                                │
│  Рекрутеры (2):                                │
│  ┌──────────────────────────────────────────┐  │
│  │ 👤 Recruiter1#5678                       │  │
│  │    Discord ID: 222222222                 │  │
│  │    Назначил: AdminUser#1234              │  │
│  │    [Удалить роль]                        │  │
│  └──────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────┐  │
│  │ 👤 Recruiter2#9999                       │  │
│  │    [Удалить роль]                        │  │
│  └──────────────────────────────────────────┘  │
└────────────────────────────────────────────────┘
```

### 2. **Модальное окно добавления роли**

```
┌────────────────────────────────────────────────┐
│  Добавить пользователя                    [✕]  │
├────────────────────────────────────────────────┤
│  Discord ID:                                   │
│  [__________________________________________]  │
│                                                │
│  Роль:                                         │
│  ( ) Admin      - Полный доступ к серверу      │
│  (•) Recruiter  - Агитации и заявки            │
│  ( ) User       - Базовый доступ               │
│                                                │
│  💡 Подсказка:                                 │
│  Recruiter может отправлять только             │
│  агитации-маркетплейс и агитации-wn            │
│                                                │
│  [Отмена]  [Добавить]                          │
└────────────────────────────────────────────────┘
```

---

## 🚀 Функционал для Recruiter

### Доступные типы контрактов:

**Только 2 типа:**
1. **агитации-маркетплейс** - вставка ссылок на Discord маркетплейс
2. **агитации-wn** - скриншоты агитации в WhatsApp News

### Форма отправки для Recruiter:

```
┌────────────────────────────────────────────────┐
│  📝 Отправить контракт агитации                │
├────────────────────────────────────────────────┤
│  Тип контракта:                                │
│  ( ) Агитации - Маркетплейс                    │
│  (•) Агитации - WhatsApp News                  │
│                                                │
│  Сумма за контракт: [_______] $                │
│  💡 Укажите стоимость этого контракта          │
│                                                │
│  [Категория: Зеленка(чат) ▼]                   │
│                                                │
│  Скриншоты:                                    │
│  [📤 Загрузить] или Ctrl+V                     │
│  • screenshot1.png [❌]                         │
│  • screenshot2.png [❌]                         │
│                                                │
│  [Отправить]                                   │
└────────────────────────────────────────────────┘
```

**Важно:** Recruiter указывает сумму за контракт при отправке, в отличие от обычных контрактов где сумма рассчитывается автоматически.

---

## 🔄 Процесс авторизации с ролями

```
1. User нажимает "Войти через Discord"
   ↓
2. Discord OAuth2 возвращает discord_id
   ↓
3. Backend проверяет роль:
   - Если Owner (из .env) → role = 'owner'
   - Иначе → SELECT role FROM permissions WHERE discord_id = ?
   ↓
4. Backend создает JWT с полями:
   {
     discordId: "123...",
     username: "User#1234",
     role: "recruiter",  // или owner/admin/user
     guilds: ["guild_id1", "guild_id2"],  // серверы где есть доступ
     exp: ...
   }
   ↓
5. Frontend определяет что показывать:
   - owner → все серверы + owner panel
   - admin → только свой сервер + admin panel
   - recruiter → форма агитаций + список заявок (readonly)
   - user → форма контрактов + форма заявки
```

---

## 📋 Миграция для добавления роли recruiter

```sql
-- Добавить роль recruiter в существующие constraints
-- (Если используется старая схема - нужно пересоздать таблицу)

-- 1. Создать новую таблицу с обновленным constraint
CREATE TABLE permissions_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id TEXT NOT NULL,
    discord_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('owner', 'admin', 'recruiter', 'user')),
    granted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    granted_by TEXT,
    FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE,
    UNIQUE(guild_id, discord_id)
);

-- 2. Скопировать данные из старой
INSERT INTO permissions_new 
SELECT * FROM permissions;

-- 3. Удалить старую
DROP TABLE permissions;

-- 4. Переименовать новую
ALTER TABLE permissions_new RENAME TO permissions;
```

---

## ✅ Чек-лист реализации

- [ ] Обновить таблицу `permissions` (добавить recruiter)
- [ ] Создать middleware для проверки ролей
- [ ] API endpoints для управления ролями
- [ ] Обновить форму контрактов (показывать только доступные типы)
- [ ] Добавить поле "сумма" для агитаций от recruiter
- [ ] UI для назначения ролей (Admin panel)
- [ ] Обновить Discord OAuth2 (включать роль в JWT)
- [ ] Тестирование прав доступа

---

## 🎯 Следующие шаги

1. **Обновить backend** - добавить endpoints и middleware для ролей
2. **Обновить frontend** - условный рендеринг по ролям
3. **Создать UI** - страница управления ролями для Admin
4. **Обновить форму контрактов** - поддержка recruiter с суммой
5. **Тестирование** - проверить все 4 уровня доступа

Начинаем с backend?
