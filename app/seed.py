"""Seed watchlist + history so the dashboard is useful before a live scrape."""
from datetime import datetime, timedelta
import random

from sqlalchemy.orm import Session

from .models import Sku, Snapshot

WATCH = [
    ("NS-MUG-01", "Serene ceramic pour-over", "Kitchen", 1299, "Northstar Living", "NS-MUG-01", "fixtures/northstar.html", "article[data-sku='NS-MUG-01'] .price", 86, 1180),
    ("NS-LAMP-04", "Arc oak table lamp", "Home", 3190, "Northstar Living", "NS-LAMP-04", "fixtures/northstar.html", "article[data-sku='NS-LAMP-04'] .price", 24, 3050),
    ("NS-TOWEL-2", "Waffle bath towel set", "Bath", 899, "Northstar Living", "NS-TOWEL-2", "fixtures/northstar.html", "article[data-sku='NS-TOWEL-2'] .price", 140, 860),
    ("NS-CANDLE-9", "Vetiver soy candle", "Fragrance", 620, "Northstar Living", "NS-CANDLE-9", "fixtures/northstar.html", "article[data-sku='NS-CANDLE-9'] .price", 210, 590),
    ("HB-MUG-01", "Stoneware pour-over mug", "Kitchen", 1299, "Harbour & Co", "HB-MUG-01", "fixtures/harbour.html", "div[data-sku='HB-MUG-01'] .offer", 86, 1140),
    ("HB-LAMP-04", "Bentwood desk lamp", "Home", 3190, "Harbour & Co", "HB-LAMP-04", "fixtures/harbour.html", "div[data-sku='HB-LAMP-04'] .offer", 24, 3280),
    ("HB-TOWEL-2", "Cotton waffle towels", "Bath", 899, "Harbour & Co", "HB-TOWEL-2", "fixtures/harbour.html", "div[data-sku='HB-TOWEL-2'] .offer", 140, 780),
    ("HB-CANDLE-9", "Vetiver candle 180g", "Fragrance", 620, "Harbour & Co", "HB-CANDLE-9", "fixtures/harbour.html", "div[data-sku='HB-CANDLE-9'] .offer", 210, 520),
]


def seed_if_empty(db: Session) -> None:
    if db.query(Sku).count():
        return
    rng = random.Random(7)
    today = datetime.utcnow().replace(hour=6, minute=0, second=0, microsecond=0)
    for row in WATCH:
        sku = Sku(
            our_sku=row[0], name=row[1], category=row[2], our_price=row[3],
            competitor=row[4], competitor_sku=row[5], source_url=row[6],
            price_selector=row[7], units_7d=row[8],
        )
        db.add(sku)
        db.flush()
        price = float(row[9])
        for day in range(21, 0, -1):
            price = max(99, price * (1 + rng.uniform(-0.012, 0.008)))
            if day == 3 and row[0] in {"HB-CANDLE-9", "NS-TOWEL-2"}:
                price *= 0.90
            db.add(Snapshot(
                sku_id=sku.id,
                captured_at=today - timedelta(days=day),
                price=round(price, 2),
                source="seed",
            ))
    db.commit()
