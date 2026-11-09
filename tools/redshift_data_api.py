"""Small DB-API-compatible cursor for private Redshift source operations."""
import datetime as dt
import os
import time
from decimal import Decimal

import boto3

TYPE_OIDS = {
    "bool": 16, "boolean": 16, "int2": 21, "int4": 23, "int8": 20,
    "smallint": 21, "integer": 23, "bigint": 20,
    "numeric": 1700, "decimal": 1700, "float4": 700, "float8": 701,
    "date": 1082, "timestamp": 1114, "timestamptz": 1184,
    "bpchar": 1042, "char": 1042, "varchar": 1043, "text": 25, "super": 4000,
}


def decode(field, oid):
    if field.get("isNull"):
        return None
    value = next(iter(field.values()))
    if oid == 1700:
        return Decimal(value)
    if oid == 1082:
        return dt.date.fromisoformat(value)
    if oid in (1114, 1184):
        return dt.datetime.fromisoformat(value)
    return value


class Connection:
    def __init__(self, database, client=None):
        self.client = client or boto3.client("redshift-data", region_name=os.environ.get("AWS_REGION", "us-east-1"))
        self.options = {
            "Database": database,
            "WorkgroupName": os.environ["REDSHIFT_WORKGROUP"],
            "SecretArn": os.environ["REDSHIFT_SECRET_ARN"],
            "SessionKeepAliveSeconds": 300,
        }
        self.session_id = None
        self.autocommit = True

    def cursor(self):
        return Cursor(self)

    def close(self):
        self.session_id = None


class Cursor:
    def __init__(self, connection):
        self.connection = connection
        self.description = None
        self.rows = []

    def execute(self, sql, parameters=None):
        connection = self.connection
        args = dict(connection.options, Sql=sql)
        if connection.session_id:
            args = {"Sql": sql, "SessionId": connection.session_id, "SessionKeepAliveSeconds": 300}
        if parameters:
            parts = sql.split("%s")
            if len(parts) != len(parameters) + 1:
                raise ValueError("SQL parameter count mismatch")
            args["Sql"] = "".join(p + f":p{i}" for i, p in enumerate(parts[:-1])) + parts[-1]
            args["Parameters"] = [{"name": f"p{i}", "value": str(v)} for i, v in enumerate(parameters)]
        response = connection.client.execute_statement(**args)
        connection.session_id = response.get("SessionId", connection.session_id)
        statement_id = response["Id"]
        deadline = time.monotonic() + 900
        while True:
            status = connection.client.describe_statement(Id=statement_id)
            if status["Status"] == "FINISHED":
                break
            if status["Status"] in ("FAILED", "ABORTED"):
                raise RuntimeError(status.get("Error", status["Status"]))
            if time.monotonic() > deadline:
                connection.client.cancel_statement(Id=statement_id)
                raise TimeoutError("Redshift statement timed out")
            time.sleep(0.5)
        self.description, self.rows = None, []
        if status.get("HasResultSet"):
            options = {"Id": statement_id}
            while True:
                result = connection.client.get_statement_result(**options)
                if self.description is None:
                    self.description = [
                        (c["name"], TYPE_OIDS[c["typeName"].lower()]) for c in result["ColumnMetadata"]
                    ]
                self.rows.extend([
                    [decode(f, col[1]) for f, col in zip(row, self.description)] for row in result["Records"]
                ])
                if not result.get("NextToken"):
                    break
                options["NextToken"] = result["NextToken"]
        return self

    def fetchone(self):
        return self.rows.pop(0) if self.rows else None

    def fetchall(self):
        rows, self.rows = self.rows, []
        return rows
