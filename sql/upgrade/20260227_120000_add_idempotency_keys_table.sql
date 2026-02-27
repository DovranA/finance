-- Upgrade: add_idempotency_keys_table
-- Created: 2026-02-27 12:00:00

CREATE TABLE IF NOT EXISTS idempotency_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4 (),
    key VARCHAR(256) NOT NULL UNIQUE,
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (
        status IN (
            'pending',
            'completed',
            'failed'
        )
    ),
    response_code INTEGER,
    response_body TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ
);

-- Fast lookup by key (covered by UNIQUE, but explicit for clarity)
CREATE INDEX IF NOT EXISTS idx_idempotency_keys_key ON idempotency_keys (key);

-- TTL cleanup: periodically DELETE WHERE expires_at < NOW()
CREATE INDEX IF NOT EXISTS idx_idempotency_keys_expires ON idempotency_keys (expires_at)
WHERE
    expires_at IS NOT NULL;

-- Status-based queries (e.g., find stuck 'pending' rows)
CREATE INDEX IF NOT EXISTS idx_idempotency_keys_status ON idempotency_keys (status, created_at);