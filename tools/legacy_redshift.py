"""Operator-only Redshift runner: setup | build | capture | all.

    python tools/legacy_redshift.py all

Connects with redshift_connector (autocommit, one connection per phase).
Operators only — the captured goldens are the reference outputs.

Env: REDSHIFT_HOST, REDSHIFT_PORT (5439), REDSHIFT_USER, REDSHIFT_PASSWORD,
REDSHIFT_DATABASE (default daiwt_03_retail), REDSHIFT_ADMIN_DATABASE
(default dev; used only for CREATE DATABASE).
"""
import csv
import datetime as dt
import hashlib
import json
import os
import pathlib
import subprocess
import sys

import redshift_connector
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = ROOT / ".migration" / "units.yaml"
SEED_DIR = ROOT / "data" / "seed" / "csv"
GOLDEN_DIR = ROOT / "golden"
FOUNDATION_DIR = ROOT / "legacy" / "redshift" / "00_foundation"
LOG_DIR = ROOT / ".migration" / "evidence"
LOG_PATH = LOG_DIR / "redshift_connector_run.log"

sys.path.insert(0, str(ROOT))
from validation.sqlsplit import splitStatements

NULL_TOKEN = "\\N"
BATCH_ROWS = 500 if os.environ.get("REDSHIFT_DATA_API") == "1" else 1000

# CSV column -> Redshift value kind, for correct INSERT rendering.
TABLE_COLUMNS = {
    "customers": ["int", "str", "str", "str", "str", "str", "int", "date", "bool"],
    "stores": ["int", "str", "str", "str", "str"],
    "products": ["int", "str", "str", "str", "str", "numeric", "numeric", "bool"],
    "orders": ["int", "int", "int", "ts", "str", "str"],
    "order_items": ["int", "int", "int", "int", "numeric", "numeric"],
    "payments": ["int", "int", "str", "numeric", "ts"],
    "returns": ["int", "int", "int", "str", "ts"],
    "shipments": ["int", "int", "str", "ts", "ts"],
    "web_events": ["int", "int", "ts", "str", "str"],
    "campaign_touches": ["int", "int", "super"],
}

OID_FAMILIES = {
    16: "bool",
    20: "int", 21: "int", 23: "int",
    1700: "decimal",
    700: "float", 701: "float",
    1082: "date",
    1114: "timestamp", 1184: "timestamp",
}

_logLines = []


def log(msg):
    line = f"{dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')} {msg}"
    print(line)
    _logLines.append(line)


def writeLog():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    LOG_PATH.write_text("\n".join(_logLines) + "\n")


def env(name, default=None):
    value = os.environ.get(name, default)
    if value is None:
        raise SystemExit(f"{name} is not set")
    return value


def connect(database):
    if os.environ.get("REDSHIFT_DATA_API") == "1":
        from tools.redshift_data_api import Connection
        return Connection(database)
    conn = redshift_connector.connect(
        host=env("REDSHIFT_HOST"),
        port=int(env("REDSHIFT_PORT", "5439")),
        database=database,
        user=env("REDSHIFT_USER"),
        password=env("REDSHIFT_PASSWORD"),
    )
    conn.autocommit = True
    return conn


def loadManifest():
    with open(MANIFEST) as f:
        return yaml.safe_load(f)


def sqlLiteral(value, kind):
    if value == NULL_TOKEN or value is None:
        return "NULL"
    if kind in ("int", "numeric"):
        return value
    if kind == "bool":
        return "true" if value in ("t", "true", "1") else "false"
    if kind == "super":
        return "JSON_PARSE('" + value.replace("'", "''") + "')"
    return "'" + value.replace("'", "''") + "'"


def runStatements(cur, path):
    for statement in splitStatements(path.read_text()):
        log(f"  exec {path.name}: {statement.splitlines()[0][:80]}")
        cur.execute(statement)


def cmdSetup():
    database = env("REDSHIFT_DATABASE", "daiwt_03_retail")
    adminDb = env("REDSHIFT_ADMIN_DATABASE", "dev")

    conn = connect(adminDb)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (database,))
    if cur.fetchone() is None:
        log(f"CREATE DATABASE {database}")
        cur.execute(f'CREATE DATABASE "{database}"')
    else:
        log(f"database {database} exists")
    conn.close()

    conn = connect(database)
    cur = conn.cursor()
    log("recreating schemas core, mart")
    cur.execute("DROP SCHEMA IF EXISTS core CASCADE")
    cur.execute("DROP SCHEMA IF EXISTS mart CASCADE")
    for path in sorted(FOUNDATION_DIR.glob("*.sql")):
        runStatements(cur, path)

    for csvPath in sorted(SEED_DIR.glob("*.csv")):
        table = csvPath.stem
        kinds = TABLE_COLUMNS[table]
        with open(csvPath, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)
            rows = list(reader)
        cols = ", ".join(header)
        loaded = 0
        while loaded < len(rows):
            batch = rows[loaded : loaded + BATCH_ROWS]
            values = ",\n".join(
                "(" + ", ".join(sqlLiteral(v, k) for v, k in zip(row, kinds)) + ")"
                for row in batch
            )
            cur.execute(f"INSERT INTO core.{table} ({cols}) VALUES\n{values}")
            loaded += len(batch)
        log(f"loaded core.{table}: {loaded} rows")
    conn.close()


