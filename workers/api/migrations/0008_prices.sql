-- Migration 0008: global price list (mirrors bot prices table)
CREATE TABLE IF NOT EXISTS prices (
    item_key TEXT PRIMARY KEY,
    price REAL NOT NULL DEFAULT 0,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
