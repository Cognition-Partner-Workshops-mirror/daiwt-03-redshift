-- BI report: RFM segment sizes and value.
SELECT rfm_segment,
       COUNT(*)          AS customers,
       SUM(monetary)     AS total_monetary,
       AVG(frequency)    AS avg_frequency
FROM   mart.rfm_segments
GROUP  BY rfm_segment
ORDER  BY rfm_segment;
