"""Idempotently provision the private retail warehouse in the current AWS account."""
import json
import os
import secrets
import string
import time

import boto3

REGION = os.environ.get("AWS_REGION", "us-east-1")
NAME = "daiwt-03-retail"
SECRET = "daiwt-03-redshift-connection"
TAGS = [{"key": "project", "value": "daiwt"}, {"key": "demo", "value": "03"}]


def main():
    session = boto3.Session(region_name=REGION)
    rs = session.client("redshift-serverless")
    sm = session.client("secretsmanager")
    ec2 = session.client("ec2")
    try:
        credential = json.loads(sm.get_secret_value(SecretId=SECRET)["SecretString"])
    except sm.exceptions.ResourceNotFoundException:
        credential = {
            "engine": "redshift", "username": "retail_admin",
            "password": "Aa1!" + "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(36)),
            "port": 5439, "dbname": "daiwt_03_retail", "database": "daiwt_03_retail",
            "workgroup": NAME, "region": REGION,
        }
        sm.create_secret(Name=SECRET, SecretString=json.dumps(credential),
                         Tags=[{"Key": t["key"], "Value": t["value"]} for t in TAGS])
    try:
        rs.get_namespace(namespaceName=NAME)
    except rs.exceptions.ResourceNotFoundException:
        rs.create_namespace(namespaceName=NAME, dbName="dev", adminUsername=credential["username"],
                            adminUserPassword=credential["password"], tags=TAGS)
    try:
        rs.get_workgroup(workgroupName=NAME)
    except rs.exceptions.ResourceNotFoundException:
        vpc = ec2.describe_vpcs(Filters=[{"Name": "is-default", "Values": ["true"]}])["Vpcs"][0]["VpcId"]
        groups = ec2.describe_security_groups(Filters=[{"Name": "group-name", "Values": [NAME]},
                                                       {"Name": "vpc-id", "Values": [vpc]}])["SecurityGroups"]
        if groups:
            sg = groups[0]["GroupId"]
        else:
            sg = ec2.create_security_group(
                GroupName=NAME, Description="Private retail warehouse; AWS Data API access only", VpcId=vpc,
                TagSpecifications=[{"ResourceType": "security-group",
                                    "Tags": [{"Key": t["key"], "Value": t["value"]} for t in TAGS]}])["GroupId"]
        subnets = ec2.describe_subnets(Filters=[{"Name": "vpc-id", "Values": [vpc]}])["Subnets"]
        by_az = {s["AvailabilityZone"]: s["SubnetId"] for s in subnets}
        rs.create_workgroup(workgroupName=NAME, namespaceName=NAME, baseCapacity=4, maxCapacity=4,
                            publiclyAccessible=False, securityGroupIds=[sg],
                            subnetIds=list(by_az.values())[:3], tags=TAGS)
    deadline = time.monotonic() + 1800
    while True:
        wg = rs.get_workgroup(workgroupName=NAME)["workgroup"]
        print("workgroup status:", wg["status"], flush=True)
        if wg["status"] == "AVAILABLE":
            break
        if time.monotonic() > deadline:
            raise TimeoutError("Redshift workgroup did not become available")
        time.sleep(20)
    credential["host"] = wg["endpoint"]["address"]
    sm.put_secret_value(SecretId=SECRET, SecretString=json.dumps(credential))
    print(json.dumps({"workgroup": NAME, "host": credential["host"],
                      "database": credential["database"], "region": REGION, "secret": SECRET}, indent=2))


if __name__ == "__main__":
    main()
