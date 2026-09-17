# Настройка Google Sheets для мультисервера

## 📋 Обзор

Начиная с версии 2.0, каждый Discord сервер может использовать свою собственную Google Sheets таблицу для импорта контрактов. Это позволяет разным серверам работать независимо друг от друга.

## 🔧 Настройки в базе данных

Для каждого сервера в таблице `guild_settings` хранятся следующие настройки:

| Ключ | Описание | Значение по умолчанию |
|------|----------|----------------------|
| `sheet_id` | ID Google таблицы | Из `config.SHEET_ID` |
| `credentials_path` | Путь к credentials.json | `credentials.json` |
| `sheets_enabled` | Включить импорт из Sheets | `true` / `false` |

## 📝 Миграция существующих серверов

Если у вас уже есть работающий бот со старой схемой БД:

```bash
# 1. Миграция на multi-guild схему (если еще не сделано)
python migrate_to_v2.py

# 2. Добавление настроек Google Sheets
python migrate_add_sheets_settings.py
```

Миграция автоматически:
- Добавит настройки для всех активных серверов
- Использует текущий `SHEET_ID` из `.env` как значение по умолчанию
- Включит импорт для серверов, у которых настроен `SHEET_ID`

## 🌐 Настройка через веб-панель (в разработке)

В будущих версиях администраторы смогут настраивать Google Sheets через веб-интерфейс:

1. Войти в панель управления
2. Выбрать свой сервер
3. Перейти в раздел "Интеграции → Google Sheets"
4. Указать `SHEET_ID` и загрузить `credentials.json`

## 🤖 Настройка через Discord команды

### Команда `/setup_sheets` (планируется в задаче #4)

```
/setup_sheets
  sheet_id: <ID вашей Google таблицы>
  credentials: <прикрепить credentials.json>
```

Пример:
```
/setup_sheets sheet_id:1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms
```

### Проверка текущих настроек

```
/settings google_sheets
```

Покажет:
- ✅ sheet_id: `1BxiMVs...`
- ✅ credentials_path: `credentials/123456789.json`
- ✅ sheets_enabled: `true`
- 📊 Последний импорт: 5 минут назад (10 контрактов)

## 📂 Организация credentials файлов

### Структура директории

```
BOT Melancholia Now/
├── credentials/
│   ├── 123456789.json          # Сервер 1
│   ├── 987654321.json          # Сервер 2
│   └── default.json            # Глобальный по умолчанию
├── credentials.json            # Старый формат (deprecated)
└── ...
```

### Изоляция credentials (задача #6)

Каждый сервер должен иметь свой credentials файл:
- Защита от конфликтов между серверами
- Разные Google аккаунты для разных серверов
- Безопасность: один сервер не может получить доступ к данным другого

## 🔐 Получение Google Sheets credentials

### 1. Создать проект в Google Cloud Console

1. Перейти на https://console.cloud.google.com/
2. Создать новый проект или выбрать существующий
3. Перейти в "APIs & Services" → "Enable APIs and Services"
4. Найти и включить "Google Sheets API"

### 2. Создать Service Account

1. Перейти в "APIs & Services" → "Credentials"
2. Нажать "Create Credentials" → "Service Account"
3. Заполнить имя сервисного аккаунта
4. Нажать "Create and Continue"
5. Пропустить роли (можно оставить пустым)
6. Нажать "Done"

### 3. Создать ключ JSON

1. Открыть созданный Service Account
2. Перейти во вкладку "Keys"
3. Нажать "Add Key" → "Create new key"
4. Выбрать тип "JSON"
5. Скачать файл (будет `your-project-xxxxx.json`)

### 4. Предоставить доступ к таблице

1. Открыть скачанный JSON файл
2. Найти поле `client_email` (например: `bot@project.iam.gserviceaccount.com`)
3. Открыть вашу Google Sheets таблицу
4. Нажать "Поделиться" (Share)
5. Вставить `client_email` и дать права "Редактор" (Editor)
6. Снять галочку "Уведомить людей" (Notify people)
7. Нажать "Поделиться"

### 5. Получить Sheet ID

Sheet ID находится в URL таблицы:
```
https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit
                                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                                    Это ваш SHEET_ID
```

