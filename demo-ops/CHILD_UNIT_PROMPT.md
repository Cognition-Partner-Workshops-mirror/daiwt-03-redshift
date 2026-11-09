# Child unit session prompt

You are a child migration session owning exactly one unit: `<name>`.

1. Branch `unit/<name>` from `migration-run-N`. Read your unit's entry in
   `.migration/units.yaml` (legacy files, reads/writes, outputs + keys,
   expected_lakebridge, constructs) and `AGENTS.md`.
2. If a Lakebridge draft exists under `.migration/lakebridge/transpiled/<name>/`,
   start from it; otherwise hand-convert
   `legacy/redshift/units/<name>/etl.sql` and `report.sql`.
3. Write only `databricks/units/<name>/etl.sql` and `report.sql` — unqualified
   `silver.x`/`gold.x` references; the harness sets the catalog.
4. Set `DATABRICKS_HOST`, `DATABRICKS_TOKEN`, `DATABRICKS_WAREHOUSE_ID` (and
   `MIG_CATALOG` if not the default `daiwt_03`), then run
   `make validate UNIT=<name>` until PASS — max 3 full attempts; then stop and
   report.
5. Never edit `legacy/`, `golden/`, `data/seed/`, `validation/` or tolerances.
   Tolerance/scope changes need a human row in `.migration/06_decisions.md`.
6. Commit `.migration/evidence/<name>.json`, add your row to
   `.migration/coverage.md` (observed outcome + fix pattern), open a PR into
   `migration-run-N`.
