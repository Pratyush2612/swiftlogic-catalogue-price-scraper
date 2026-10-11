# Deploy notes

- Process: `python run.py` behind a reverse proxy, or `uvicorn app.main:app --host 0.0.0.0 --port 8080`.
- Scheduler: call `POST /api/scrape` from cron / Windows Task Scheduler once a day. The UI button uses the same endpoint.
- Secrets: SMTP and `DATABASE_URL` live in `.env`, not in git.
- Postgres is the production store; SQLite is the laptop demo.
- Alert mail uses STARTTLS on port 587. Blank SMTP settings keep alerts in the database only.
- Do not point the scraper at sites whose terms forbid automated access. The fixtures are synthetic catalogues for the demo.
