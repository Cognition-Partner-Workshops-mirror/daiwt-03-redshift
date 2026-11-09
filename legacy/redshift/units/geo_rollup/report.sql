-- BI report: the rollup as published (NULL grouping columns included).
SELECT grouping_id, region, state, order_count, revenue
FROM   mart.geo_rollup
ORDER  BY grouping_id, region, state;
