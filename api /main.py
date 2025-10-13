# api/main.py
from fastapi import FastAPI, Header, HTTPException, Query, Response
from typing import Optional, List
from pathlib import Path
import os
import sys
import subprocess
import psycopg2

app = FastAPI(title="Stockfriend API")

# ----- ENV -----
DATABASE_URL = os.getenv("DATABASE_URL")  # provided by Render Postgres
X_API_KEYS   = set((os.getenv("X_API_KEYS") or "").split(","))  # for protected endpoints
ADMIN_KEY    = os.getenv("ADMIN_KEY", "")  # for /admin/backfill

# ----- Helpers -----
def check_key(k: Optional[str]) -> bool:
    return (not X_API_KEYS) or (k in X_API_KEYS)

def pg():
    # simple connection helper (open → use → close each request)
    return psycopg2.connect(DATABASE_URL)

# ===== Public endpoints =====

@app.get("/healthz", include_in_schema=False)
def healthz():
    """Public health endpoint used by Render."""
    return {"status": "ok"}

@app.get("/action-openapi.yaml", include_in_schema=False)
def action_openapi_yaml():
    """Serve the GPT Action schema from the same domain."""
    path = Path(__file__).parent / ".." / "openapi" / "stockfriend-action.yaml"
    text = path.read_text(encoding="utf-8")
    return Response(content=text, media_type="text/yaml")

# ===== Protected endpoints (require X-API-Key) =====

@app.get("/universe")
def universe(
    name: str = Query("fno"),
    x_api_key: Optional[str] = Header(None),
):
    """Return a simple list of symbols (from repo file to start with)."""
    if not check_key(x_api_key):
        raise HTTPException(401, "bad key")

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
    """
    Return the latest LTP/bid/ask per symbol from the 'snapshots' table.
    The worker maintains this table via UPSERT.
    """
    if not check_key(x_api_key):
        raise HTTPException(401, "bad key")

    wanted = [s.strip() for s in symbols.split(",") if s.strip()]
    if not wanted:
        return []

    conn = pg()
    try:
        cur = conn.cursor()
        # ANY(%s) expects a list/array
        cur.execute(
            "SELECT symbol, ts, ltp, bid, ask FROM snapshots WHERE symbol = ANY(%s)",
            (wanted,),
        )
        rows = cur.fetchall()
    finally:
        conn.close()

    got = {
        r[0]: {
            "symbol": r[0],
            "ts": r[1],
            "ltp": float(r[2]) if r[2] is not None else None,
            "bid": float(r[3]) if r[3] is not None else None,
            "ask": float(r[4]) if r[4] is not None else None,
        }
        for r in rows
    }
    # Keep order and fill missing
    return [
        got.get(s, {"symbol": s, "ts": None, "ltp": None, "bid": None, "ask": None})
        for s in wanted
    ]

@app.get("/bars")
def bars(
    symbol: str,
    tf: str = Query("1m", pattern="^(1s|1m|5m|15m|1h|1d)$"),
    limit: int = Query(500, ge=1, le=5000),
    x_api_key: Optional[str] = Header(None),
):
    """
    Placeholder: once you aggregate or backfill candles, query and return here.
    For now we return an empty list to keep the schema stable.
    """
    if not check_key(x_api_key):
        raise HTTPException(401, "bad key")
    return []

@app.get("/signals")
def signals(
    rule: str,
    timeframe: str = Query("1m"),
    universe: str = "fno",
    max_results: int = 20,
    x_api_key: Optional[str] = Header(None),
):
    """
    Placeholder: compute rule-based signals over bars in DB.
    """
    if not check_key(x_api_key):
        raise HTTPException(401, "bad key")
    return []

# ===== Admin endpoint to trigger backfill from GitHub Actions (FREE plan replacement for Render Cron) =====

@app.post("/admin/backfill", include_in_schema=False)
def admin_backfill(x_admin_key: Optional[str] = Header(None)):
    """
    Kicks off jobs/backfill_minutes.py in a background process.
    Protect with ADMIN_KEY, and call it from GitHub Actions.
    """
    if ADMIN_KEY and x_admin_key != ADMIN_KEY:
        raise HTTPException(401, "bad admin key")

    script = Path(__file__).parent / ".." / "jobs" / "backfill_minutes.py"
    # Working directory = project root so relative imports/paths work
    cwd = Path(__file__).parent.parent
    subprocess.Popen([sys.executable, str(script)], cwd=str(cwd))
    return {"ok": True, "msg": "backfill started"}
