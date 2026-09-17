# -*- coding: utf-8 -*-
"""
Миграция базы данных с версии 1 (single-guild) на версию 2 (multi-guild)

Что делает этот скрипт:
1. Проверяет текущую версию базы
2. Создает бэкап старой базы
3. Обновляет схему (добавляет guild_id колонки)
4. Мигрирует все данные с DEFAULT_GUILD_ID
5. Создает индексы для производительности
6. Обновляет версию базы
"""

import sqlite3
import os
import shutil
import sys
from datetime import datetime

# Константы
DB_PATH = "bot.db"
BACKUP_DIR = "backups"
DEFAULT_GUILD_ID = "880440495233454080"  # Твой текущий сервер
TARGET_VERSION = 2

# Цвета для вывода (работают в Windows 10+ с ANSI support)
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
RESET = "\033[0m"

# Включить ANSI цвета в Windows
if sys.platform == "win32":
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except:
        pass  # Если не получилось - цвета просто не будут работать

def print_step(emoji, message, color=RESET):
    """Красивый вывод шагов"""
    print(f"{color}{emoji} {message}{RESET}")

def create_backup(db_path):
    """Создать бэкап базы данных"""
    if not os.path.exists(db_path):
        print_step("⚠️", "База данных не найдена. Будет создана новая.", YELLOW)
        return None

    # Создать папку для бэкапов
    os.makedirs(BACKUP_DIR, exist_ok=True)

    # Имя бэкапа с датой
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_path = os.path.join(BACKUP_DIR, f"bot_backup_{timestamp}.db")

    # Копировать файл
    shutil.copy2(db_path, backup_path)
    print_step("✅", f"Бэкап создан: {backup_path}", GREEN)
    return backup_path

def get_db_version(conn):
    """Получить текущую версию базы данных"""
    cursor = conn.cursor()

    # Проверить есть ли таблица версий
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='db_version'
    """)

    if not cursor.fetchone():
        # Таблицы версий нет - это версия 1
        return 1

    # Получить версию
    cursor.execute("SELECT version FROM db_version ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    return row[0] if row else 1

def create_version_table(conn):
    """Создать таблицу версий если её нет"""
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS db_version (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version INTEGER NOT NULL,
            migrated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()

def update_db_version(conn, version):
    """Обновить версию базы данных"""
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO db_version (version) VALUES (?)
    """, (version,))
    conn.commit()

def table_exists(conn, table_name):
    """Проверить существует ли таблица"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name=?
    """, (table_name,))
    return cursor.fetchone() is not None

def column_exists(conn, table_name, column_name):
    """Проверить существует ли колонка в таблице"""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns

