-- finance_export: monthly finance rollup on the fiscal calendar
-- (fiscal year starts Feb 1) via f_fiscal_qtr.
DROP TABLE IF EXISTS mart.finance_monthly;
CREATE TABLE mart.finance_monthly AS
SELECT DATE_TRUNC('month', o.order_ts)::DATE                          AS month,
       CASE WHEN EXTRACT(MONTH FROM o.order_ts) >= 2
            THEN EXTRACT(YEAR FROM o.order_ts)::INT
            ELSE EXTRACT(YEAR FROM o.order_ts)::INT - 1
       END                                                       AS fiscal_year,
       f_fiscal_qtr(TRUNC(o.order_ts)::DATE)                     AS fiscal_qtr,
       COUNT(DISTINCT o.order_id)                                AS order_count,
       SUM(oi.quantity * (oi.unit_price - oi.discount))          AS revenue
FROM   core.orders o
JOIN   core.order_items oi ON oi.order_id = o.order_id
GROUP  BY 1, 2, 3
ORDER  BY month;
