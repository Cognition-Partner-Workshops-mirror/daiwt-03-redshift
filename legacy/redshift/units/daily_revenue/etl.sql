-- daily_revenue: revenue and order count per day x channel.
DROP TABLE IF EXISTS mart.daily_revenue;
CREATE TABLE mart.daily_revenue
DISTSTYLE ALL
SORTKEY(order_date, sales_channel)
AS
SELECT TRUNC(o.order_ts)::DATE                       AS order_date,
       o.sales_channel                               AS sales_channel,
       COUNT(DISTINCT o.order_id)                    AS order_count,
       SUM(oi.quantity * (oi.unit_price - oi.discount)) AS revenue
FROM   core.orders o
JOIN   core.order_items oi ON oi.order_id = o.order_id
GROUP  BY 1, 2
ORDER  BY 1, 2;
