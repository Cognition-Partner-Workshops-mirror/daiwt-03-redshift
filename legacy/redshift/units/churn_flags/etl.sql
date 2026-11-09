-- churn_flags: plpgsql procedure with a FOR loop over customers and a temp
-- table, then CALL. Flags are computed as of the fixed literal '2025-12-31'.
DROP TABLE IF EXISTS mart.churn_flags;
CREATE TABLE mart.churn_flags (
    customer_id      BIGINT,
    last_order_date  DATE,
    days_since_order INT,
    churn_flag       VARCHAR(16)
)
DISTKEY(customer_id)
SORTKEY(customer_id);

CREATE OR REPLACE PROCEDURE sp_build_churn_flags()
AS $$
DECLARE
    rec RECORD;
BEGIN
    CREATE TEMP TABLE tmp_last_orders (
        customer_id     BIGINT,
        last_order_date DATE
    );

    INSERT INTO tmp_last_orders
    SELECT c.customer_id,
           MAX(o.order_ts)::DATE
    FROM   core.customers c
    LEFT JOIN core.orders o ON o.customer_id = c.customer_id
    GROUP  BY c.customer_id;

    FOR rec IN
        SELECT customer_id, last_order_date FROM tmp_last_orders ORDER BY customer_id
    LOOP
        INSERT INTO mart.churn_flags
        VALUES (
            rec.customer_id,
            rec.last_order_date,
            CASE WHEN rec.last_order_date IS NULL
                 THEN NULL
                 ELSE '2025-12-31'::DATE - rec.last_order_date END,
            CASE
                WHEN rec.last_order_date IS NULL                        THEN 'never_ordered'
                WHEN '2025-12-31'::DATE - rec.last_order_date > 180     THEN 'churned'
                WHEN '2025-12-31'::DATE - rec.last_order_date > 90      THEN 'at_risk'
                ELSE 'active'
            END
        );
    END LOOP;

    DROP TABLE tmp_last_orders;
END;
$$ LANGUAGE plpgsql;

CALL sp_build_churn_flags();
