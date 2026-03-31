-- Upgrade: add_competition_table
-- Created: 2026-03-31 12:00:00

CREATE TABLE IF NOT EXISTS competition (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid (),
    user_id UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id)
);

CREATE INDEX IF NOT EXISTS idx_competition_user_id ON competition (user_id);

CREATE INDEX IF NOT EXISTS idx_competition_created_at ON competition (created_at);