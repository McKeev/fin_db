-- Ingest data to updates table for the first time

INSERT INTO updates (
    instrument_id,
    field,
    source,
    frequency,
    last_update
)
VALUES (
    %(instrument_id)s,
    %(field)s,
    %(source)s,
    %(frequency)s,
    CURRENT_DATE
)
ON CONFLICT (instrument_id, field, source) DO NOTHING;
