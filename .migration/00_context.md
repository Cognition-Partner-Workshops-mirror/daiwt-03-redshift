# Source contract

The live Amazon Redshift Serverless source database is `daiwt_03_retail`, with
ten seeded tables in `core` and 18 marts plus executive summary in `mart`.
The private workgroup is `daiwt-03-retail` in `us-east-1`. Use AWS Secrets
Manager `daiwt-03-redshift-connection` through the AWS Data API.

`golden/` contains sorted, keyed source query outputs. Provenance records the
database, engine version, source revision and seed checksums. The reporting
anchor is `2025-12-31`. No replacement implementation exists in this branch.

The optional external reconciliation namespace is `daiwt_03` (`MIG_CATALOG`).
It is intentionally empty. Source/output schema mappings in the manifest are
comparison metadata, not deployed tables. The source capture operator maps
these logical names back to Redshift `core` and `mart` before querying.
