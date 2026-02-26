DROP INDEX IF EXISTS idx_accounts_active;

DROP INDEX IF EXISTS idx_accounts_user_id;

DROP TABLE IF EXISTS accounts;

ALTER TABLE accounts DROP CONSTRAINT balance_non_negative;