def migrate_v1_to_v2(conn):
    """Миграция с версии 1 на версию 2"""
    cursor = conn.cursor()

    print_step("🔄", "Начинаем миграцию на версию 2...", BLUE)
    print()

    # === 1. Создать новые таблицы ===
    print_step("📦", "Создаем новые таблицы...", BLUE)

    # Таблица серверов
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS guilds (
            guild_id TEXT PRIMARY KEY,
            guild_name TEXT NOT NULL,
            icon_url TEXT,
            joined_at TEXT DEFAULT CURRENT_TIMESTAMP,
            is_active INTEGER DEFAULT 1
        )
    """)

    # Таблица модулей
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS guild_modules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT NOT NULL,
            module_name TEXT NOT NULL,
            is_enabled INTEGER DEFAULT 1,
            config TEXT,
            FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE,
            UNIQUE(guild_id, module_name)
        )
    """)

    # Таблица настроек
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS guild_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT NOT NULL,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE,
            UNIQUE(guild_id, key)
        )
    """)

    # Таблица прав доступа
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS permissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT NOT NULL,
            discord_id TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('owner', 'admin', 'user')),
            granted_at TEXT DEFAULT CURRENT_TIMESTAMP,
            granted_by TEXT,
            FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE,
            UNIQUE(guild_id, discord_id)
        )
    """)

    # Таблица owner аккаунта (глобальная)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS owner_account (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    print_step("✅", "Новые таблицы созданы", GREEN)

    # === 2. Обновить существующие таблицы ===
    print_step("🔧", "Обновляем существующие таблицы...", BLUE)

    tables_to_migrate = [
        'contracts',
        'ranks',
        'users',
        'promotions',
        'bonus_reports',
        'applications',
        'settings'
    ]

    migrated_tables = []

    for table_name in tables_to_migrate:
        if not table_exists(conn, table_name):
            print_step("⏭️", f"Таблица {table_name} не существует, пропускаем", YELLOW)
            continue

        if column_exists(conn, table_name, 'guild_id'):
            print_step("⏭️", f"Таблица {table_name} уже имеет guild_id, пропускаем", YELLOW)
            continue

        print_step("🔄", f"Мигрируем таблицу {table_name}...", BLUE)

        # Переименовать старую таблицу
        cursor.execute(f"ALTER TABLE {table_name} RENAME TO {table_name}_old")

        # Получить структуру старой таблицы
        cursor.execute(f"PRAGMA table_info({table_name}_old)")
        columns = cursor.fetchall()
        column_defs = []
        column_names = []

        for col in columns:
            col_name = col[1]
            col_type = col[2]
            col_notnull = col[3]
            col_default = col[4]
            col_pk = col[5]

            column_names.append(col_name)

            col_def = f"{col_name} {col_type}"
            if col_pk:
                col_def += " PRIMARY KEY"
            if col_notnull and not col_pk:
                col_def += " NOT NULL"
            if col_default is not None:
                col_def += f" DEFAULT {col_default}"

            column_defs.append(col_def)

        # Добавить guild_id колонку
        column_defs.append("guild_id TEXT NOT NULL")

        # Создать новую таблицу
        create_sql = f"""
            CREATE TABLE {table_name} (
                {', '.join(column_defs)}
            )
        """
        cursor.execute(create_sql)

        # Скопировать данные с DEFAULT_GUILD_ID
        columns_str = ', '.join(column_names)
        cursor.execute(f"""
            INSERT INTO {table_name} ({columns_str}, guild_id)
            SELECT {columns_str}, ? FROM {table_name}_old
        """, (DEFAULT_GUILD_ID,))

        rows_migrated = cursor.rowcount
        migrated_tables.append((table_name, rows_migrated))

        print_step("✅", f"Таблица {table_name} обновлена ({rows_migrated} записей)", GREEN)

    conn.commit()

    # === 3. Зарегистрировать текущий сервер ===
    print_step("🎯", "Регистрируем текущий сервер...", BLUE)

    cursor.execute("""
        INSERT OR IGNORE INTO guilds (guild_id, guild_name)
        VALUES (?, 'Default Server')
    """, (DEFAULT_GUILD_ID,))

    # Включить все модули по умолчанию
    modules = ['contracts', 'ranks', 'bonus', 'applications', 'pending', 'sheets_sync']
    for module in modules:
        cursor.execute("""
            INSERT OR IGNORE INTO guild_modules (guild_id, module_name, is_enabled)
            VALUES (?, ?, 1)
        """, (DEFAULT_GUILD_ID, module))

    conn.commit()
    print_step("✅", "Сервер зарегистрирован", GREEN)

    # === 4. Создать индексы ===
    print_step("⚡", "Создаем индексы для производительности...", BLUE)

    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_contracts_guild ON contracts(guild_id)",
        "CREATE INDEX IF NOT EXISTS idx_contracts_discord ON contracts(discord_id, guild_id)",
        "CREATE INDEX IF NOT EXISTS idx_users_guild ON users(guild_id)",
        "CREATE INDEX IF NOT EXISTS idx_users_discord ON users(discord_id, guild_id)",
        "CREATE INDEX IF NOT EXISTS idx_ranks_guild ON ranks(guild_id)",
        "CREATE INDEX IF NOT EXISTS idx_promotions_guild ON promotions(guild_id)",
        "CREATE INDEX IF NOT EXISTS idx_promotions_discord ON promotions(discord_id, guild_id)",
        "CREATE INDEX IF NOT EXISTS idx_bonus_guild ON bonus_reports(guild_id)",
        "CREATE INDEX IF NOT EXISTS idx_bonus_discord ON bonus_reports(discord_id, guild_id)",
        "CREATE INDEX IF NOT EXISTS idx_permissions_guild ON permissions(guild_id)",
        "CREATE INDEX IF NOT EXISTS idx_permissions_discord ON permissions(discord_id)",
        "CREATE INDEX IF NOT EXISTS idx_settings_guild ON guild_settings(guild_id)",
    ]

    for index_sql in indexes:
        try:
            cursor.execute(index_sql)
        except sqlite3.OperationalError:
            pass  # Индекс уже существует

    conn.commit()
    print_step("✅", "Индексы созданы", GREEN)

    # === 5. Вывести статистику ===
    print()
    print_step("📊", "Статистика миграции:", BLUE)
    if migrated_tables:
        for table_name, rows_count in migrated_tables:
            print(f"  - {table_name}: {rows_count} записей")
    else:
        print("  Все таблицы уже были в версии 2")

    return True

