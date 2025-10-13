# api/main.py
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, Header, HTTPException, Query, Response
from fastapi.responses import JSONResponse
from psycopg2.extras import RealDictCursor

from utils import pg, kv, check_key

app = FastAPI(title="Stockfriend API")

# ---------- helpers ----------

def require_key(x_api_key: Optional[str]) -> None:
    if not check_key(x_api_key):
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key.")

def universe_path() -> Path:
    # Render default checkout path
    default_path = Path("/opt/render/project/src/universe/fno.csv")
    env_path = os.getenv("UNIVERSE_FILE")
    return Path(env_path) if env_path else default_path

def parse_tf_to_interval(tf: str) -> str:
    tf = tf.lower()
    if tf in ("1s", "1sec", "1second"):
        return "1 second"
    if tf in ("1m", "1min", "1minute"):
        return "1 minute"
    if tf in ("5m",):
        return "5 minutes"
    if tf in ("15m",):
        return "15 minutes"
    if tf in ("1h", "1hr"):
        return "1 hour"
    if tf in ("1d", "1day"):
        return "1 day"
    # default
    return "1 minute"

def read_universe_list() -> List[str]:
    p = universe_path()
    if not p.exists():
        return []
    lines = [x.strip() for x in p.read_text(encoding="utf-8").splitlines()]
    return [x for x in lines if x and not x.startswith("#")]

def safe_int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except Exception:
        return default

