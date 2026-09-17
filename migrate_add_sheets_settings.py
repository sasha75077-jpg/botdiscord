"""
Миграция: Добавление настроек Google Sheets в guild_settings

Для каждого сервера добавляет возможность настроить:
- sheet_id: ID Google таблицы
- credentials_path: путь к credentials.json файлу
- sheets_enabled: включить/выключить импорт из Google Sheets
"""
import asyncio
import aiosqlite
from config import DB_PATH, SHEET_ID, SHEET_CREDENTIALS

async def migrate():
    print("🔄 Миграция: Добавление настроек Google Sheets в guild_settings")

    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row

    try:
        # Проверить существует ли таблица guilds
        async with db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='guilds'"
        ) as cursor:
            guilds_exists = await cursor.fetchone() is not None

        if not guilds_exists:
            print("❌ Таблица guilds не найдена. Сначала выполните миграцию на multi-guild.")
            return

        # Получить все активные серверы
        async with db.execute("SELECT guild_id, guild_name FROM guilds WHERE is_active = 1") as cursor:
            guilds = await cursor.fetchall()

        if not guilds:
            print("⚠️  Нет активных серверов в БД")
            return

        print(f"📊 Найдено серверов: {len(guilds)}")

        # Для каждого сервера добавить настройки Google Sheets
        for guild in guilds:
            guild_id = guild["guild_id"]
            guild_name = guild["guild_name"]

            print(f"\n🔧 Настройка сервера: {guild_name} ({guild_id})")

            # Проверить есть ли уже настройки
            async with db.execute(
                "SELECT setting_key FROM guild_settings WHERE guild_id = ? AND setting_key IN ('sheet_id', 'credentials_path', 'sheets_enabled')",
                (guild_id,)
            ) as cursor:
                existing = await cursor.fetchall()
                existing_keys = {row["setting_key"] for row in existing}

            # Добавить sheet_id если его нет
            if "sheet_id" not in existing_keys:
                # Использовать глобальный SHEET_ID как значение по умолчанию
                default_sheet_id = SHEET_ID or ""
                await db.execute(
                    """
                    INSERT INTO guild_settings (guild_id, setting_key, setting_value, updated_at)
                    VALUES (?, 'sheet_id', ?, CURRENT_TIMESTAMP)
                    """,
                    (guild_id, default_sheet_id)
                )
                print(f"  ✅ Добавлен sheet_id: {default_sheet_id or '(пусто)'}")
            else:
                print(f"  ⏭️  sheet_id уже существует")

            # Добавить credentials_path если его нет
            if "credentials_path" not in existing_keys:
                # Использовать глобальный путь как значение по умолчанию
                default_creds = SHEET_CREDENTIALS or "credentials.json"
                await db.execute(
                    """
                    INSERT INTO guild_settings (guild_id, setting_key, setting_value, updated_at)
                    VALUES (?, 'credentials_path', ?, CURRENT_TIMESTAMP)
                    """,
                    (guild_id, default_creds)
                )
                print(f"  ✅ Добавлен credentials_path: {default_creds}")
            else:
                print(f"  ⏭️  credentials_path уже существует")

            # Добавить sheets_enabled если его нет
            if "sheets_enabled" not in existing_keys:
                # По умолчанию включено, если SHEET_ID настроен
                default_enabled = "true" if SHEET_ID else "false"
                await db.execute(
                    """
                    INSERT INTO guild_settings (guild_id, setting_key, setting_value, updated_at)
                    VALUES (?, 'sheets_enabled', ?, CURRENT_TIMESTAMP)
                    """,
                    (guild_id, default_enabled)
                )
                print(f"  ✅ Добавлен sheets_enabled: {default_enabled}")
            else:
                print(f"  ⏭️  sheets_enabled уже существует")

        await db.commit()

        print("\n" + "="*60)
        print("✅ Миграция завершена успешно!")
        print("="*60)
        print("\n📝 Настройки Google Sheets для каждого сервера:")
        print("   - sheet_id: ID Google таблицы")
        print("   - credentials_path: путь к credentials.json")
        print("   - sheets_enabled: включить/выключить импорт")
        print("\n💡 Используйте команду /setup_sheets для настройки")

    except Exception as e:
        print(f"\n❌ Ошибка миграции: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(migrate())
