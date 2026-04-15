INSERT INTO observations (instrument_id, field, date, source, value)
WITH
    portfolio_nav AS (
        SELECT
            pf_id,
            date,
            SUM(units * close_usd) AS nav
        FROM portfolio_holdings
        GROUP BY (pf_id, date)
    ),
    cash_adj AS (
        SELECT
            pf_id,
            ts::date AS date,  -- Take timestamp as date
            SUM(cashflow_usd) AS cashflow
        FROM portfolio_activity
        WHERE type IN ('deposit', 'withdrawal')
        GROUP BY (pf_id, ts::date)
    ),
    joined AS (
        SELECT
            nav.pf_id,
            nav.date,
            nav.nav,
            COALESCE(c.cashflow, 0) AS cashflow
        FROM portfolio_nav AS nav
        LEFT JOIN cash_adj AS c
        ON nav.pf_id = c.pf_id
            AND nav.date = (
                SELECT MIN(n2.date)
                FROM portfolio_nav AS n2
                WHERE n2.pf_id = nav.pf_id
                    AND n2.date >= c.date
            )
    ),
    final AS (
        SELECT
            pf_id AS instrument_id,
            'close' AS field,
            date,
            'system' AS source,
            nav AS value
        FROM joined

        UNION ALL

        SELECT
            pf_id AS instrument_id,
            'totret' AS field,
            date,
            'system' AS source,
            ( (nav - cashflow) / (LAG(nav, 1) OVER (PARTITION BY pf_id ORDER BY date)) - 1 ) * 100 AS value
        FROM joined
    )
SELECT
    instrument_id,
    field,
    date,
    source,
    ROUND(value, 5)::NUMERIC(19,5) AS value
FROM final WHERE value IS NOT NULL
-- On conflict, update with latest value
ON CONFLICT (instrument_id, field, date, source) DO UPDATE
SET value = EXCLUDED.value;
