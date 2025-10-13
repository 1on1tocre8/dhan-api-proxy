# Stockfriend Data Plane (Render + Dhan)

This repo runs a 24×7 WebSocket ingestor for Dhan, stores/aggregates data, and exposes a small HTTP API for a GPT Action.

## Services
- **Web API** (FastAPI): `/health`, `/snapshot`, `/bars`, `/signals`, `/universe`
- **Worker**: connects to Dhan Live Market Feed; subscribes in 100-symbol batches up to 5,000/connection
- **Cron**: nightly backfill of minute bars
- **Postgres**: historical bars/ticks
- **Key Value**: hot snapshots / small aggregates

## Deploy on Render
1. Push this repo to GitHub (private is fine).
2. In Render → **New → Blueprint**, pick this repo. Confirm resources.
3. Add env vars (services → Environment): `DHAN_CLIENT_ID`, `DHAN_ACCESS_TOKEN`, `X_API_KEYS`.
4. Upload `universe/fno.csv` with your symbols.
5. Hit **Deploy**.

API base URL is your Render web service URL (e.g., `https://stockfriend-api.onrender.com`).

> Educational-only. Respect your broker/data vendor T&Cs.
