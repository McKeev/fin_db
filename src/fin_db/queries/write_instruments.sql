-- Add to instruments table (should fail easily)

INSERT INTO instruments (
    instrument_id,
    name,
    asset_class,
    unit,
    internal_ticker
) VALUES (
    %(instrument_id)s,
    %(name)s,
    %(asset_class)s,
    %(unit)s,
    %(internal_ticker)s
)
