# Run of show

Reusable checklist for one migration demo run.

## Pre-flight (operator)

- [ ] `pip install -r requirements.txt`
- [ ] Goldens present: `python tools/check_manifest.py` passes on `main`.
- [ ] If re-capturing: set `REDSHIFT_*` env vars, `make legacy-all` (Redshift
      only — never in migration sessions).
- [ ] `databricks labs install lakebridge && databricks labs lakebridge install-transpile`

## Run

- [ ] Orchestrator session starts on `migration-run-N` (see
      `ORCHESTRATOR_PROMPT.md`).
- [ ] `make db-setup` — empty catalog `daiwt_03` only. Foundation creates schemas and uploads seed after explicit authorization.
- [ ] Lakebridge analyze + per-unit transpile; drafts committed to run branch.
- [ ] Wave 0: `foundation` (own session via `demo-ops/FOUNDATION_PROMPT.md`,
      or orchestrator): bronze from `/Volumes/<catalog>/bronze/raw`, then
      `silver.*`, validates.
- [ ] Wave 1a: 5 parallel child sessions (one unit each).
- [ ] Wave 1b: 13 parallel child sessions.
- [ ] Wave 2: orchestration (`exec_summary` + Lakeflow job from
      `refresh_schedule.yaml`).
- [ ] Verifier session: `make validate-all`, summary table.
- [ ] Review PRs; merge run branch into `main` only by a human.

## Talking points

- Golden-snapshot recon: each child validates hermetically on its own VM.
- `expected_lakebridge` is a hypothesis — `.migration/coverage.md` is where
  observed outcomes and fix patterns accumulate (review feedback updates the
  playbook).
- Constructs that hurt: CHAR padding, NUMERIC scale, hour-boundary DATEDIFF,
  DECODE/NVL2, plpgsql procedures, SUPER navigation, UNLOAD.
