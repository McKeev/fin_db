\pset pager off
\pset border 2
\pset linestyle ascii
\pset null '<NULL>'
\x auto
\timing on
\set ON_ERROR_STOP on

BEGIN;
\echo '---------------------------- Create view -----------------------------'
CREATE VIEW canonical_obs AS
SELECT DISTINCT ON (o.instrument_id, o.field, o.date)
    o.instrument_id,
    o.field,
    o.date,
    o.source,
    o.value,
    o.scale
FROM observations AS o
JOIN sources AS s
    ON o.source = s.name
ORDER BY
    o.instrument_id,
    o.field,
    o.date,
    s.priority;  -- lower number = higher priority

COMMIT;