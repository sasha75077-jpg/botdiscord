#!/usr/bin/env python3
"""
Миграция: Добавление роли 'recruiter' в таблицу permissions

Изменения:
- Пересоздает таблицу permissions с поддержкой 4 ролей: owner, admin, recruiter, user
- Сохраняет все существующие данные
"""

import asyncio
import aiosqlite
import os
from database import DB_PATH

async def migrate():
    print("🔄 Начало миграции: добавление роли 'recruiter'")

    if not os.path.exists(DB_PATH):
        print(f"❌ База данных не найдена: {DB_PATH}")
        return

    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row

    try:
        # Проверить существует ли таблица permissions
        async with db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='permissions'"
        ) as cursor:
            table_exists = await cursor.fetchone()

        if not table_exists:
            print("⚠️  Таблица permissions не существует, создаем новую...")
            await db.execute("""
                CREATE TABLE permissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id TEXT NOT NULL,
                    discord_id TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('owner', 'admin', 'recruiter', 'user')),
                    granted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    granted_by TEXT,
                    FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE,
                    UNIQUE(guild_id, discord_id)
                )
            """)
            await db.commit()
            print("✅ Таблица permissions создана с поддержкой роли 'recruiter'")
            return

        # Проверить текущий CHECK constraint
        async with db.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='permissions'"
        ) as cursor:
            row = await cursor.fetchone()
            table_sql = row[0] if row else ""

        if "'recruiter'" in table_sql:
            print("✅ Роль 'recruiter' уже поддерживается в таблице permissions")
            return

        print("📋 Обновление таблицы permissions...")

        # Шаг 1: Создать новую таблицу с обновленным constraint
        await db.execute("""
            CREATE TABLE permissions_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id TEXT NOT NULL,
                discord_id TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('owner', 'admin', 'recruiter', 'user')),
                granted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                granted_by TEXT,
                FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE,
                UNIQUE(guild_id, discord_id)
            )
        """)
        print("  ✓ Создана временная таблица permissions_new")

        # Шаг 2: Скопировать данные из старой таблицы
        await db.execute("""
            INSERT INTO permissions_new (id, guild_id, discord_id, role, granted_at, granted_by)
            SELECT id, guild_id, discord_id, role, granted_at, granted_by
            FROM permissions
        """)

        # Посчитать сколько записей скопировано
        async with db.execute("SELECT COUNT(*) as cnt FROM permissions_new") as cursor:
            row = await cursor.fetchone()
            count = row[0]
        print(f"  ✓ Скопировано {count} записей")

        # Шаг 3: Удалить старую таблицу
        await db.execute("DROP TABLE permissions")
        print("  ✓ Удалена старая таблица permissions")

        # Шаг 4: Переименовать новую таблицу
        await db.execute("ALTER TABLE permissions_new RENAME TO permissions")
        print("  ✓ Таблица permissions_new переименована в permissions")

        await db.commit()
        print("✅ Миграция завершена успешно!")
        print("\n📊 Теперь таблица permissions поддерживает 4 роли:")
        print("   • owner     - Владелец бота (полный доступ)")
        print("   • admin     - Администратор сервера")
        print("   • recruiter - Рекрутер (агитации)")
        print("   • user      - Обычный пользователь")

    except Exception as e:
        print(f"❌ Ошибка миграции: {e}")
        await db.rollback()
        raise
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(migrate())
