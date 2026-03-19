-- Downgrade: add_description_i18n_to_rules
-- Created: 2026-03-19 14:00:00

ALTER TABLE rules DROP COLUMN IF EXISTS description_i18n;