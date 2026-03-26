## Performing a Backup with pgBackRest

To run a backup using pgBackRest inside your Docker container (note: dependency on gdrive for full backups):

1. **Start your container as usual**

2. **Run the backup command:**

    Note for first time setup:
    - You'll have to create the stanza:
	```sh
	docker exec -it -u postgres fin-db-postgres pgbackrest --stanza=main stanza-create
	```

	- This will perform a backup (of type `full` or `incr`) using the configuration and paths set up in your container and volumes:
	```sh
	bash db/ops/backup.sh -t backup_type
	```

3. **Check backup status:**
	```sh
	docker exec -it -u postgres fin-db-postgres pgbackrest --stanza=main info
	```

## Restoring The Latest Backup

To restore your database from the latest backup using pgBackRest and Docker,
use the provided script for a safe, automated restore:

```
bash db/docker/restore.sh
```

- This script will:
	- Warn and ask for confirmation.
	- Stop your running Postgres container.
	- Load environment variables from your .env file.
	- Run the restore in a one-off container (using your backup and config volumes).
	- Fix permissions on /tmp/pgbackrest to avoid future errors.
	- Restart your main Postgres container.

- You can also provide `-b path/to/intermediate` to save a backup of the current database for
safety

## Editing pgBackRest Configuration

You can edit the pgBackRest configuration file at:

	 db/docker/pgbackrest.conf

This file is mounted into the container (see your `docker-compose.yaml`), so any changes you make will be picked up the next time you run a backup or restart the container.

## Docker Volume Permissions: Avoiding Permission Errors

When running Postgres and pgBackRest in Docker, you must ensure that all host-mounted directories (volumes) are owned by the same UID and GID as the user running the container process. Otherwise, you will encounter permission errors (e.g., "Permission denied" or "unable to open file").

### 1. Determine the UID and GID used by Postgres in your container

Run this command to check the UID/GID for the `postgres` user inside your running container:

```sh
docker exec -it fin-db-postgres bash -c "id postgres"
```

Example output:
```
uid=70(postgres) gid=70(postgres) groups=70(postgres)
```

This means you should use UID 70 and GID 70 for all host-mounted directories.

### 2. Recursively chown all host-mounted directories to match

Replace `/path/to/postgres/data`, `/path/to/pgbackrest` (backup location), and `/path/to/pgbackrest.conf` with the actual paths you use in your `docker-compose.yaml` volumes section.

```sh
sudo chown -R 70:70 /path/to/postgres/data
sudo chown -R 70:70 /path/to/pgbackrest
sudo chmod -R a+rx/mnt/wd_elements/findb_pgbackrest
sudo chown 70:70 /path/to/pgbackrest.conf
```

In order, this:
- Changes ownership of `/path/to/postgres/data` to 70:70 (postgres)
- Changes ownership of `/path/to/pgbackrest` to 70:70 (postgres)
- Allows all users to read and list access to `/path/to/pgbackrest` (needed for gdrive backup)
- Changes ownership of `/path/to/pgbackrest.conf` to 70:70 (postgres)

Do this for every directory or file you mount into the container.

### 3. Restart your container

```sh
docker compose down
docker compose up -d
```

### Why is this necessary?

Docker does not automatically fix permissions on host-mounted volumes. If the files/directories are not owned by the container's user, Postgres and pgBackRest will not be able to read/write as needed, causing errors.

**Always match host-side ownership to the container's UID/GID for reliable operation.**