def unitWaveOrder(manifest):
    return [name for wave in manifest["waves"] for name in wave["units"]]


def cmdBuild():
    manifest = loadManifest()
    conn = connect(env("REDSHIFT_DATABASE", "daiwt_03_retail"))
    cur = conn.cursor()
    for name in unitWaveOrder(manifest):
        unit = manifest["units"][name]
        skip = set(unit.get("capture_skip") or [])
        for sqlFile in unit["legacy"]:
            if sqlFile in skip or not sqlFile.endswith(".sql"):
                continue
            path = ROOT / sqlFile
            if "etl.sql" not in sqlFile:
                continue
            log(f"build {name}: {sqlFile}")
            runStatements(cur, path)
    conn.close()


def renderCell(value, family):
    if value is None:
        return NULL_TOKEN
    if family == "bool":
        return "true" if value else "false"
    if family == "decimal":
        return format(value, "f")
    if family == "float":
        return repr(value)
    if family == "timestamp":
        return value.isoformat(sep=" ")
    if family == "date":
        return value.isoformat()
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def fetchOutput(cur, output):
    if "table" in output:
        schema, table = output["table"].split(".")
        source_schema = {"silver": "core", "gold": "mart"}.get(schema, schema)
        cur.execute(f"SELECT * FROM {source_schema}.{table}")
        return cur.description, cur.fetchall()
    statements = splitStatements((ROOT / output["legacy_sql"]).read_text())
    description, rows = None, []
    for statement in statements:
        cur.execute(statement)
        if cur.description:
            description, rows = cur.description, cur.fetchall()
    if description is None:
        raise RuntimeError(f"{output['legacy_sql']} produced no result set")
    return description, rows


def cmdCapture():
    manifest = loadManifest()
    conn = connect(env("REDSHIFT_DATABASE", "daiwt_03_retail"))
    cur = conn.cursor()

    for name in unitWaveOrder(manifest):
        unit = manifest["units"][name]
        for output in unit["outputs"]:
            description, rows = fetchOutput(cur, output)
            columns = []
            for col in description:
                colName = col[0].decode() if isinstance(col[0], bytes) else col[0]
                oid = col[1]
                family = OID_FAMILIES.get(oid, "string")
                if family == "string" and oid not in (1042, 1043, 25):
                    log(f"  NOTE {name}/{output['name']}: column {colName} oid {oid} -> string")
                columns.append({"name": colName.lower(), "family": family,
                                "redshift_type_oid": oid})
            families = [c["family"] for c in columns]
            rendered = [[renderCell(v, fam) for v, fam in zip(row, families)] for row in rows]
            keyIdx = [[c["name"] for c in columns].index(k) for k in output["keys"]]
            rendered.sort(key=lambda r: tuple("" if r[i] == NULL_TOKEN else r[i] for i in keyIdx))

            outDir = GOLDEN_DIR / name
            outDir.mkdir(parents=True, exist_ok=True)
            csvPath = outDir / f"{output['name']}.csv"
            with open(csvPath, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f, lineterminator="\n")
                w.writerow([c["name"] for c in columns])
                w.writerows(rendered)
            digest = hashlib.sha256(csvPath.read_bytes()).hexdigest()
            meta = {"columns": columns, "row_count": len(rendered),
                    "keys": output["keys"], "sha256": digest}
            (outDir / f"{output['name']}.meta.json").write_text(
                json.dumps(meta, indent=2) + "\n")
            log(f"captured {name}/{output['name']}: {len(rendered)} rows")

    cur.execute("SELECT version()")
    version = cur.fetchone()[0]
    seedSha = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
               for p in sorted(SEED_DIR.glob("*.csv"))}
    try:
        gitCommit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        gitCommit = None
    provenance = {
        "source": "Amazon Redshift Serverless",
        "redshift_version": version,
        "database": env("REDSHIFT_DATABASE", "daiwt_03_retail"),
        "captured_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "git_commit": gitCommit,
        "seed_csv_sha256": seedSha,
    }
    (GOLDEN_DIR / "PROVENANCE.json").write_text(json.dumps(provenance, indent=2) + "\n")
    conn.close()


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("setup", "build", "capture", "all"):
        raise SystemExit(__doc__)
    cmd = sys.argv[1]
    try:
        if cmd in ("setup", "all"):
            log("== setup")
            cmdSetup()
        if cmd in ("build", "all"):
            log("== build")
            cmdBuild()
        if cmd in ("capture", "all"):
            log("== capture")
            cmdCapture()
        log("done")
    finally:
        writeLog()


if __name__ == "__main__":
    main()
