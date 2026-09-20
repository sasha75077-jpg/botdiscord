-- Migration 0009: static id on users for bonus export
ALTER TABLE users ADD COLUMN static TEXT;
