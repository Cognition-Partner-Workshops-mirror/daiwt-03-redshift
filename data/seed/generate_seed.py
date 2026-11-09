"""Deterministic seed generator for the legacy estate.

random.Random(42), anchored to END_DATE = 2025-12-31 (365 days of history).
Never depends on today's date. Writes data/seed/csv/<table>.csv with a header,
NULL as the literal \\N, UTF-8. Regenerate with `make seed`.
"""
import csv
import datetime as dt
import json
import random
from decimal import Decimal
from pathlib import Path

END_DATE = dt.date(2025, 12, 31)
START_TS = dt.datetime(2025, 1, 1)
OUT_DIR = Path(__file__).resolve().parent / "csv"
NULL = "\\N"

N_CUSTOMERS = 1500
N_STORES = 40
N_PRODUCTS = 300
N_ORDERS = 20000
N_WEB_EVENTS = 25000
N_CAMPAIGN_TOUCHES = 8000

REGIONS = ["WEST", "EAST", "NRTH", "SOTH", "WEST", "EAST", "NRTH", "SOTH", "NE", "SW"]
STATES = {
    "WEST": ["CA", "OR", "WA"], "EAST": ["NY", "MA", "NJ"],
    "NRTH": ["MN", "WI", "IL"], "SOTH": ["TX", "FL", "GA"],
    "NE": ["VT", "NH"], "SW": ["AZ", "NM"],
}
CATEGORIES = ["Apparel", "Footwear", "Accessories", "Home", "Electronics", "Outdoors"]
CHANNELS = ["web", "store", "mobile", "phone"]
PAY_METHODS = ["card", "card", "card", "cash", "wallet", "gift_card", None]
CARRIERS = ["ups", "fedex", "usps", "dhl"]
EVENT_TYPES = ["page_view", "page_view", "page_view", "search", "add_to_cart", "checkout", "login"]
REASONS = ["size", "damaged", "wrong_item", "changed_mind", "late_delivery", None]
CAMPAIGNS = [f"CMP-{n:03d}" for n in range(1, 21)]
TOUCH_CHANNELS = ["email", "social", "search_ad", "display", "affiliate"]

FIRST = ["Avery", "Jordan", "Riley", "Morgan", "Casey", "Quinn", "Parker", "Reese",
         "Devon", "Skyler", "Rowan", "Emerson", "Finley", "Hayden", "Kendall", "Marlowe"]
LAST = ["Nguyen", "Garcia", "Kim", "Patel", "Johnson", "Silva", "Novak", "Osei",
        "Larsen", "Mbeki", "Rossi", "Tanaka", "Weber", "Costa", "Iqbal", "Fischer"]
CITIES = {
    "CA": "Los Angeles", "OR": "Portland", "WA": "Seattle", "NY": "New York",
    "MA": "Boston", "NJ": "Newark", "MN": "Minneapolis", "WI": "Madison",
    "IL": "Chicago", "TX": "Austin", "FL": "Miami", "GA": "Atlanta",
    "VT": "Burlington", "NH": "Concord", "AZ": "Phoenix", "NM": "Santa Fe",
}


def money(rng, lo, hi):
    return Decimal(rng.randrange(lo * 100, hi * 100)) / 100


def randTs(rng, start, end):
    span = int((end - start).total_seconds())
    return start + dt.timedelta(seconds=rng.randrange(span))


def writeTable(name, header, rows):
    path = OUT_DIR / f"{name}.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header)
        for row in rows:
            w.writerow([NULL if v is None else v for v in row])
    return path


def genStores(rng):
    rows = []
    for i in range(1, N_STORES + 1):
        region = REGIONS[i % len(REGIONS)]
        state = STATES[region][i % len(STATES[region])]
        rows.append([i, region, f"Store {i:03d}", CITIES[state], state])
    return rows


