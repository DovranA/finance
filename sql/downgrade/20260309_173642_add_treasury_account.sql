-- Downgrade: add_treasury_account
-- Created: 2026-03-09 17:36:42

DELETE FROM accounts
WHERE
    currency = 'TMT'
    and owner_type = 'treasury';

DROP INDEX IF EXISTS uniq_accounts_owner_currency;