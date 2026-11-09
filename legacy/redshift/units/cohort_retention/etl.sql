-- cohort_retention: TEMP TABLE steps + DATEDIFF(month) retention matrix.
DROP TABLE IF EXISTS mart.cohort_retention;
CREATE TABLE mart.cohort_retention (
    cohort_month   DATE,
    month_offset   INT,
    cohort_size    BIGINT,
    active_buyers  BIGINT
)
SORTKEY(cohort_month, month_offset);

DROP TABLE IF EXISTS tmp_cohorts;
CREATE TEMP TABLE tmp_cohorts AS
SELECT customer_id,
       DATE_TRUNC('month', MIN(order_ts))::DATE AS cohort_month
FROM   core.orders
GROUP  BY customer_id;

DROP TABLE IF EXISTS tmp_activity;
CREATE TEMP TABLE tmp_activity AS
SELECT c.cohort_month,
       DATEDIFF(month, c.cohort_month, DATE_TRUNC('month', o.order_ts)::DATE) AS month_offset,
       COUNT(DISTINCT c.customer_id)                                     AS active_buyers
FROM   core.orders o
JOIN   tmp_cohorts c ON c.customer_id = o.customer_id
GROUP  BY c.cohort_month,
          DATEDIFF(month, c.cohort_month, DATE_TRUNC('month', o.order_ts)::DATE);

INSERT INTO mart.cohort_retention
SELECT s.cohort_month,
       s.month_offset,
       sz.cohort_size,
       s.active_buyers
FROM   tmp_activity s
JOIN (SELECT cohort_month, COUNT(*) AS cohort_size
      FROM tmp_cohorts GROUP BY cohort_month) sz
  ON sz.cohort_month = s.cohort_month
ORDER  BY s.cohort_month, s.month_offset;

DROP TABLE tmp_cohorts;
DROP TABLE tmp_activity;
