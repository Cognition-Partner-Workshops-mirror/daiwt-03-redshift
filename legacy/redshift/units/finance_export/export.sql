-- Monthly finance export to S3. Placeholders — never executed at capture
-- (listed in the unit's capture_skip in .migration/units.yaml).
UNLOAD ('SELECT * FROM mart.finance_monthly ORDER BY month')
TO 's3://<bucket>/finance_export/monthly/'
IAM_ROLE '<role-arn>'
PARALLEL OFF
CSV
HEADER;
