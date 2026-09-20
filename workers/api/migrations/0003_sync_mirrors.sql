-- Migration 0003: external ids for bot sync + missing mirrors
-- (bonus_reports never made it into D1 with 0001, create it fully here)

CREATE TABLE IF NOT EXISTS bonus_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    external_id TEXT UNIQUE,
    guild_id TEXT NOT NULL,
    reporter_discord_id TEXT NOT NULL,
    reporter_username TEXT,
    recipient_discord_id TEXT NOT NULL,
    recipient_nickname TEXT NOT NULL,
    bonus_type TEXT NOT NULL,
    amount REAL NOT NULL,
    reason TEXT,
    screenshot_url TEXT,
    status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'approved', 'rejected')),
    admin_notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_bonus_reports_guild ON bonus_reports(guild_id, status);

ALTER TABLE applications ADD COLUMN external_id TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS ux_applications_external ON applications(external_id);

CREATE TABLE IF NOT EXISTS promotion_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    external_id TEXT UNIQUE,
    guild_id TEXT NOT NULL,
    discord_id TEXT NOT NULL,
    discord_username TEXT,
    from_rank TEXT,
    to_rank TEXT,
    reason TEXT,
    status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'approved', 'rejected')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_promotion_reports_guild ON promotion_reports(guild_id, status);