def fetch_bars_from_ticks(symbol: str, tf: str, limit: int = 500,
                          start_iso: Optional[str] = None,
                          end_iso: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Build OHLC from ticks table on-the-fly using date_trunc.
    Assumes ticks table columns: symbol, ts (timestamptz), ltp (numeric), vol (cumulative)
    Volume here is approximated (0) because cumulative tick volume needs differencing.
    """
    interval = parse_tf_to_interval(tf)

    where = ["symbol = %s"]
    params: List[Any] = [symbol]

    if start_iso:
        where.append("ts >= %s")
        params.append(start_iso)
    if end_iso:
        where.append("ts <= %s")
        params.append(end_iso)

    where_sql = " AND ".join(where)

    sql = f"""
    WITH b AS (
      SELECT
        date_trunc('{interval}', ts) AS bucket,
        ltp,
        ts
      FROM ticks
      WHERE {where_sql}
    ),
    o AS (
      SELECT bucket,
             FIRST_VALUE(ltp) OVER (PARTITION BY bucket ORDER BY ts ASC) AS o,
             MAX(ltp)  OVER (PARTITION BY bucket) AS h,
             MIN(ltp)  OVER (PARTITION BY bucket) AS l,
             FIRST_VALUE(ltp) OVER (PARTITION BY bucket ORDER BY ts DESC) AS c
      FROM b
    )
    SELECT bucket AS ts, o, h, l, c
    FROM (
      SELECT DISTINCT ON (bucket) bucket, o, h, l, c
      FROM o
      ORDER BY bucket DESC
    ) x
    ORDER BY ts DESC
    LIMIT %s
    """
    params.append(limit)

    with pg() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

    # shape + add fields
    out: List[Dict[str, Any]] = []
    for r in reversed(rows):  # chronological
        out.append({
            "symbol": symbol,
            "tf": tf,
            "ts": r["ts"].isoformat(),
            "o": float(r["o"]) if r["o"] is not None else None,
            "h": float(r["h"]) if r["h"] is not None else None,
            "l": float(r["l"]) if r["l"] is not None else None,
            "c": float(r["c"]) if r["c"] is not None else None,
            "v": 0,  # placeholder; build proper volume in your ingestion if needed
        })
    return out

def parse_extras(extras: Optional[str]) -> Dict[str, Any]:
    if not extras:
        return {}
    try:
        return json.loads(extras)
    except Exception:
        return {}

# ---------- public routes ----------

@app.get("/healthz", include_in_schema=False)
def healthz():
    """Public health endpoint for Render load balancer checks."""
    return {"status": "ok"}

# ---------- protected routes (require X-API-Key) ----------

@app.get("/health")
def health(x_api_key: Optional[str] = Header(None)):
    require_key(x_api_key)
    # Optional: basic checks
    try:
        with pg() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "db_error", "detail": str(e)})

    try:
        r = kv().ping()
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "cache_error", "detail": str(e)})

    return {"status": "ok", "db": "ok", "cache_ping": bool(r)}

@app.get("/universe")
def universe(
    name: str = Query("fno"),
    x_api_key: Optional[str] = Header(None),
):
    require_key(x_api_key)
    # Simple implementation: return fno.csv (ignore name for now)
    return read_universe_list()

@app.get("/snapshot")
def snapshot(
    symbols: str = Query(..., description="Comma-separated symbols"),
    x_api_key: Optional[str] = Header(None),
):
    require_key(x_api_key)
    redis = kv()
    out: List[Dict[str, Any]] = []
    for s in [x.strip() for x in symbols.split(",") if x.strip()]:
        data = redis.hgetall(f"snap:{s}")
        if data:
            # Redis returns bytes; decode safely
            def d(k): return data.get(k.encode())  # type: ignore
            def f(v): 
                try:
                    return float(v.decode()) if v is not None else None
                except Exception:
                    return None
            def t(v): return v.decode() if v is not None else None
            out.append({
                "symbol": s,
                "ts": t(d("ts")),
                "ltp": f(d("ltp")),
                "bid": f(d("bid")),
                "ask": f(d("ask")),
            })
        else:
            out.append({"symbol": s, "ts": None, "ltp": None, "bid": None, "ask": None})
    return out

@app.get("/bars")
def bars(
    symbol: str = Query(...),
    tf: str = Query("1m", description="1s,1m,5m,15m,1h,1d"),
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    limit: int = Query(500, ge=1, le=5000),
    x_api_key: Optional[str] = Header(None),
):
    require_key(x_api_key)
    return fetch_bars_from_ticks(symbol=symbol, tf=tf, limit=limit, start_iso=start, end_iso=end)

@app.get("/signals")
def signals(
    rule: str = Query(..., regex="^(breakdown|ma_flip_down|structure_break)$"),
    timeframe: str = Query("1m"),
    universe: str = Query("fno"),
    max_results: int = Query(20, ge=1, le=200),
    extras: Optional[str] = Query(None, description='JSON string, e.g. {"lookback":20,"min_vol_z":2}'),
    x_api_key: Optional[str] = Header(None),
):
    """
    Lightweight, educational rules:
      - breakdown: latest close < min(low) of lookback bars (default 20)
      - ma_flip_down: SMA(fast) just crossed below SMA(slow) (defaults: 20/50)
      - structure_break: close < last swing low from pivot window (very simple)
    """
    require_key(x_api_key)
    params = parse_extras(extras)
    uni = read_universe_list() if universe in ("fno", "all", "custom") else read_universe_list()

    out: List[Dict[str, Any]] = []

    # Keep things simple and fast: fetch ~200 bars per symbol
    lookback = safe_int(params.get("lookback", 20), 20)
    fast = safe_int(params.get("fast", 20), 20)
    slow = safe_int(params.get("slow", 50), 50)
    pivot = safe_int(params.get("pivot", 5), 5)

    for s in uni:
        bars = fetch_bars_from_ticks(s, timeframe, limit=max(200, slow + 5))
        if len(bars) < max(lookback, slow) + 2:
            continue

        closes = [b["c"] for b in bars if b["c"] is not None]
        lows   = [b["l"] for b in bars if b["l"] is not None]
        if len(closes) < max(lookback, slow) + 2 or len(lows) < lookback + 1:
            continue
        last_c = closes[-1]

        score = 0.0
        hit = False
        extra: Dict[str, Any] = {}

        if rule == "breakdown":
            rolling_low = min(lows[-lookback-1:-1])
            hit = last_c is not None and rolling_low is not None and last_c < rolling_low
            score = 0.6 if hit else 0.0
            extra = {"rolling_low": rolling_low, "lookback": lookback}

        elif rule == "ma_flip_down":
            # Simple SMA cross: SMA(fast) just went below SMA(slow)
            def sma(arr: List[float], n: int) -> Optional[float]:
                if len(arr) < n: return None
                return sum(arr[-n:]) / n
            sma_fast_now = sma(closes, fast)
            sma_slow_now = sma(closes, slow)
            sma_fast_prev = sum(closes[-fast-1:-1]) / fast if len(closes) >= fast + 1 else None
            sma_slow_prev = sum(closes[-slow-1:-1]) / slow if len(closes) >= slow + 1 else None
            if None not in (sma_fast_now, sma_slow_now, sma_fast_prev, sma_slow_prev):
                crossed = (sma_fast_prev >= sma_slow_prev) and (sma_fast_now < sma_slow_now)
                hit = bool(crossed)
                score = 0.65 if hit else 0.0
                extra = {"sma_fast": sma_fast_now, "sma_slow": sma_slow_now, "fast": fast, "slow": slow}

        elif rule == "structure_break":
            # Very simple pivot-based swing low: min of last 'pivot' lows before last bar
            pivot_low = min(lows[-pivot-1:-1])
            hit = last_c is not None and pivot_low is not None and last_c < pivot_low
            score = 0.55 if hit else 0.0
            extra = {"pivot_low": pivot_low, "pivot": pivot}

        if hit:
            out.append({
                "rule": rule,
                "symbol": s,
                "ts": bars[-1]["ts"],
                "timeframe": timeframe,
                "score": round(score, 3),
                "extras": extra,
            })

        if len(out) >= max_results:
            break

    # sort by score desc (if many)
    out.sort(key=lambda r: r.get("score", 0), reverse=True)
    return out[:max_results]

# ---------- serve the OpenAPI (Action) from the same domain ----------

@app.get("/action-openapi.yaml", include_in_schema=False)
def action_openapi_yaml():
    """Expose the Action schema so ChatGPT can import a single URL."""
    path = Path(__file__).parent / ".." / "openapi" / "stockfriend-action.yaml"
    if not path.exists():
        return Response("# missing openapi file at openapi/stockfriend-action.yaml\n", media_type="text/yaml")
    return Response(content=path.read_text(encoding="utf-8"), media_type="text/yaml")
