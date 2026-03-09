-- Upgrade: add_treasury_account
-- Created: 2026-03-09 17:36:42

CREATE UNIQUE INDEX uniq_accounts_owner_currency ON accounts (owner_type, currency, user_id);

INSERT INTO
    accounts (
        id,
        owner_type,
        currency,
        balance,
        is_active
    )
VALUES (
        gen_random_uuid (),
        'treasury',
        'TMT',
        1000000,
        true
    )
ON CONFLICT (owner_type, currency, user_id) DO
UPDATE
SET
    balance = EXCLUDED.balance;