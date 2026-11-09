-- attribution: SUPER/PartiQL navigation over campaign_touches payloads.
DROP TABLE IF EXISTS mart.attribution;
CREATE TABLE mart.attribution AS
SELECT tc.campaign_id::VARCHAR(16)          AS campaign_id,
       tc.channel::VARCHAR(16)              AS touch_channel,
       COUNT(*)                             AS touches,
       COUNT(DISTINCT t.customer_id)        AS customers_reached
FROM   core.campaign_touches t, t.payload.touches tc
GROUP  BY tc.campaign_id::VARCHAR(16), tc.channel::VARCHAR(16)
ORDER  BY campaign_id, touch_channel;
