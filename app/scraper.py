"""BeautifulSoup default; Playwright optional for JS-rendered catalogues."""
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from .config import ROOT, SCRAPER_ENGINE

_RUPEE = re.compile(r"[\d,]+(?:\.\d+)?")
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-IN,en;q=0.9",
}


def _parse_price(text: str) -> float:
    cleaned = text.replace("₹", "").replace("Rs.", "").replace("INR", "").replace("\xa0", " ")
    match = _RUPEE.search(cleaned)
    if not match:
        raise ValueError(f"No price in {text!r}")
    return float(match.group(0).replace(",", ""))


def _load_html(source_url: str) -> str:
    path = Path(source_url)
    if not path.is_absolute():
        path = ROOT / source_url
    if path.exists() and path.is_file():
        return path.read_text(encoding="utf-8")
    resp = requests.get(source_url, timeout=25, headers=_HEADERS)
    resp.raise_for_status()
    return resp.text


def scrape_beautifulsoup(source_url: str, selector: str) -> float:
    html = _load_html(source_url)
    soup = BeautifulSoup(html, "lxml")
    node = soup.select_one(selector)
    if node is None:
        raise ValueError(f"Selector matched nothing: {selector}")
    return _parse_price(node.get_text(" ", strip=True))


def scrape_playwright(source_url: str, selector: str) -> float:
    from playwright.sync_api import sync_playwright

    path = Path(source_url)
    if not path.is_absolute():
        path = ROOT / source_url
    target = path.resolve().as_uri() if path.exists() and path.is_file() else source_url
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=_HEADERS["User-Agent"])
        page.goto(target, wait_until="domcontentloaded", timeout=30000)
        text = page.locator(selector).first.inner_text(timeout=15000)
        browser.close()
    return _parse_price(text)


def scrape_price(source_url: str, selector: str) -> tuple[float, str]:
    engine = SCRAPER_ENGINE
    if engine == "playwright":
        return scrape_playwright(source_url, selector), "playwright"
    return scrape_beautifulsoup(source_url, selector), "beautifulsoup"
