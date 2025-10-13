import asyncio, json, os, time, datetime
import websockets, psycopg2, redis

DHAN_WS_URL = os.getenv("DHAN_WS_URL")  # e.g., wss://live.dhan.co/ws/marketfeed
CLIENT_ID = os.getenv("DHAN_CLIENT_ID")
ACCESS_TOKEN = os.getenv("DHAN_ACCESS_TOKEN")
UNIVERSE_FILE = os.getenv("UNIVERSE_FILE")  # /workspace/universe/fno.csv

KV = redis.from_url(os.getenv("KEYVALUE_URL"))
conn = psycopg2.connect(os.getenv("DATABASE_URL"))
conn.autocommit = True
cur = conn.cursor()
cur.execute("""
CREATE TABLE IF NOT EXISTS ticks (
  symbol text,
  ts timestamptz,
  ltp numeric,
  bid numeric,
  ask numeric,
  vol bigint
);""")

with open(UNIVERSE_FILE, "r", encoding="utf-8") as f:
    UNIVERSE = [x.strip() for x in f if x.strip()]

async def subscribe(ws, symbols):
    # Dhan: subscribe in batches of 100 per message (up to ~5000 per connection)
    for i in range(0, len(symbols), 100):
        batch = symbols[i:i+100]
        msg = {"action": "subscribe", "data": [{"securityId": s, "mode": "FULL"} for s in batch]}
        await ws.send(json.dumps(msg))
        await asyncio.sleep(0.05)

async def run():
    while True:
        try:
            async with websockets.connect(
                DHAN_WS_URL,
                extra_headers={"access-token": ACCESS_TOKEN, "client-id": CLIENT_ID, "Accept": "application/json"},
                ping_interval=20, ping_timeout=20,
            ) as ws:
                await subscribe(ws, UNIVERSE)
                async for raw in ws:
                    try:
                        pkt = json.loads(raw)
                        s = pkt.get("securityId")
                        ts = pkt.get("timestamp") or datetime.datetime.utcnow().isoformat() + "Z"
                        ltp = pkt.get("lastTradedPrice"); bid = pkt.get("bestBidPrice"); ask = pkt.get("bestAskPrice")
                        vol = pkt.get("volumeTraded")
                        cur.execute(
                            "INSERT INTO ticks(symbol, ts, ltp, bid, ask, vol) VALUES(%s,%s,%s,%s,%s,%s)",
                            (s, ts, ltp, bid, ask, vol),
                        )
                        KV.hset(f"snap:{s}", mapping={"ts": ts, "ltp": ltp or 0, "bid": bid or 0, "ask": ask or 0})
                    except Exception:
                        continue
        except Exception:
            time.sleep(2)

if __name__ == "__main__":
    asyncio.run(run())
