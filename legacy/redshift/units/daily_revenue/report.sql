-- BI report: monthly revenue by channel.
SELECT DATE_TRUNC('month', order_date)::DATE AS order_month,
       sales_channel,
       SUM(order_count)                      AS order_count,
       SUM(revenue)                          AS revenue
FROM   mart.daily_revenue
GROUP  BY 1, 2
ORDER  BY 1, 2;
