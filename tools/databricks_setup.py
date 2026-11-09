"""Create an empty external analytics catalog only; never create tables or volumes."""
import os
import time

from databricks.sdk import WorkspaceClient


def run_sql(w, statement):
    result = w.statement_execution.execute_statement(
        warehouse_id=os.environ["DATABRICKS_WAREHOUSE_ID"], statement=statement, wait_timeout="50s")
    while result.status.state.value in ("PENDING", "RUNNING"):
        time.sleep(2)
        result = w.statement_execution.get_statement(result.statement_id)
    if result.status.state.value != "SUCCEEDED":
        raise RuntimeError(result.status.error)


def main():
    name = os.environ.get("MIG_CATALOG", "daiwt_03")
    if name != "daiwt_03":
        raise SystemExit("Only daiwt_03 is permitted")
    w = WorkspaceClient()
    run_sql(w, f"CREATE CATALOG IF NOT EXISTS {name}")
    run_sql(w, f"GRANT ALL PRIVILEGES ON CATALOG {name} TO `account users`")
    print(f"Empty catalog {name} ready; no tables, schemas or volumes created")


if __name__ == "__main__":
    main()
