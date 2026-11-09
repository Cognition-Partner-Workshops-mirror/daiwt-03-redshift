"""Databricks SQL client for the validation harness (Statement Execution API).

Connection comes from the standard Databricks SDK config: DATABRICKS_HOST +
DATABRICKS_TOKEN, or DATABRICKS_CONFIG_PROFILE. The warehouse comes from
DATABRICKS_WAREHOUSE_ID and the migration catalog from MIG_CATALOG.
"""
import os
import time

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import Disposition, Format, StatementState

DEFAULT_CATALOG = "daiwt_03"
_pendingStates = {StatementState.PENDING, StatementState.RUNNING}


def warehouseId():
    value = os.environ.get("DATABRICKS_WAREHOUSE_ID")
    if not value:
        raise SystemExit("DATABRICKS_WAREHOUSE_ID is not set")
    return value


def catalogName():
    return os.environ.get("MIG_CATALOG", DEFAULT_CATALOG)


class DbSql:
    def __init__(self, catalog=None, warehouse=None, client=None):
        self.client = client or WorkspaceClient()
        self.catalog = catalog or catalogName()
        self.warehouse = warehouse or warehouseId()

    def run(self, statement):
        """Run one statement; return (columns, rows). Rows are lists of str|None."""
        resp = self.client.statement_execution.execute_statement(
            statement=statement,
            warehouse_id=self.warehouse,
            catalog=self.catalog,
            disposition=Disposition.INLINE,
            format=Format.JSON_ARRAY,
            wait_timeout="50s",
        )
        while resp.status.state in _pendingStates:
            time.sleep(2)
            resp = self.client.statement_execution.get_statement(resp.statement_id)
        if resp.status.state != StatementState.SUCCEEDED:
            error = resp.status.error.message if resp.status.error else resp.status.state
            raise RuntimeError(f"Databricks SQL failed: {error}\n{statement[:400]}")
        columns = []
        if resp.manifest and resp.manifest.schema and resp.manifest.schema.columns:
            columns = [
                (c.name, c.type_name.value if c.type_name else (c.type_text or ""))
                for c in resp.manifest.schema.columns
            ]
        rows = []
        chunkIndex = None
        if resp.result:
            rows.extend(resp.result.data_array or [])
            chunkIndex = resp.result.next_chunk_index
        while chunkIndex is not None:
            chunk = self.client.statement_execution.get_statement_result_chunk_n(
                resp.statement_id, chunkIndex
            )
            rows.extend(chunk.data_array or [])
            chunkIndex = chunk.next_chunk_index
        return columns, rows
