-- BI report: campaign reach by channel.
SELECT campaign_id,
       SUM(touches)          AS touches,
       SUM(customers_reached) AS customers_reached
FROM   mart.attribution
GROUP  BY campaign_id
ORDER  BY campaign_id;
