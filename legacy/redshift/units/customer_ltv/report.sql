-- BI report: LTV summary per region (region is CHAR(4) — padding matters).
SELECT region,
       COUNT(*)        AS customers,
       SUM(order_count) AS orders,
       SUM(ltv)        AS total_ltv,
       AVG(ltv)        AS avg_ltv
FROM   mart.customer_ltv
GROUP  BY region
ORDER  BY region;
