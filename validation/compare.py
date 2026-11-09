"""Compare a Databricks result set against a committed golden output.

Golden format (written by tools/legacy_redshift.py capture):
  <name>.csv       header row of lowercase column names; NULL is the literal \\N
  <name>.meta.json {"columns": [{"name", "family"}], "row_count", "sha256"}
Families: int, decimal, float, bool, date, timestamp, string.
Both sides are parsed with the golden family, then matched row-by-row on the
output's key columns.
"""
import csv
import datetime as dt
import hashlib
import json
import math
import re
from decimal import Decimal, InvalidOperation

NULL_TOKEN = "\\N"
FAMILIES = {"int", "decimal", "float", "bool", "date", "timestamp", "string"}
MAX_SAMPLES = 20
_tzSuffixRe = re.compile(r"[+-]\d{2}(:?\d{2})?$")


def loadGolden(csvPath, metaPath):
    with open(metaPath) as f:
        meta = json.load(f)
    with open(csvPath, "rb") as f:
        digest = hashlib.sha256(f.read()).hexdigest()
    if meta.get("sha256") and meta["sha256"] != digest:
        raise ValueError(f"{csvPath} does not match the sha256 in {metaPath}")
    with open(csvPath, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = [[None if v == NULL_TOKEN else v for v in row] for row in reader]
    columns = [(c["name"], c["family"]) for c in meta["columns"]]
    if [c[0] for c in columns] != header:
        raise ValueError(f"{csvPath} header does not match {metaPath}")
    return columns, rows


def parseValue(raw, family, stringRstrip=False):
    if raw is None:
        return None
    if family in ("int", "decimal"):
        try:
            return Decimal(raw)
        except InvalidOperation:
            raise ValueError(f"not numeric: {raw!r}")
    if family == "float":
        return float(raw)
    if family == "bool":
        lowered = raw.strip().lower()
        if lowered in ("true", "t", "1"):
            return True
        if lowered in ("false", "f", "0"):
            return False
        raise ValueError(f"not boolean: {raw!r}")
    if family == "date":
        return dt.date.fromisoformat(raw.strip()[:10])
    if family == "timestamp":
        text = raw.strip().replace("T", " ")
        text = text.removesuffix("Z")
        if len(text) == 10:
            text += " 00:00:00"
        text = _tzSuffixRe.sub("", text)
        if "." in text:
            whole, fraction = text.split(".", 1)
            text = f"{whole}.{(fraction + '000000')[:6]}"
        value = dt.datetime.fromisoformat(text)
        return value.replace(tzinfo=None)
    if family == "string":
        return raw.rstrip(" ") if stringRstrip else raw
    raise ValueError(f"unknown family {family!r}")


def valuesEqual(goldenValue, targetValue, family, tol):
    if goldenValue is None or targetValue is None:
        return goldenValue is None and targetValue is None
    if family == "decimal":
        return abs(goldenValue - targetValue) <= Decimal(str(tol["decimal_abs"]))
    if family == "float":
        if math.isnan(goldenValue) or math.isnan(targetValue):
            return math.isnan(goldenValue) and math.isnan(targetValue)
        return math.isclose(
            goldenValue, targetValue, rel_tol=tol["float_rel"], abs_tol=tol["float_abs"]
        )
    return goldenValue == targetValue


def _keyValue(value):
    if isinstance(value, Decimal):
        return value.normalize()
    return value


def _render(value):
    if value is None:
        return None
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, (dt.date, dt.datetime)):
        return value.isoformat(sep=" ") if isinstance(value, dt.datetime) else value.isoformat()
    return value


def compareOutput(goldenColumns, goldenRows, targetColumns, targetRows, keys, tolFor):
    """tolFor(column) -> tolerance dict for that column."""
    checks = []
    goldenNames = [c[0] for c in goldenColumns]
    families = dict(goldenColumns)
    targetNames = [c[0].lower() for c in targetColumns]

    missingCols = [c for c in goldenNames if c not in targetNames]
    extraCols = [c for c in targetNames if c not in goldenNames]
    colsOk = not missingCols and not extraCols
    checks.append({
        "check": "columns",
        "status": "PASS" if colsOk else "FAIL",
        "missing": missingCols,
        "extra": extraCols,
        "target_types": {name: typ for name, typ in targetColumns},
    })

    countOk = len(goldenRows) == len(targetRows)
    checks.append({
        "check": "row_count",
        "status": "PASS" if countOk else "FAIL",
        "golden": len(goldenRows),
        "target": len(targetRows),
    })

    if missingCols:
        checks.append({"check": "row_values", "status": "FAIL", "detail": "skipped: missing columns"})
        return _result(checks)

    badFamilies = [k for k in keys if families.get(k) == "float"]
    if badFamilies or any(k not in families for k in keys) or not keys:
        raise ValueError(f"invalid keys {keys}: must be non-empty, existing, non-float columns")

    targetIndex = [targetNames.index(c) for c in goldenNames]

    def parseRow(raw, fromTarget):
        values = {}
        for pos, name in enumerate(goldenNames):
            cell = raw[targetIndex[pos]] if fromTarget else raw[pos]
            values[name] = parseValue(cell, families[name], tolFor(name)["string_rstrip"])
        return values

    def index(rows, fromTarget, label):
        indexed, duplicates = {}, []
        for raw in rows:
            parsed = parseRow(raw, fromTarget)
            key = tuple(_keyValue(parsed[k]) for k in keys)
            if key in indexed:
                duplicates.append([_render(v) for v in key])
            indexed[key] = parsed
        if duplicates and label == "golden":
            raise ValueError(f"golden keys {keys} are not unique, e.g. {duplicates[:3]}")
        return indexed, duplicates

    goldenIndex, _ = index(goldenRows, False, "golden")
    targetIndexed, targetDuplicates = index(targetRows, True, "target")

    missingKeys = [k for k in goldenIndex if k not in targetIndexed]
    extraKeys = [k for k in targetIndexed if k not in goldenIndex]
    mismatches = []
    columnMismatchCounts = {}
    for key, goldenValues in goldenIndex.items():
        targetValues = targetIndexed.get(key)
        if targetValues is None:
            continue
        diffs = {}
        for name in goldenNames:
            if not valuesEqual(goldenValues[name], targetValues[name], families[name], tolFor(name)):
                diffs[name] = {"golden": _render(goldenValues[name]), "target": _render(targetValues[name])}
                columnMismatchCounts[name] = columnMismatchCounts.get(name, 0) + 1
        if diffs:
            mismatches.append({"key": [_render(v) for v in key], "diffs": diffs})

    valuesOk = not missingKeys and not extraKeys and not mismatches and not targetDuplicates
    checks.append({
        "check": "row_values",
        "status": "PASS" if valuesOk else "FAIL",
        "keys": keys,
        "matched_rows": len(goldenIndex) - len(missingKeys) - len(mismatches),
        "mismatched_rows": len(mismatches),
        "missing_in_target": len(missingKeys),
        "extra_in_target": len(extraKeys),
        "duplicate_keys_in_target": len(targetDuplicates),
        "mismatches_by_column": columnMismatchCounts,
        "sample_mismatches": mismatches[:MAX_SAMPLES],
        "sample_missing": [[_render(v) for v in k] for k in missingKeys[:MAX_SAMPLES]],
        "sample_extra": [[_render(v) for v in k] for k in extraKeys[:MAX_SAMPLES]],
    })
    return _result(checks)


def _result(checks):
    status = "PASS" if all(c["status"] == "PASS" for c in checks) else "FAIL"
    return {"status": status, "checks": checks}
