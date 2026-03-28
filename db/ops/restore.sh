#!/bin/bash

set -e

usage() {
  echo "Usage: $0 <YYYY-MM-DD> [HH:MM:SS] [-b backup_location] [-r]"
  echo "  - YYYY-MM-DD: Required. The date to restore to."
  echo "  - HH:MM:SS: Optional. The time to restore to. If not provided, defaults to 00:00:00 (the start of the day)."
  echo "  -b backup_location: Optional. If provided, a manual backup of the current data directory will be saved to this location before the restore."
  echo "  -r: Optional. If provided, the Postgres container will be left in recovery mode after the restore."
  exit 1
}

# ====================================================== PARSE ARGUMENTS ======================================================
BACKUP_LOCATION=""
RECOVERY=""
TARGET_DATE=""
TARGET_TIME=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    -b) BACKUP_LOCATION="$2"; shift 2 ;;
    -r) RECOVERY="true"; shift ;;
    -b=*) BACKUP_LOCATION="${1#*=}"; shift ;;
    --) shift; break ;;
    -*) echo "Unknown option: $1"; usage ;;
    *)
      if [[ -z "$TARGET_DATE" ]]; then
        TARGET_DATE="$1"
      elif [[ -z "$TARGET_TIME" ]]; then
        TARGET_TIME="$1"
      else
        echo "Unexpected argument: $1"; usage
      fi
      shift
      ;;
  esac
done

TARGET_TIME="${TARGET_TIME:-00:00:00}"

[ -n "$TARGET_DATE" ] || usage

if ! [[ "$TARGET_DATE" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
  echo "Error: Invalid date format. Expected YYYY-MM-DD."
  exit 1
fi

if ! [[ "$TARGET_TIME" =~ ^[0-9]{2}:[0-9]{2}:[0-9]{2}$ ]]; then
  echo "Error: Invalid time format. Expected HH:MM:SS."
  exit 1
fi

TARGET="${TARGET_DATE} ${TARGET_TIME}"

echo "Target restore point: $TARGET"
echo "Backup location for current data directory (if specified): ${BACKUP_LOCATION:-None}"
echo "Leave Postgres in recovery mode after restore: ${RECOVERY:-No}"
echo ""

# ==================================================== CONFIRMATION PROMPT ====================================================

echo "WARNING: This will stop your running Postgres container and overwrite your database data directory with the latest backup! \
Please check restore settings above."

read -p "Are you sure you want to continue? (type 'y' to proceed): " confirm
if [[ "$confirm" != "y" ]]; then
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
if [ -f "$DB_DIR/ops/.env" ]; then
    set -a
    source "$DB_DIR/ops/.env"
    set +a
else
    echo "ERROR: .env file not found in db directory."
    exit 1
fi

# ======================================== BACKUP CURRENT DATA DIRECTORY (IF SPECIFIED) =======================================
if [ -n "$BACKUP_LOCATION" ]; then
  echo "Creating manual backup of current data directory..."
  BACKUP_TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
  MANUAL_BACKUP_DIR="$BACKUP_LOCATION/manual_backup"
  mkdir -p "$MANUAL_BACKUP_DIR"
  sudo tar czf "$MANUAL_BACKUP_DIR/dbdata_before_restore_$BACKUP_TIMESTAMP.tar.gz" -C "${MOUNT_PATH}" .
  echo "Manual backup of current data directory saved to $MANUAL_BACKUP_DIR"
fi

# =============================== RESTORE FROM BACKUP USING PGBACKREST IN A TEMPORARY CONTAINER ===============================
echo "Restoring from backup..."
docker run --rm -it \
    -v "${PGBACKREST_BACKUP_PATH}:/var/lib/pgbackrest" \
    -v "${PGBACKREST_CONF}:/etc/pgbackrest/pgbackrest.conf" \
    -v "${MOUNT_PATH}:/var/lib/postgresql" \
    --user 70:70 \
    db-postgres-pgbackrest sh -c "pgbackrest --stanza=main restore --delta --type=time --target=\"$TARGET\" && chown -R 70:70 /tmp/pgbackrest"

echo "Restore complete."

# ========================= START POSTGRES CONTAINER AND PROMOTE TO PRIMARY (IF NOT IN RECOVERY MODE) =========================
docker start fin-db-postgres
echo "Postgres container started."
if [ -n "$RECOVERY" ]; then
  echo "Postgres is in recovery mode. To promote it to primary, run the following command:"
  echo "- docker exec -it -u postgres fin-db-postgres pg_ctl promote"
else
  docker exec -it -u postgres fin-db-postgres pg_ctl promote
  echo "Postgres database promoted to primary."
fi
