-- BI report: payment family mix.
SELECT method_family,
       SUM(payment_count) AS payment_count,
       SUM(amount_total)  AS amount_total
FROM   mart.payment_mix
GROUP  BY method_family
ORDER  BY method_family;
