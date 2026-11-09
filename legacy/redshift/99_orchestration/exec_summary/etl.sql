-- exec_summary: executive summary mart joining four earlier-wave marts.
-- Runs last in the nightly schedule (see refresh_schedule.yaml).
DROP TABLE IF EXISTS mart.exec_summary;
CREATE TABLE mart.exec_summary AS
SELECT 'as_of_2025-12-31'::VARCHAR(32)                 AS snapshot_label,
       DATE '2025-12-31'                               AS as_of_date,
       dr.total_revenue,
       dr.total_orders,
       ltv.avg_ltv                                     AS avg_customer_ltv,
       rr.return_pct                                   AS overall_return_pct,
       sla.avg_hours_to_deliver                        AS avg_ship_hours
FROM (SELECT SUM(revenue) AS total_revenue, SUM(order_count) AS total_orders
      FROM mart.daily_revenue) dr
CROSS JOIN (SELECT AVG(ltv) AS avg_ltv FROM mart.customer_ltv) ltv
CROSS JOIN (SELECT SUM(returned_qty)::NUMERIC(14,4) / SUM(sold_qty)::NUMERIC(14,4) * 100
                   AS return_pct FROM mart.returns_rate) rr
CROSS JOIN (SELECT SUM(avg_hours_to_deliver * delivered) / SUM(delivered)
                   AS avg_hours_to_deliver FROM mart.shipping_sla) sla;
