# worker/ingest_dhan.py
import asyncio, json, os, time, datetime
from pathlib import Path
import psycopg2
import websockets

DHAN_WS_URL  = os.getenv("DHAN_WS_URL")
CLIENT_ID    = os.getenv("DHAN_CLIENT_ID")
ACCESS_TOKEN = os.getenv("DHAN_ACCESS_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

UNIVERSE_FILE = os.getenv("UNIVERSE_FILE") or str(
    Path(__file__).resolve().parents[1] / "universe" / "fno.csv"
)

pg = psycopg2.connect(DATABASE_URL)
pg.autocommit = True
cur = pg.cursor()
cur.execute("""
CREATE TABLE IF NOT EXISTS ticks(
  symbol text,
  ts timestamptz,
  ltp numeric,
  bid numeric,
  ask numeric,
  vol bigint
);
""")
cur.execute("""
CREATE TABLE IF NOT EXISTS snapshots(
  symbol text PRIMARY KEY,
  ts timestamptz,
  ltp numeric,
  bid numeric,
  ask numeric
);
""")

with open(UNIVERSE_FILE, "r", encoding="utf-8") as f:
    UNIVERSE = [x.strip() for x in f if x.strip()]
print(f"[worker] Loaded {len(UNIVERSE)} symbols from {UNIVERSE_FILE}")

async def subscribe(ws, symbols):
    for i in range(0, len(symbols), 100):  # Dhan: 100 per message
        batch = symbols[i:i+100]
        await ws.send(json.dumps({
            "action":"subscribe",
            "data":[{"securityId":s,"mode":"FULL"} for s in batch]
        }))
        await asyncio.sleep(0.05)

def parse(raw: str):
    pkt = json.loads(raw)
    d = pkt.get("data", pkt) if isinstance(pkt, dict) else {}
    s   = d.get("securityId") or d.get("symbol") or d.get("token")
    if not s: return None
    ts  = d.get("timestamp") or datetime.datetime.utcnow().isoformat()+"Z"
    ltp = d.get("lastTradedPrice") or 0
    bid = d.get("bestBidPrice") or 0
    ask = d.get("bestAskPrice") or 0
    vol = d.get("volumeTraded") or 0
    return s, ts, ltp, bid, ask, vol

async def run():
    backoff = 2
    while True:
        try:
            print("[worker] Connecting WS…")
            async with websockets.connect(
                DHAN_WS_URL,
                extra_headers={
                    "access-token": ACCESS_TOKEN,
                    "client-id": CLIENT_ID,
                    "Accept": "application/json"
                },
                ping_interval=20, ping_timeout=20
            ) as ws:
                backoff = 2
                await subscribe(ws, UNIVERSE)
                async for raw in ws:
                    try:
                        p = parse(raw)
                        if not p: continue
                        s, ts, ltp, bid, ask, vol = p
                        cur.execute(
                          "INSERT INTO ticks(symbol, ts, ltp, bid, ask, vol) VALUES(%s,%s,%s,%s,%s,%s)",
                          (s, ts, ltp, bid, ask, vol)
                        )
                        cur.execute(
                          """INSERT INTO snapshots(symbol, ts, ltp, bid, ask)
                             VALUES(%s,%s,%s,%s,%s)
                             ON CONFLICT (symbol) DO UPDATE SET
                               ts = EXCLUDED.ts, ltp = EXCLUDED.ltp,
                               bid = EXCLUDED.bid, ask = EXCLUDED.ask""",
                          (s, ts, ltp, bid, ask)
                        )
                    except Exception:
                        continue
        except Exception as e:
            print(f"[worker] WS error: {e}; retrying in {backoff}s")
            time.sleep(backoff); backoff = min(backoff*2, 30)

if __name__ == "__main__":
    asyncio.run(run())
