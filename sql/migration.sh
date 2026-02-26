#!/bin/bash

# Directories for migrations
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
UPGRADE_DIR="${SCRIPT_DIR}/upgrade"
DOWNGRADE_DIR="${SCRIPT_DIR}/downgrade"

# Check if an argument is provided
if [ -z "$1" ]; then
  echo "Usage: $0 <migration_name>"
  exit 1
fi

# Migration name (first argument)
NAME="$1"

# Create directories if they don't exist
mkdir -p "$UPGRADE_DIR"
mkdir -p "$DOWNGRADE_DIR"

# Timestamp
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# File name
FILENAME="${TIMESTAMP}_${NAME}.sql"

# Create files with comment templates
echo "-- Upgrade: ${NAME}
-- Created: $(date '+%Y-%m-%d %H:%M:%S')
" > "${UPGRADE_DIR}/${FILENAME}"

echo "-- Downgrade: ${NAME}
-- Created: $(date '+%Y-%m-%d %H:%M:%S')
" > "${DOWNGRADE_DIR}/${FILENAME}"

echo "Created migration files:"
echo "  upgrade/${FILENAME}"
echo "  downgrade/${FILENAME}"