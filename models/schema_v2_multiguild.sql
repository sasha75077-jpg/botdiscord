-- ============================================================================
-- SCHEMA V2: Multi-Guild Support
-- ============================================================================

-- Серверы Discord
CREATE TABLE IF NOT EXISTS guilds (
    guild_id TEXT PRIMARY KEY,
    guild_name TEXT NOT NULL,
    owner_id TEXT,
    icon_url TEXT,
    added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1
);

-- Настройки серверов (заменяет старую таблицу settings)
CREATE TABLE IF NOT EXISTS guild_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id TEXT NOT NULL,
    setting_key TEXT NOT NULL,
    setting_value TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE,
    UNIQUE(guild_id, setting_key)
);

-- Права доступа для веб-панели
CREATE TABLE IF NOT EXISTS permissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id TEXT NOT NULL,
    discord_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('owner', 'admin', 'user')),
    granted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    granted_by TEXT,
    FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE,
    UNIQUE(guild_id, discord_id)
);

-- Owner аккаунт для веб-панели (один на всю систему)
CREATE TABLE IF NOT EXISTS owner_account (
    id INTEGER PRIMARY KEY CHECK(id = 1),
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    discord_id TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login DATETIME
);

-- Ранги (привязаны к серверу)
CREATE TABLE IF NOT EXISTS ranks (
    rank_id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id TEXT NOT NULL,
    name TEXT NOT NULL,
    order_num INTEGER NOT NULL,
    role_id TEXT,
    FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE,
    UNIQUE(guild_id, name),
    UNIQUE(guild_id, order_num)
);

-- Требования для повышения (основная система)
CREATE TABLE IF NOT EXISTS rank_requirements_main (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id TEXT NOT NULL,
    rank_from INTEGER NOT NULL,
    rank_to INTEGER NOT NULL,
    family_contracts INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE,
    FOREIGN KEY (rank_from) REFERENCES ranks(rank_id),
    FOREIGN KEY (rank_to) REFERENCES ranks(rank_id),
    UNIQUE(guild_id, rank_from, rank_to)
);

-- Требования для повышения (альтернативная система)
CREATE TABLE IF NOT EXISTS rank_requirements_alt (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id TEXT NOT NULL,
    rank_from INTEGER NOT NULL,
    rank_to INTEGER NOT NULL,
    family_contracts INTEGER NOT NULL DEFAULT 0,
    tuning_contracts INTEGER NOT NULL DEFAULT 0,
    require_surname_change INTEGER DEFAULT 0,
    FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE,
    FOREIGN KEY (rank_from) REFERENCES ranks(rank_id),
    FOREIGN KEY (rank_to) REFERENCES ranks(rank_id),
    UNIQUE(guild_id, rank_from, rank_to)
);

-- Цены на контракты/ресурсы (по серверам)
CREATE TABLE IF NOT EXISTS prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id TEXT NOT NULL,
    item_key TEXT NOT NULL,
    price REAL NOT NULL DEFAULT 0,
    FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE,
    UNIQUE(guild_id, item_key)
);

-- Пользователи (привязаны к серверу)
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id TEXT NOT NULL,
    discord_id TEXT NOT NULL,
    current_rank_id INTEGER,
    surname_changed INTEGER DEFAULT 0,
    family_total INTEGER DEFAULT 0,
    tuning_total INTEGER DEFAULT 0,
    joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE,
    FOREIGN KEY (current_rank_id) REFERENCES ranks(rank_id),
    UNIQUE(guild_id, discord_id)
);

