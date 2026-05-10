-- Upgrade: add_frozen_rank_and_balance_to_competition
-- Created: 2026-05-10 00:00:00

ALTER TABLE competition
ADD COLUMN IF NOT EXISTS frozen_rank INT,
ADD COLUMN IF NOT EXISTS frozen_balance BIGINT,
ADD COLUMN IF NOT EXISTS frozen_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_competition_frozen_at ON competition (frozen_at);