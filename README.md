# Catalogue price scraper

Daily competitor SKU watcher for D2C catalogues. BeautifulSoup (default) or Playwright reads product pages, stores price history, flags drops, and emails ops.

Portfolio build for the ₹30,000–₹70,000 + ₹4,000/mo engagement: watchlist, history, alerts, and a small price-intelligence layer (trend forecast + unusual-drop detection).

## Run

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
copy .env.example .env          # optional
python run.py
```

Open the URL printed by `run.py` (binds `127.0.0.1` on a free port).

The demo seeds 8 SKUs and ~21 days of history into SQLite, so charts and alerts work before any live scrape. Click **Scrape now** to re-read the bundled competitor HTML fixtures (prices jitter so a drop can fire).

## Stack

- FastAPI + Jinja dashboard
- SQLAlchemy — SQLite by default, Postgres via `DATABASE_URL`
- BeautifulSoup on local fixtures or any URL; Playwright path in `app/scraper.py`
- smtplib alerts (logged to the Alerts table if SMTP is blank)
- pandas + scikit-learn: 7-day price forecast and isolation-forest unusual drops

## Postgres

```sql
CREATE USER pricewatch WITH PASSWORD 'pricewatch';
CREATE DATABASE pricewatch OWNER pricewatch;
```

Set `DATABASE_URL=postgresql+psycopg2://pricewatch:pricewatch@localhost:5432/pricewatch` and restart. Tables are created on startup.

## Playwright

```bash
python -m playwright install chromium
```

Set `SCRAPER_ENGINE=playwright` in `.env`. Live pages need a real CSS selector on the watch row (`price_selector`).
