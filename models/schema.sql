-- Настройки бота (каналы, роли с правами)
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);

-- Ранги (лестница повышения)
CREATE TABLE IF NOT EXISTS ranks (
    rank_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    order_num INTEGER UNIQUE NOT NULL,
    role_id TEXT
);

-- Требования для повышения (основная система)
CREATE TABLE IF NOT EXISTS rank_requirements_main (
    rank_from INTEGER NOT NULL,
    rank_to INTEGER NOT NULL,
    family_contracts INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (rank_from, rank_to),
    FOREIGN KEY (rank_from) REFERENCES ranks(rank_id),
    FOREIGN KEY (rank_to) REFERENCES ranks(rank_id)
);

-- Требования для повышения (альтернативная система)
CREATE TABLE IF NOT EXISTS rank_requirements_alt (
    rank_from INTEGER NOT NULL,
    rank_to INTEGER NOT NULL,
    family_contracts INTEGER NOT NULL DEFAULT 0,
    tuning_contracts INTEGER NOT NULL DEFAULT 0,
    require_surname_change INTEGER DEFAULT 0,
    PRIMARY KEY (rank_from, rank_to),
    FOREIGN KEY (rank_from) REFERENCES ranks(rank_id),
    FOREIGN KEY (rank_to) REFERENCES ranks(rank_id)
);

-- Цены на контракты/ресурсы
CREATE TABLE IF NOT EXISTS prices (
    item_key TEXT PRIMARY KEY,
    price REAL NOT NULL DEFAULT 0
);

-- Пользователи
CREATE TABLE IF NOT EXISTS users (
    discord_id TEXT PRIMARY KEY,
    current_rank_id INTEGER DEFAULT 3,
    surname_changed INTEGER DEFAULT 0,
    family_total INTEGER DEFAULT 0,
    tuning_total INTEGER DEFAULT 0,
    FOREIGN KEY (current_rank_id) REFERENCES ranks(rank_id)
);

-- Контракты (импорт из Sheets)
CREATE TABLE IF NOT EXISTS contracts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    discord_id TEXT NOT NULL,
    contract_type TEXT NOT NULL,
    channel_id TEXT,
    discord_message_id TEXT,
    attachment_urls TEXT,
    msk_date TEXT,
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
    tuning_has_screenshot TEXT,
    
    -- подтверждение
    confirm_status TEXT DEFAULT 'PENDING',
    confirmed_by TEXT,
    confirmed_at TEXT,
    reject_reason TEXT,
    
    UNIQUE(ts, discord_id, contract_type)
);

-- Отчёты на повышение
CREATE TABLE IF NOT EXISTS promotion_reports (
    report_id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    FOREIGN KEY (from_rank_id) REFERENCES ranks(rank_id),
    FOREIGN KEY (to_rank_id) REFERENCES ranks(rank_id)
);

-- Отчёты на премии
CREATE TABLE IF NOT EXISTS bonus_reports (
    report_id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    reason TEXT
);
