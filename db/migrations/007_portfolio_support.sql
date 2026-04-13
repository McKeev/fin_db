-- =============================================================================
-- Migration: Portfolio Support
-- =============================================================================
-- Purpose:
--   - Adds portfolio activity storage for broker transactions.
--   - Normalizes transaction types via a dedicated enum.
--   - Rebuilds time_series_usd to handle currency instruments correctly.
--   - Adds synthetic USD observations for every trading day used by the portfolio view.
--   - Builds portfolio_holdings to combine position activity and cash into a unified holdings view.
--
-- Major changes:
--   * New type: transaction_type
--   * New table: portfolio_activity
--   * New/updated object: time_series_usd (materialized view)
--   * New/updated object: portfolio_holdings (view)
--   * New indexes: time_series_usd lookup indexes, portfolio_activity holdings index
--   * New seed data: synthetic USD observations for trading days
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



\echo '------------- ADD USD OBSERVATIONS FOR EVERY TRADING DAY -------------'
INSERT INTO observations (instrument_id, field, date, source, value)
SELECT
    'CURUSDXUSDXXXXXXXXXX' AS instrument_id,
    'close' AS field,
    date::date AS date,
    'system' AS source,
    100000.0 AS value
FROM (
    SELECT DISTINCT date 
    FROM observations 
    WHERE instrument_id = 'CUREURXUSDXXXXXXXXXX'
)
ON CONFLICT (instrument_id, field, date, source) DO NOTHING;

\echo '------------------------- RECREATE USD VIEW --------------------------'
-- Found a bug where currencies were not displayed correctly
DROP MATERIALIZED VIEW IF EXISTS time_series_usd CASCADE;
CREATE MATERIALIZED VIEW time_series_usd AS
SELECT
    i.instrument_id,
    i.internal_ticker,
    o.field,
    o.date,
    ROUND(o.value * CASE
        WHEN i.asset_class = 'currency' THEN (SELECT scale FROM units WHERE code = i.internal_ticker::varchar(3))
        WHEN f.fx_conversion = 'change' THEN u.change
        ELSE u.value
    END, 5)::numeric(19, 5) AS value
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



\echo '------------------- NEW TABLE: PORTFOLIO_ACTIVITY --------------------'
DROP TYPE IF EXISTS transaction_type CASCADE;
CREATE TYPE transaction_type AS ENUM (
    'open',
    'close',
    'deposit',
    'withdrawal',
    'dividend',
    'interest',
    'split'
);

DROP TABLE IF EXISTS portfolio_activity CASCADE;
CREATE TABLE portfolio_activity (
    pf_id varchar(20) NOT NULL,
    type transaction_type NOT NULL,
    broker text NOT NULL,
    ts timestamptz NOT NULL,
    position_id text,
    instrument_id varchar(20),
    units numeric,
    fee numeric,
    cashflow_usd numeric,
    notes text,
    CONSTRAINT fk_portfolio_activity_instrument
        FOREIGN KEY (instrument_id)
        REFERENCES instruments (instrument_id),
    CONSTRAINT fk_portfolio_activity_pf_id
        FOREIGN KEY (pf_id)
        REFERENCES instruments (instrument_id)
);

-- For the holdings view
CREATE INDEX idx_portfolio_activity_holdings 
    ON portfolio_activity (pf_id, type, ts, instrument_id);

COMMENT ON COLUMN portfolio_activity.pf_id IS 
  'Portfolio identifier (instrument_id).';

COMMENT ON COLUMN portfolio_activity.type IS 
  'Transaction type: one of open, close, deposit, withdrawal, dividend, interest, split.';

COMMENT ON COLUMN portfolio_activity.broker IS 
  'Broker through which the transaction was executed (e.g. etoro).';

COMMENT ON COLUMN portfolio_activity.ts IS 
  'Transaction timestamp in UTC.';

COMMENT ON COLUMN portfolio_activity.position_id IS 
  'Broker-assigned position identifier, shared across all transactions for the same position. Null for cash transactions.';

COMMENT ON COLUMN portfolio_activity.instrument_id IS 
  'Internal instrument_id. Null for cash transactions.';

COMMENT ON COLUMN portfolio_activity.units IS 
  'Number of units involved. Positive for opens, negative for closes. Null for cash transactions.';

