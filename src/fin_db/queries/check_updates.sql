-- Returns the instruments whose most recent update is older than given date.

SELECT i.instrument_id, i.name, u.field, u.last_update
FROM instruments AS i
JOIN updates AS u
USING(instrument_id)
WHERE u.last_update <= %(cutoff_date)s
