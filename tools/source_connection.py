"""Load connection configuration in memory, then run the source warehouse operator."""
import json
import os
import runpy
import sys
from pathlib import Path

import boto3


def main():
    if os.environ.get("REDSHIFT_HOST") and os.environ.get("REDSHIFT_PASSWORD"):
        os.environ.setdefault("REDSHIFT_DATABASE", "daiwt_03_retail")
    else:
        region = os.environ.get("AWS_REGION", "us-east-1")
        sm = boto3.client("secretsmanager", region_name=region)
        response = sm.get_secret_value(SecretId=os.environ.get("REDSHIFT_SECRET", "daiwt-03-redshift-connection"))
        connection = json.loads(response["SecretString"])
        os.environ.update({
            "REDSHIFT_DATA_API": "1", "REDSHIFT_SECRET_ARN": response["ARN"],
            "REDSHIFT_WORKGROUP": connection["workgroup"],
            "REDSHIFT_DATABASE": connection["database"], "AWS_REGION": region,
        })
    if os.environ["REDSHIFT_DATABASE"] != "daiwt_03_retail":
        raise SystemExit("Source operator is restricted to daiwt_03_retail")
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    runpy.run_path(str(Path(__file__).with_name("legacy_redshift.py")), run_name="__main__")


if __name__ == "__main__":
    main()
