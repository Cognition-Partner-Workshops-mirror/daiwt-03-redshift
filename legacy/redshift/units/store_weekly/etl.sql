-- store_weekly: weekly revenue per store.
DROP TABLE IF EXISTS mart.store_weekly;
CREATE TABLE mart.store_weekly
DISTKEY(store_id)
SORTKEY(store_id, week_start)
AS
SELECT o.store_id,
       DATE_TRUNC('week', o.order_ts)::DATE                        AS week_start,
       DATEADD(day, 6, DATE_TRUNC('week', o.order_ts))::DATE       AS week_end,
       DATEDIFF(week, DATE '2025-01-01',
                DATE_TRUNC('week', o.order_ts)::DATE)             AS week_number,
       COUNT(DISTINCT o.order_id)                                 AS order_count,
       SUM(oi.quantity * (oi.unit_price - oi.discount))            AS revenue
FROM   core.orders o
JOIN   core.order_items oi ON oi.order_id = o.order_id
GROUP  BY o.store_id, DATE_TRUNC('week', o.order_ts)
ORDER  BY o.store_id, week_start;
