#!/bin/bash

set -e

# Parse optional -b argument
BACKUP_LOCATION=""
while getopts "b:" opt; do
  case $opt in
    b) BACKUP_LOCATION="$OPTARG" ;;
    *) echo "Usage: $0 [-b backup_location]"; exit 1 ;;
  esac
done

echo "WARNING: This will stop your running Postgres container and overwrite your database data directory with the latest backup!"
if [ -n "$BACKUP_LOCATION" ]; then
  echo "A manual backup of the current data directory will be saved to $BACKUP_LOCATION before the restore."
  else
  echo "If you want to create a manual backup of the current data directory before restoring, run this script with the -b option followed by the backup location (e.g. $0 -b /path/to/backup)."
fi
read -p "Are you sure you want to continue? (type YES to proceed): " confirm
if [[ "$confirm" != "YES" ]]; then
    echo "Aborted."
    exit 1
fi

# Get location
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DB_DIR="$SCRIPT_DIR/.."

# Stop the running Postgres container
docker stop fin-db-postgres || true
echo "Postgres container stopped."

# Load environment variables
if [ -f "$DB_DIR/.env" ]; then
    set -a
    source "$DB_DIR/.env"
    set +a
else
    echo "ERROR: .env file not found in db directory."
    exit 1
fi

# If backup location is provided, make a manual backup
if [ -n "$BACKUP_LOCATION" ]; then
  echo "Creating manual backup of current data directory..."
  BACKUP_TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
  MANUAL_BACKUP_DIR="$BACKUP_LOCATION/manual_backup"
  mkdir -p "$MANUAL_BACKUP_DIR"
  sudo tar czf "$MANUAL_BACKUP_DIR/dbdata_before_restore_$BACKUP_TIMESTAMP.tar.gz" -C "${MOUNT_PATH}" .
  echo "Manual backup of current data directory saved to $MANUAL_BACKUP_DIR"
fi

# Run the restore in a one-off container and fix /tmp/pgbackrest permissions
echo "Restoring from backup..."
docker run --rm -it \
    -v "${PGBACKREST_BACKUP_PATH}:/var/lib/pgbackrest" \
    -v "${PGBACKREST_CONF}:/etc/pgbackrest/pgbackrest.conf" \
    -v "${MOUNT_PATH}:/var/lib/postgresql/data" \
    --user 70:70 \
    db-postgres-pgbackrest sh -c "pgbackrest --stanza=main restore && chown -R 70:70 /tmp/pgbackrest"

echo "Restore complete."

# Start the Postgres container again
docker start fin-db-postgres
echo "Postgres container started."
