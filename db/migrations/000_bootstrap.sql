-- This SQL file is used to bootstrap the database for the first time.
-- Run with `psql -f db/migrations/000_bootstrap.sql` to create the database and the associated roles.

-- CHANGE PASSWORDS for the roles before running this file!!!!!!!!!!

SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = 'fin_db' AND pid <> pg_backend_pid();

DROP DATABASE IF EXISTS fin_db;
DROP ROLE IF EXISTS fin_db_admin;
DROP ROLE IF EXISTS fin_db_app;
DROP ROLE IF EXISTS fin_db_reader;


-- --------------------------------------------------
-- Roles
-- --------------------------------------------------

CREATE ROLE fin_db_admin LOGIN PASSWORD '***';
CREATE ROLE fin_db_app LOGIN PASSWORD '***';
CREATE ROLE fin_db_reader LOGIN PASSWORD '***';


-- --------------------------------------------------
-- Create and connect to the database
-- --------------------------------------------------

CREATE DATABASE fin_db OWNER fin_db_admin;
\connect fin_db


-- --------------------------------------------------
-- Database access
-- --------------------------------------------------

REVOKE ALL ON DATABASE fin_db FROM PUBLIC;

GRANT CONNECT ON DATABASE fin_db TO fin_db_app;
GRANT CONNECT ON DATABASE fin_db TO fin_db_reader;


-- --------------------------------------------------
-- Schema permissions
-- --------------------------------------------------

REVOKE ALL ON SCHEMA public FROM PUBLIC;


-- app and reader can access schema objects
GRANT USAGE ON SCHEMA public TO fin_db_app;
GRANT USAGE ON SCHEMA public TO fin_db_reader;

ALTER SCHEMA public OWNER TO fin_db_admin;


-- --------------------------------------------------
-- Default privileges (future tables)
-- --------------------------------------------------

ALTER DEFAULT PRIVILEGES FOR ROLE fin_db_admin
IN SCHEMA public
GRANT SELECT, INSERT, UPDATE, DELETE
ON TABLES TO fin_db_app;

ALTER DEFAULT PRIVILEGES FOR ROLE fin_db_admin
IN SCHEMA public
GRANT SELECT
ON TABLES TO fin_db_reader;


-- --------------------------------------------------
-- Default privileges (future sequences)
-- --------------------------------------------------

ALTER DEFAULT PRIVILEGES FOR ROLE fin_db_admin
IN SCHEMA public
GRANT USAGE, SELECT
ON SEQUENCES TO fin_db_app;

ALTER DEFAULT PRIVILEGES FOR ROLE fin_db_admin
IN SCHEMA public
GRANT SELECT
ON SEQUENCES TO fin_db_reader;