-- This query resolves a list of raw input strings to their corresponding instruments in the database,
-- using both exact ticker matches and fuzzy name matching.
-- It returns the original input, the matched instrument's ID, internal ticker, name, and a similarity score for the name match.

-- TLDR: Fuzzy Matcher

WITH inputs(raw) AS (
    SELECT unnest(%(raw_inputs)s::text[])
)
SELECT
    i.raw,
    inst.instrument_id,
    inst.internal_ticker,
    inst.name,
    inst.simpler_name,
    inst.asset_class,
    similarity(inst.simpler_name, simpler_name_normalize(i.raw)) AS name_score
FROM inputs i
LEFT JOIN LATERAL (
    SELECT *
    FROM instruments
    WHERE lower(internal_ticker) = lower(i.raw)
    OR simpler_name %% simpler_name_normalize(i.raw)
    ORDER BY
        (lower(internal_ticker) = lower(i.raw)) DESC,
        similarity(simpler_name, simpler_name_normalize(i.raw)) DESC
    LIMIT 1
) inst ON true;
