#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   ./db/migrations/run.sh 001
#   ./db/migrations/run.sh 001 002
#   ./db/migrations/run.sh all
#
# Optional:
#   ENV_FILE=db/.env ./db/migrations/run.sh 001

# Repo root assumed as current working directory
ENV_FILE="${ENV_FILE:-db/.env}"

if [ -f "$ENV_FILE" ]; then
  set -a
  . "$ENV_FILE"
  set +a
else
  echo "Missing env file: $ENV_FILE"
  exit 1
fi

if [ "$#" -lt 1 ]; then
  echo "Usage: $0 <all|prefix...>"
  exit 1
fi

for arg in "$@"; do
  if [[ "$arg" == 000* ]]; then
    echo "Refusing to run bootstrap via run.sh."
    echo "Run bootstrap manually as admin:"
    exit 1
  fi
done

run_file() {
  local file="$1"
  echo "==> Running $file"
  psql "host=$DB_HOST port=$DB_PORT user=$DBUSER_ADMIN dbname=$DB_NAME" \
    -v ON_ERROR_STOP=1 \
    -f "$file"
}

if [ "$1" = "all" ]; then
  files=$(ls -1 db/migrations/[0-9][0-9][0-9]_*.sql 2>/dev/null | grep -v '/000_' || true)

  if [ -z "$files" ]; then
    echo "No migration files found."
    exit 1
  fi

  while IFS= read -r f; do
    [ -n "$f" ] && run_file "$f"
  done <<EOF
$files
EOF
  exit 0
fi

for prefix in "$@"; do
  matches=$(ls -1 "db/migrations/${prefix}"_*.sql 2>/dev/null || true)

  if [ -z "$matches" ]; then
    echo "No migration found for prefix: $prefix"
    exit 1
  fi

  count=$(printf '%s\n' "$matches" | sed '/^$/d' | wc -l | tr -d ' ')
  if [ "$count" -gt 1 ]; then
    echo "Multiple migrations found for prefix: $prefix"
    printf '%s\n' "$matches"
    exit 1
  fi

  run_file "$matches"
done