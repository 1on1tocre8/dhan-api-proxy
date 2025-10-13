# api/main.py
from fastapi import FastAPI, Header, HTTPException, Query, Response
from typing import Optional
from pathlib import Path
import os, psycopg2

app = FastAPI(title="Stockfriend API")

DATABASE_URL = os.getenv("DATABASE_URL")
X_API_KEYS = set((os.getenv("X_API_KEYS") or "").split(","))

def check_key(k: Optional[str]) -> bool:
    return (not X_API_KEYS) or (k in X_API_KEYS)

def pg():
    return psycopg2.connect(DATABASE_URL)

@app.get("/healthz", include_in_schema=False)
def healthz():
    return {"status": "ok"}

@app.get("/action-openapi.yaml", include_in_schema=False)
def action_openapi_yaml():
    path = Path(__file__).parent / ".." / "openapi" / "stockfriend-action.yaml"
    return Response(content=path.read_text(encoding="utf-8"), media_type="text/yaml")

@app.get("/universe")
def universe(name: str = Query("fno"), x_api_key: Optional[str] = Header(None)):
    if not check_key(x_api_key): raise HTTPException(401, "bad key")
    uni = Path(__file__).parent / ".." / "universe" / "fno.csv"
    if not uni.exists(): return []
    return [x.strip() for x in uni.read_text(encoding="utf-8").splitlines() if x.strip()]

@app.get("/snapshot")
def snapshot(symbols: str, x_api_key: Optional[str] = Header(None)):
    if not check_key(x_api_key): raise HTTPException(401, "bad key")
    wanted = [s.strip() for s in symbols.split(",") if s.strip()]
    if not wanted: return []
    conn = pg(); cur = conn.cursor()
    cur.execute("SELECT symbol, ts, ltp, bid, ask FROM snapshots WHERE symbol = ANY(%s)", (wanted,))
    rows = cur.fetchall()
    got = {r[0]: {"symbol": r[0], "ts": r[1], "ltp": float(r[2]) if r[2] is not None else None,
                  "bid": float(r[3]) if r[3] is not None else None,
                  "ask": float(r[4]) if r[4] is not None else None} for r in rows}
    # fill missing
    return [got.get(s, {"symbol": s, "ts": None, "ltp": None, "bid": None, "ask": None}) for s in wanted]

@app.get("/bars")
def bars(symbol: str, tf: str = Query("1m"), limit: int = Query(500, ge=1, le=5000),
         x_api_key: Optional[str] = Header(None)):
    if not check_key(x_api_key): raise HTTPException(401, "bad key")
    # TODO: return aggregated candles once you add jobs/backfill + aggregation
    return []

@app.get("/signals")
def signals(rule: str, timeframe: str = Query("1m"), universe: str = "fno", max_results: int = 20,
            x_api_key: Optional[str] = Header(None)):
    if not check_key(x_api_key): raise HTTPException(401, "bad key")
    # TODO: compute signals from bars
    return []
