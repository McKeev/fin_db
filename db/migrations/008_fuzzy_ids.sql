-- =============================================================================
-- Migration: 008_fuzzy_ids
-- =============================================================================
-- Purpose:
--   - Adds `simpler_name` column to `instruments` for fuzzy name matching.
--   - Adds normalization function `simpler_name_normalize` to canonicalize instrument names (lowercase, unaccent, strip legal suffixes and filler words).
--   - Populates `simpler_name` for existing rows and maintains it via a trigger on `name`.
--   - Adds a trigram GIN index on `simpler_name` and a case-insensitive index on `internal_ticker` to speed lookups.
--   - Requires `pg_trgm` and `unaccent` extensions for fuzzy and diacritic-insensitive matching.
--
-- Major changes:
--   * New column: instruments.simpler_name (text)
--   * New function: simpler_name_normalize(text)
--   * New trigger/function: set_simpler_name_trigger()
--   * New indexes: idx_instruments_simpler_name_trgm, idx_instruments_ticker_lower
--   * Requires extensions: pg_trgm, unaccent
--
-- =============================================================================

\pset pager off
\pset border 2
\pset linestyle ascii
\pset null '<NULL>'
\x auto
\timing on
\set ON_ERROR_STOP on

BEGIN;

CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;

ALTER TABLE instruments ADD COLUMN IF NOT EXISTS simpler_name text;

CREATE OR REPLACE FUNCTION simpler_name_normalize(text) RETURNS text
LANGUAGE plpgsql IMMUTABLE AS $$
DECLARE
    s text := $1;
BEGIN
    IF s IS NULL THEN
        RETURN NULL;
    END IF;

    -- lowercase + remove accents
    s := lower(unaccent(s));

    -- named exceptions before any stripping
    IF s = lower(unaccent('Taiwan Semiconductor Manufacturing Co Ltd')) THEN
        RETURN 'tsmc';
    ELSIF s = lower(unaccent('Alphabet Inc (Class A)')) THEN
        RETURN 'alphabet';
    END IF;

    -- normalize connectors
    s := regexp_replace(s, '\s*&\s*', ' and ', 'g');

    -- remove leading "the"
    s := regexp_replace(s, '^the\s+', '');

    -- remove legal suffixes
    s := regexp_replace(s,
        E'[[:punct:]]*[[:space:]]*(inc|plc|ltd|llc|corp|corporation|co(?:mpany)?|holdings|s\\.a\\.|sa|ag|nv|bv|gmbh|sarl|se|spa|ab|oy|asa|pte|sdn\\.?\\s*bhd)\.?$',
        '', 'gi');

    -- remove filler words (full forms and abbreviations)
    s := regexp_replace(s,
        '\y(group|global|solutions|technologies?|tech|services?|svcs|systems?|international|intl|holdings?)\y',
        '', 'gi');

    -- punctuation to spaces
    s := regexp_replace(s, '[[:punct:]]', ' ', 'g');

    -- collapse whitespace + trim
    s := regexp_replace(s, '[[:space:]]+', ' ', 'g');
    s := btrim(s);

    RETURN s;
END;
$$;

UPDATE instruments
SET simpler_name = simpler_name_normalize(name);

CREATE INDEX IF NOT EXISTS idx_instruments_simpler_name_trgm
    ON instruments USING GIN (simpler_name gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_instruments_ticker_lower
    ON instruments (lower(internal_ticker));

CREATE OR REPLACE FUNCTION set_simpler_name_trigger() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    NEW.simpler_name := simpler_name_normalize(NEW.name);
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_set_simpler_name ON instruments;
CREATE TRIGGER trg_set_simpler_name
    BEFORE INSERT OR UPDATE OF name ON instruments
    FOR EACH ROW EXECUTE FUNCTION set_simpler_name_trigger();

SELECT * FROM instruments WHERE internal_ticker in ('GOOGL', 'GOOG', 'BRK-A', 'BRK-B');

COMMIT;
