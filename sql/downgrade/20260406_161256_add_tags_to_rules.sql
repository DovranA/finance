-- Downgrade: add_tags_to_rules
-- Created: 2026-04-06 16:12:56

ALTER TABLE rules DROP COLUMN IF EXISTS tags;