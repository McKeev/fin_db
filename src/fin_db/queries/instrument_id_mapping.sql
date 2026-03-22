-- Serves to translate external tickers to internal `instrument_id`s

SELECT
    {identifier},
    instrument_id
FROM identifiers
WHERE {identifier} =  ANY(%(tickers)s)
