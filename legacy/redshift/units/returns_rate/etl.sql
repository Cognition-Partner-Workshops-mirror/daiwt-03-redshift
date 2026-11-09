-- returns_rate: returns per category. return_rate_int is INTEGER division
-- (INT/INT); return_pct uses an explicit :: cast.
DROP TABLE IF EXISTS mart.returns_rate;
CREATE TABLE mart.returns_rate AS
SELECT p.category,
       SUM(oi.quantity)::BIGINT                          AS sold_qty,
       COALESCE(SUM(r.quantity), 0)::BIGINT              AS returned_qty,
       COALESCE(SUM(r.quantity), 0) / SUM(oi.quantity)   AS return_rate_int,
       (COALESCE(SUM(r.quantity), 0)::NUMERIC(14,4)
           / SUM(oi.quantity)::NUMERIC(14,4)) * 100      AS return_pct
FROM   core.order_items oi
JOIN   core.products p   ON p.product_id     = oi.product_id
LEFT JOIN core.returns r ON r.order_item_id  = oi.order_item_id
GROUP  BY p.category
ORDER  BY p.category;
