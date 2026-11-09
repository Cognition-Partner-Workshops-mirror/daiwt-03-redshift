-- product_perf: per-product sales with a LISTAGG of top store codes.
DROP TABLE IF EXISTS mart.product_perf;
CREATE TABLE mart.product_perf
DISTKEY(product_id)
SORTKEY(product_id)
AS
WITH per_store AS (
    SELECT oi.product_id,
           s.region,
           SUM(oi.quantity) AS units
    FROM   core.order_items oi
    JOIN   core.orders o ON o.order_id = oi.order_id
    JOIN   core.stores s ON s.store_id = o.store_id
    GROUP  BY oi.product_id, s.region
),
top_stores AS (
    SELECT product_id,
           LISTAGG(region, ',') WITHIN GROUP (ORDER BY units DESC, region)::VARCHAR(64) AS codes
    FROM (
        SELECT product_id, region, units,
               ROW_NUMBER() OVER (PARTITION BY product_id
                                  ORDER BY units DESC, region) AS rn
        FROM   per_store
    ) ranked
    WHERE  rn <= 3
    GROUP  BY product_id
),
agg AS (
    SELECT product_id,
           SUM(quantity)::BIGINT                                    AS units_sold,
           SUM(quantity * (unit_price - discount))::NUMERIC(18,2)   AS revenue
    FROM   core.order_items
    GROUP  BY product_id
)
SELECT p.product_id,
       p.category,
       COALESCE(a.units_sold, 0)  AS units_sold,
       COALESCE(a.revenue, 0)     AS revenue,
       ts.codes                   AS top_stores
FROM   core.products p
LEFT JOIN agg        a  ON a.product_id = p.product_id
LEFT JOIN top_stores ts ON ts.product_id = p.product_id
ORDER  BY p.product_id;
