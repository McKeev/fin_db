# Migrations

## Overview

- `000_bootstrap.sql` is first-time admin setup.
- `001_*.sql`, `002_*.sql`, ... are normal schema/data migrations.
- `run.sh` is the normal migration runner (uses admin role and `db/.env.local`).

## Prerequisites

- Postgres is running.
- `db/.env.local` exists with:

```bash
DB_HOST=localhost
DB_PORT=5432
DB_NAME=fin_db
DBUSER_ADMIN=fin_db_admin
```

- Password is stored in `~/.pgpass` (recommended).

## First-Time Setup

Run bootstrap manually as admin (not via `run.sh`):

```bash
psql -d postgres -f db/migrations/000_bootstrap.sql
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
ENV_FILE=db/.env.local bash db/migrations/run.sh 001
```

## Notes

- `run.sh` intentionally blocks `000*` bootstrap files.
- Keep bootstrap credentials out of committed files when possible.
- For experiments, use `db/sandbox/sandbox.sql` with `BEGIN ... ROLLBACK`.