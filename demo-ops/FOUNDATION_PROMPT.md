# Foundation prompt

Run this as its own session before the orchestrator.

> Set up the Databricks foundation in `daiwt-03-redshift` only after migration is explicitly authorized. Start a `migration-run-1` branch off `main`. Take the Redshift table definitions in `legacy/redshift/00_foundation` and rebuild them in `databricks/foundation/`. The catalog `daiwt_03` starts empty: create the required schemas and raw volume, upload the committed seed CSVs, then load bronze Delta tables as-is. Build typed silver tables mirroring Redshift core. Check the silver tables against the Redshift goldens with `make validate UNIT=foundation`, then open a PR into `migration-run-1`. Stay inside `daiwt_03` and follow `AGENTS.md`. Never modify the shared Redshift source.
