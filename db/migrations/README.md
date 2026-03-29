# Migrations

## Overview

- `000_bootstrap.sql` is first-time admin setup.
- `001_*.sql`, `002_*.sql`, ... are normal schema/data migrations.
- `run.sh` is the normal migration runner (uses admin role and `db/ops/.env`).

## Prerequisites

- Postgres is running.
- `db/ops/.env` exists with the template from `db/ops/.env.example`

- Password is stored in `~/.pgpass` (recommended).

## First-Time Setup

Run bootstrap manually as admin from project root (not via `run.sh`):

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

Why: bootstrap includes admin operations (database/role setup).

## Run Normal Migrations

Run one migration by prefix:

```bash
bash db/migrations/run.sh 001
```

Run specific multiple migrations:

```bash
bash db/migrations/run.sh 001 002
```

Run all normal migrations:

```bash
bash db/migrations/run.sh all
```

Use another env file:

```bash
ENV_FILE=db/ops/.env bash db/migrations/run.sh 001
```

## Notes

- `run.sh` intentionally blocks `000*` bootstrap files.
- Keep bootstrap credentials out of committed files when possible.
- For experiments, use `db/sandbox/sandbox.sql` with `BEGIN ... ROLLBACK`.

## Migrations


### `005_add_unit_support.sql`

Purpose: adds support for value scaling and currency/unit handling.

What it does:

- Adds `fields` and `units` tables for value scaling and unit/currency normalization
- Drops `scale` from `observations` and moves scale logic to new tables
- Adds USD instrument and system source for currency normalization
- Adds constraints and indexes for new relationships
- Rebuilds `canonical_obs` view and creates `units_ts` materialized view for unit time series
- Adds `time_series_usd` view for normalized values in USD

---

### `004_reorg_tickers.sql`

Purpose: reorganizes identifier storage and adds internal ticker to instruments.

What it does:

- Adds `internal_ticker` column to `instruments` and populates it from `identifiers.ticker`
- Sets `internal_ticker` as NOT NULL and UNIQUE
- Reformats `identifiers` table to long form with columns: `instrument_id`, `source`, `ext_id`
- Adds ISIN as a source and migrates ISIN, RIC, YFIN, ETORO to the modified `identifiers` table
- Adds index on `(source, ext_id)` for fast lookup
- Cleans up any legacy `identifier` column in `sources`

---

### `003_canonical_view.sql`

Purpose: creates canonical read view across multiple data sources.

What it does:

- Creates/replaces `canonical_obs`
- Selects one row per `(instrument_id, field, date)`
- Chooses source by `sources.priority` (`lower number = higher priority`)

---

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

---

### `001_initial_schema.sql`

Purpose: creates the core relational schema.

What it does:

- Creates core tables: `instruments`, `identifiers`, `instrument_attributes`, `observations`, `sources`, `updates`,
  `ingest_failures`
- Adds primary keys and foreign keys
- Adds lookup/performance indexes (identifiers, observations, updates)

---

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

