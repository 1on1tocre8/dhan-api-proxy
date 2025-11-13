
# Changelog — 2025-11-13 15:44 IST

- Fixed trailing-space directories (`api`, `openapi`, `universe`) that would break Render builds.
- Implemented **/sf/run** orchestrator (FastAPI) supporting ops: ensureToken, getQuotes, getOHLC, placeOrder, getNews, getRegulatory.
- Added **/healthz** endpoint to match Render health checks.
- Added **jobs/rotate_token.py** cron to call **Dhan /v2/RenewToken** and persist token to Postgres.
- Server now prefers DB-stored token; falls back to `DHAN_ACCESS_TOKEN` if none stored yet.
- Integrated **NewsAPI** + **SEBI/NSE/RBI RSS** (free) with IST timestamps.
- Upgraded worker to **Dhan v2 WebSocket** endpoint with query-string auth and sane ping settings.
- Updated Python deps (requests, python-dateutil) and added minimal XML RSS parsing (stdlib).
- Enhanced `render.yaml` with env vars, cron job, and default RSS URLs.
