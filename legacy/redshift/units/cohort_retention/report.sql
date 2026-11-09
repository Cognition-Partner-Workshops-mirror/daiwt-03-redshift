-- BI report: retention share per cohort x month offset.
SELECT cohort_month,
       month_offset,
       cohort_size,
       active_buyers,
       ROUND(100.0 * active_buyers / cohort_size, 2) AS retention_pct
FROM   mart.cohort_retention
ORDER  BY cohort_month, month_offset;
