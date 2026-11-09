"""Validate one migrated unit on Databricks SQL against its committed goldens.

    python -m validation.validate_unit --unit daily_revenue
    python -m validation.validate_unit --unit daily_revenue --skip-build

Steps: run the unit's converted etl.sql (unless --skip-build), fetch each
output declared in .migration/units.yaml (a table or the converted report
query), compare it with golden/<unit>/<output>.csv on this machine, write
.migration/evidence/<unit>.json and exit non-zero on any FAIL.
"""
import argparse
import datetime as dt
import json
import pathlib
import subprocess
import sys

import yaml

from validation.compare import compareOutput, loadGolden
from validation.dbsql import DbSql
from validation.sqlsplit import splitStatements

ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = ROOT / ".migration" / "units.yaml"
TOLERANCES = ROOT / "validation" / "tolerances.yaml"
EVIDENCE_DIR = ROOT / ".migration" / "evidence"
DECISIONS = ROOT / ".migration" / "06_decisions.md"


def loadYaml(path):
    with open(path) as f:
        return yaml.safe_load(f)


def toleranceLookup(tolerances, unit, output):
    default = dict(tolerances["default"])
    overrides = ((tolerances.get("overrides") or {}).get(unit) or {}).get(output) or {}
    decisionsText = DECISIONS.read_text() if DECISIONS.exists() else ""
    for column, override in overrides.items():
        decision = override.get("decision")
        if not decision or decision not in decisionsText:
            raise SystemExit(
                f"tolerance override {unit}.{output}.{column} has no decision recorded in {DECISIONS.name}"
            )

    def tolFor(column):
        merged = dict(default)
        merged.update({k: v for k, v in (overrides.get(column) or {}).items() if k != "decision"})
        return merged

    return tolFor, {c: o for c, o in overrides.items()}


def runFile(db, path):
    for statement in splitStatements(path.read_text()):
        db.run(statement)


def fetchOutput(db, output):
    if "table" in output:
        return db.run(f"SELECT * FROM {output['table']}")
    sqlPath = ROOT / output["target_sql"]
    if not sqlPath.exists():
        raise FileNotFoundError(f"{output['target_sql']} does not exist yet")
    statements = splitStatements(sqlPath.read_text())
    result = ([], [])
    for statement in statements:
        result = db.run(statement)
    return result


def gitCommit():
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def validateUnit(unitName, skipBuild=False, db=None):
    manifest = loadYaml(MANIFEST)
    units = manifest["units"]
    if unitName not in units:
        raise SystemExit(f"unknown unit {unitName!r}; see {MANIFEST.relative_to(ROOT)}")
    unit = units[unitName]
    tolerances = loadYaml(TOLERANCES)
    db = db or DbSql()

    evidence = {
        "unit": unitName,
        "engine": "databricks_sql",
        "catalog": db.catalog,
        "warehouse_id": db.warehouse,
        "git_commit": gitCommit(),
        "started_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "build": None,
        "outputs": [],
    }

    etlPath = ROOT / unit["target_dir"] / "etl.sql"
    if skipBuild:
        evidence["build"] = {"status": "SKIPPED"}
    elif not etlPath.exists():
        evidence["build"] = {"status": "FAIL", "detail": f"{etlPath.relative_to(ROOT)} does not exist"}
    else:
        try:
            runFile(db, etlPath)
            evidence["build"] = {"status": "PASS", "file": str(etlPath.relative_to(ROOT))}
        except RuntimeError as exc:
            evidence["build"] = {"status": "FAIL", "detail": str(exc)[:2000]}

    if evidence["build"]["status"] != "FAIL":
        for output in unit["outputs"]:
            tolFor, overrides = toleranceLookup(tolerances, unitName, output["name"])
            goldenCsv = ROOT / output["golden"]
            goldenMeta = goldenCsv.with_suffix(".meta.json")
            record = {"output": output["name"], "golden": output["golden"],
                      "target": output.get("table") or output.get("target_sql"),
                      "tolerance_overrides": overrides}
            try:
                goldenColumns, goldenRows = loadGolden(goldenCsv, goldenMeta)
                targetColumns, targetRows = fetchOutput(db, output)
                record.update(compareOutput(goldenColumns, goldenRows, targetColumns,
                                            targetRows, output["keys"], tolFor))
            except (RuntimeError, FileNotFoundError, ValueError) as exc:
                record.update({"status": "FAIL", "checks": [], "error": str(exc)[:2000]})
            evidence["outputs"].append(record)

    statuses = [evidence["build"]["status"]] + [o["status"] for o in evidence["outputs"]]
    evidence["status"] = "FAIL" if "FAIL" in statuses else "PASS"
    evidence["finished_at"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    (EVIDENCE_DIR / f"{unitName}.json").write_text(json.dumps(evidence, indent=2) + "\n")
    return evidence


def printSummary(evidence):
    print(f"unit {evidence['unit']}: {evidence['status']}  (catalog {evidence['catalog']})")
    print(f"  build: {evidence['build']['status']} {evidence['build'].get('detail', '')[:300]}")
    for output in evidence["outputs"]:
        print(f"  output {output['output']}: {output['status']}")
        if output.get("error"):
            print(f"    error: {output['error'][:300]}")
        for check in output.get("checks", []):
            extra = ""
            if check["check"] == "row_count":
                extra = f"golden={check['golden']} target={check['target']}"
            elif check["check"] == "columns" and check["status"] == "FAIL":
                extra = f"missing={check['missing']} extra={check['extra']}"
            elif check["check"] == "row_values" and "mismatched_rows" in check:
                extra = (f"mismatched={check['mismatched_rows']} missing={check['missing_in_target']} "
                         f"extra={check['extra_in_target']} by_column={check['mismatches_by_column']}")
            print(f"    {check['check']}: {check['status']} {extra}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--unit", required=True)
    parser.add_argument("--skip-build", action="store_true", help="compare existing tables without running etl.sql")
    args = parser.parse_args()
    evidence = validateUnit(args.unit, skipBuild=args.skip_build)
    printSummary(evidence)
    sys.exit(0 if evidence["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
