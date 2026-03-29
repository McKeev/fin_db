-- =============================================================================
-- Migration: Add Unit and Field Support
-- =============================================================================
-- Purpose:
--   - Adds `fields` and `units` tables to support value scaling and currency/unit handling.
--   - Drops `scale` from `observations` and moves scale logic to new tables.
--   - Adds USD instrument and system source for currency normalization.
--   - Adds constraints and indexes for new relationships.
--   - Rebuilds `canonical_obs` view and creates `units_ts` materialized view for unit time series.
--   - Adds `time_series_usd` view for normalized values in USD.
--
-- Major changes:
--   * New tables: `fields`, `units`
--   * New/updated views: `canonical_obs`, `units_ts`, `time_series_usd`
--   * New constraints and indexes for referential integrity and performance
--
-- =============================================================================

\pset pager off
\pset border 2
\pset linestyle ascii
\pset null '<NULL>'
\x auto
\timing on
\set ON_ERROR_STOP on

BEGIN;

\echo '-------------------------- Create `fields` ---------------------------'
\echo 'Drop canonical_obs'
DROP VIEW canonical_obs;
\echo 'Drop scale from observations'
ALTER TABLE observations DROP COLUMN "scale";
\echo 'Create fields table and insert data'
CREATE TABLE "fields" (
    "name" varchar PRIMARY KEY,
    "scale" numeric(12, 4) NOT NULL,
    "fx_conversion" varchar
);
INSERT INTO fields (name, scale, fx_conversion)
VALUES
    ('close', 1, 'value'),
    ('totret', 0.01, 'change');;


\echo '--------------------------- Create `units` ---------------------------'
\echo 'Insert USD instrument'
INSERT INTO instruments (instrument_id, name, asset_class, unit, internal_ticker) 
VALUES ('CURUSDXUSDXXXXXXXXXX', 'United States Dollar', 'currency', 'USD', 'USDUSD');
INSERT INTO sources (name, priority) VALUES ('system', 0);
INSERT INTO observations (instrument_id, field, date, source, value)
VALUES (
    'CURUSDXUSDXXXXXXXXXX',
    'close',
    (SELECT date FROM observations ORDER BY date LIMIT 1),  -- Assign the date of the first observation in the table
    'system',
    100000
);

\echo 'Create the units table and populate'
CREATE TABLE "units" (
    "code" char(3) PRIMARY KEY,
    "scale" numeric(10, 7) NOT NULL,
    "instrument_id" char(20)
);
-- Add restrictions to `units`
ALTER TABLE units
ADD CONSTRAINT fk_instrument
FOREIGN KEY (instrument_id) REFERENCES instruments(instrument_id);
ALTER TABLE units
ADD CONSTRAINT unique_instrument
UNIQUE (code);

INSERT INTO units (code, scale, instrument_id)
SELECT 
    internal_ticker::varchar(3) AS code,  -- Takes first 3 from internal_ticker (EURUSD -> EUR)
    0.00001 AS scale,  -- We store currencies as pipette
    instrument_id
FROM instruments
WHERE asset_class = 'currency';

INSERT INTO units (code, scale, instrument_id)
VALUES ('GBp', 0.0000001, 'CURGBPXUSDXXXXXXXXXX');


\echo '-------------- Add new restrictions to affected tables ---------------'
ALTER TABLE observations
ADD CONSTRAINT fk_field
FOREIGN KEY (field) REFERENCES fields(name);

ALTER TABLE instruments
ADD CONSTRAINT fk_unit
FOREIGN KEY (unit) REFERENCES units(code);

CREATE INDEX idx_obs_field_date 
ON observations (field, date, instrument_id);  -- to optimize the new view we will create below

\echo '------------------ Re-create the canonical_obs view ------------------'
CREATE OR REPLACE VIEW canonical_obs AS
SELECT DISTINCT ON (o.instrument_id, o.field, o.date)
    o.instrument_id,
    o.field,
    o.date,
    o.value
FROM observations AS o
JOIN sources AS s
    ON o.source = s.name
ORDER BY
    o.instrument_id,
    o.field,
    o.date,
    s.priority NULLS LAST;  -- lower number = higher priority


