-- Migration 0013: contracts_json on bonus_reports (site submit stores snapshot)
ALTER TABLE bonus_reports ADD COLUMN contracts_json TEXT DEFAULT '[]';
