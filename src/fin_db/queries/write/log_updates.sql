-- Log latest upates to `updates` table

UPDATE updates
SET last_update = CURRENT_DATE
WHERE instrument_id = %(instrument_id)s
  AND field = %(field)s
  AND source = %(source)s;
