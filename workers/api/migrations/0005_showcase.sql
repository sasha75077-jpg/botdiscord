-- Migration 0005: public showcase of family Discord servers for strangers
CREATE TABLE IF NOT EXISTS showcase_servers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id TEXT,
    title TEXT NOT NULL,
    description TEXT,
    majestic_server TEXT,
    invite_url TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_showcase_active ON showcase_servers(is_active, sort_order);
