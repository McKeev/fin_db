-- Serves to translate external tickers to internal `instrument_id`s

WITH input_tickers AS (
    SELECT unnest(%(tickers)s::text[]) AS ext_id
)
SELECT
    t.ext_id,
    i.instrument_id
FROM input_tickers t
LEFT JOIN identifiers i
    ON t.ext_id = i.ext_id AND i.source = %(source)s;
