-- Downgrade: add_frozen_rank_and_balance_to_competition
-- Created: 2026-05-10 00:00:00

ALTER TABLE competition
DROP COLUMN IF EXISTS frozen_rank INT,
DROP COLUMN IF EXISTS frozen_balance BIGINT,
DROP COLUMN IF EXISTS frozen_at TIMESTAMPTZ;

DELETE INDEX IF EXISTS idx_competition_frozen_at ON competition (frozen_at);