def genCustomers(rng, stores):
    rows = []
    for i in range(1, N_CUSTOMERS + 1):
        first = FIRST[rng.randrange(len(FIRST))]
        last = LAST[rng.randrange(len(LAST))]
        email = f"{first.lower()}.{last.lower()}{i}@example.com"
        region = REGIONS[rng.randrange(len(REGIONS))]
        store = stores[rng.randrange(len(stores))]
        # deliberately messy phones: mixed case/punctuation/whitespace, ~12% NULL
        if rng.random() < 0.12:
            phone = None
        else:
            digits = f"{rng.randrange(10**9):010d}"
            style = rng.randrange(4)
            if style == 0:
                phone = f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
            elif style == 1:
                phone = f" {digits[:3]}.{digits[3:6]}.{digits[6:]} "
            elif style == 2:
                phone = f"+1 ({digits[:3]}) {digits[3:6]} - {digits[6:]}"
            else:
                phone = digits
        signup = randTs(rng, dt.datetime(2023, 1, 1), START_TS).date()
        rows.append([i, email, first, last, phone, region, store[0],
                     signup.isoformat(), "true" if rng.random() < 0.08 else "false"])
    return rows


def genProducts(rng):
    rows = []
    for i in range(1, N_PRODUCTS + 1):
        cat = CATEGORIES[i % len(CATEGORIES)]
        price = money(rng, 5, 400)
        cost = (price * Decimal(rng.randrange(45, 75))) / 100
        rows.append([i, f"SKU-{i:05d}", f"{cat} item {i}", cat,
                     f"{cat.lower()}-sub-{i % 6}", f"{price:.2f}",
                     f"{cost.quantize(Decimal('0.01')):.2f}",
                     "true" if rng.random() < 0.95 else "false"])
    return rows


def genOrdersEtc(rng, customers, products, stores):
    """orders, order_items, payments, returns, shipments (linked rows)."""
    orders, items, payments, returns, shipments = [], [], [], [], []
    end = dt.datetime.combine(END_DATE, dt.time(23, 59, 59))
    # ~90% of customers order; some customers order repeatedly
    buyers = [c for c in customers if rng.random() < 0.9]
    itemId = returnId = shipmentId = 0
    for orderId, _ in enumerate(range(N_ORDERS), start=1):
        cust = buyers[rng.randrange(len(buyers))]
        store = stores[rng.randrange(len(stores))]
        ts = randTs(rng, START_TS, end)
        channel = CHANNELS[rng.randrange(len(CHANNELS))]
        orders.append([orderId, cust[0], store[0], ts.strftime("%Y-%m-%d %H:%M:%S"),
                       channel, rng.choice(["complete", "complete", "complete", "returned", "cancelled"])])
        nItems = rng.choices([1, 2, 3, 4, 5], weights=[45, 25, 15, 10, 5])[0]
        orderTotal = Decimal(0)
        chosen = rng.sample(products, nItems)
        for prod in chosen:
            itemId += 1
            qty = rng.choices([1, 2, 3], weights=[75, 18, 7])[0]
            unitPrice = Decimal(prod[5])
            discount = (unitPrice * Decimal(rng.randrange(0, 20)) / 100).quantize(Decimal("0.01"))
            items.append([itemId, orderId, prod[0], qty, f"{unitPrice:.2f}", f"{discount:.2f}"])
            orderTotal += (unitPrice - discount) * qty
            if rng.random() < 0.06:
                returnId += 1
                rts = ts + dt.timedelta(days=rng.randrange(1, 30))
                rts = min(rts, end)
                returns.append([returnId, itemId, rng.choices([1, qty], weights=[80, 20])[0],
                                rng.choice(REASONS), rts.strftime("%Y-%m-%d %H:%M:%S")])
        payTs = ts + dt.timedelta(minutes=rng.randrange(0, 60))
        payments.append([orderId, orderId, rng.choice(PAY_METHODS),
                         f"{orderTotal:.2f}", payTs.strftime("%Y-%m-%d %H:%M:%S")])
        if channel in ("web", "mobile", "phone") and rng.random() < 0.85:
            shipmentId += 1
            shipTs = ts + dt.timedelta(hours=rng.randrange(4, 72))
            if rng.random() < 0.08:  # in-flight: delivered_ts NULL
                delivered = None
            else:
                delivered = shipTs + dt.timedelta(hours=rng.randrange(6, 140))
                delivered = min(delivered, end)
            shipments.append([shipmentId, orderId, CARRIERS[rng.randrange(len(CARRIERS))],
                              shipTs.strftime("%Y-%m-%d %H:%M:%S"),
                              None if delivered is None else delivered.strftime("%Y-%m-%d %H:%M:%S")])
    return orders, items, payments, returns, shipments


