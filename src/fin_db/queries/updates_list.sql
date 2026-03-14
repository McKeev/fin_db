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
        {identifier_col} AS ticker,
        ARRAY_AGG(field ORDER BY field) AS field_set
    FROM updates
    JOIN identifiers
      USING (instrument_id)
    WHERE source = %(source)s
      AND frequency = %(frequency)s
    GROUP BY {identifier_col}
)
SELECT
    field_set,
    ARRAY_AGG(ticker ORDER BY ticker) AS instruments
FROM instrument_fields
GROUP BY field_set;