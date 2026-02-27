-- Upgrade: add_ledger_entries_table
-- Created: 2026-02-26 18:04:21

CREATE TABLE IF NOT EXISTS ledger_entries (
    id UUID PRIMARY KEY,
    account_id UUID NOT NULL,
    amount BIGINT NOT NULL CHECK (amount > 0),
    entry_type VARCHAR(10) NOT NULL CHECK (
        entry_type IN ('credit', 'debit')
    ),
    currency VARCHAR(10) NOT NULL,
    reference_id UUID NOT NULL,
    reference_type VARCHAR(50) NOT NULL,
    idempotency_key VARCHAR(128) NOT NULL UNIQUE,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT fk_ledger_account FOREIGN KEY (account_id) REFERENCES accounts (id)
);

CREATE INDEX IF NOT EXISTS idx_ledger_account_created ON ledger_entries (account_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_ledger_reference ON ledger_entries (reference_id, reference_type);