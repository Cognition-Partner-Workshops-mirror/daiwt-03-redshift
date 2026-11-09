"""Static manifest checks for .migration/units.yaml.

Checks:
- every unit's legacy files exist
- every output's golden csv + meta.json exist and sha256 matches
- declared keys exist in the golden header and are unique across rows
- no two units write the same table
- every read is silver.* or an earlier-wave write
- waves list every unit exactly once; width >= units in wave
"""
import csv
import hashlib
import json
import pathlib
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = ROOT / ".migration" / "units.yaml"


def checkManifest(path=MANIFEST):
    errors = []
    with open(path) as f:
        manifest = yaml.safe_load(f)

    units = manifest["units"]
    waves = manifest["waves"]

    # waves list every unit exactly once, width >= units listed
    listed = [u for w in waves for u in w["units"]]
    if sorted(listed) != sorted(units.keys()):
        errors.append(f"waves list {sorted(listed)} but units are {sorted(units.keys())}")
    for wave in waves:
        if len(wave["units"]) > wave["width"]:
            errors.append(f"wave {wave['wave']} has {len(wave['units'])} units > width {wave['width']}")

    waveOrder = {w["wave"]: i for i, w in enumerate(waves)}
    writes = {}
    for name, unit in units.items():
        for sqlFile in unit["legacy"]:
            if not (ROOT / sqlFile).exists():
                errors.append(f"{name}: missing file {sqlFile}")
        for table in unit["writes"]:
            if table in writes:
                errors.append(f"{table} written by both {writes[table]} and {name}")
            writes[table] = name
        for read in unit["reads"]:
            schema = read.split(".")[0]
            if schema == "silver":
                continue
            writer = writes.get(read)
            if writer is None:
                errors.append(f"{name}: reads {read} which no unit writes")
            elif waveOrder[units[writer]["wave"]] >= waveOrder[unit["wave"]]:
                errors.append(f"{name}: reads {read} written by {writer} in a later/same wave")

        for output in unit["outputs"]:
            golden = ROOT / output["golden"]
            metaPath = golden.with_suffix(".meta.json")
            if not golden.exists() or not metaPath.exists():
                errors.append(f"{name}/{output['name']}: missing golden {output['golden']}")
                continue
            meta = json.loads(metaPath.read_text())
            digest = hashlib.sha256(golden.read_bytes()).hexdigest()
            if meta["sha256"] != digest:
                errors.append(f"{name}/{output['name']}: sha256 mismatch")
            with open(golden, newline="", encoding="utf-8") as f:
                reader = csv.reader(f)
                header = next(reader)
                rows = list(reader)
            for key in output["keys"]:
                if key not in header:
                    errors.append(f"{name}/{output['name']}: key {key} not in golden header")
            keyIdx = [header.index(k) for k in output["keys"] if k in header]
            if len(keyIdx) == len(output["keys"]):
                seen = [tuple(r[i] for i in keyIdx) for r in rows]
                if len(seen) != len(set(seen)):
                    errors.append(f"{name}/{output['name']}: keys not unique in golden")
            if meta["row_count"] != len(rows):
                errors.append(f"{name}/{output['name']}: meta row_count != csv rows")

    return errors


def main():
    errors = checkManifest()
    for e in errors:
        print(f"ERROR: {e}")
    if errors:
        sys.exit(1)
    print("manifest OK")


if __name__ == "__main__":
    main()
