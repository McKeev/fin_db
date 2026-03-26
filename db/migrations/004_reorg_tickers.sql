-- Main purpose: external identifiers to 

\pset pager off
\pset border 2
\pset linestyle ascii
\pset null '<NULL>'
\x auto
\timing on
\set ON_ERROR_STOP on

BEGIN;

\echo '-------------------------- START MIGRATION ---------------------------'
-- Before migration: check current state
\echo '-------------------- BEFORE MIGRATION: instruments -------------------'
SELECT * FROM instruments LIMIT 10;

\echo '------------------- BEFORE MIGRATION: identifiers --------------------'
SELECT * FROM identifiers LIMIT 10;

\echo '---------------------- BEFORE MIGRATION: sources ---------------------'
SELECT * FROM sources LIMIT 10;

\echo '-  1. Add internal_ticker to instruments'
ALTER TABLE instruments ADD COLUMN internal_ticker varchar;

\echo '- 2. Populate internal_ticker from identifiers.ticker'
UPDATE instruments
SET internal_ticker = i.ticker
FROM identifiers i
WHERE instruments.instrument_id = i.instrument_id;

\echo '- 3. Set NOT NULL and UNIQUE constraints'
ALTER TABLE instruments ALTER COLUMN internal_ticker SET NOT NULL;
CREATE UNIQUE INDEX idx_instruments_internal_ticker ON instruments(internal_ticker);

\echo '- 4. Prepare new identifiers table'
CREATE TABLE identifiers_new (
  instrument_id char(20) NOT NULL,
  source varchar NOT NULL,
  ext_id varchar NOT NULL,
  PRIMARY KEY (instrument_id, source),
  UNIQUE (instrument_id, source, ext_id),
  FOREIGN KEY (instrument_id) REFERENCES instruments(instrument_id),
  FOREIGN KEY (source) REFERENCES sources(name)
);
CREATE INDEX idx_identifiers_source_extid ON identifiers_new (source, ext_id);

\echo '- 5. Remove identifier column from sources if it exists'
ALTER TABLE sources DROP COLUMN IF EXISTS identifier;

\echo '- 6. Add ISIN to sources'
INSERT INTO sources (name, priority)
VALUES ('ISIN', '100');

\echo '- 7. Migrate ISIN, RIC, YFIN, ETORO to new identifiers'
INSERT INTO identifiers_new (instrument_id, source, ext_id)
SELECT instrument_id, 'ISIN', isin FROM identifiers WHERE isin IS NOT NULL;

INSERT INTO identifiers_new (instrument_id, source, ext_id)
SELECT instrument_id, 'LSEG', ric FROM identifiers WHERE ric IS NOT NULL;
INSERT INTO identifiers_new (instrument_id, source, ext_id)
SELECT instrument_id, 'YAHOO', yfin FROM identifiers WHERE yfin IS NOT NULL;
INSERT INTO identifiers_new (instrument_id, source, ext_id)
SELECT instrument_id, 'ETORO', etoro::varchar FROM identifiers WHERE etoro IS NOT NULL;

\echo '- 8. Drop old identifiers and rename new'
DROP TABLE identifiers;
ALTER TABLE identifiers_new RENAME TO identifiers;

\echo '- 9. Remove identifier column from sources if it exists'
ALTER TABLE sources DROP COLUMN IF EXISTS identifier;

-- After migration: check new state (will be rolled back)
\echo '-------------------- AFTER MIGRATION: instruments --------------------'
SELECT * FROM instruments LIMIT 10;

\echo '-------------------- AFTER MIGRATION: identifiers --------------------'
SELECT * FROM identifiers LIMIT 10;

\echo '---------------------- AFTER MIGRATION: sources ----------------------'
SELECT * FROM sources LIMIT 10;


COMMIT;
