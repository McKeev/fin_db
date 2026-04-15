-- Adds to identifiers table (should fail easily)

INSERT INTO identifiers (
    instrument_id,
    source,
    ext_id
) VALUES (
    %(instrument_id)s,
    %(source)s,
    %(ext_id)s
)