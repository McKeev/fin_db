-- =============================================================================
-- Batch Update Query for yfinance
-- =============================================================================
-- Purpose:
--   Groups instruments by their required field sets to enable efficient
--   batched API calls to yfinance. yfinance is much faster when downloading
--   multiple tickers in a single call, but all tickers must request the same
--   data fields.
--
-- Returns:
--   field_set   | instruments
--   ------------|------------------
--   close,volume| ['AAPL','MSFT','GOOGL']
--   close,div   | ['VOO','SPY']
--
-- Usage:
--   For each row, call yf.download(instruments, ...) with appropriate fields
--   This minimizes API calls and respects rate limits.
--
-- Performance:
--   Uses index: idx_updates_source_frequency_instrument
--
-- =============================================================================

WITH instrument_fields AS (
    SELECT
        id.ext_id AS ticker,
        ARRAY_AGG(u.field ORDER BY u.field) AS field_set
    FROM updates AS u
    JOIN identifiers AS id
      USING (instrument_id)
    WHERE id.source = %(source)s
      AND u.source = %(source)s
      AND u.frequency = %(frequency)s
    GROUP BY id.ext_id
)
SELECT
    field_set,
    ARRAY_AGG(ticker ORDER BY ticker) AS instruments
FROM instrument_fields
GROUP BY field_set;