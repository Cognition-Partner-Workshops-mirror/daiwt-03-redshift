# Retail Order Analytics

This is the handover package for a retail order-analytics warehouse running on
Amazon Redshift Serverless in `us-east-1`. All records are synthetic. The
deterministic fixture is anchored to 31 December 2025.

## Systems and consumers

The source database is `daiwt_03_retail` on workgroup `daiwt-03-retail`.
`core` holds ten tables: customers, stores, products, orders, order items,
payments, returns, shipments, web events, and campaign touches (131,113 rows).
`mart` holds 18 departmental marts and an executive summary. Finance uses
revenue and payment reports, merchandising uses product performance and basket
analysis, operations uses shipping and inventory, and marketing uses customer
value, churn, cohorts, and attribution.

The recorded nightly refresh begins at 02:00 UTC: load core, refresh independent
departmental marts, then build the executive summary. The scheduler handover
is `legacy/redshift/99_orchestration/refresh_schedule.yaml`; it is a specification,
not an installed scheduler. Finance's UNLOAD script is retained as source but
is not run by setup: no export destination is provisioned.

## Repository layout

- `legacy/redshift/00_foundation/`: schemas, typed source tables and SQL UDFs.
- `legacy/redshift/units/`: the 18 existing mart builds and reporting queries.
- `legacy/redshift/99_orchestration/`: refresh dependencies and executive summary.
- `data/seed/`: deterministic generator and committed fixture CSVs.
- `golden/`: live Redshift result snapshots, type metadata, checksums and provenance.
- `validation/`: offline comparison and baseline-checking harness.
- `.migration/units.yaml`: machine-readable dependency and output inventory.

SQL preserves the existing behavior, including integer arithmetic, CHAR padding,
timezone conversion, ordered aggregates, SUPER navigation and stored procedures.

## Setup and reset

Requires Python 3.10+, AWS credentials with Redshift Serverless, EC2, Secrets
Manager and Redshift Data API permissions, and network access to AWS APIs.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export AWS_REGION=us-east-1
make setup
make check
```

`make setup` idempotently creates the private workgroup (base/max 4 RPUs),
namespace, restricted security group and connection secret, then recreates
`daiwt_03_retail.core` and `.mart`, loads the committed CSVs, builds every mart
and recaptures all golden files. Credentials never need to be written locally.
The private endpoint is reached using the IAM-authorized AWS Data API.

```bash
make reset                  # source rebuild; only core/mart in daiwt_03_retail
make legacy-all             # rebuild using the configured connection
make capture-golden         # refresh snapshots without rebuilding
make seed                   # regenerate the deterministic source CSVs
```

Reset is destructive to `core` and `mart` in this source database. Coordinate
with downstream consumers before running it. It does not drop other databases
or change any external analytics platform. Goldens are changed by explicit
operator capture only, never to hide a reconciliation difference.

Connection metadata and credentials are in AWS Secrets Manager
`daiwt-03-redshift-connection`. For Data API clients, use its ARN as `SecretArn`,
workgroup `daiwt-03-retail`, and database `daiwt_03_retail`. The endpoint and port
are also in the secret; TCP access is private and the security group has no
inbound rules. Raw TCP clients require a separately authorized private network
path. `core` and `mart` are the shared consumer schemas.

## Cost and operational boundaries

Serverless compute automatically suspends when idle; do not delete the
workgroup between consumers. Persistent managed storage and the Secrets Manager
secret remain billable. Active compute is capped at 4 RPUs. There are no EC2
instances, NAT gateways, recurring refresh jobs or export buckets created here.

`make check` runs lint, the local tests and checksum/key/manifest checks. It
does not execute any remote target workload. Historical finance exports and
BI reports are SQL assets, not mocked dashboard applications.
