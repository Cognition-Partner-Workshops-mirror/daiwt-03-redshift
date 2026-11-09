# Orchestrator prompt

You are the orchestrator of a Redshift → Databricks SQL migration run for this
repository. Read `AGENTS.md`, `.migration/00_context.md` and
`.migration/units.yaml` first.

## Steps

1. Create the run integration branch `migration-run-N` from `main` (or use it
   if it already exists).
2. Run Lakebridge analyze + per-unit transpile yourself (the repo is a pure
   "before" estate — run the commands live, no wrappers):

   ```bash
   databricks labs install lakebridge                 # if `databricks labs lakebridge --help` fails
   databricks labs lakebridge install-transpile
   mkdir -p .migration/lakebridge/transpiled .migration/lakebridge/errors
   databricks labs lakebridge analyze \
     --source-directory legacy/redshift \
     --source-tech Redshift \
     --report-file .migration/lakebridge/analyze.xlsx \
     --generate-json true

   # optional read-only Redshift discovery (only if AWS creds are present):
   aws redshift-data execute-statement \
     --workgroup-name "$REDSHIFT_WORKGROUP" \
     --database daiwt_03_retail \
     --secret-arn "$REDSHIFT_SECRET_ARN" \
     --sql "<SELECT ...>"        # SELECT / information_schema / svv_* only —
                                # confirm the core/mart table inventory and row
                                # counts against .migration/units.yaml

   # per unit <u> in .migration/units.yaml:
   databricks labs lakebridge transpile \
     --input-source legacy/redshift/units/<u> \
     --output-folder .migration/lakebridge/transpiled/<u> \
     --source-dialect redshift \
     --error-file-path .migration/lakebridge/errors/<u>.log \
     --skip-validation false \
     --catalog-name "$MIG_CATALOG" \
     --schema-name gold
   ```

   `--source-tech` must be exactly `Redshift` (case-sensitive; any other value
   makes analyze prompt interactively). Then commit `.migration/lakebridge/`
   to the run branch. Lakebridge output is a draft, never the merge gate.
3. Run wave 0 (`foundation`): if `databricks/foundation/` is already on the
   run branch (pre-built with `demo-ops/FOUNDATION_PROMPT.md`), run
   `make validate UNIT=foundation` and continue. Otherwise build it yourself:
   bronze Delta tables from `/Volumes/<catalog>/bronze/raw` (seed CSVs
   uploaded by `make db-setup`), then typed `silver.*` tables mirroring the
   Redshift core DDL, and validate against the foundation goldens.
4. Launch wave 1a (width 5) and wave 1b (width 13) as parallel child sessions —
   one unit each — using `demo-ops/CHILD_UNIT_PROMPT.md`. Never exceed wave
   width; children branch `unit/<name>` from `migration-run-N` and PR back into
   it.
5. After both waves merge, run wave 2 (`orchestration`): `exec_summary` +
   turn `refresh_schedule.yaml` into a Lakeflow job in the DAB.
6. Launch the verifier (`demo-ops/VERIFIER_PROMPT.md`) to re-validate every
   merged unit.

Report per wave: units PASS/FAIL, evidence files, coverage.md updates.
