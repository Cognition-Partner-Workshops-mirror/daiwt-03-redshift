from validation.sqlsplit import splitStatements


def test_splitsSimpleStatements():
    assert splitStatements("SELECT 1; SELECT 2;") == ["SELECT 1", "SELECT 2"]


def test_ignoresSemicolonsInLiteralsAndComments():
    sql = "SELECT 'a;b' AS x; -- c;d\nSELECT \"e;f\" /* g;h */ FROM t;"
    assert splitStatements(sql) == ["SELECT 'a;b' AS x", "-- c;d\nSELECT \"e;f\" /* g;h */ FROM t"]


def test_keepsDollarQuotedProcedureWhole():
    sql = (
        "CREATE OR REPLACE PROCEDURE p() AS $$\nBEGIN\n  DELETE FROM t;\n  INSERT INTO t SELECT 1;\nEND;\n$$ "
        "LANGUAGE plpgsql;\nCALL p();"
    )
    statements = splitStatements(sql)
    assert len(statements) == 2
    assert statements[1] == "CALL p()"


def test_keepsScriptingBlockWhole():
    sql = (
        "BEGIN\n  DECLARE x INT DEFAULT 0;\n  IF x = 0 THEN\n    SELECT CASE WHEN x = 0 THEN 1 ELSE 2 END;\n"
        "  END IF;\n  WHILE x < 2 DO\n    SET x = x + 1;\n  END WHILE;\nEND;\nSELECT 3;"
    )
    statements = splitStatements(sql)
    assert len(statements) == 2
    assert statements[1] == "SELECT 3"


def test_caseExpressionDoesNotSplit():
    assert splitStatements("SELECT CASE WHEN a THEN 1 END AS c FROM t; SELECT 2") == [
        "SELECT CASE WHEN a THEN 1 END AS c FROM t",
        "SELECT 2",
    ]


def test_transactionBeginIsNotABlock():
    assert splitStatements("BEGIN; DELETE FROM t; COMMIT;") == ["BEGIN", "DELETE FROM t", "COMMIT"]


def test_dropsCommentOnlyTail():
    assert splitStatements("SELECT 1;\n-- trailing note\n") == ["SELECT 1"]
