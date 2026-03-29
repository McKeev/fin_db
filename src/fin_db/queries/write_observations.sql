-- Adds data to the observations table, overriding on conlict to allow for vendor corrections.

INSERT INTO observations (
    instrument_id,
    field,
    date,
    source,
    value
) VALUES (
    %(instrument_id)s,
    %(field)s,
    %(date)s,
    %(source)s,
    %(value)s
)
ON CONFLICT (instrument_id, field, date, source)
DO UPDATE SET
    value = EXCLUDED.value;
