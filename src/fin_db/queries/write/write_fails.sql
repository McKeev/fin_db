-- Log ingestion failures

INSERT INTO ingest_failures (
    instrument_id,
    field,
    source,
    error_timestamp,
    error_message
) VALUES (
    %(instrument_id)s,
    %(field)s,
    %(source)s,
    CURRENT_TIMESTAMP,
    %(error_message)s
);
