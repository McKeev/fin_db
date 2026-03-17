-- This SQL file is used to bootstrap the database for the first time.
-- Run with `psql -f db/migrations/000_bootstrap.sql` to create the database and the associated roles.

-- Required psql variables:
--   DB_NAME
--   DBUSER_ADMIN
--   DBUSER_APP
--   DBUSER_READ
--   DBUSER_ADMIN_PASSWORD
--   DBUSER_APP_PASSWORD
--   DBUSER_READ_PASSWORD

SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = :'DB_NAME' AND pid <> pg_backend_pid();

DROP DATABASE IF EXISTS :"DB_NAME";
DROP ROLE IF EXISTS :"DBUSER_ADMIN";
DROP ROLE IF EXISTS :"DBUSER_APP";
DROP ROLE IF EXISTS :"DBUSER_READ";


-- --------------------------------------------------
-- Roles
-- --------------------------------------------------

CREATE ROLE :"DBUSER_ADMIN" LOGIN PASSWORD :'DBUSER_ADMIN_PASSWORD';
CREATE ROLE :"DBUSER_APP" LOGIN PASSWORD :'DBUSER_APP_PASSWORD';
CREATE ROLE :"DBUSER_READ" LOGIN PASSWORD :'DBUSER_READ_PASSWORD';


-- --------------------------------------------------
-- Create and connect to the database
-- --------------------------------------------------

CREATE DATABASE :"DB_NAME" OWNER :"DBUSER_ADMIN";
\connect :DB_NAME


-- --------------------------------------------------
-- Database access
-- --------------------------------------------------

REVOKE ALL ON DATABASE :"DB_NAME" FROM PUBLIC;

GRANT CONNECT ON DATABASE :"DB_NAME" TO :"DBUSER_APP";
GRANT CONNECT ON DATABASE :"DB_NAME" TO :"DBUSER_READ";


-- --------------------------------------------------
-- Schema permissions
-- --------------------------------------------------

REVOKE ALL ON SCHEMA public FROM PUBLIC;


-- app and reader can access schema objects
GRANT USAGE ON SCHEMA public TO :"DBUSER_APP";
GRANT USAGE ON SCHEMA public TO :"DBUSER_READ";

ALTER SCHEMA public OWNER TO :"DBUSER_ADMIN";


-- --------------------------------------------------
-- Default privileges (future tables)
-- --------------------------------------------------

ALTER DEFAULT PRIVILEGES FOR ROLE :"DBUSER_ADMIN"
IN SCHEMA public
GRANT SELECT, INSERT, UPDATE, DELETE
ON TABLES TO :"DBUSER_APP";

ALTER DEFAULT PRIVILEGES FOR ROLE :"DBUSER_ADMIN"
IN SCHEMA public
GRANT SELECT
ON TABLES TO :"DBUSER_READ";


-- --------------------------------------------------
-- Default privileges (future sequences)
-- --------------------------------------------------

ALTER DEFAULT PRIVILEGES FOR ROLE :"DBUSER_ADMIN"
IN SCHEMA public
GRANT USAGE, SELECT
ON SEQUENCES TO :"DBUSER_APP";

ALTER DEFAULT PRIVILEGES FOR ROLE :"DBUSER_ADMIN"
IN SCHEMA public
GRANT SELECT
ON SEQUENCES TO :"DBUSER_READ";