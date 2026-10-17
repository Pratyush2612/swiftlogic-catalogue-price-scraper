from datetime import datetime
from pathlib import Path

import pandas as pd
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .alerts import send_drop_email
from .analysis import forecast_and_anomalies, history_frame, latest_board, series_for_chart
from .config import APP_PASSWORD, DEMO_SEED, DROP_ALERT_PCT, ROOT, SCHEDULE_HOURS
from .db import Base, SessionLocal, engine, get_db
from .models import Alert, Sku, Snapshot
from .scraper import scrape_price
from .seed import seed_if_empty

app = FastAPI(title="SwiftLogic catalogue price scraper")
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
templates = Jinja2Templates(directory=str(ROOT / "templates"))
REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)


class SkuIn(BaseModel):
    our_sku: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=200)
    category: str = "General"
    our_price: float = Field(gt=0)
    competitor: str = Field(min_length=1, max_length=80)
    competitor_sku: str = ""
    source_url: str = Field(min_length=4, max_length=400)
    price_selector: str = Field(min_length=1, max_length=200)
    units_7d: int = 0


def _require_auth(request: Request) -> None:
    if not APP_PASSWORD:
        return
    header = request.headers.get("authorization", "")
    if header == f"Bearer {APP_PASSWORD}":
        return
    token = request.query_params.get("token", "")
    if token == APP_PASSWORD:
        return
    raise HTTPException(status_code=401, detail="Unauthorized")


def run_scrape(db: Session) -> dict:
    fired = []
    errors = []
    for sku in db.query(Sku).all():
        try:
            price, engine_name = scrape_price(sku.source_url, sku.price_selector)
            price = round(price, 2)
            prev = (
                db.query(Snapshot)
                .filter(Snapshot.sku_id == sku.id)
                .order_by(Snapshot.captured_at.desc())
                .first()
            )
            db.add(Snapshot(sku_id=sku.id, captured_at=datetime.utcnow(), price=price, source=engine_name))
            if prev and prev.price > 0:
                drop = (prev.price - price) / prev.price * 100
                if drop >= DROP_ALERT_PCT:
                    body = (
                        f"{sku.name} ({sku.competitor})\n"
                        f"SKU {sku.our_sku}\n"
                        f"\u20b9{prev.price:.0f} \u2192 \u20b9{price:.0f} ({drop:.1f}% drop)\n"
                        f"Our price \u20b9{sku.our_price:.0f}\n"
                        f"Source: {sku.source_url}"
                    )
                    channel = send_drop_email(f"Price drop {sku.our_sku} \u2212{drop:.1f}%", body)
                    db.add(Alert(
                        sku_id=sku.id, old_price=prev.price, new_price=price,
                        drop_pct=round(drop, 2), channel=channel, body=body,
                    ))
                    fired.append({"sku": sku.our_sku, "drop_pct": round(drop, 2), "channel": channel})
        except Exception as exc:
            errors.append({"sku": sku.our_sku, "error": str(exc)})
    db.commit()
    return {"alerts": fired, "errors": errors, "scraped": db.query(Sku).count()}


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(engine)
    if DEMO_SEED:
        db = SessionLocal()
        try:
            seed_if_empty(db)
        finally:
            db.close()
    if SCHEDULE_HOURS > 0:
        from apscheduler.schedulers.background import BackgroundScheduler

        def job():
            db = SessionLocal()
            try:
                run_scrape(db)
            finally:
                db.close()

        sched = BackgroundScheduler()
        sched.add_job(job, "interval", hours=SCHEDULE_HOURS, id="daily-scrape", replace_existing=True)
        sched.start()


@app.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    _require_auth(request)
    df = history_frame(db)
    board = latest_board(df)
    intel = forecast_and_anomalies(df)
    alerts = db.query(Alert).order_by(Alert.created_at.desc()).limit(12).all()
    skus = db.query(Sku).order_by(Sku.our_sku).all()
    undercut = sum(1 for r in board if r["gap"] < 0)
    return templates.TemplateResponse(request, "index.html", {
        "board": board,
        "intel": intel,
        "alerts": alerts,
        "skus": skus,
        "undercut": undercut,
        "watched": len(skus),
        "threshold": DROP_ALERT_PCT,
    })


@app.get("/api/board")
def api_board(request: Request, db: Session = Depends(get_db)):
    _require_auth(request)
    df = history_frame(db)
    return {
        "board": latest_board(df),
        "series": series_for_chart(df),
        "intel": forecast_and_anomalies(df),
    }


@app.post("/api/skus")
def add_sku(payload: SkuIn, request: Request, db: Session = Depends(get_db)):
    _require_auth(request)
    if db.query(Sku).filter(Sku.our_sku == payload.our_sku).first():
        raise HTTPException(status_code=409, detail="SKU already watched")
    sku = Sku(
        our_sku=payload.our_sku.strip(),
        name=payload.name.strip(),
        category=payload.category.strip() or "General",
        our_price=payload.our_price,
        competitor=payload.competitor.strip(),
        competitor_sku=(payload.competitor_sku or payload.our_sku).strip(),
        source_url=payload.source_url.strip(),
        price_selector=payload.price_selector.strip(),
        units_7d=payload.units_7d,
    )
    db.add(sku)
    db.commit()
    db.refresh(sku)
    return {"id": sku.id, "our_sku": sku.our_sku}


@app.delete("/api/skus/{sku_id}")
def delete_sku(sku_id: int, request: Request, db: Session = Depends(get_db)):
    _require_auth(request)
    sku = db.get(Sku, sku_id)
    if not sku:
        raise HTTPException(status_code=404, detail="Not found")
    db.query(Snapshot).filter(Snapshot.sku_id == sku.id).delete()
    db.query(Alert).filter(Alert.sku_id == sku.id).delete()
    db.delete(sku)
    db.commit()
    return {"deleted": sku_id}


@app.post("/api/test-scrape")
def test_scrape(payload: dict, request: Request):
    _require_auth(request)
    url = (payload.get("source_url") or "").strip()
    selector = (payload.get("price_selector") or "").strip()
    if not url or not selector:
        raise HTTPException(status_code=400, detail="source_url and price_selector required")
    try:
        price, engine_name = scrape_price(url, selector)
    except Exception as exc:
        return JSONResponse(status_code=422, content={"error": str(exc)})
    return {"price": price, "engine": engine_name}


@app.post("/api/scrape")
def api_scrape(request: Request, db: Session = Depends(get_db)):
    _require_auth(request)
    return run_scrape(db)


@app.get("/api/export")
def api_export(request: Request, db: Session = Depends(get_db)):
    _require_auth(request)
    df = history_frame(db)
    path = REPORTS / "price_history.csv"
    if df.empty:
        path.write_text("sku,name,category,competitor,our_price,units_7d,captured_at,price\n", encoding="utf-8")
    else:
        df.to_csv(path, index=False)
    return FileResponse(path, filename="price_history.csv")
