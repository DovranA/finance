-- Upgrade: add_description_i18n_to_rules
-- Created: 2026-03-19 14:00:00

ALTER TABLE rules
ADD COLUMN IF NOT EXISTS description_i18n JSONB NOT NULL DEFAULT '{}'::jsonb;

UPDATE rules
SET
    description_i18n = jsonb_build_object('en', description)
WHERE (
        description_i18n IS NULL
        OR description_i18n = '{}'::jsonb
    )
    AND description IS NOT NULL;