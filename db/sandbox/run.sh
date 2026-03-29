#!/usr/bin/env bash
set -euo pipefail

# Retrieve assumed ENV_FILE from db/ops/.env
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${ENV_FILE:-$SCRIPT_DIR/../ops/.env}"

# Sandbox script
SANDBOX="${SANDBOX:-$SCRIPT_DIR/sandbox.sql}"

if [ -f "$ENV_FILE" ]; then
  set -a
  . "$ENV_FILE"
  set +a
else
  echo "Missing env file: $ENV_FILE"
  exit 1
fi

# Optional fallbacks if not set in env file
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5433}"
DB_NAME="${DB_NAME:-fin_db}"
DBUSER_MIGRATOR="${DBUSER_MIGRATOR:-fin_db_migrator}"

psql "host=$DB_HOST port=$DB_PORT user=$DBUSER_ADMIN dbname=$DB_NAME" \
  -v ON_ERROR_STOP=1 \
  -f "$SANDBOX"