-- BI report: sessions per customer.
SELECT customer_id,
       COUNT(*)              AS sessions,
       SUM(event_count)      AS events,
       SUM(checkout_events)  AS checkout_sessions
FROM   mart.web_sessions
GROUP  BY customer_id
ORDER  BY customer_id;
