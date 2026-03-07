-- Use the `template.sql` file to create `sandbox.sql` to test SQL queries/migrations.
-- You can then use `run.sh` file to conveniently run this file!
-- By default, it uses the migrator role, so be careful future me :)

\pset pager off
\pset border 2
\pset linestyle ascii
\pset null '<NULL>'
\x auto
\timing on
\set ON_ERROR_STOP on

BEGIN;

\echo '---------------------- Your SQL statements here ----------------------'

ROLLBACK;
