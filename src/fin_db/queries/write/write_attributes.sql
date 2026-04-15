-- Add attributes to instrument_attributes table (should fail easily)

INSERT INTO instrument_attributes (
    instrument_id,
    field,
    value
) VALUES (
    %(instrument_id)s,
    %(field)s,
    %(value)s
)