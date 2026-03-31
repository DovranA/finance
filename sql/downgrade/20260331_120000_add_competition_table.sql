-- Downgrade: add_competition_table
-- Created: 2026-03-31 12:00:00

DROP INDEX IF EXISTS idx_competition_created_at;

DROP INDEX IF EXISTS idx_competition_user_id;

DROP TABLE IF EXISTS competition;