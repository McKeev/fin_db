# Database

## Overview

Migration order:

1. `000_bootstrap.sql` (one-time, destructive bootstrap)
2. `001_initial_schema.sql` (core schema)
3. `002_first_ingest.sql` (initial data load)
4. `003_canonical_view.sql` (canonical prioritized view)

---

## Docker Setup (`docker-compose`)

### 1) Create env file

```bash
cp db/ops/.env.example db/ops/.env
```

Edit `db/ops/.env` and set at minimum:

- `MOUNT_PATH` (host path for persistent Postgres data)
- `POSTGRES_PASSWORD`
- role passwords (`DBUSER_ADMIN_PASSWORD`, `DBUSER_APP_PASSWORD`, `DBUSER_READ_PASSWORD`)

### 2) Start Postgres

```bash
cd db/ops && docker compose up -d
```

---

## Credentials

Use `~/.pgpass` for local password management so `psql` and scripts can run without interactive prompts.

---

## Migrations

### `000_bootstrap.sql`

Purpose: first-time database bootstrap and role setup.

What it does:

- Terminates active connections to target DB
- Drops and recreates database and roles
- Sets schema ownership and permissions
- Configures default table/sequence privileges for app/read roles

Notes:

- Destructive by design
- Must be run manually as superuser (`postgres`)
- Intentionally blocked by `db/migrations/run.sh`

### `001_initial_schema.sql`

Purpose: creates the core relational schema.

What it does:

- Creates core tables: `instruments`, `identifiers`, `instrument_attributes`, `observations`, `sources`, `updates`,
`ingest_failures`, 
- Adds primary keys and foreign keys
- Adds lookup/performance indexes (identifiers, observations, updates)

### `002_first_ingest.sql`

Purpose: initial load of seed and bootstrap data from CSV files.

What it does:

- Creates temp staging tables for equities and observations
- Loads CSV inputs from `db/initial_setup/equities_final.csv` and `data/bootstrap_data.csv`
- Seeds `sources`
- Inserts `instruments`, `identifiers`, and `instrument_attributes`
- Inserts `observations` by mapping source identifiers to `instrument_id`
- Seeds `updates` for daily ingestion workflow
- Outputs row counts for validation

### `003_canonical_view.sql`

Purpose: creates canonical read view across multiple data sources.

What it does:

- Creates/replaces `canonical_obs`
- Selects one row per `(instrument_id, field, date)`
- Chooses source by `sources.priority` (`lower number = higher priority`)

---

## Running Migrations

### First-time bootstrap (manual)

```bash
set -a
. db/ops/.env
set +a

psql "host=$DB_HOST port=$DB_PORT user=postgres dbname=postgres" \
	-v DB_NAME="$DB_NAME" \
	-v DBUSER_ADMIN="$DBUSER_ADMIN" \
	-v DBUSER_APP="$DBUSER_APP" \
	-v DBUSER_READ="$DBUSER_READ" \
	-v DBUSER_ADMIN_PASSWORD="$DBUSER_ADMIN_PASSWORD" \
	-v DBUSER_APP_PASSWORD="$DBUSER_APP_PASSWORD" \
	-v DBUSER_READ_PASSWORD="$DBUSER_READ_PASSWORD" \
	-f db/migrations/000_bootstrap.sql
```

### Normal migrations

Run one migration:

```bash
bash db/migrations/run.sh 001
```

Run multiple specific migrations:

```bash
bash db/migrations/run.sh 001 002 003
```

Run all non-bootstrap migrations:

```bash
bash db/migrations/run.sh all
```

Use alternate env file:

```bash
ENV_FILE=db/ops/.env bash db/migrations/run.sh all
```

---

## Notes

- `identifiers.ticker` is the actively used display/API ticker; for equities this should currently align with the yfinance ticker.
- `run.sh` intentionally refuses `000*` migrations.
- Use `db/sandbox/` for ad-hoc SQL experiments.