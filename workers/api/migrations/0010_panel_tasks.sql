-- Migration 0010: panel posting tasks (site -> bot)
CREATE TABLE IF NOT EXISTS panel_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id TEXT NOT NULL,
    panel_type TEXT NOT NULL CHECK(panel_type IN ('admin_hub', 'profile')),
    channel_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'done', 'error')),
    result TEXT,
    created_by TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_panel_tasks_pending ON panel_tasks(status, id) WHERE status = 'pending';