\echo '-------------------- Create the units_ts m view ----------------------'
CREATE MATERIALIZED VIEW units_ts AS
WITH base_data AS (
    SELECT
        u.code,
        o.date,
        o.value * u.scale AS value
    FROM canonical_obs AS o
    JOIN units AS u  -- many to one join to associate each observation with it's unit
        ON o.instrument_id = u.instrument_id
    ),
    --   At this point, base data looks like this:
    --   +------+------------+----------------+
    --   | code |    date    |     value      |
    --   +------+------------+----------------+
    --   | USD  | 1979-12-31 | 1.000000000000 |
    --   | GBP  | 1979-12-31 | 2.225194570500 |
    --   | GBp  | 1979-12-31 | 0.022251945705 |
    --   | EUR  | 1979-12-31 | 1.508084082300 |
    --   | CHF  | 1979-12-31 | 0.626566416000 |
    --   +------+------------+----------------+
    --
    -- Now, let's add a column to measure change in value day-over-day for each currency
    with_changes AS (
        SELECT
            code,
            date,
            value,
            value / LAG(value) OVER (
                PARTITION BY code
                ORDER BY date
            ) AS change
        FROM base_data
    ),
    -- Create a timeseries of all dates in the dataset
    calendar AS (
        SELECT generate_series(
            (SELECT MIN(date) FROM base_data),
            (SELECT MAX(date) FROM base_data),
            '1 day'::interval
            )::date AS date
    ),
    -- Cross join calendar with distinct currency codes to create a complete grid of all dates and codes
    spine AS (
        SELECT u.code, c.date
        FROM calendar AS c
        CROSS JOIN (SELECT DISTINCT code FROM base_data) AS u
    ),
    -- Create groups of consecutive dates for each code, where we have observations. This will allow us to frontfill values within these groups
    spine_with_groups AS (
        SELECT
            s.code,
            s.date,
            w.value,
            w.change,
            COUNT(w.value) OVER (    -- COUNT ignores nulls naturally
                PARTITION BY s.code  -- so it only increments when a real
                ORDER BY s.date      -- observation exists, staying flat
            ) AS grp                 -- across gaps => same grp = same ffill group
        FROM spine AS s
        LEFT JOIN with_changes AS w
            ON s.code = w.code
            AND s.date = w.date
    )
    --   At this point, `spine_with_groups` looks like this:
    --   +------+------------+----------------+------------------------+-----+
    --   | code |    date    |     value      |         change         | grp |
    --   +------+------------+----------------+------------------------+-----+
    --   | AUD  | 1979-12-31 | 1.106580956100 |                 <NULL> |   1 |
    --   | AUD  | 1980-01-01 |         <NULL> |                 <NULL> |   1 |
    --   | AUD  | 1980-01-02 | 1.108512276900 | 1.00174530457022022846 |   2 |
    --   | AUD  | 1980-01-03 | 1.110000555000 | 1.00134259054321169152 |   3 |
    --   | AUD  | 1980-01-04 | 1.110112167000 | 1.00010055130107570081 |   4 |
    --   | AUD  | 1980-01-05 |         <NULL> |                 <NULL> |   4 |
    --   | AUD  | 1980-01-06 |         <NULL> |                 <NULL> |   4 |
    --   | AUD  | 1980-01-07 | 1.113816908000 | 1.00333726726913713756 |   5 |
    --   +------+------------+----------------+------------------------+-----+

-- Final: frontfill `value` and `change` = 1 for dates where we don't have observations
SELECT
    code,
    date,
    FIRST_VALUE(value) OVER (
        PARTITION BY code, grp
        ORDER BY date
    ) AS value,
    COALESCE(change, 1) AS change
FROM spine_with_groups
;
CREATE INDEX idx_units_ts_date_code ON units_ts (date, code);
GRANT MAINTAIN ON units_ts TO fin_db_app;

\echo '----------------------- Create time_series_usd -----------------------'
CREATE VIEW time_series_usd AS
SELECT
    i.internal_ticker,
    o.field,
    o.date,
    o.value * CASE 
        WHEN f.fx_conversion = 'change' THEN u.change
        ELSE u.value
        END AS value
FROM canonical_obs AS o
JOIN instruments AS i
    ON o.instrument_id = i.instrument_id
JOIN fields AS f
    ON o.field = f.name
JOIN units_ts AS u
    ON i.unit = u.code
    AND o.date = u.date;


COMMIT;
