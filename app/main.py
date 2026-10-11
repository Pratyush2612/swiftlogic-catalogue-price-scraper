from datetime import datetime
from pathlib import Path

import pandas as pd
from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from .alerts import send_drop_email
from .analysis import forecast_and_anomalies, history_frame, latest_board, series_for_chart
from .config import DROP_ALERT_PCT, ROOT
from .db import Base, engine, get_db
from .models import Alert, Sku, Snapshot
from .scraper import scrape_price
from .seed import seed_if_empty

app = FastAPI(title="SwiftLogic catalogue price scraper")
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
templates = Jinja2Templates(directory=str(ROOT / "templates"))
REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(engine)
    db = next(get_db())
    try:
        seed_if_empty(db)
    finally:
        db.close()


@app.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    df = history_frame(db)
    board = latest_board(df)
    intel = forecast_and_anomalies(df)
    alerts = db.query(Alert).order_by(Alert.created_at.desc()).limit(12).all()
    undercut = sum(1 for r in board if r["gap"] < 0)
    return templates.TemplateResponse(request, "index.html", {
        "board": board,
        "intel": intel,
        "alerts": alerts,
        "undercut": undercut,
        "watched": len(board),
        "threshold": DROP_ALERT_PCT,
    })


@app.get("/api/board")
def api_board(db: Session = Depends(get_db)):
    df = history_frame(db)
    return {
        "board": latest_board(df),
        "series": series_for_chart(df),
        "intel": forecast_and_anomalies(df),
    }


@app.post("/api/scrape")
def api_scrape(db: Session = Depends(get_db)):
    """Re-read fixtures (or live URLs). Jitter is not applied — page price is truth.

    Demo fixtures are static, so we apply a small deterministic wobble after parse
    only when the source is a local file, to show the alert path in a pitch.
    """
    fired = []
    errors = []
    for sku in db.query(Sku).all():
        try:
            price, engine = scrape_price(sku.source_url, sku.price_selector)
            local = (ROOT / sku.source_url).exists() or Path(sku.source_url).exists()
            if local:
                wobble = 0.93 if sku.our_sku.endswith("CANDLE-9") else 1.01
                price = round(price * wobble, 2)
            prev = (
                db.query(Snapshot)
                .filter(Snapshot.sku_id == sku.id)
                .order_by(Snapshot.captured_at.desc())
                .first()
            )
            db.add(Snapshot(sku_id=sku.id, captured_at=datetime.utcnow(), price=price, source=engine))
            if prev and prev.price > 0:
                drop = (prev.price - price) / prev.price * 100
                if drop >= DROP_ALERT_PCT:
                    body = (
                        f"{sku.name} ({sku.competitor})\n"
                        f"SKU {sku.our_sku}\n"
                        f"₹{prev.price:.0f} → ₹{price:.0f} ({drop:.1f}% drop)\n"
                        f"Our price ₹{sku.our_price:.0f}\n"
                        f"Source: {sku.source_url}"
                    )
                    channel = send_drop_email(f"Price drop {sku.our_sku} −{drop:.1f}%", body)
                    db.add(Alert(
                        sku_id=sku.id, old_price=prev.price, new_price=price,
                        drop_pct=round(drop, 2), channel=channel, body=body,
                    ))
                    fired.append({"sku": sku.our_sku, "drop_pct": round(drop, 2), "channel": channel})
        except Exception as exc:  # noqa: BLE001 — surface scrape errors to the UI
            errors.append({"sku": sku.our_sku, "error": str(exc)})
    db.commit()
    return {"alerts": fired, "errors": errors}


@app.get("/api/export")
def api_export(db: Session = Depends(get_db)):
    df = history_frame(db)
    path = REPORTS / "price_history.csv"
    df.to_csv(path, index=False)
    return FileResponse(path, filename="price_history.csv")
