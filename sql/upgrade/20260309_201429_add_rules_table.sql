-- Upgrade: add_rules_table
-- Created: 2026-03-09 20:14:29

CREATE TABLE IF NOT EXISTS rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid (),
    event_code VARCHAR(128) NOT NULL UNIQUE,
    description TEXT,
    conditions JSONB NOT NULL DEFAULT '{}',
    actions JSONB NOT NULL DEFAULT '{}',
    priority INT NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    expired_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_rules_active ON rules (is_active)
WHERE
    is_active = TRUE;

-- Seed: official rule
-- direction = -1 (debit), min_balance = 200, currency TMT, expires in 30 days
INSERT INTO
    rules (
        event_code,
        description,
        conditions,
        actions,
        priority,
        expired_at
    )
VALUES (
        'official',
        'Official event — debit with min balance check',
        '{"min_balance": 200}'::jsonb,
        '{"direction": -1, "currency": "TMT"}'::jsonb,
        10,
        NOW() + INTERVAL '30 days'
    )
ON CONFLICT (event_code) DO NOTHING;

-- Seed: repost rule
-- direction = 1 (credit), reward = 3, currency TMT, role = [official, simple]
INSERT INTO
    rules (
        event_code,
        description,
        conditions,
        actions,
        priority
    )
VALUES (
        'repost',
        'Repost event — credit reward with role check',
        '{"role_required": ["official", "simple"]}'::jsonb,
        '{"direction": 1, "currency": "TMT", "reward": 3}'::jsonb,
        10
    )
ON CONFLICT (event_code) DO NOTHING;