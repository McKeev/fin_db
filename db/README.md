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

To run the scripts and notebooks in `db/initial_setup/`, you need:

1. **Python 3.12**  
2. Install the optional dependencies for setup (including Refinitiv) via Poetry:

```bash
poetry install --with setup,refinitiv
```

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
- Get recent dbml `db2dbml postgres "postgresql://fin_db_admin@minicomp:5433/fin_db" -o db/schema.dbml`

## Migrations

### `007_portfolio_support.sql`

Purpose: adds portfolio activity storage and a holdings view.

What it does:

- Adds synthetic USD observations for every trading day used by the portfolio view
- Rebuilds `time_series_usd` to handle currency instruments correctly
- Creates a dedicated `transaction_type` enum for portfolio events
- Creates `portfolio_activity` to store broker transactions
- Builds `portfolio_holdings` to combine position activity and cash into a unified holdings view
- Adds lookup indexes for `time_series_usd` and portfolio holdings queries

---


### `006_support_currency_change.sql`

Purpose: supports currency/listing changes over time with effective-dated instrument units.

What it does:

- Adds `instrument_units` table to track unit history per instrument across date ranges
- Enforces non-overlapping effective date ranges per instrument for temporal integrity
- Backfills `instrument_units` from `instruments.unit` using each instrument's first observation date
- Rebuilds `time_series_usd` to resolve unit by `(instrument_id, date)` instead of static `instruments.unit`
- Materializes `time_series_usd` and adds lookup indexes for ticker/date and instrument/date query paths
- Drops `instruments.unit` after migrating unit responsibility to `instrument_units`

---


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

