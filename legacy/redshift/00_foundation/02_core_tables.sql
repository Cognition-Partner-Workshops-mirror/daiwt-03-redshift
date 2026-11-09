-- core.* landing tables: append-only raw extract, Redshift-flavored DDL.
CREATE TABLE core.customers (
    customer_id         BIGINT NOT NULL,
    email               VARCHAR(320) ENCODE lzo,
    first_name          VARCHAR(64),
    last_name           VARCHAR(64),
    phone               VARCHAR(32),
    region              CHAR(4) ENCODE lzo,
    preferred_store_id  INT,
    signup_date         DATE,
    is_business         BOOLEAN
)
DISTKEY(customer_id)
SORTKEY(customer_id);

CREATE TABLE core.stores (
    store_id    INT NOT NULL,
    region      CHAR(4) ENCODE lzo,
    store_name  VARCHAR(64),
    city        VARCHAR(64),
    state       VARCHAR(2)
)
DISTSTYLE ALL
SORTKEY(store_id);

CREATE TABLE core.products (
    product_id      INT NOT NULL,
    sku             VARCHAR(16),
    product_name    VARCHAR(128),
    category        VARCHAR(32) ENCODE lzo,
    subcategory     VARCHAR(32),
    unit_price      NUMERIC(12,2),
    cost            NUMERIC(12,2),
    active          BOOLEAN
)
DISTSTYLE ALL
SORTKEY(product_id);

CREATE TABLE core.orders (
    order_id        BIGINT NOT NULL,
    customer_id     BIGINT,
    store_id        INT,
    order_ts        TIMESTAMP ENCODE lzo,
    sales_channel   VARCHAR(16) ENCODE lzo,
    status          VARCHAR(16)
)
DISTKEY(customer_id)
SORTKEY(order_ts);

CREATE TABLE core.order_items (
    order_item_id   BIGINT NOT NULL,
    order_id        BIGINT,
    product_id      INT,
    quantity        INT,
    unit_price      NUMERIC(12,2),
    discount        NUMERIC(12,2)
)
DISTKEY(order_id)
SORTKEY(order_id);

CREATE TABLE core.payments (
    payment_id  BIGINT NOT NULL,
    order_id    BIGINT,
    method      VARCHAR(16),
    amount      NUMERIC(12,2),
    paid_ts     TIMESTAMP
)
DISTKEY(order_id)
SORTKEY(order_id);

CREATE TABLE core.returns (
    return_id       BIGINT NOT NULL,
    order_item_id   BIGINT,
    quantity        INT,
    reason          VARCHAR(64),
    returned_ts     TIMESTAMP
)
DISTKEY(order_item_id)
SORTKEY(returned_ts);

CREATE TABLE core.shipments (
    shipment_id     BIGINT NOT NULL,
    order_id        BIGINT,
    carrier         VARCHAR(16) ENCODE lzo,
    ship_ts         TIMESTAMP,
    delivered_ts    TIMESTAMP
)
DISTKEY(order_id)
SORTKEY(ship_ts);

CREATE TABLE core.web_events (
    event_id     BIGINT NOT NULL,
    customer_id  BIGINT,
    event_ts     TIMESTAMP,
    event_type   VARCHAR(16) ENCODE lzo,
    page_url     VARCHAR(256)
)
DISTKEY(customer_id)
SORTKEY(event_ts);

CREATE TABLE core.campaign_touches (
    touch_id     BIGINT NOT NULL,
    customer_id  BIGINT,
    payload      SUPER
)
DISTKEY(customer_id)
SORTKEY(touch_id);
