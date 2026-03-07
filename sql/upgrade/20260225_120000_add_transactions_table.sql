-- Upgrade: add_transactions_table
-- Created: 2026-02-27 12:00:00

CREATE TABLE IF NOT EXISTS transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4 (),
    idempotency_key VARCHAR(256) NOT NULL UNIQUE,
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (
        status IN (
            'pending',
            'completed',
            'failed'
        )
    ),
    reference_type VARCHAR(64),
    reference_id VARCHAR(256),
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ
);

-- Fast lookup by key (covered by UNIQUE, but explicit for clarity)
CREATE INDEX IF NOT EXISTS idx_transactions_key ON transactions (idempotency_key);

-- TTL cleanup: periodically DELETE WHERE expires_at < NOW()
CREATE INDEX IF NOT EXISTS idx_transactions_expires ON transactions (expires_at)
WHERE
    expires_at IS NOT NULL;

-- Status-based queries (e.g., find stuck 'pending' rows)
CREATE INDEX IF NOT EXISTS idx_transactions_status ON transactions (status, created_at);