def main():
    """Главная функция миграции"""
    print()
    print_step("🚀", "=== Миграция базы данных ===", BLUE)
    print()

    # Проверить существует ли база
    if not os.path.exists(DB_PATH):
        print_step("⚠️", f"База данных {DB_PATH} не найдена", YELLOW)
        print_step("ℹ️", "Будет создана новая база версии 2 при первом запуске бота", BLUE)
        return

    # Создать бэкап
    backup_path = create_backup(DB_PATH)

    # Подключиться к базе
    conn = sqlite3.connect(DB_PATH)

    try:
        # Создать таблицу версий если её нет
        create_version_table(conn)

        # Получить текущую версию
        current_version = get_db_version(conn)
        print_step("🔍", f"Текущая версия базы: {current_version}", BLUE)

        if current_version >= TARGET_VERSION:
            print_step("✅", f"База уже версии {current_version}, миграция не требуется", GREEN)
            return

        print_step("🎯", f"Целевая версия: {TARGET_VERSION}", BLUE)
        print()

        # Выполнить миграцию
        if current_version == 1:
            success = migrate_v1_to_v2(conn)

            if success:
                # Обновить версию базы
                update_db_version(conn, TARGET_VERSION)
                print()
                print_step("🎉", "Миграция завершена успешно!", GREEN)
                print_step("✅", f"База данных обновлена до версии {TARGET_VERSION}", GREEN)
                print()
                print_step("📝", "Что дальше:", BLUE)
                print("  1. Проверь настройки в .env файле")
                print("  2. Убедись что GUILD_IDS содержит твой Server ID")
                print("  3. Запусти бота: python main.py")
                print()
                if backup_path:
                    print_step("💡", f"Бэкап старой базы: {backup_path}", YELLOW)
            else:
                print_step("❌", "Ошибка миграции", RED)

                if backup_path:
                    print_step("🔄", "Восстанавливаем из бэкапа...", YELLOW)
                    conn.close()
                    shutil.copy2(backup_path, DB_PATH)
                    print_step("✅", "База восстановлена из бэкапа", GREEN)

    except Exception as e:
        print_step("❌", f"Ошибка: {str(e)}", RED)

        if backup_path:
            print_step("🔄", "Восстанавливаем из бэкапа...", YELLOW)
            conn.close()
            shutil.copy2(backup_path, DB_PATH)
            print_step("✅", "База восстановлена из бэкапа", GREEN)

        raise

    finally:
        conn.close()

if __name__ == "__main__":
    main()
