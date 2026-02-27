-- Downgrade: add_idempotency_keys_table
-- Created: 2026-02-27 12:00:00

DROP INDEX IF EXISTS idx_idempotency_keys_status;

DROP INDEX IF EXISTS idx_idempotency_keys_expires;

DROP INDEX IF EXISTS idx_idempotency_keys_key;

DROP TABLE IF EXISTS idempotency_keys;