-- Downgrade: init_schema
-- Drop all tables in reverse dependency order

DROP TABLE IF EXISTS outbox_messages CASCADE;

DROP TABLE IF EXISTS balance_snapshots CASCADE;

DROP TABLE IF EXISTS processed_events CASCADE;

DROP TABLE IF EXISTS reward_batches CASCADE;

DROP TABLE IF EXISTS actor_actions CASCADE;

DROP TABLE IF EXISTS economic_action_versions CASCADE;

DROP TABLE IF EXISTS economic_actions CASCADE;

DROP TRIGGER IF EXISTS trg_ledger_immutable ON ledger_entries;

DROP FUNCTION IF EXISTS prevent_ledger_mutation ();

DROP TABLE IF EXISTS ledger_entries CASCADE;

DROP TABLE IF EXISTS treasury_account CASCADE;

DROP TABLE IF EXISTS accounts CASCADE;