-- Downgrade: add_ledger_entries_table
-- Created: 2026-02-26 18:04:21

DROP INDEX IF EXISTS idx_ledger_account_created;

DROP INDEX IF EXISTS idx_ledger_reference;

DROP TABLE IF EXISTS ledger_entries;