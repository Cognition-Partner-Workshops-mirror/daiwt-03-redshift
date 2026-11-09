-- BI report: top affinities with product names.
SELECT b.product_id_a,
       b.product_id_b,
       pa.product_name || ' + ' || pb.product_name AS pair,
       b.pair_orders
FROM   mart.basket_affinity b
JOIN   core.products pa ON pa.product_id = b.product_id_a
JOIN   core.products pb ON pb.product_id = b.product_id_b
ORDER  BY b.pair_orders DESC, b.product_id_a, b.product_id_b
LIMIT  50;