COMMENT ON COLUMN portfolio_activity.fee IS 
  'Transaction fee in USD, always non-negative.';

COMMENT ON COLUMN portfolio_activity.cashflow_usd IS 
  'Net cash impact in USD. Positive = cash in (deposit, dividend), negative = cash out (open, withdrawal). Includes possible fees.';

COMMENT ON COLUMN portfolio_activity.notes IS 
  'Optional free-text notes for this transaction.';



\echo '----------------------- BUILDING HOLDINGS VIEW -----------------------'
DROP VIEW IF EXISTS portfolio_holdings CASCADE;
CREATE VIEW portfolio_holdings AS
WITH
    -- Base data make transactions daily
    activity AS (
        SELECT
            pf_id,
            ts::date AS date,  -- Take timestamp as date
            instrument_id,
            SUM(units) AS units
        FROM portfolio_activity
        WHERE type IN ('open', 'close', 'split')
        GROUP BY (pf_id, ts::date, instrument_id)
    ),
    -- Include cash transactions as a synthetic "holding" in USD to track cash balance over time
    cash AS (
        SELECT
            pf_id,
            ts::date AS date,  -- Take timestamp as date
            (SELECT instrument_id FROM units WHERE code = 'USD') AS instrument_id,
            SUM(cashflow_usd) AS units
        FROM portfolio_activity
        GROUP BY (pf_id, ts::date)
    ),
    -- Combine raw activity before cumulating
    combined AS (
        SELECT * FROM activity
        UNION ALL
        SELECT * FROM cash
    ),
    -- We identify a trading day as any day where at least 50% of the portfolio's instruments have a price
    -- (i.e. are traded) to avoid creating holdings entries on days where we have no price data for most
    -- instruments, which would lead to misleading flat valuations. Not perfect but should be OK considering data.
    trading_days AS (
        SELECT date
        FROM time_series_usd
        WHERE instrument_id IN (SELECT DISTINCT instrument_id FROM combined)
            AND field = 'close'
            AND date BETWEEN (SELECT MIN(date) FROM combined) AND (SELECT MAX(date) FROM time_series_usd)
        GROUP BY date
        HAVING COUNT(DISTINCT instrument_id) > (
            SELECT COUNT(DISTINCT instrument_id) * 0.5
            FROM combined
        )
    ),
    -- Get all combinations of pf_id, instrument_id, and date
    spine AS (
        SELECT DISTINCT pf_id, trading_days.date AS date, instrument_id
        FROM combined
        CROSS JOIN trading_days
    ),
    --Join to get units for all combinations, filling missing with 0
    all_combinations AS (
        SELECT
            COALESCE(spine.pf_id, combined.pf_id) AS pf_id,
            COALESCE(spine.date, combined.date) AS date,
            COALESCE(spine.instrument_id, combined.instrument_id) AS instrument_id,
            COALESCE(combined.units, 0) AS units
        FROM spine
        FULL OUTER JOIN combined ON spine.pf_id = combined.pf_id  -- in case we have deposits on weekends and such
            AND spine.date = combined.date
            AND spine.instrument_id = combined.instrument_id
    ),
    -- Get cumulative holdings
    c_holdings AS (
        SELECT
            pf_id,
            date,
            instrument_id,
            SUM(units) OVER (PARTITION BY pf_id, instrument_id ORDER BY date) AS units
        FROM all_combinations
    ),
    -- Get frontfilled prices for observations
    frontfilled AS (
        SELECT
            pf_id,
            instrument_id,
            date,
            units,
            FIRST_VALUE(price) OVER (
                PARTITION BY pf_id, instrument_id, grp ORDER BY date
            ) AS close_usd
        FROM (
            SELECT
                h.*,
                t.value AS price,
                COUNT(t.value) OVER (
                    PARTITION BY h.pf_id, h.instrument_id ORDER BY h.date
                ) AS grp
            FROM c_holdings AS h
            LEFT JOIN time_series_usd AS t
                ON h.instrument_id = t.instrument_id
                AND h.date = t.date
                AND t.field = 'close'
            WHERE units > 0.00001 AND h.date IN (SELECT date FROM trading_days)
        )
    )
SELECT * FROM frontfilled;



COMMIT;