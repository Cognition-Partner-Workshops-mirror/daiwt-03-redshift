import datetime as dt
from decimal import Decimal
from unittest.mock import Mock

import pytest

from tools.legacy_redshift import fetchOutput
from tools.redshift_data_api import Connection, decode


def connection(monkeypatch):
    monkeypatch.setenv("REDSHIFT_WORKGROUP", "source")
    monkeypatch.setenv("REDSHIFT_SECRET_ARN", "secret-arn")
    client = Mock()
    client.execute_statement.return_value = {"Id": "statement", "SessionId": "session"}
    client.describe_statement.return_value = {"Status": "FINISHED", "HasResultSet": False}
    return Connection("source_db", client=client), client


def test_session_reuse_excludes_connection_options(monkeypatch):
    conn, client = connection(monkeypatch)
    cur = conn.cursor()
    cur.execute("SELECT %s", ("value",))
    first = client.execute_statement.call_args.kwargs
    assert first["Database"] == "source_db"
    assert first["Sql"] == "SELECT :p0"
    assert first["Parameters"] == [{"name": "p0", "value": "value"}]
    cur.execute("CREATE TEMP TABLE t (id int)")
    second = client.execute_statement.call_args.kwargs
    assert second["SessionId"] == "session"
    assert not {"Database", "WorkgroupName", "SecretArn"} & second.keys()


def test_result_pagination_and_decimal_precision(monkeypatch):
    conn, client = connection(monkeypatch)
    client.describe_statement.return_value = {"Status": "FINISHED", "HasResultSet": True}
    client.get_statement_result.side_effect = [
        {"ColumnMetadata": [{"name": "amount", "typeName": "numeric"}],
         "Records": [[{"stringValue": "12345678901234.5600"}]], "NextToken": "page2"},
        {"Records": [[{"isNull": True}]]},
    ]
    cur = conn.cursor().execute("SELECT amount FROM t")
    assert cur.description == [("amount", 1700)]
    assert cur.fetchall() == [[Decimal("12345678901234.5600")], [None]]
    assert cur.fetchone() is None
    assert client.get_statement_result.call_args.kwargs["NextToken"] == "page2"


def test_failed_statement_is_not_success(monkeypatch):
    conn, client = connection(monkeypatch)
    client.describe_statement.return_value = {"Status": "FAILED", "Error": "source error"}
    with pytest.raises(RuntimeError, match="source error"):
        conn.cursor().execute("bad SQL")


def test_source_capture_maps_logical_schema_names():
    cur = Mock()
    fetchOutput(cur, {"table": "silver.orders"})
    cur.execute.assert_called_with("SELECT * FROM core.orders")
    fetchOutput(cur, {"table": "gold.daily_revenue"})
    cur.execute.assert_called_with("SELECT * FROM mart.daily_revenue")


def test_decode_preserves_dates_and_nulls():
    assert decode({"stringValue": "2025-12-31"}, 1082) == dt.date(2025, 12, 31)
    assert decode({"stringValue": "2025-12-31 12:34:56"}, 1114).isoformat() == "2025-12-31T12:34:56"
    assert decode({"isNull": True}, 1700) is None
