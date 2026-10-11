import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{ROOT / 'pricewatch.db'}")
DROP_ALERT_PCT = float(os.getenv("DROP_ALERT_PCT", "5"))
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
ALERT_FROM = os.getenv("ALERT_FROM", "alerts@swiftlogic.local")
ALERT_TO = os.getenv("ALERT_TO", "ops@brand.example")
SCRAPER_ENGINE = os.getenv("SCRAPER_ENGINE", "beautifulsoup").lower()
