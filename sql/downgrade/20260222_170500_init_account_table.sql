-- Downgrade: init_account_table
-- Created: 2026-02-22 17:05:00

DROP INDEX IF EXISTS idx_accounts_active;

DROP INDEX IF EXISTS idx_accounts_owner_id;

DROP TABLE IF EXISTS accounts;