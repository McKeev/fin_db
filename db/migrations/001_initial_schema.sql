-- SQL dump generated using DBML (dbml.dbdiagram.io)
-- Database: PostgreSQL
-- Generated at: 2026-03-22T21:41:27.806Z

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
  "etoro" integer UNIQUE
);

CREATE TABLE "instrument_attributes" (
  "instrument_id" char(20),
  "field" varchar,
  "value" varchar NOT NULL,
  PRIMARY KEY ("instrument_id", "field")
);

CREATE TABLE "sources" (
  "name" varchar PRIMARY KEY,
  "priority" integer NOT NULL
);

CREATE TABLE "observations" (
  "instrument_id" char(20),
  "field" varchar,
  "date" date,
  "source" varchar,
  "value" numeric(19,5) NOT NULL,
  "scale" numeric(19,5) NOT NULL,
  PRIMARY KEY ("instrument_id", "field", "date", "source")
);

CREATE TABLE "updates" (
  "instrument_id" char(20),
  "field" varchar,
  "source" varchar,
  "frequency" varchar NOT NULL,
  "last_update" date NOT NULL,
  PRIMARY KEY ("instrument_id", "field", "source")
);

CREATE TABLE "ingest_failures" (
  "instrument_id" char(20),
  "field" varchar,
  "source" varchar,
  "error_timestamp" timestampz,
  "error_message" varchar,
  PRIMARY KEY ("instrument_id", "field", "source", "error_timestamp")
);

CREATE INDEX "idx_obs_lookup" ON "observations" ("instrument_id", "field", "date");

CREATE INDEX "idx_updates_source_frequency_instrument" ON "updates" ("source", "frequency", "instrument_id", "field");

CREATE INDEX "idx_updates_due_scan" ON "updates" ("source", "frequency", "last_update");

ALTER TABLE "identifiers" ADD FOREIGN KEY ("instrument_id") REFERENCES "instruments" ("instrument_id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "instrument_attributes" ADD FOREIGN KEY ("instrument_id") REFERENCES "instruments" ("instrument_id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "observations" ADD FOREIGN KEY ("instrument_id") REFERENCES "instruments" ("instrument_id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "observations" ADD FOREIGN KEY ("source") REFERENCES "sources" ("name") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "updates" ADD FOREIGN KEY ("instrument_id") REFERENCES "instruments" ("instrument_id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "updates" ADD FOREIGN KEY ("source") REFERENCES "sources" ("name") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "ingest_failures" ADD FOREIGN KEY ("instrument_id") REFERENCES "instruments" ("instrument_id") DEFERRABLE INITIALLY IMMEDIATE;

ALTER TABLE "ingest_failures" ADD FOREIGN KEY ("source") REFERENCES "sources" ("name") DEFERRABLE INITIALLY IMMEDIATE;
