#!/usr/bin/env python3
"""
FastAPI server for US Options Volume Dashboard.
Visualizes CBOE daily call/put volumes and call/put ratio via Plotly.
"""
import subprocess
import threading
import time
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).parent
DATA_CSV = BASE_DIR / "data" / "options_volume.csv"

app = FastAPI(title="US Options Volume Dashboard")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

PORT = 8005


def _load_df() -> pd.DataFrame:
    df = pd.read_csv(DATA_CSV, parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)
    return df


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/api/chart/volume")
async def api_chart_volume():
    """Call and put volume line chart data (2 years)."""
    df = _load_df()
    dates = df["date"].dt.strftime("%Y-%m-%d").tolist()
    return JSONResponse({
        "dates": dates,
        "call_volume": df["call_volume"].tolist(),
        "put_volume": df["put_volume"].tolist(),
        "total_volume": df["total_volume"].tolist(),
    })


@app.get("/api/chart/ratio")
async def api_chart_ratio():
    """Call/put ratio line chart data with 20-day moving average."""
    df = _load_df()
    df["cp_ma20"] = df["call_put_ratio"].rolling(20, min_periods=1).mean().round(4)
    df["pc_ma20"] = df["put_call_ratio"].rolling(20, min_periods=1).mean().round(4)
    dates = df["date"].dt.strftime("%Y-%m-%d").tolist()
    return JSONResponse({
        "dates": dates,
        "call_put_ratio": df["call_put_ratio"].round(4).tolist(),
        "cp_ma20": df["cp_ma20"].tolist(),
        "put_call_ratio": df["put_call_ratio"].round(4).tolist(),
        "pc_ma20": df["pc_ma20"].tolist(),
    })


@app.get("/api/stats")
async def api_stats():
    """Summary statistics."""
    df = _load_df()
    latest = df.iloc[-1]
    return JSONResponse({
        "latest_date": latest["date"].strftime("%Y-%m-%d"),
        "latest_call": int(latest["call_volume"]),
        "latest_put": int(latest["put_volume"]),
        "latest_total": int(latest["total_volume"]),
        "latest_cp_ratio": round(float(latest["call_put_ratio"]), 4),
        "latest_pc_ratio": round(float(latest["put_call_ratio"]), 4),
        "avg_cp_ratio": round(float(df["call_put_ratio"].mean()), 4),
        "avg_pc_ratio": round(float(df["put_call_ratio"].mean()), 4),
        "min_cp_ratio": round(float(df["call_put_ratio"].min()), 4),
        "max_cp_ratio": round(float(df["call_put_ratio"].max()), 4),
        "avg_call_volume": int(df["call_volume"].mean()),
        "avg_put_volume": int(df["put_volume"].mean()),
        "total_days": len(df),
    })


def open_browser():
    time.sleep(1.5)
    subprocess.Popen(
        ["cmd.exe", "/c", "start", f"http://localhost:{PORT}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


if __name__ == "__main__":
    import uvicorn
    threading.Thread(target=open_browser, daemon=True).start()
    uvicorn.run(app, host="0.0.0.0", port=PORT)
