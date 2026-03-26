-- Serves to translate external tickers to internal `instrument_id`s

SELECT
    ext_id,
    instrument_id
FROM identifiers
WHERE 
    source = %(source)s
    AND ext_id =  ANY(%(tickers)s);