## 🔄 Как работает импорт

1. Каждые 60 секунд (`POLLING_INTERVAL`) бот проверяет все серверы
2. Для каждого сервера:
   - Проверяет включен ли модуль `contracts`
   - Проверяет `sheets_enabled = true`
   - Получает `sheet_id` и `credentials_path` из БД
   - Если настройки не указаны, использует значения из `config.py`
3. Импортирует строки со статусом `NEW` или `POSTED`
4. Добавляет контракты с правильным `guild_id`

## 🐛 Troubleshooting

### Ошибка: "guild_id не указан в контракте"

**Проблема:** Старая версия `sheets_sync.py` не передавала `guild_id`

**Решение:** Обновить код до версии с исправлением (задача #1)

### Ошибка: "SHEET_ID не настроен"

**Проблема:** Настройка `sheet_id` пустая или отсутствует

**Решение:**
```bash
# Через SQL
sqlite3 bot.db "INSERT OR REPLACE INTO guild_settings (guild_id, setting_key, setting_value) VALUES ('YOUR_GUILD_ID', 'sheet_id', 'YOUR_SHEET_ID');"

# Или запустить миграцию
python migrate_add_sheets_settings.py
```

### Ошибка: "Ошибка подключения к Google Sheets"

**Возможные причины:**
1. Файл `credentials.json` не найден
2. Service Account не имеет доступа к таблице
3. Google Sheets API не включен в проекте
4. Неверный `sheet_id`

**Решение:**
1. Проверить путь к credentials файлу
2. Предоставить доступ к таблице (см. шаг 4 выше)
3. Включить API в Google Cloud Console
4. Проверить правильность `sheet_id`

### Импорт не работает для конкретного сервера

**Проверка:**
```bash
# Проверить настройки сервера
sqlite3 bot.db "SELECT * FROM guild_settings WHERE guild_id='YOUR_GUILD_ID';"

# Проверить включен ли модуль
sqlite3 bot.db "SELECT * FROM guild_modules WHERE guild_id='YOUR_GUILD_ID' AND module_name='contracts';"
```

**Включить модуль:**
```bash
sqlite3 bot.db "INSERT OR REPLACE INTO guild_modules (guild_id, module_name, is_enabled) VALUES ('YOUR_GUILD_ID', 'contracts', 1);"
```

## 📊 Формат таблицы

Таблица должна иметь лист с именем `Contracts` (настраивается в `config.CONTRACTS_SHEET`) со следующими колонками:

| Колонка | Обязательно | Описание |
|---------|-------------|----------|
| status | ✅ | NEW, POSTED (импортируются), PROCESSED (игнорируется) |
| ts | ✅ | Timestamp контракта |
| discord_id | ✅ | Discord ID пользователя |
| contract_type | ✅ | Тип контракта |
| msk_date | | Дата в формате DD-MM-YYYY |
| price | | Цена контракта |
| details | | Детали контракта |
| ... | | Другие поля (см. `sheets_sync.py`) |

## 🎯 Следующие шаги

- [ ] **Задача #3**: Перенести каналы/роли в `guild_settings`
- [ ] **Задача #4**: Добавить команду `/setup_sheets`
- [ ] **Задача #5**: Добавить команду `/setup_channels`
- [ ] **Задача #6**: Реализовать изоляцию credentials файлов
- [ ] **Задача #7**: Обновить документацию
- [ ] **Задача #8**: Тестирование на нескольких серверах

## 💡 Best Practices

1. **Один Google аккаунт на сервер**: Не используйте один credentials файл для всех серверов
2. **Регулярные бэкапы**: Делайте копии таблиц перед экспериментами
3. **Мониторинг логов**: Следите за ошибками импорта в консоли бота
4. **Тестируйте на dev-сервере**: Сначала проверьте на тестовом сервере
5. **Документируйте изменения**: Описывайте нестандартные настройки

## 📞 Поддержка

При возникновении проблем:
1. Проверьте раздел Troubleshooting выше
2. Посмотрите логи бота (строки с `[Guild XXXXX]`)
3. Проверьте настройки в БД
4. Откройте issue в репозитории с описанием проблемы и логами
