import hashlib
import json

import pytest

from validation.compare import compareOutput, loadGolden, parseValue

DEFAULT_TOL = {"decimal_abs": 0.000001, "float_rel": 1e-9, "float_abs": 1e-9, "string_rstrip": False}
COLUMNS = [("order_date", "date"), ("region", "string"), ("revenue", "decimal"), ("orders", "int"),
           ("placed_at", "timestamp"), ("share", "float"), ("active", "bool")]
GOLDEN = [
    ["2025-01-01", "WEST", "100.50", "3", "2025-01-01 10:00:00", "0.25", "true"],
    ["2025-01-01", "EAST", "20.00", "1", "2025-01-01 11:30:00.5", "0.75", "false"],
    ["2025-01-02", "WEST", None, "0", "2025-01-02 00:00:00", "1.0", None],
]
TARGET_COLUMNS = [(name, "STRING") for name, _ in COLUMNS]


def tolFor(_column):
    return DEFAULT_TOL


def run(targetRows, targetColumns=TARGET_COLUMNS, keys=("order_date", "region")):
    return compareOutput(COLUMNS, GOLDEN, targetColumns, targetRows, list(keys), tolFor)


def databricksRendering():
    return [
        ["2025-01-01", "WEST", "100.500", "3", "2025-01-01T10:00:00.000Z", "0.25", "true"],
        ["2025-01-01", "EAST", "20", "1", "2025-01-01T11:30:00.500Z", "0.75", "false"],
        ["2025-01-02", "WEST", None, "0", "2025-01-02T00:00:00.000Z", "1", None],
    ]


def test_passesOnEquivalentRenderingInAnyOrder():
    result = run(list(reversed(databricksRendering())))
    assert result["status"] == "PASS"


def test_passesWithReorderedAndUppercaseColumns():
    order = [6, 5, 4, 3, 2, 1, 0]
    columns = [(COLUMNS[i][0].upper(), "STRING") for i in order]
    rows = [[row[i] for i in order] for row in databricksRendering()]
    assert run(rows, targetColumns=columns)["status"] == "PASS"


def test_failsOnOneCentDrift():
    rows = databricksRendering()
    rows[0][2] = "100.51"
    result = run(rows)
    values = result["checks"][2]
    assert result["status"] == "FAIL"
    assert values["mismatches_by_column"] == {"revenue": 1}


def test_failsOnNullVersusValue():
    rows = databricksRendering()
    rows[2][2] = "0"
    assert run(rows)["status"] == "FAIL"


def test_failsOnCharPaddingUnlessRstripApproved():
    columns = [("region", "string"), ("n", "int")]
    golden = [["WE  ", "1"]]
    target = [["WE", "1"]]
    strict = compareOutput(columns, golden, columns, target, ["n"], tolFor)
    assert strict["status"] == "FAIL"
    relaxed = compareOutput(columns, golden, columns, target, ["n"],
                            lambda c: dict(DEFAULT_TOL, string_rstrip=True))
    assert relaxed["status"] == "PASS"


def test_reportsMissingExtraAndCount():
    rows = databricksRendering()[:2] + [["2025-01-03", "WEST", "1", "1", "2025-01-03 00:00:00", "1", "true"]]
    values = run(rows)["checks"][2]
    assert values["missing_in_target"] == 1
    assert values["extra_in_target"] == 1


def test_failsOnDuplicateTargetKeys():
    rows = databricksRendering() + [databricksRendering()[0]]
    result = run(rows)
    assert result["status"] == "FAIL"
    assert result["checks"][1]["status"] == "FAIL"
    assert result["checks"][2]["duplicate_keys_in_target"] == 1


def test_failsOnMissingColumn():
    columns = TARGET_COLUMNS[:-1]
    rows = [row[:-1] for row in databricksRendering()]
    result = run(rows, targetColumns=columns)
    assert result["status"] == "FAIL"
    assert result["checks"][0]["missing"] == ["active"]


def test_rejectsFloatKeys():
    with pytest.raises(ValueError):
        run(databricksRendering(), keys=("share",))


def test_rejectsNonUniqueGoldenKeys():
    with pytest.raises(ValueError):
        run(databricksRendering(), keys=("order_date",))


def test_parseTimestampVariants():
    assert parseValue("2025-01-01T10:00:00.000Z", "timestamp") == parseValue("2025-01-01 10:00:00", "timestamp")
    assert parseValue("2025-01-01", "timestamp") == parseValue("2025-01-01 00:00:00", "timestamp")


def test_loadGoldenChecksHashAndHeader(tmp_path):
    csvPath = tmp_path / "out.csv"
    csvPath.write_text("a,b\n1,\\N\n", encoding="utf-8")
    digest = hashlib.sha256(csvPath.read_bytes()).hexdigest()
    metaPath = tmp_path / "out.meta.json"
    metaPath.write_text(json.dumps({"columns": [{"name": "a", "family": "int"}, {"name": "b", "family": "string"}],
                                    "row_count": 1, "sha256": digest}))
    columns, rows = loadGolden(csvPath, metaPath)
    assert columns == [("a", "int"), ("b", "string")]
    assert rows == [["1", None]]
    metaPath.write_text(json.dumps({"columns": [{"name": "a", "family": "int"}, {"name": "b", "family": "string"}],
                                    "row_count": 1, "sha256": "0" * 64}))
    with pytest.raises(ValueError):
        loadGolden(csvPath, metaPath)
