\pset pager off
\pset border 2
\pset linestyle ascii
\pset null '<NULL>'
\x auto
\timing on
\set ON_ERROR_STOP on

BEGIN;

\echo '------------------------ Staging the CSV data ------------------------'
-- Create a temporary staging table to load the equities CSV data
CREATE TEMP TABLE staging_equities (
    instrument_id CHAR(20) PRIMARY KEY,
    name TEXT,
    isin TEXT,
    yfinance_ticker TEXT,
    etoro_ticker TEXT,
    ric TEXT,
    exchange TEXT,
    country_hq TEXT,
    currency TEXT,
    gics_code TEXT
) ON COMMIT DROP;

-- Load data from the CSV file into the staging table
\copy staging_equities (instrument_id, name, isin, yfinance_ticker, etoro_ticker, ric, exchange, country_hq, currency, gics_code) FROM 'initial_setup/equities_final.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');

-- Create a temporary staging table to load the observations CSV data
CREATE TEMP TABLE staging_observations (
    date DATE,
    ric TEXT,
    source TEXT,
    field TEXT,
    scale NUMERIC,
    value NUMERIC
) ON COMMIT DROP;

-- Load data from the CSV file into the staging table
\copy staging_observations (date, ric, source, field, scale, value) FROM 'data/lseg_data.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');

\echo '---------------- Insert data into `instruments` table ----------------'
INSERT INTO instruments
SELECT
    instrument_id,
    name,
    -- needs to fill to `equity`
    'equity' AS asset_class,
    currency AS unit
FROM staging_equities;

\echo '---------------- Insert data into `identifiers` table ----------------'
INSERT INTO identifiers
SELECT
    instrument_id,
    yfinance_ticker AS ticker, -- More info on this in readme
    isin,
    ric,
    yfinance_ticker AS yfin,
    NULL as etoro -- Fill in later when I add etoro support
FROM staging_equities;

\echo '----------- Insert data into `instrument_attributes` table -----------'
INSERT INTO instrument_attributes
-- Create CTE of wide version of the data
WITH sample AS (
    SELECT instrument_id, gics_code, country_hq, exchange
    FROM staging_equities
)
SELECT
    instrument_id,
    field_name,
    field_value
FROM sample
-- Unpivot the data
CROSS JOIN LATERAL (
    VALUES
        ('gics_code', gics_code),
        ('country_hq', country_hq),
        ('exchange', exchange)
) AS v(field_name, field_value);

\echo '--------------- Insert data into `observations` table ----------------'
INSERT INTO observations
SELECT
    i.instrument_id,
    o.field,
    o.date,
    o.source,
    o.value,
    o.scale
FROM staging_observations AS o
JOIN identifiers AS i -- Use join to replace ric with instrument_id
USING(ric)
WHERE o.value IS NOT NULL; -- Filter out null values

\echo '----------------- Insert data into `updates` table -------------------'
INSERT INTO updates
SELECT DISTINCT
    instrument_id,
    field,
    'daily' AS frequency,
    CURRENT_TIMESTAMP AS last_update,
    'YAHOO' AS source
FROM observations;

\echo '------------ Provide feedback on length of filled tables -------------'
-- Length of each table after insert
SELECT
    'instruments' AS table_name,
    COUNT(*) AS row_count
FROM instruments
UNION ALL
SELECT
    'identifiers' AS table_name,
    COUNT(*) AS row_count
FROM identifiers
UNION ALL
SELECT
    'instrument_attributes' AS table_name,
    COUNT(*) AS row_count
FROM instrument_attributes
UNION ALL
SELECT
    'observations' AS table_name,
    COUNT(*) AS row_count
FROM observations
UNION ALL
SELECT
    'updates' AS table_name,
    COUNT(*) AS row_count
FROM updates;

COMMIT;
