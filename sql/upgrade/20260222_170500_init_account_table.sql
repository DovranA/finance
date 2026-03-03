-- Upgrade: init_account_table
-- Created: 2026-02-22 17:05:00
CREATE TABLE IF NOT EXISTS accounts (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL UNIQUE,
    currency VARCHAR(10) NOT NULL,
    balance BIGINT NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_accounts_user_id ON accounts (user_id);

CREATE INDEX IF NOT EXISTS idx_accounts_active ON accounts (is_active);

ALTER TABLE accounts
ADD CONSTRAINT balance_non_negative CHECK (balance >= 0);