-- =============================================================================
-- Migration: Support Currency Changes with Effective-Dated Instrument Units
-- =============================================================================
-- Purpose:
--   - Adds instrument-level unit history via instrument_units to support listing/currency changes over time.
--   - Enforces non-overlapping effective date ranges per instrument for clean temporal integrity.
--   - Backfills instrument_units from current instruments.unit using each instrument's first observed date.
--   - Rebuilds time_series_usd to resolve unit by instrument and date instead of a static instruments.unit value.
--   - Materializes time_series_usd and adds lookup indexes for ticker/date and instrument/date access patterns.
--
-- Major changes:
--   * New table: instrument_units
--   * New constraints: FK to instruments/units, date validity check, exclusion constraint for non-overlap
--   * New/updated object: time_series_usd (materialized view)
--   * New indexes: instrument_units temporal lookup, time_series_usd query lookup indexes
--   * Dropped column: instruments.unit (moved to instrument_units)
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



\echo '-------------------- NEW TABLE: instrument_units ---------------------'
CREATE TABLE instrument_units (
    instrument_id bpchar(20) NOT NULL,
    unit bpchar(3) NOT NULL,
    start_date date NOT NULL,
    end_date date NOT NULL DEFAULT DATE '9999-12-31',
    PRIMARY KEY (instrument_id, start_date),
    CONSTRAINT fk_instrument_units_instrument
        FOREIGN KEY (instrument_id) REFERENCES instruments(instrument_id),
    CONSTRAINT fk_instrument_units_unit
        FOREIGN KEY (unit) REFERENCES units(code),
    CONSTRAINT ck_instrument_units_dates
        CHECK (start_date < end_date)
);

-- Prevent overlapping ranges per instrument (end date exclusive)
CREATE EXTENSION IF NOT EXISTS btree_gist;
ALTER TABLE instrument_units
ADD CONSTRAINT ex_instrument_units_no_overlap
EXCLUDE USING gist (
    instrument_id WITH =,
    daterange(start_date, end_date, '[)') WITH &&
);

-- Fast lookup for date-resolved joins
CREATE INDEX idx_instrument_units_lookup
ON instrument_units (instrument_id, start_date, end_date);



\echo '----------------------- Fill instrument_units ------------------------'
-- Start at first observation date per instrument; if none, use 1900-01-01
-- Start date inclusive, end date exclusive
WITH first_obs AS (
    SELECT instrument_id, MIN(date)::date AS start_date
    FROM observations
    GROUP BY instrument_id
)
INSERT INTO instrument_units (instrument_id, unit, start_date, end_date)
SELECT
    i.instrument_id,
    i.unit::bpchar(3),
    COALESCE(f.start_date, '1900-01-01'),
    DATE '9999-12-31'
FROM instruments AS i
LEFT JOIN first_obs AS f
    ON f.instrument_id = i.instrument_id;



\echo '------------------------- Recreate USD view --------------------------'
DROP VIEW IF EXISTS time_series_usd;
CREATE MATERIALIZED VIEW time_series_usd AS
SELECT
    i.instrument_id,
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
JOIN instrument_units AS iu
    ON iu.instrument_id = o.instrument_id
   AND o.date >= iu.start_date
   AND o.date < iu.end_date
JOIN units_ts AS u
    ON u.code = iu.unit
   AND u.date = o.date;

CREATE INDEX idx_time_series_usd_lookup_internal_ticker
ON time_series_usd (internal_ticker, field, date);

CREATE INDEX idx_time_series_usd_lookup_instrument_id
ON time_series_usd (instrument_id, field, date);

GRANT MAINTAIN ON time_series_usd TO fin_db_app;


ALTER TABLE instruments DROP COLUMN unit;
SELECT * FROM instruments LIMIT 5;



COMMIT;