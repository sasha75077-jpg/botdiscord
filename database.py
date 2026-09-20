import os
import sqlite3
import asyncio
import aiosqlite

from config import DB_PATH as CONFIG_DB_PATH


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = CONFIG_DB_PATH or os.path.join(BASE_DIR, "bot.db")

BUSY_TIMEOUT_MS = 5000


class UniqueViolation(Exception):
    pass


async def _connect():
    db = await aiosqlite.connect(DB_PATH, timeout=BUSY_TIMEOUT_MS / 1000)
    db.row_factory = aiosqlite.Row

    await db.execute("PRAGMA foreign_keys = ON;")
    await db.execute("PRAGMA journal_mode = WAL;")
    await db.execute("PRAGMA synchronous = NORMAL;")
    await db.execute(f"PRAGMA busy_timeout = {BUSY_TIMEOUT_MS};")

    return db


async def init_db():
    """Инициализация базы данных (создание таблиц если их нет)"""
    db = await _connect()
    try:
        # Проверить есть ли новая схема (multi-guild)
        async with db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='guilds'") as cursor:
            guilds_table_exists = await cursor.fetchone() is not None

        if not guilds_table_exists:
            print("⚠️  Обнаружена старая схема БД. Выполните миграцию: python migrate_to_v2.py")
            # Загрузить старую схему для совместимости
            with open("models/schema.sql", "r", encoding="utf-8") as f:
                schema = f.read()
            await db.executescript(schema)
        else:
            print("✅ Обнаружена новая схема БД (multi-guild)")

        await db.commit()
    finally:
        await db.close()


