-- Historical data query for USD time series

SELECT
    internal_ticker AS ticker,
    field,
    date,
    value
FROM time_series_usd
WHERE
    internal_ticker = ANY(%(tickers)s)
    AND field = ANY(%(fields)s)
    AND date BETWEEN %(sdate)s AND %(edate)s
ORDER BY date ASC;
