-- BI report: churn flag distribution.
SELECT churn_flag,
       COUNT(*)                  AS customers,
       AVG(days_since_order)     AS avg_days_since_order
FROM   mart.churn_flags
GROUP  BY churn_flag
ORDER  BY churn_flag;
