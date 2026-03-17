#!/usr/bin/env bash
set -euo pipefail

# Repo root assumed as current working directory
ENV_FILE="${ENV_FILE:-db/.env.local}"

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
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-fin_db}"
DBUSER_MIGRATOR="${DBUSER_MIGRATOR:-fin_db_migrator}"

psql "host=$DB_HOST port=$DB_PORT user=$DBUSER_ADMIN dbname=$DB_NAME" \
  -v ON_ERROR_STOP=1 \
  -f db/sandbox/sandbox.sql