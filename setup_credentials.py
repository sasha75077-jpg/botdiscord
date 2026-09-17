"""
Helper скрипт для настройки credentials файлов

Помогает скопировать credentials.json в правильную структуру для каждого сервера
"""
import os
import shutil
import asyncio
import aiosqlite

DB_PATH = "bot.db"
CREDENTIALS_DIR = "credentials"

async def setup_credentials():
    print("🔧 Настройка credentials файлов для серверов\n")

    # Проверить существует ли credentials.json в корне
    if not os.path.exists("credentials.json"):
        print("❌ Файл credentials.json не найден в корневой папке")
        print("\n💡 Получите credentials.json из Google Cloud Console:")
        print("   1. https://console.cloud.google.com/")
        print("   2. APIs & Services → Credentials")
        print("   3. Create Service Account → Create Key (JSON)")
        return

    # Создать папку credentials если её нет
    os.makedirs(CREDENTIALS_DIR, exist_ok=True)
    print(f"✅ Папка {CREDENTIALS_DIR}/ создана")

    # Получить все серверы из БД
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row

    try:
        async with db.execute("SELECT guild_id, guild_name FROM guilds WHERE is_active = 1") as cursor:
            guilds = await cursor.fetchall()

        if not guilds:
            print("⚠️  Нет активных серверов в БД")
            return

        print(f"\n📊 Найдено серверов: {len(guilds)}\n")

        for guild in guilds:
            guild_id = guild["guild_id"]
            guild_name = guild["guild_name"]

            target_path = os.path.join(CREDENTIALS_DIR, f"{guild_id}.json")

            # Проверить существует ли уже
            if os.path.exists(target_path):
                print(f"⏭️  {guild_name} ({guild_id}) - файл уже существует")
                continue

            # Скопировать credentials.json
            shutil.copy2("credentials.json", target_path)
            print(f"✅ {guild_name} ({guild_id}) - скопирован → {target_path}")

            # Обновить путь в БД
            await db.execute(
                """
                INSERT INTO guild_settings (guild_id, setting_key, setting_value, updated_at)
                VALUES (?, 'credentials_path', ?, CURRENT_TIMESTAMP)
                ON CONFLICT(guild_id, setting_key) DO UPDATE SET
                    setting_value = excluded.setting_value,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (guild_id, target_path)
            )

        await db.commit()

        print("\n" + "="*60)
        print("✅ Настройка завершена!")
        print("="*60)
        print("\n📝 Что дальше:")
        print(f"   1. Каждый сервер теперь имеет свой credentials файл в папке {CREDENTIALS_DIR}/")
        print("   2. Используйте /setup_sheets для настройки Sheet ID")
        print("   3. При необходимости замените credentials файл конкретного сервера")
        print("\n⚠️  Важно: НЕ добавляйте папку credentials/ в git!")

    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(setup_credentials())
