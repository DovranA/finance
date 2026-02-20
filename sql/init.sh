#!/bin/bash
# ── Database Bootstrap Script ────────────────────────────────
# Applies the SQL schema to the finance database.
# Usage: ./sql/init.sh
# Expects POSTGRES_* environment variables to be set.

set -euo pipefail

PGHOST="${POSTGRES_HOST:-localhost}"
PGPORT="${POSTGRES_PORT:-5432}"
PGDATABASE="${POSTGRES_DB:-finance_db}"
PGUSER="${POSTGRES_USER:-finance_user}"

echo "Applying schema to ${PGDATABASE}@${PGHOST}:${PGPORT}..."
psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -f /app/sql/001_schema.sql
echo "Schema applied successfully."
