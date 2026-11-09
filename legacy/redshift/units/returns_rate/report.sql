-- BI report: returns rate as published.
SELECT category, sold_qty, returned_qty, return_rate_int, return_pct
FROM   mart.returns_rate
ORDER  BY return_pct DESC, category;
