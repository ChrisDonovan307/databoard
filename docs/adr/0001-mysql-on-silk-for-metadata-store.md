# MySQL on Silk for the metadata store

## Context

Harvested Dataverse metadata was kept in flat `metadata.csv` / `.parquet` files
(and `dataverses.csv`, `installations.geojson`). At ~550k rows the parquet was
already 312 MB; datasets + dataverses across all installations project to ~3M rows
(~2 GB), and files would push it past ~30M rows (~18 GB). Flat files don't support
the flexible querying the dashboard needs, and a multi-GB artifact can't be moved
through the git-based Silk deploy.

## Decision

Store harvested metadata in **MySQL on Silk** — the database server already
provisioned on the existing host. The incremental pull runs on a developer laptop
and writes to Silk MySQL over an SSH tunnel; Flask reads it from localhost.
Nothing large ships through the deploy. Access is via SQLAlchemy 2.0 (ORM for
reads and schema, Core `on_duplicate_key_update` for bulk upserts); a
`--export-parquet` helper remains for offline sharing.

## Considered options

- **Embedded DuckDB shipped as a build artifact** — best analytical performance
  and reads the existing parquet directly, but the `.duckdb` file still has to
  reach the Flask host, and git can't carry it.
- **Hosted analytical DB (MotherDuck / object storage + DuckDB)** — solves
  distribution and scales to files-scope, but adds a new external dependency and
  effectively requires migrating hosting off Silk.
- **Migrate hosting off Silk (Vercel + managed Postgres/Neon)** — larger project;
  Vercel is a poor fit for Flask + multi-GB data, and free managed-Postgres tiers
  are below even the starting data size.

## Consequences

- MySQL is row-oriented, so large `GROUP BY` aggregations are slower than a
  columnar engine would be; mitigated with indexes and, if needed later, rollup
  tables. The dashboard's 5-minute response cache absorbs the rest.
- The loader, schema, and query layer all bind to MySQL/SQLAlchemy — reversing
  this is a rewrite, not a config change.
- Files-scope (~18 GB) may eventually exceed what's comfortable on Silk; revisit a
  hosted analytical DB then, not before.
