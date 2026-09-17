"""
Миграция: Перенос настроек каналов и ролей в guild_settings

Переносит настройки из .env в guild_settings для каждого сервера:
- admin_contracts_channel_id: канал для админских контрактов
- pending_ping_role_id: роль для пинга при новых контрактах
- pending_counter_channel_id: канал для счетчика ожидающих контрактов
"""
import asyncio
import aiosqlite
import os
from dotenv import load_dotenv

load_dotenv()

DB_PATH = "bot.db"

async def migrate():
    print("🔄 Миграция: Перенос настроек каналов и ролей в guild_settings")

    # Получить значения из .env
    admin_channel = os.getenv("ADMIN_CONTRACTS_CHANNEL_ID", "")
    pending_role = os.getenv("PENDING_PING_ROLE_ID", "")

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

        settings_to_add = [
            ("admin_contracts_channel_id", admin_channel, "Канал для админских контрактов"),
            ("pending_ping_role_id", pending_role, "Роль для пинга при новых контрактах"),
            ("pending_counter_channel_id", admin_channel, "Канал для счетчика ожидающих"),
        ]

        for guild in guilds:
            guild_id = guild["guild_id"]
            guild_name = guild["guild_name"]

            print(f"\n🔧 Настройка сервера: {guild_name} ({guild_id})")

            for key, value, description in settings_to_add:
                # Проверить есть ли уже настройка
                async with db.execute(
                    "SELECT setting_value FROM guild_settings WHERE guild_id = ? AND setting_key = ?",
                    (guild_id, key)
                ) as cursor:
                    existing = await cursor.fetchone()

                if existing:
                    print(f"  ⏭️  {key} уже существует: {existing['setting_value']}")
                    continue

                # Добавить настройку
                await db.execute(
                    """
                    INSERT INTO guild_settings (guild_id, setting_key, setting_value, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    """,
                    (guild_id, key, value)
                )
                print(f"  ✅ Добавлен {key}: {value or '(пусто)'} - {description}")

        await db.commit()

        print("\n" + "="*60)
        print("✅ Миграция завершена успешно!")
        print("="*60)
        print("\n📝 Настройки каналов и ролей для каждого сервера:")
        print("   - admin_contracts_channel_id: канал админских контрактов")
        print("   - pending_ping_role_id: роль для пинга")
        print("   - pending_counter_channel_id: канал счетчика")
        print("\n💡 Используйте команду /setup_channels для настройки")
        print("⚠️  Обновите .env и удалите старые переменные (они больше не используются)")

    except Exception as e:
        print(f"\n❌ Ошибка миграции: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(migrate())