def genWebEvents(rng, customers):
    rows = []
    end = dt.datetime.combine(END_DATE, dt.time(23, 59, 59))
    for eventId in range(1, N_WEB_EVENTS + 1):
        cust = None if rng.random() < 0.15 else customers[rng.randrange(len(customers))][0]
        rows.append([eventId, cust, randTs(rng, START_TS, end).strftime("%Y-%m-%d %H:%M:%S"),
                     rng.choice(EVENT_TYPES), f"/p/{rng.randrange(500)}"])
    return rows


def genCampaignTouches(rng, customers):
    rows = []
    for touchId in range(1, N_CAMPAIGN_TOUCHES + 1):
        cust = customers[rng.randrange(len(customers))]
        touches = []
        for _ in range(rng.randrange(1, 5)):
            touches.append({
                "channel": rng.choice(TOUCH_CHANNELS),
                "campaign_id": rng.choice(CAMPAIGNS),
                "ts": randTs(rng, START_TS, dt.datetime.combine(END_DATE, dt.time(0, 0))).strftime(
                    "%Y-%m-%d %H:%M:%S"),
            })
        payload = {"customer_ref": cust[0], "touches": touches,
                   "meta": {"source": "crm_export", "batch": touchId % 10}}
        rows.append([touchId, cust[0], json.dumps(payload, separators=(",", ":"))])
    return rows


def main():
    rng = random.Random(42)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    stores = genStores(rng)
    customers = genCustomers(rng, stores)
    products = genProducts(rng)
    orders, items, payments, returns, shipments = genOrdersEtc(rng, customers, products, stores)
    webEvents = genWebEvents(rng, customers)
    touches = genCampaignTouches(rng, customers)

    writeTable("stores", ["store_id", "region", "store_name", "city", "state"], stores)
    writeTable("customers", ["customer_id", "email", "first_name", "last_name", "phone",
                             "region", "preferred_store_id", "signup_date", "is_business"], customers)
    writeTable("products", ["product_id", "sku", "product_name", "category", "subcategory",
                            "unit_price", "cost", "active"], products)
    writeTable("orders", ["order_id", "customer_id", "store_id", "order_ts",
                          "sales_channel", "status"], orders)
    writeTable("order_items", ["order_item_id", "order_id", "product_id", "quantity",
                               "unit_price", "discount"], items)
    writeTable("payments", ["payment_id", "order_id", "method", "amount", "paid_ts"], payments)
    writeTable("returns", ["return_id", "order_item_id", "quantity", "reason", "returned_ts"], returns)
    writeTable("shipments", ["shipment_id", "order_id", "carrier", "ship_ts", "delivered_ts"], shipments)
    writeTable("web_events", ["event_id", "customer_id", "event_ts", "event_type", "page_url"], webEvents)
    writeTable("campaign_touches", ["touch_id", "customer_id", "payload"], touches)

    for p in sorted(OUT_DIR.glob("*.csv")):
        with open(p) as f:
            rows = sum(1 for _ in f) - 1
        print(f"{p.name}: {rows} rows")


if __name__ == "__main__":
    main()
