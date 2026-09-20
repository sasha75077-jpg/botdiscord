-- Migration 0006: details JSON for site-submitted contracts
ALTER TABLE contracts ADD COLUMN details TEXT;
