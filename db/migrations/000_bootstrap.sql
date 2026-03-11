-- This SQL file is used to bootstrap the database for the first time.
-- Run with `psql -f db/migrations/000_bootstrap.sql` to create the database and the migrator role.

-- CHANGE PASSWORD for the migrator role before running this file!!!!!!!!!!
CREATE DATABASE fin_db;

CREATE ROLE fin_db_migrator LOGIN PASSWORD 'CHANGE ME';

\connect fin_db

GRANT CONNECT, TEMP ON DATABASE fin_db TO fin_db_migrator;
GRANT USAGE, CREATE ON SCHEMA public TO fin_db_migrator;

GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO fin_db_migrator;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO fin_db_migrator;

ALTER DEFAULT PRIVILEGES FOR ROLE fin_db_migrator IN SCHEMA public
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO fin_db_migrator;

ALTER DEFAULT PRIVILEGES FOR ROLE fin_db_migrator IN SCHEMA public
GRANT USAGE, SELECT ON SEQUENCES TO fin_db_migrator;