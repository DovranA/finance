-- Upgrade: add_ledger_entries_table
-- Created: 2026-02-26 18:04:21

CREATE TABLE IF NOT EXISTS ledger_entries (
    id UUID PRIMARY KEY,
    account_id UUID NOT NULL,
    transaction_id UUID NOT NULL,
    amount BIGINT NOT NULL CHECK (amount > 0),
    direction SMALLINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT fk_ledger_account FOREIGN KEY (account_id) REFERENCES accounts (id)
);

CREATE INDEX idx_ledger_account ON ledger_entries (account_id);

CREATE INDEX IF NOT EXISTS idx_ledger_account_created ON ledger_entries (account_id, created_at DESC);

CREATE INDEX idx_ledger_tx_account ON ledger_entries (transaction_id, account_id);

ALTER TABLE ledger_entries
ADD CONSTRAINT fk_ledger_tx FOREIGN KEY (transaction_id) REFERENCES transactions (id);

ALTER TABLE ledger_entries
ADD CONSTRAINT direction_check CHECK (direction IN (-1, 1));