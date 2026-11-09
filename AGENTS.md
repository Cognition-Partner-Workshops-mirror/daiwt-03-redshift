# Warehouse handover guardrails

- This main branch is the source estate, not an implemented replacement.
- Source rebuilds and golden capture are explicit operator actions only.
- The operator may recreate `core` and `mart` only in `daiwt_03_retail` on
  workgroup `daiwt-03-retail`. Never write to other Redshift databases.
- Reconciliation sessions treat `legacy/`, `golden/`, `data/seed/` and
  `validation/` as read-only. Fix a changed implementation, not the baseline.
- External analytics writes are restricted to catalog `daiwt_03`.
- Never print or commit credentials. Use AWS Secrets Manager references.
- Keep calculations deterministic: the reporting anchor is `2025-12-31`.
- Reset affects the shared source schemas; coordinate with downstream consumers.