-- Контракты (привязаны к серверу)
CREATE TABLE IF NOT EXISTS contracts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id TEXT NOT NULL,
    ts TEXT NOT NULL,
    discord_id TEXT NOT NULL,
    contract_type TEXT NOT NULL,
    channel_id TEXT,
    discord_message_id TEXT,
    attachment_urls TEXT,
    msk_date TEXT,
    msk_date_iso TEXT,
    details TEXT,

    -- нормализованные поля
    price REAL DEFAULT 0,
    fish_type TEXT,
    fish_qty INTEGER DEFAULT 0,
    ore_type TEXT,
    m_iron INTEGER DEFAULT 0,
    m_silver INTEGER DEFAULT 0,
    m_copper INTEGER DEFAULT 0,
    m_tin INTEGER DEFAULT 0,
    m_gold INTEGER DEFAULT 0,
    goods_delivery TEXT,
    goods_loading TEXT,
    atelier_total_uniforms INTEGER DEFAULT 0,
    marketplace_links_count INTEGER DEFAULT 0,
    wn_category TEXT,
    wn_screenshots_count INTEGER DEFAULT 0,
    tuning_has_screenshot TEXT,

    -- статусы
    source_status TEXT DEFAULT '',
    confirm_status TEXT DEFAULT 'PENDING',
    confirmed_by TEXT,
    confirmed_at TEXT,
    reject_reason TEXT,

    FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE,
    UNIQUE(guild_id, ts, discord_id, contract_type)
);

-- Отчёты на повышение
CREATE TABLE IF NOT EXISTS promotion_reports (
    report_id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id TEXT NOT NULL,
    discord_id TEXT NOT NULL,
    from_rank_id INTEGER,
    to_rank_id INTEGER,
    system_type TEXT,
    submitted_at TEXT,
    status TEXT DEFAULT 'NEW',
    taken_by TEXT,
    reviewed_by TEXT,
    reviewed_at TEXT,
    decision TEXT,
    reason TEXT,
    FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE,
    FOREIGN KEY (from_rank_id) REFERENCES ranks(rank_id),
    FOREIGN KEY (to_rank_id) REFERENCES ranks(rank_id)
);

-- Отчёты на премии
CREATE TABLE IF NOT EXISTS bonus_reports (
    report_id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id TEXT NOT NULL,
    discord_id TEXT NOT NULL,
    week_start TEXT,
    week_end TEXT,
    total_amount REAL,
    contracts_json TEXT,
    submitted_at TEXT,
    status TEXT DEFAULT 'NEW',
    taken_by TEXT,
    reviewed_by TEXT,
    reviewed_at TEXT,
    decision TEXT,
    reason TEXT,
    FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE
);

-- Уникальный индекс для bonus_reports (предотвращение дубликатов)
CREATE UNIQUE INDEX IF NOT EXISTS ux_bonus_reports_week_active
ON bonus_reports(guild_id, discord_id, week_start, week_end)
WHERE status IN ('NEW','TAKEN','APPROVED');

-- Индексы для производительности
CREATE INDEX IF NOT EXISTS idx_contracts_guild_status ON contracts(guild_id, confirm_status);
CREATE INDEX IF NOT EXISTS idx_contracts_discord_id ON contracts(discord_id);
CREATE INDEX IF NOT EXISTS idx_users_guild_discord ON users(guild_id, discord_id);
CREATE INDEX IF NOT EXISTS idx_permissions_guild ON permissions(guild_id);
CREATE INDEX IF NOT EXISTS idx_bonus_reports_guild_status ON bonus_reports(guild_id, status);
CREATE INDEX IF NOT EXISTS idx_promotion_reports_guild_status ON promotion_reports(guild_id, status);

-- Модули и их настройки (для включения/выключения функций)
CREATE TABLE IF NOT EXISTS guild_modules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id TEXT NOT NULL,
    module_name TEXT NOT NULL,
    is_enabled BOOLEAN DEFAULT 1,
    config_json TEXT,
    FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE,
    UNIQUE(guild_id, module_name)
);

-- Audit log для отслеживания действий
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id TEXT,
    actor_id TEXT NOT NULL,
    action_type TEXT NOT NULL,
    target_type TEXT,
    target_id TEXT,
    changes_json TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_audit_log_guild_timestamp ON audit_log(guild_id, timestamp DESC);
