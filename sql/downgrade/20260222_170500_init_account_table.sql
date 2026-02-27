-- Downgrade: add_ledger_entries_table
-- Created: 2026-02-23 15:03:21

DROP INDEX IF EXISTS idx_accounts_active;

DROP INDEX IF EXISTS idx_accounts_user_id;

DROP TABLE IF EXISTS accounts;

ALTER TABLE accounts DROP CONSTRAINT balance_non_negative;