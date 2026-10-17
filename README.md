# Catalogue price scraper

Production watchlist for D2C catalogues. Add real competitor product URLs and a CSS selector for the price. The app scrapes on a schedule, stores history in Postgres (or SQLite), and emails price-drop alerts.

## Run locally

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python run.py
```

Open the printed URL. The watchlist starts empty. Add a SKU, click **Test scrape** to confirm the selector, then **Scrape now**.

## Production (Render)

- Build: `pip install -r requirements.txt`
- Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Set `DATABASE_URL` to a Postgres connection string.
- Set SMTP vars for real email. Blank SMTP stores alerts in the database only.
- Set `APP_PASSWORD` to lock the dashboard.
- `SCHEDULE_HOURS=24` runs a scrape every day.

## Selector

Inspect the competitor product page, find the element that holds the price (for example `.price`, `#product-price`, `span[data-price]`), and paste that CSS selector. Use Playwright (`SCRAPER_ENGINE=playwright` and `python -m playwright install chromium`) if the price is rendered by JavaScript.

Do not scrape sites whose terms forbid automated access.
