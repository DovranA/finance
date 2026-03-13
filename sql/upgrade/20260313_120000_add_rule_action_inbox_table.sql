-- Upgrade: add_rule_action_inbox_table
-- Created: 2026-03-13 12:00:00

CREATE TABLE IF NOT EXISTS rule_action_inbox (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid (),
    event_id UUID NOT NULL UNIQUE,
    event_code VARCHAR(128) NOT NULL,
    user_id UUID NOT NULL,
    role VARCHAR(64),
    metadata JSONB NOT NULL DEFAULT '{}',
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processed_at TIMESTAMPTZ
);

CREATE INDEX idx_rule_action_inbox_status_created ON rule_action_inbox (status, created_at);

CREATE INDEX idx_rule_action_inbox_event_code ON rule_action_inbox (event_code);