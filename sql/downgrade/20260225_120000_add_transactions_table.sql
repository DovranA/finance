-- Downgrade: add_transactions_table
-- Created: 2026-02-27 12:00:00

DROP INDEX IF EXISTS idx_transactions_status;

DROP INDEX IF EXISTS idx_transactions_expires;

DROP INDEX IF EXISTS idx_transactions_key;

DROP TABLE IF EXISTS transactions;