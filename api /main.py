# api/main.py
from fastapi import FastAPI, Header, HTTPException, Query, Response
from typing import Optional, List
from pathlib import Path
import os
import psycopg2
import redis

app = FastAPI(title="Stockfriend API")

# ---------- Simple deps (self-contained) ----------
DATABASE_URL = os.getenv("DATABASE_URL")
KEYVALUE_URL = os.getenv("KEYVALUE_URL")
X_API_KEYS = set((os.getenv("X_API_KEYS") or "").split(","))

def check_key(k: Optional[str]) -> bool:
    return (not X_API_KEYS) or (k in X_API_KEYS)

def pg():
    return psycopg2.connect(DATABASE_URL)

def kv():
    return redis.from_url(KEYVALUE_URL)

# ---------- Public health (for Render) ----------
@app.get("/healthz", include_in_schema=False)
def healthz():
    return {"status": "ok"}

# ---------- Public schema (one URL for GPT Action) ----------
@app.get("/action-openapi.yaml", include_in_schema=False)
def action_openapi_yaml():
    path = Path(__file__).parent / ".." / "openapi" / "stockfriend-action.yaml"
    text = path.read_text(encoding="utf-8")
    return Response(content=text, media_type="text/yaml")

# ---------- Protected endpoints ----------
@app.get("/universe")
def universe(
    name: str = Query("fno"),
    x_api_key: Optional[str] = Header(None),
):
    if not check_key(x_api_key):
        raise HTTPException(401, "bad key")

    # Minimal: read from the repo file to start with
    uni_path = Path(__file__).parent / ".." / "universe" / "fno.csv"
    if not uni_path.exists():
        return []
    symbols = [x.strip() for x in uni_path.read_text(encoding="utf-8").splitlines() if x.strip()]
    return symbols

@app.get("/snapshot")
def snapshot(
    symbols: str,
    x_api_key: Optional[str] = Header(None),
):
    if not check_key(x_api_key):
        raise HTTPException(401, "bad key")

    r = kv()
    out = []
    for s in [x.strip() for x in symbols.split(",") if x.strip()]:
        h = r.hgetall(f"snap:{s}")
        if not h:
            out.append({"symbol": s, "ts": None, "ltp": None, "bid": None, "ask": None})
            continue
        # redis returns bytes; decode
        def dec(v): return v.decode("utf-8") if isinstance(v, (bytes, bytearray)) else v
        out.append({
            "symbol": s,
            "ts": dec(h.get(b"ts")),
            "ltp": float(dec(h.get(b"ltp"))) if h.get(b"ltp") else None,
            "bid": float(dec(h.get(b"bid"))) if h.get(b"bid") else None,
            "ask": float(dec(h.get(b"ask"))) if h.get(b"ask") else None,
        })
    return out

@app.get("/bars")
def bars(
    symbol: str,
    tf: str = Query("1m"),
    limit: int = Query(500, ge=1, le=5000),
    x_api_key: Optional[str] = Header(None),
):
    if not check_key(x_api_key):
        raise HTTPException(401, "bad key")

    # TODO: query your aggregated bars table once you add it
    # For now, return empty list to keep API stable
    return []

@app.get("/signals")
def signals(
    rule: str,
    timeframe: str = Query("1m"),
    universe: str = "fno",
    max_results: int = 20,
    x_api_key: Optional[str] = Header(None),
):
    if not check_key(x_api_key):
        raise HTTPException(401, "bad key")

    # TODO: compute rule-based signals over bars in DB
    return []
