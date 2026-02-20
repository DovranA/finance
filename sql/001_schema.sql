-- ============================================================
-- Finance Microservice — Database Schema
-- All monetary values stored as BIGINT (cents / smallest unit)
-- Partition-ready, index-optimized, immutable ledger
-- ============================================================

-- ── Extensions ────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── 1. Accounts ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS accounts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4 (),
    user_id UUID NOT NULL UNIQUE,
    balance BIGINT NOT NULL DEFAULT 0 CONSTRAINT balance_non_negative CHECK (balance >= 0),
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_accounts_user_id ON accounts (user_id);

-- ── 2. Treasury Account ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS treasury_account (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4 (),
    account_type VARCHAR(50) NOT NULL UNIQUE, -- 'platform_fee', 'treasury'
    balance BIGINT NOT NULL DEFAULT 0,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Seed treasury accounts
INSERT INTO
    treasury_account (account_type, balance)
VALUES ('platform_fee', 0),
    ('treasury', 0)
ON CONFLICT (account_type) DO NOTHING;

-- ── 3. Ledger Entries (Immutable / Append-Only) ──────────────
CREATE TABLE IF NOT EXISTS ledger_entries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4 (),
    account_id UUID NOT NULL,
    amount BIGINT NOT NULL, -- positive = credit, negative = debit
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    entry_type VARCHAR(50) NOT NULL, -- 'actor_reward', 'publisher_reward', 'platform_fee', 'treasury_cut'
    reference_id UUID NOT NULL, -- links to actor_action / reward_batch
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Partition-ready: can be partitioned by created_at range
-- ALTER TABLE ledger_entries RENAME TO ledger_entries_old;
-- CREATE TABLE ledger_entries (...) PARTITION BY RANGE (created_at);

CREATE INDEX idx_ledger_account_id ON ledger_entries (account_id);

CREATE INDEX idx_ledger_reference_id ON ledger_entries (reference_id);

CREATE INDEX idx_ledger_created_at ON ledger_entries (created_at);

CREATE INDEX idx_ledger_entry_type ON ledger_entries (entry_type);

-- Prevent mutations: only INSERTs allowed (enforced at app level + optional trigger)
CREATE OR REPLACE FUNCTION prevent_ledger_mutation()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'ledger_entries is immutable: UPDATE and DELETE are forbidden';
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_ledger_immutable
    BEFORE UPDATE OR DELETE ON ledger_entries
    FOR EACH ROW EXECUTE FUNCTION prevent_ledger_mutation();

-- ── 4. Economic Actions (Dynamic Definitions) ────────────────
CREATE TABLE IF NOT EXISTS economic_actions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4 (),
    code VARCHAR(100) NOT NULL UNIQUE, -- 'LIKE', 'SHARE', 'VIEW', etc.
    description TEXT NOT NULL DEFAULT '',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_economic_actions_code ON economic_actions (code);

CREATE INDEX idx_economic_actions_active ON economic_actions (is_active)
WHERE
    is_active = TRUE;

-- ── 5. Economic Action Versions ──────────────────────────────
CREATE TABLE IF NOT EXISTS economic_action_versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4 (),
    action_id UUID NOT NULL REFERENCES economic_actions (id),
    publisher_reward BIGINT NOT NULL DEFAULT 0,
    actor_reward BIGINT NOT NULL DEFAULT 0,
    platform_fee BIGINT NOT NULL DEFAULT 0,
    treasury_cut BIGINT NOT NULL DEFAULT 0,
    version INTEGER NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    active_from TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (action_id, version)
);

CREATE INDEX idx_eav_action_id ON economic_action_versions (action_id);

CREATE INDEX idx_eav_active ON economic_action_versions (action_id, is_active)
WHERE
    is_active = TRUE;

-- ── 6. Actor Actions ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS actor_actions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4 (),
    actor_id UUID NOT NULL,
    content_id UUID NOT NULL,
    action_code VARCHAR(100) NOT NULL,
    economic_version_id UUID NOT NULL REFERENCES economic_action_versions (id),
    reward_amount BIGINT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Partition-ready by created_at
CREATE INDEX idx_actor_actions_actor ON actor_actions (actor_id);

CREATE INDEX idx_actor_actions_content ON actor_actions (content_id);

CREATE INDEX idx_actor_actions_created ON actor_actions (created_at);

-- ── 7. Reward Batches ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS reward_batches (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4 (),
    content_id UUID NOT NULL,
    publisher_id UUID NOT NULL,
    action_code VARCHAR(100) NOT NULL,
    total_publisher_reward BIGINT NOT NULL DEFAULT 0,
    total_platform_fee BIGINT NOT NULL DEFAULT 0,
    total_treasury_cut BIGINT NOT NULL DEFAULT 0,
    action_count INTEGER NOT NULL DEFAULT 0,
    is_processed BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processed_at TIMESTAMPTZ,
    UNIQUE (
        content_id,
        action_code,
        is_processed
    )
);

-- For batch processor: SELECT ... FOR UPDATE SKIP LOCKED
CREATE INDEX idx_reward_batches_unprocessed ON reward_batches (is_processed, created_at)
WHERE
    is_processed = FALSE;

CREATE INDEX idx_reward_batches_publisher ON reward_batches (publisher_id);

-- ── 8. Processed Events (Idempotency) ────────────────────────
CREATE TABLE IF NOT EXISTS processed_events (
    event_id UUID PRIMARY KEY,
    event_type VARCHAR(100) NOT NULL,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- TTL cleanup: periodically DELETE WHERE processed_at < NOW() - INTERVAL '7 days'
CREATE INDEX idx_processed_events_time ON processed_events (processed_at);

-- ── 9. Balance Snapshots ─────────────────────────────────────
CREATE TABLE IF NOT EXISTS balance_snapshots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4 (),
    account_id UUID NOT NULL REFERENCES accounts (id),
    balance BIGINT NOT NULL,
    snapshot_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_balance_snapshots_account ON balance_snapshots (account_id, snapshot_at);

-- ── 10. Outbox Messages (Transactional Outbox Pattern) ───────
-- Events are written to this table inside the SAME transaction as
-- business data. A separate relay worker polls unsent rows, publishes
-- them to RabbitMQ, and marks them as sent. This guarantees at-least-once
-- delivery without two-phase commit.
CREATE TABLE IF NOT EXISTS outbox_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4 (),
    aggregate_type VARCHAR(100) NOT NULL, -- 'reward_event', 'batch_processed', 'action_config_changed'
    aggregate_id UUID NOT NULL, -- FK to the originating entity
    event_type VARCHAR(100) NOT NULL, -- routing key for RabbitMQ
    payload JSONB NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending', -- 'pending', 'sent', 'failed'
    retry_count INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 5,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sent_at TIMESTAMPTZ
);

-- Relay worker polls only unsent messages, ordered by creation time
CREATE INDEX idx_outbox_pending ON outbox_messages (status, created_at)
WHERE
    status = 'pending';

CREATE INDEX idx_outbox_failed ON outbox_messages (status, retry_count)
WHERE
    status = 'failed';