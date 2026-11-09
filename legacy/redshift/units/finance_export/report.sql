-- BI report: fiscal-year revenue summary.
SELECT fiscal_year, fiscal_qtr,
       SUM(order_count) AS order_count,
       SUM(revenue)     AS revenue
FROM   mart.finance_monthly
GROUP  BY fiscal_year, fiscal_qtr
ORDER  BY fiscal_year, fiscal_qtr;
