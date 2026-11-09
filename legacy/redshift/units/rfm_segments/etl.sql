-- rfm_segments: NTILE(5) over recency/frequency/monetary as of '2025-12-31',
-- including customers with NULL metrics (NULL ordering matters).
DROP TABLE IF EXISTS mart.rfm_segments;
CREATE TABLE mart.rfm_segments
DISTKEY(customer_id)
SORTKEY(customer_id)
AS
WITH metrics AS (
    SELECT c.customer_id,
           DATEDIFF(day, MAX(o.order_ts)::DATE, DATE '2025-12-31')        AS recency_days,
           COUNT(DISTINCT o.order_id)                                    AS frequency,
           COALESCE(SUM(oi.quantity * (oi.unit_price - oi.discount)), 0) AS monetary
    FROM   core.customers c
    LEFT JOIN core.orders      o  ON o.customer_id = c.customer_id
    LEFT JOIN core.order_items oi ON oi.order_id   = o.order_id
    GROUP  BY c.customer_id
),
tiles AS (
    SELECT customer_id,
           recency_days,
           frequency,
           monetary,
           NTILE(5) OVER (ORDER BY recency_days ASC, customer_id)             AS r_tile,
           NTILE(5) OVER (ORDER BY frequency   DESC,            customer_id)  AS f_tile,
           NTILE(5) OVER (ORDER BY monetary    DESC,            customer_id)  AS m_tile
    FROM   metrics
)
SELECT customer_id,
       recency_days,
       frequency,
       monetary,
       r_tile,
       f_tile,
       m_tile,
       (r_tile::VARCHAR || f_tile::VARCHAR || m_tile::VARCHAR)::VARCHAR(3) AS rfm_segment
FROM   tiles
ORDER  BY customer_id;
