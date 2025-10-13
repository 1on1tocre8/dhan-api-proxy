# worker/ingest_dhan.py
import asyncio
import json
import os
import time
import datetime
from pathlib import Path

import psycopg2
import redis
import websockets

# --------- ENV (Render passes these) ----------
DHAN_WS_URL   = os.getenv("DHAN_WS_URL")           # e.g. wss://live.dhan.co/ws/marketfeed
CLIENT_ID     = os.getenv("DHAN_CLIENT_ID")
ACCESS_TOKEN  = os.getenv("DHAN_ACCESS_TOKEN")
DATABASE_URL  = os.getenv("DATABASE_URL")
KEYVALUE_URL  = os.getenv("KEYVALUE_URL")

# If UNIVERSE_FILE not set, default to repo/universe/fno.csv
UNIVERSE_FILE = os.getenv("UNIVERSE_FILE")
if not UNIVERSE_FILE:
    UNIVERSE_FILE = str(Path(__file__).resolve().parents[1] / "universe" / "fno.csv")

# --------- DB & Cache ----------
kv = redis.from_url(KEYVALUE_URL)
pg = psycopg2.connect(DATABASE_URL)
pg.autocommit = True
cur = pg.cursor()
cur.execute("""
CREATE TABLE IF NOT EXISTS ticks (
  symbol text,
  ts timestamptz,
  ltp numeric,
  bid numeric,
  ask numeric,
  vol bigint
);
""")

# --------- Universe load (safe) ----------
with open(UNIVERSE_FILE, "r", encoding="utf-8") as f:
    UNIVERSE = [x.strip() for x in f if x.strip()]

print(f"[worker] Loaded {len(UNIVERSE)} symbols from {UNIVERSE_FILE}")

# --------- Helpers ----------
async def subscribe(ws, symbols):
    """Subscribe in batches of 100 (Dhan limit per message)."""
    count = 0
    for i in range(0, len(symbols), 100):
        batch = symbols[i:i + 100]
        msg = {
            "action": "subscribe",
            "data": [{"securityId": s, "mode": "FULL"} for s in batch]
        }
        await ws.send(json.dumps(msg))
        count += len(batch)
        await asyncio.sleep(0.05)
    print(f"[worker] Subscribed {count} symbols")

def _first(d, *keys):
    """Return the first available key value from the dict."""
    for k in keys:
        if k in d:
            return d[k]
    return None

def parse_tick(raw: str):
    """Make this tolerant to slight format differences."""
    pkt = json.loads(raw)
    d = pkt.get("data", pkt) if isinstance(pkt, dict) else {}
    sym = _first(d, "securityId", "symbol", "token")
    if not sym:
        return None

    ts  = _first(d, "timestamp", "ts") or datetime.datetime.utcnow().isoformat() + "Z"
    ltp = _first(d, "lastTradedPrice", "ltp", "last_price")
    bid = _first(d, "bestBidPrice", "bid")
    ask = _first(d, "bestAskPrice", "ask")
    vol = _first(d, "volumeTraded", "volume", "vol")

    return {
        "symbol": sym,
        "ts": ts,
        "ltp": ltp or 0,
        "bid": bid or 0,
        "ask": ask or 0,
        "vol": vol or 0,
    }

# --------- Main loop ----------
async def run():
    backoff = 2
    while True:
        try:
            print("[worker] Connecting to Dhan WS…")
            async with websockets.connect(
                DHAN_WS_URL,
                extra_headers={
                    "access-token": ACCESS_TOKEN,
                    "client-id": CLIENT_ID,
                    "Accept": "application/json",
                },
                ping_interval=20,
                ping_timeout=20,
            ) as ws:
                backoff = 2  # reset backoff on success
                await subscribe(ws, UNIVERSE)

                async for raw in ws:
                    try:
                        tick = parse_tick(raw)
                        if not tick:
                            continue
                        # Insert into DB
                        cur.execute(
                            "INSERT INTO ticks(symbol, ts, ltp, bid, ask, vol) VALUES(%s,%s,%s,%s,%s,%s)",
                            (tick["symbol"], tick["ts"], tick["ltp"], tick["bid"], tick["ask"], tick["vol"]),
                        )
                        # Cache latest snapshot
                        kv.hset(
                            f"snap:{tick['symbol']}",
                            mapping={"ts": tick["ts"], "ltp": tick["ltp"], "bid": tick["bid"], "ask": tick["ask"]},
                        )
                    except Exception as e:
                        # Keep going on single-message errors
                        continue

        except Exception as e:
            print(f"[worker] WS error: {e}. Reconnecting in {backoff}s…")
            time.sleep(backoff)
            backoff = min(backoff * 2, 30)

if __name__ == "__main__":
    asyncio.run(run())
