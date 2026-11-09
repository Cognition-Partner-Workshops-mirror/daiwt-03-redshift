---
name: capture-golden
description: One-time, operator-run golden capture of the Redshift estate (not for migration sessions).
---

# Capture goldens (operator only)

This runs against the live Redshift estate and is a one-time bootstrap step.
Migration child sessions must never run it.

```bash
export AWS_REGION=us-east-1
make legacy-all        # = tools/legacy_redshift.py all
```

Subcommands of `tools/legacy_redshift.py`:

- `setup` — create database `daiwt_03_retail` (via `REDSHIFT_ADMIN_DATABASE`,
  default `dev`), then `00_foundation` DDL and multi-row INSERT load of
  `data/seed/csv/` (`\N` → NULL, SUPER via `JSON_PARSE`). Idempotent:
  drops/recreates `core` and `mart`.
- `build` — run every unit's `etl.sql` in manifest wave order (skips files in
  `capture_skip`), then orchestration.
- `capture` — for each manifest output write `golden/<unit>/<name>.csv` +
  `.meta.json` (families by type OID, sha256) and refresh
  `golden/PROVENANCE.json`.
- `all` — setup + build + capture.
