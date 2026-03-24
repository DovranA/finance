-- Downgrade: add_treasury_account
-- Created: 2026-03-09 17:36:42

-- Remove ledger entries and transactions referencing the treasury account
DELETE FROM ledger_entries
WHERE
    account_id IN (
        SELECT id
        FROM accounts
        WHERE
            currency = 'TOKEN'
            AND owner_type = 'treasury'
    );

DELETE FROM transactions
WHERE
    reference_id IN (
        SELECT id::text
        FROM accounts
        WHERE
            currency = 'TOKEN'
            AND owner_type = 'treasury'
    );

DELETE FROM accounts
WHERE
    currency = 'TOKEN'
    AND owner_type = 'treasury';

DROP INDEX IF EXISTS uniq_accounts_owner_currency;