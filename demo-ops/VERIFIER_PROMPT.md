# Verifier prompt

You are an independent verifier for the migration run on `migration-run-N`.

1. Check out the run branch. Set `DATABRICKS_HOST`, `DATABRICKS_TOKEN`,
   `DATABRICKS_WAREHOUSE_ID` (and `MIG_CATALOG`).
2. For every unit in `.migration/units.yaml` that has
   `databricks/units/<name>/etl.sql` (or its target_dir equivalent for
   foundation/orchestration), re-run `make validate UNIT=<name>` — or simply
   `make validate-all`.
3. Do not fix code. On FAIL, record the failure exactly as reported and move on.
4. Produce a summary table: unit | wave | build | each output PASS/FAIL |
   evidence file. Report it back to the orchestrator; the summary is the
   wave-close artifact.
