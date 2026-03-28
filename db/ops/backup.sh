#!/bin/bash

set -e

# Get case
BACKUP_TYPE='incr'
while getopts "t:" opt; do
  case $opt in
    t) if [[ "$OPTARG" != "full" && "$OPTARG" != "incr" ]]; then
            echo "Invalid backup type. Use 'full' or 'incr'."| tee -a "$BACKUP_LOG"
            exit 1
        fi
        BACKUP_TYPE="$OPTARG" ;;
    *) echo "Usage: $0 [-type backup_type]"| tee -a "$BACKUP_LOG"; exit 1 ;;
  esac
done

# Load needed variables
if [ -f "$(dirname "$0")/.env" ]; then
    set -a
    source "$(dirname "$0")/.env"
    set +a
else
    echo "$(date): ERROR: .env file not found in db/ops directory." | tee -a "$BACKUP_LOG"
    exit 1
fi

printf "\n\n" >> "$BACKUP_LOG"  # Add spacing between backup runs in log file

# ===================================== INCR BACKUP =======================================
if [ "$BACKUP_TYPE" == "incr" ]; then
    # Check if docker is up and do incremental backup
    printf "=========================================================================" \
    | tee -a "$BACKUP_LOG"
    printf "\n==================== Incremental Backup ($(date +"%Y-%m-%d")) ====================" \
    | tee -a "$BACKUP_LOG"
    printf "\n=========================================================================\n" \
    | tee -a "$BACKUP_LOG"
    echo "$(date): Starting incremental pgBackRest backup..." | tee -a "$BACKUP_LOG"
    if docker ps | grep -q fin-db-postgres; then
        docker exec -u postgres fin-db-postgres pgbackrest --stanza=$STANZA backup --type=incr
    else
        echo "$(date): ERROR: Docker container is not running." | tee -a "$BACKUP_LOG"
        exit 1
    fi

    # 2. Check if the backup was successful
    if [ $? -eq 0 ]; then
        echo "$(date): Incremental backup successful." | tee -a "$BACKUP_LOG"
    else
        echo "$(date): ERROR: pgBackRest backup failed." | tee -a "$BACKUP_LOG"
        exit 1
    fi


# ===================================== FULL BACKUP ========================================
else
    printf "=========================================================================" \
    | tee -a "$BACKUP_LOG"
    printf "\n======================== Full Backup ($(date +"%Y-%m-%d")) =======================" \
    | tee -a "$BACKUP_LOG"
    printf "\n=========================================================================\n" \
    | tee -a "$BACKUP_LOG"
    # Sync the repository to GDrive (before pgBackRest backup to get longer history of backups in GDrive)
    sudo chmod -R a+rx $PGBACKREST_BACKUP_PATH
    echo "$(date): Backing up to GDrive ($REMOTE)..." | tee -a "$BACKUP_LOG"
    if /usr/bin/rclone sync $PGBACKREST_BACKUP_PATH $REMOTE \
        --fast-list \
        --drive-use-trash=false \
        --transfers 4 \
        --drive-chunk-size 64M \
        --log-file $BACKUP_LOG \
        --log-level ERROR; then
        echo "$(date): GDrive sync complete." | tee -a "$BACKUP_LOG"
    else
        echo "$(date): ERROR: GDrive sync failed." | tee -a "$BACKUP_LOG"
        exit 1
    fi

    # Check if docker is up and do full backup
    echo "$(date): Starting full pgBackRest backup..." | tee -a "$BACKUP_LOG"
    if docker ps | grep -q fin-db-postgres; then
        docker exec -u postgres fin-db-postgres pgbackrest --stanza=$STANZA backup --type=full
    else
        echo "$(date): ERROR: Docker container is not running." | tee -a "$BACKUP_LOG"
        exit 1
    fi

    # 2. Check if the backup was successful
    if [ $? -eq 0 ]; then
        echo "$(date): Full backup successful." | tee -a "$BACKUP_LOG"
    else
        echo "$(date): ERROR: pgBackRest backup failed." | tee -a "$BACKUP_LOG"
        exit 1
    fi
fi