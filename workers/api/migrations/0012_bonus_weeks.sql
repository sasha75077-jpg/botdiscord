-- Migration 0012: week columns on bonus_reports (code already expects them)
ALTER TABLE bonus_reports ADD COLUMN week_start TEXT;
ALTER TABLE bonus_reports ADD COLUMN week_end TEXT;
UPDATE bonus_reports
SET week_start = substr(reason, 1, instr(reason, '..') - 1),
    week_end = substr(reason, instr(reason, '..') + 2)
WHERE (week_start IS NULL OR week_start = '')
  AND reason LIKE '%..%';
