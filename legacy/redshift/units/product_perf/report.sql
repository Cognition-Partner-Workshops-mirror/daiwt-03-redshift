-- BI report: category performance.
SELECT category,
       COUNT(*)      AS products,
       SUM(units_sold) AS units_sold,
       SUM(revenue)  AS revenue
FROM   mart.product_perf
GROUP  BY category
ORDER  BY category;
