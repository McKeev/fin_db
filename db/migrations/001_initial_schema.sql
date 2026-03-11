-- SQL dump generated using DBML (dbml.dbdiagram.io)
-- Database: PostgreSQL
-- Generated at: 2026-02-24T13:24:05.510Z

CREATE TABLE "instruments" (
  "instrument_id" char(20) PRIMARY KEY,
  "name" varchar UNIQUE NOT NULL,
  "asset_class" varchar NOT NULL,
  "unit" varchar NOT NULL
);

CREATE TABLE "identifiers" (
  "instrument_id" char(20) PRIMARY KEY,
  "ticker" varchar UNIQUE,
  "isin" varchar UNIQUE,
  "ric" varchar UNIQUE,
  "yfin" varchar UNIQUE,
  "etoro" varchar UNIQUE
);

CREATE TABLE "instrument_attributes" (
  "instrument_id" char(20),
  "field" varchar,
  "value" varchar NOT NULL,
  PRIMARY KEY ("instrument_id", "field")
);

CREATE TABLE "observations" (
  "instrument_id" char(20),
  "field" varchar,
  "date" date,
  "source" varchar NOT NULL,
  "value" numeric(19,4) NOT NULL,
  "scale" numeric(19,4) NOT NULL,
  PRIMARY KEY ("instrument_id", "field", "date")
);

CREATE TABLE "updates" (
  "instrument_id" char(20),
  "field" varchar,
  "frequency" varchar NOT NULL,
  "last_update" timestamp NOT NULL,
  "source" varchar NOT NULL,
  PRIMARY KEY ("instrument_id", "field")
);

CREATE INDEX "idx_identifiers_ticker" ON "identifiers" ("ticker");

CREATE INDEX "idx_identifiers_isin" ON "identifiers" ("isin");

CREATE INDEX "idx_identifiers_ric" ON "identifiers" ("ric");

CREATE INDEX "idx_identifiers_yfin" ON "identifiers" ("yfin");

CREATE INDEX "idx_identifiers_etoro" ON "identifiers" ("etoro");

CREATE INDEX "idx_updates_source_frequency_instrument" ON "updates" ("source", "frequency", "instrument_id");

ALTER TABLE "identifiers" ADD FOREIGN KEY ("instrument_id") REFERENCES "instruments" ("instrument_id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "instrument_attributes" ADD FOREIGN KEY ("instrument_id") REFERENCES "instruments" ("instrument_id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "observations" ADD FOREIGN KEY ("instrument_id") REFERENCES "instruments" ("instrument_id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "updates" ADD FOREIGN KEY ("instrument_id") REFERENCES "instruments" ("instrument_id") DEFERRABLE INITIALLY IMMEDIATE;