async def migrate_db():
    """Дополнительные миграции для обновления схемы"""
    db = await _connect()
    try:
        # Проверить есть ли таблица guilds
        async with db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='guilds'") as cursor:
            has_guilds = await cursor.fetchone() is not None

        if not has_guilds:
            print("⚠️  Таблица guilds не найдена. Пропускаем дополнительные миграции.")
            return

        # Создать индекс для bonus_reports если его нет
        await db.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS ux_bonus_reports_week_active
            ON bonus_reports(guild_id, discord_id, week_start, week_end)
            WHERE status IN ('NEW','TAKEN','APPROVED');
        """)

        # site_id для связи локальных заявок с панелью
        try:
            await db.execute("ALTER TABLE applications ADD COLUMN site_id INTEGER")
        except Exception:
            pass  # колонка уже есть

        # answers (JSON ответов) для заявок с сайта/модалки
        try:
            await db.execute("ALTER TABLE applications ADD COLUMN answers TEXT")
        except Exception:
            pass  # колонка уже есть

        await db.commit()
    finally:
        await db.close()


async def register_guild(guild_id: str, guild_name: str, icon_url: str = None):
    """Зарегистрировать сервер Discord в базе данных"""
    db = await _connect()
    try:
        await db.execute("""
            INSERT INTO guilds (guild_id, guild_name, icon_url, is_active)
            VALUES (?, ?, ?, 1)
            ON CONFLICT(guild_id) DO UPDATE SET
                guild_name = excluded.guild_name,
                icon_url = excluded.icon_url
        """, (guild_id, guild_name, icon_url))
        await db.commit()
        print(f"✅ Сервер зарегистрирован: {guild_name} ({guild_id})")
    finally:
        await db.close()


async def is_module_enabled(guild_id: str, module_name: str) -> bool:
    """Проверить включен ли модуль на сервере"""
    db = await _connect()
    try:
        async with db.execute(
            "SELECT is_enabled FROM guild_modules WHERE guild_id = ? AND module_name = ?",
            (guild_id, module_name)
        ) as cursor:
            row = await cursor.fetchone()
            return bool(row["is_enabled"]) if row else True  # По умолчанию включено
    finally:
        await db.close()


async def execute(query: str, params: tuple = ()):
    db = await _connect()
    try:
        await db.execute(query, params)
        await db.commit()
    except sqlite3.IntegrityError as e:
        raise UniqueViolation(str(e)) from e
    finally:
        await db.close()


async def fetch_one(query: str, params: tuple = ()):
    db = await _connect()
    try:
        async with db.execute(query, params) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row is not None else None
    finally:
        await db.close()


async def fetch_all(query: str, params: tuple = ()):
    db = await _connect()
    try:
        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]
    finally:
        await db.close()


async def insert_contract_if_new(row: dict):
    """Вставить контракт если его еще нет (для импорта из Google Sheets)"""
    guild_id = row.get("guild_id")
    if not guild_id:
        print("⚠️  guild_id не указан в контракте, пропускаем")
        return

    params_check = (
        guild_id,
        row.get("ts"),
        row.get("discord_id"),
        row.get("contract_type"),
    )
    existing = await fetch_one(
        "SELECT id FROM contracts WHERE guild_id=? AND ts=? AND discord_id=? AND contract_type=?",
        params_check
    )

    if existing:
        # Обновить существующий контракт
        await execute("""
            UPDATE contracts SET
                channel_id=?, discord_message_id=?, attachment_urls=?,
                msk_date=?, details=?, price=?, fish_type=?, fish_qty=?,
                ore_type=?, m_iron=?, m_silver=?, m_copper=?, m_tin=?, m_gold=?,
                goods_delivery=?, goods_loading=?, atelier_total_uniforms=?,
                marketplace_links_count=?, wn_category=?, wn_screenshots_count=?,
                tuning_has_screenshot=?, msk_date_iso=?, source_status=?
            WHERE guild_id=? AND ts=? AND discord_id=? AND contract_type=?
        """, (
            row.get("channel_id"),
            row.get("discord_message_id"),
            row.get("attachment_urls"),
            row.get("msk_date"),
            row.get("details"),
            row.get("price", 0),
            row.get("fish_type"),
            row.get("fish_qty", 0),
            row.get("ore_type"),
            row.get("m_iron", 0),
            row.get("m_silver", 0),
            row.get("m_copper", 0),
            row.get("m_tin", 0),
            row.get("m_gold", 0),
            row.get("goods_delivery"),
            row.get("goods_loading"),
            row.get("atelier_total_uniforms", 0),
            row.get("marketplace_links_count", 0),
            row.get("wn_category"),
            row.get("wn_screenshots_count", 0),
            row.get("tuning_has_screenshot"),
            row.get("msk_date_iso"),
            row.get("status", ""),
            guild_id,
            row.get("ts"),
            row.get("discord_id"),
            row.get("contract_type"),
        ))
    else:
        # Вставить новый контракт
        await execute("""
            INSERT INTO contracts (
                guild_id, ts, discord_id, contract_type, channel_id, discord_message_id,
                attachment_urls, msk_date, details,
                price, fish_type, fish_qty, ore_type,
                m_iron, m_silver, m_copper, m_tin, m_gold,
                goods_delivery, goods_loading,
                atelier_total_uniforms, marketplace_links_count,
                wn_category, wn_screenshots_count, tuning_has_screenshot,
                msk_date_iso, source_status, confirm_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING')
        """, (
            guild_id,
            row.get("ts"),
            row.get("discord_id"),
            row.get("contract_type"),
            row.get("channel_id"),
            row.get("discord_message_id"),
            row.get("attachment_urls"),
            row.get("msk_date"),
            row.get("details"),
            row.get("price", 0),
            row.get("fish_type"),
            row.get("fish_qty", 0),
            row.get("ore_type"),
            row.get("m_iron", 0),
            row.get("m_silver", 0),
            row.get("m_copper", 0),
            row.get("m_tin", 0),
            row.get("m_gold", 0),
            row.get("goods_delivery"),
            row.get("goods_loading"),
            row.get("atelier_total_uniforms", 0),
            row.get("marketplace_links_count", 0),
            row.get("wn_category"),
            row.get("wn_screenshots_count", 0),
            row.get("tuning_has_screenshot"),
            row.get("msk_date_iso"),
            row.get("status", ""),
        ))

    # Синхронизация с облачной панелью (не роняет бота при ошибке сети)
    try:
        from services.api_sync import queue_contract_sync
        cur = await fetch_one(
            "SELECT confirm_status, price FROM contracts WHERE guild_id=? AND ts=? AND discord_id=? AND contract_type=?",
            (guild_id, row.get("ts"), row.get("discord_id"), row.get("contract_type"))
        )
        queue_contract_sync(
            guild_id,
            row.get("ts"),
            row.get("discord_id"),
            row.get("contract_type"),
            price=((cur or {}).get("price") or row.get("price", 0)),
            status=((cur or {}).get("confirm_status") or "PENDING"),
        )
    except Exception as e:
        print(f"[api_sync] warn: {e}")


async def get_setting(key: str, guild_id: str = None):
    """Получить настройку (для конкретного сервера или глобальную)"""
    if guild_id:
        # Новая схема - настройки по серверам
        row = await fetch_one(
            "SELECT setting_value FROM guild_settings WHERE guild_id = ? AND setting_key = ?",
            (guild_id, key)
        )
        return row["setting_value"] if row else None
    else:
        # Старая схема - глобальные настройки
        row = await fetch_one("SELECT value FROM settings WHERE key = ?", (key,))
        return row["value"] if row else None


async def set_setting(key: str, value: str, guild_id: str = None):
    """Установить настройку (для конкретного сервера или глобальную)"""
    if guild_id:
        # Новая схема
        await execute(
            """
            INSERT INTO guild_settings(guild_id, setting_key, setting_value, updated_at)
            VALUES(?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(guild_id, setting_key) DO UPDATE SET
                setting_value = excluded.setting_value,
                updated_at = CURRENT_TIMESTAMP
            """,
            (guild_id, key, value)
        )
    else:
        # Старая схема
        await execute(
            "INSERT OR REPLACE INTO settings(key, value) VALUES(?, ?)",
            (key, value)
        )


def row_to_dict(row):
    return dict(row) if row is not None else None


# ============================================================================
# Управление ролями и правами доступа
# ============================================================================

async def get_user_role(discord_id: str, guild_id: str, owner_discord_id: str = None) -> str:
    """
    Получить роль пользователя на сервере.

    Args:
        discord_id: Discord ID пользователя
        guild_id: ID сервера
        owner_discord_id: Discord ID владельца бота (для проверки owner)

    Returns:
        'owner', 'admin', 'recruiter' или 'user'
    """
    # Проверить является ли пользователь owner
    if owner_discord_id and discord_id == owner_discord_id:
        return 'owner'

    # Проверить в БД
    row = await fetch_one(
        "SELECT role FROM permissions WHERE guild_id = ? AND discord_id = ?",
        (guild_id, discord_id)
    )

    if row:
        return row["role"]

    # По умолчанию - user
    return 'user'


async def set_user_role(guild_id: str, discord_id: str, role: str, granted_by: str = None):
    """
    Назначить роль пользователю на сервере.

    Args:
        guild_id: ID сервера
        discord_id: Discord ID пользователя
        role: Роль ('owner', 'admin', 'recruiter', 'user')
        granted_by: Discord ID того кто назначил роль

    Raises:
        ValueError: Если роль невалидна
    """
    valid_roles = ['owner', 'admin', 'recruiter', 'user']
    if role not in valid_roles:
        raise ValueError(f"Невалидная роль: {role}. Допустимые: {', '.join(valid_roles)}")

    await execute(
        """
        INSERT INTO permissions (guild_id, discord_id, role, granted_by, granted_at)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(guild_id, discord_id) DO UPDATE SET
            role = excluded.role,
            granted_by = excluded.granted_by,
            granted_at = CURRENT_TIMESTAMP
        """,
        (guild_id, discord_id, role, granted_by)
    )


async def list_permissions(guild_id: str):
    """
    Получить список всех пользователей с ролями на сервере.

    Args:
        guild_id: ID сервера

    Returns:
        List[dict]: Список словарей с полями: discord_id, role, granted_at, granted_by
    """
    rows = await fetch_all(
        """
        SELECT discord_id, role, granted_at, granted_by
        FROM permissions
        WHERE guild_id = ?
        ORDER BY
            CASE role
                WHEN 'owner' THEN 1
                WHEN 'admin' THEN 2
                WHEN 'recruiter' THEN 3
                WHEN 'user' THEN 4
            END,
            granted_at DESC
        """,
        (guild_id,)
    )
    return rows


async def delete_permission(guild_id: str, discord_id: str):
    """
    Удалить роль пользователя на сервере.

    Args:
        guild_id: ID сервера
        discord_id: Discord ID пользователя

    Returns:
        bool: True если роль была удалена, False если не найдена
    """
    # Проверить существует ли роль
    existing = await fetch_one(
        "SELECT id FROM permissions WHERE guild_id = ? AND discord_id = ?",
        (guild_id, discord_id)
    )

    if not existing:
        return False

    await execute(
        "DELETE FROM permissions WHERE guild_id = ? AND discord_id = ?",
        (guild_id, discord_id)
    )
    return True


async def get_user_guilds(discord_id: str, owner_discord_id: str = None):
    """
    Получить список серверов где пользователь имеет доступ.

    Args:
        discord_id: Discord ID пользователя
        owner_discord_id: Discord ID владельца бота

    Returns:
        List[dict]: Список серверов с полями: guild_id, guild_name, role, icon_url
    """
    # Если owner - вернуть все серверы
    if owner_discord_id and discord_id == owner_discord_id:
        guilds = await fetch_all(
            """
            SELECT guild_id, guild_name, icon_url, is_active
            FROM guilds
            WHERE is_active = 1
            ORDER BY guild_name
            """
        )
        # Добавить роль owner ко всем серверам
        for guild in guilds:
            guild['role'] = 'owner'
        return guilds

    # Иначе вернуть серверы где есть роль
    guilds = await fetch_all(
        """
        SELECT g.guild_id, g.guild_name, g.icon_url, g.is_active, p.role
        FROM guilds g
        INNER JOIN permissions p ON g.guild_id = p.guild_id
        WHERE p.discord_id = ? AND g.is_active = 1
        ORDER BY
            CASE p.role
                WHEN 'admin' THEN 1
                WHEN 'recruiter' THEN 2
                WHEN 'user' THEN 3
            END,
            g.guild_name
        """,
        (discord_id,)
    )
    return guilds


# Алиасы для обратной совместимости
fetchone = fetch_one
fetchall = fetch_all
getsetting = get_setting
setsetting = set_setting


def insert_contract_if_new_sync(data):
    asyncio.run(insert_contract_if_new(data))
