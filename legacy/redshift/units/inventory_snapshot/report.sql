-- BI report: low stock as of the snapshot.
SELECT product_id, snapshot_date, units_sold, on_hand
FROM   mart.inventory_snapshot
ORDER  BY on_hand ASC, product_id
LIMIT  50;
