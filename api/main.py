from fastapi import FastAPI, Header, HTTPException, Query, Response
from typing import Optional, List, Dict, Any
import os, json, datetime as dt, requests, psycopg2
from dateutil import parser as dtp

app = FastAPI(title="Stockfriend Orchestrator")

# --- ENVIRONMENT VARIABLES ---
DB = os.getenv("DATABASE_URL")
DHAN_CLIENT_ID = os.getenv("DHAN_CLIENT_ID")
BOOT_TOKEN = os.getenv("DHAN_ACCESS_TOKEN")
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY")
SEBI_RSS = os.getenv("SEBI_RSS", "https://www.sebi.gov.in/sebirss.xml")
NSE_RSS  = os.getenv("NSE_RSS", "https://www.nseindia.com/rss-feed")
RBI_RSS  = os.getenv("RBI_RSS", "https://www.rbi.org.in/pressreleases_rss.xml")
API_KEYS = set((os.getenv("X_API_KEYS") or "").split(","))
ADMIN_KEY = os.getenv("ADMIN_KEY","")

# --- UTILS ---
def pg():
    con = psycopg2.connect(DB)
    con.autocommit = True
    return con

def current_token() -> str:
    """Prefer DB token, fallback to BOOT_TOKEN"""
    try:
        con = pg(); cur = con.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS tokens(name text primary key, token text, expiry timestamptz)")
        cur.execute("SELECT token FROM tokens WHERE name='DHAN'")
        row = cur.fetchone()
        cur.close(); con.close()
        if row and row[0]:
            return row[0]
    except Exception as e:
        print("Token fetch error:", e)
    return BOOT_TOKEN

@app.get("/healthz")
def healthz():
    """Basic health check"""
    return {"ok": True, "ts_ist": dt.datetime.now(dt.timezone(dt.timedelta(hours=5,minutes=30))).isoformat()}

# --- DHAN API WRAPPER ---
def dhan(path:str, payload:Dict[str,Any]):
    url = "https://api.dhan.co" + path
    headers = {"access-token": current_token(), "Content-Type": "application/json"}
    r = requests.post(url, headers=headers, json=payload, timeout=20)
    if r.status_code >= 400:
        return {"ok": False, "status": r.status_code, "error": r.text}
    try:
        j = r.json()
    except Exception:
        j = {"raw": r.text}
    return {"ok": True, "data": j}

# --- NEWS + RSS ---
def newsapi(query:str, limit:int=20):
    if not NEWSAPI_KEY:
        return []
    url = "https://newsapi.org/v2/top-headlines"
    params = {"country":"in", "category":"business", "q": query or "", "pageSize": limit}
    r = requests.get(url, params=params, headers={"X-Api-Key": NEWSAPI_KEY}, timeout=20)
    j = r.json()
    items = []
    for a in j.get("articles", []):
        items.append({
            "publishedAt_ist": dt.datetime.fromisoformat(a.get("publishedAt").replace("Z","+00:00")).astimezone(dt.timezone(dt.timedelta(hours=5,minutes=30))).isoformat() if a.get("publishedAt") else None,
            "headline": a.get("title"),
            "source": a.get("source",{}).get("name"),
            "url": a.get("url")
        })
    return items

def fetch_rss(url:str, tag:str):
    try:
        r = requests.get(url, timeout=20, headers={"User-Agent":"sf/1.0"})
        from xml.etree import ElementTree as ET
        root = ET.fromstring(r.content)
        items = []
        for item in root.findall(".//item"):
            title = (item.findtext("title") or "").strip()
            link  = (item.findtext("link") or "").strip()
            pub   = item.findtext("pubDate")
            ts = None
            if pub:
                try:
                    ts = dtp.parse(pub).astimezone(dt.timezone(dt.timedelta(hours=5,minutes=30))).isoformat()
                except Exception:
                    ts = None
            items.append({"publishedAt_ist": ts, "headline": title, "source": tag, "url": link})
        return items
    except Exception as e:
        print("RSS fetch error:", e)
        return []

# --- MAIN ORCHESTRATOR ---
@app.post("/sf/run")
def sf_run(body: Dict[str, Any], x_api_key: Optional[str] = Header(None)):
    """Main orchestrator for Stockfriend AI actions"""

    # --- DEBUG LOGGING ---
    print("DEBUG: Received X-API-Key =", x_api_key)
    print("DEBUG: Allowed API_KEYS =", API_KEYS)

    # --- SECURITY CHECK ---
    if API_KEYS and (x_api_key not in API_KEYS):
        print("DEBUG: Unauthorized attempt detected.")
        raise HTTPException(401, "bad api key")

    plan = body.get("plan", [])
    results = []

    for step in plan:
        op = step.get("op")
        try:
            if op == "ensureToken":
                j = dhan("/v2/RenewToken", {})
                ok = j.get("ok", False)
                if ok and j["data"].get("accessToken"):
                    con = pg(); cur = con.cursor()
                    cur.execute("""
                        INSERT INTO tokens(name, token, expiry)
                        VALUES('DHAN', %s, %s)
                        ON CONFLICT (name)
                        DO UPDATE SET token=EXCLUDED.token, expiry=EXCLUDED.expiry
                    """, (j["data"]["accessToken"], j["data"].get("expiryTime")))
                    cur.close(); con.close()
                results.append({"op": op, **j})
            elif op == "getQuotes":
                instruments = step.get("instruments", [])
                j = dhan("/v2/market/quote", {"instruments": instruments})
                results.append({"op": op, **j})
            elif op == "getOHLC":
                j = dhan("/v2/market/ohlc", {
                    "instrument": step.get("instrument"),
                    "interval": step.get("interval"),
                    "from": step.get("from"),
                    "to": step.get("to"),
                })
                results.append({"op": op, **j})
            elif op == "placeOrder":
                p = {k:v for k,v in step.items() if k not in ("op",)}
                j = dhan("/v2/orders", p)
                results.append({"op": op, **j})
            elif op == "getNews":
                items = newsapi(step.get("q",""), int(step.get("limit", 20)))
                results.append({"op": op, "ok": True, "items": items})
            elif op == "getRegulatory":
                out = []
                out += fetch_rss(SEBI_RSS, "SEBI")
                out += fetch_rss(NSE_RSS, "NSE")
                out += fetch_rss(RBI_RSS, "RBI")
                results.append({"op": op, "ok": True, "items": out})
            else:
                results.append({"op": op, "ok": False, "error": "unknown op"})
        except Exception as e:
            results.append({"op": op, "ok": False, "error": str(e)})

    return {
        "ts_ist": dt.datetime.now(dt.timezone(dt.timedelta(hours=5,minutes=30))).isoformat(),
        "ok": True,
        "results": results,
        "meta": {"sources": ["dhan","newsapi","rss"]}
    }
