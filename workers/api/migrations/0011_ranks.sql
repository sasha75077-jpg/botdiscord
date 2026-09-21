-- Migration 0011: ranks ladder + promotion requirements (mirrors bot tables)
CREATE TABLE IF NOT EXISTS ranks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    role_id TEXT,
    min_contracts INTEGER NOT NULL DEFAULT 0,
    sort_order INTEGER NOT NULL DEFAULT 0,
    guild_id TEXT NOT NULL,
    FOREIGN KEY (guild_id) REFERENCES guilds(guild_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS rank_requirements_main (
    rank_from INTEGER NOT NULL,
    rank_to INTEGER NOT NULL,
    family_contracts INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (rank_from, rank_to)
);

CREATE TABLE IF NOT EXISTS rank_requirements_alt (
    rank_from INTEGER NOT NULL,
    rank_to INTEGER NOT NULL,
    family_contracts INTEGER NOT NULL DEFAULT 0,
    tuning_contracts INTEGER NOT NULL DEFAULT 0,
    system_type TEXT NOT NULL DEFAULT 'main',
    PRIMARY KEY (rank_from, rank_to)
);
