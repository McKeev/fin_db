-- =============================================================================
-- Batch Update Query for yfinance
-- =============================================================================
-- Purpose:
--   Groups instruments by their required field sets and asset class to enable efficient
--   batched API calls to yfinance. yfinance is much faster when downloading
--   multiple tickers in a single call, but all tickers must request the same
--   data fields.
--
-- Returns:
--   asset_class | field_set   | instruments
--   ------------|-------------|------------------
--   equity      | close,totret| ['AAPL','MSFT','GOOGL']
--   equity      | close       | ['VOO','SPY']
--   currency    | close       | ['=EUR']
--
-- Usage:
--   For each row, call yf.download(instruments, ...) with the specified fields.
--   Grouping by asset_class and field_set minimizes API calls and respects rate limits.
--
-- Performance:
--   Uses index: idx_updates_source_frequency_instrument
--
-- =============================================================================

WITH instrument_fields AS (
    SELECT
        i.asset_class,
        id.ext_id AS ticker,
        ARRAY_AGG(u.field ORDER BY u.field) AS field_set
    FROM updates AS u
    JOIN identifiers AS id
        USING (instrument_id)
    JOIN instruments AS i
        USING (instrument_id)
    WHERE id.source = %(source)s
      AND u.source = %(source)s
      AND u.frequency = %(frequency)s
    GROUP BY i.asset_class, id.ext_id
)
SELECT
    asset_class,
    field_set,
    ARRAY_AGG(ticker ORDER BY ticker) AS instruments
FROM instrument_fields
GROUP BY asset_class, field_set;
