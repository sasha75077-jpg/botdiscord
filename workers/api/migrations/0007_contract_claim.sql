-- Migration 0007: claim tracking on contracts
ALTER TABLE contracts ADD COLUMN claimed_by TEXT;
ALTER TABLE contracts ADD COLUMN claimed_at DATETIME;
