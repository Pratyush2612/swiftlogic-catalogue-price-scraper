"""Price index, gap vs our catalogue, and a light ML layer.

Forecast: ordinary least squares on day index → next 7 days.
Unusual drops: IsolationForest on daily pct change and price level.
"""
from datetime import datetime

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.linear_model import LinearRegression
from sqlalchemy.orm import Session

from .models import Sku, Snapshot


def history_frame(db: Session) -> pd.DataFrame:
    rows = (
        db.query(
            Sku.our_sku, Sku.name, Sku.category, Sku.competitor, Sku.our_price, Sku.units_7d,
            Snapshot.captured_at, Snapshot.price,
        )
        .join(Snapshot, Snapshot.sku_id == Sku.id)
        .all()
    )
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows, columns=["sku", "name", "category", "competitor", "our_price", "units_7d", "captured_at", "price"])
    df["captured_at"] = pd.to_datetime(df["captured_at"])
    return df.sort_values(["sku", "captured_at"])


def latest_board(df: pd.DataFrame) -> list[dict]:
    if df.empty:
        return []
    out = []
    for sku, g in df.groupby("sku"):
        g = g.sort_values("captured_at")
        last = g.iloc[-1]
        prev = g.iloc[-2] if len(g) > 1 else last
        week = g.tail(7)["price"]
        gap = float(last["price"] - last["our_price"])
        out.append({
            "sku": sku,
            "name": last["name"],
            "category": last["category"],
            "competitor": last["competitor"],
            "our_price": round(float(last["our_price"]), 2),
            "their_price": round(float(last["price"]), 2),
            "gap": round(gap, 2),
            "gap_pct": round(100 * gap / float(last["our_price"]), 1),
            "dod_pct": round(100 * (float(last["price"]) / float(prev["price"]) - 1), 2),
            "week_avg": round(float(week.mean()), 2),
            "units_7d": int(last["units_7d"]),
        })
    return out


def forecast_and_anomalies(df: pd.DataFrame) -> dict:
    if df.empty:
        return {"forecasts": [], "anomalies": []}
    forecasts = []
    feat_rows = []
    for sku, g in df.groupby("sku"):
        g = g.sort_values("captured_at").reset_index(drop=True)
        y = g["price"].to_numpy(dtype=float)
        x = np.arange(len(y)).reshape(-1, 1)
        model = LinearRegression().fit(x, y)
        future_x = np.arange(len(y), len(y) + 7).reshape(-1, 1)
        pred = model.predict(future_x)
        forecasts.append({
            "sku": sku,
            "name": g.iloc[-1]["name"],
            "competitor": g.iloc[-1]["competitor"],
            "last": round(float(y[-1]), 2),
            "day7": round(float(pred[-1]), 2),
            "slope_per_day": round(float(model.coef_[0]), 2),
        })
        pct = np.diff(y) / y[:-1] * 100
        for i, change in enumerate(pct):
            feat_rows.append({"sku": sku, "name": g.iloc[i + 1]["name"], "change": float(change), "price": float(y[i + 1]), "when": g.iloc[i + 1]["captured_at"]})
    anomalies = []
    if len(feat_rows) >= 8:
        fdf = pd.DataFrame(feat_rows)
        clf = IsolationForest(contamination=0.08, random_state=7)
        flags = clf.fit_predict(fdf[["change", "price"]])
        fdf["flag"] = flags
        for _, row in fdf[fdf["flag"] == -1].tail(8).iterrows():
            anomalies.append({
                "sku": row["sku"],
                "name": row["name"],
                "change_pct": round(row["change"], 2),
                "price": round(row["price"], 2),
                "when": row["when"].strftime("%Y-%m-%d") if isinstance(row["when"], datetime) else str(row["when"])[:10],
            })
    return {"forecasts": forecasts, "anomalies": anomalies}


def series_for_chart(df: pd.DataFrame) -> dict:
    if df.empty:
        return {}
    payload = {}
    for sku, g in df.groupby("sku"):
        g = g.sort_values("captured_at")
        payload[sku] = {
            "labels": [t.strftime("%d %b") for t in g["captured_at"]],
            "prices": [round(float(p), 2) for p in g["price"]],
            "our": round(float(g.iloc[-1]["our_price"]), 2),
        }
    return payload
