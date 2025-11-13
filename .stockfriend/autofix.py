import os, shutil, pathlib, textwrap

ROOT = pathlib.Path(".")
def ensure_dir(p): p.mkdir(exist_ok=True, parents=True)

# 1) fix trailing-space folders
for name in ["api ", "openapi ", "universe "]:
    p = ROOT / name
    if p.exists() and p.is_dir():
        shutil.move(str(p), str(ROOT / name.strip()))

# ensure base dirs
for d in ["api","openapi","universe","jobs","worker"]:
    ensure_dir(ROOT/d)

# 2) api requirements
(ROOT/"api"/"requirements.txt").write_text(
    "fastapi==0.115.0\nuvicorn==0.30.6\npsycopg2-binary==2.9.9\npython-dateutil==2.9.0\nrequests==2.32.3\npython-dotenv==1.0.1\n",
    encoding="utf-8"
)

# 3) orchestrator api/main.py (healthz + /sf/run)
MAIN = r'''
from fastapi import FastAPI, Header, HTTPException
from typing import Optional, Dict, Any
import os, requests, datetime as dt, psycopg2
from dateutil import parser as dtp

app = FastAPI(title="Stockfriend Orchestrator")
DB = os.getenv("DATABASE_URL")
CID = os.getenv("DHAN_CLIENT_ID")
BOOT = os.getenv("DHAN_ACCESS_TOKEN")
NEWS = os.getenv("NEWSAPI_KEY")
API_KEYS = set((os.getenv("X_API_KEYS") or "").split(","))

def pg():
    con = psycopg2.connect(DB); con.autocommit = True
    return con

def current_token():
    try:
        con = pg(); cur = con.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS tokens(name text primary key, token text, expiry timestamptz)")
        cur.execute("SELECT token FROM tokens WHERE name='DHAN'")
        row = cur.fetchone(); cur.close(); con.close()
        if row and row[0]: return row[0]
    except Exception:
        pass
    return BOOT

@app.get("/healthz")
def healthz():
    return {"ok": True, "ts_ist": dt.datetime.now(dt.timezone(dt.timedelta(hours=5,minutes=30))).isoformat()}

def dhan(path: str, payload: Dict[str, Any]):
    r = requests.post("https://api.dhan.co"+path,
        headers={"access-token": current_token(), "Content-Type":"application/json"},
        json=payload, timeout=20)
    try: j = r.json()
    except Exception: j = {"raw": r.text}
    return {"ok": r.status_code < 400, "data": j, "status": r.status_code}

def news(query: str, limit: int = 20):
    if not NEWS: return []
    r = requests.get("https://newsapi.org/v2/top-headlines",
                     params={"country":"in","category":"business","q":query or "","pageSize":limit},
                     headers={"X-Api-Key": NEWS}, timeout=20)
    j = r.json(); out=[]
    for a in j.get("articles", []):
        ts = a.get("publishedAt"); ts_ist=None
        if ts:
            try: ts_ist = dt.datetime.fromisoformat(ts.replace("Z","+00:00")).astimezone(dt.timezone(dt.timedelta(hours=5,minutes=30))).isoformat()
            except Exception: pass
        out.append({"publishedAt_ist": ts_ist, "headline": a.get("title"),
                    "source": (a.get("source") or {}).get("name"), "url": a.get("url")})
    return out

def rss(url: str, tag: str):
    try:
        r = requests.get(url, timeout=20, headers={"User-Agent": "sf/1.0"})
        from xml.etree import ElementTree as ET
        root = ET.fromstring(r.content); out=[]
        for item in root.findall(".//item"):
            title = (item.findtext("title") or "").strip()
            link  = (item.findtext("link") or "").strip()
            pub   = item.findtext("pubDate"); ts=None
            if pub:
                try: ts = dtp.parse(pub).astimezone(dt.timezone(dt.timedelta(hours=5,minutes=30))).isoformat()
                except Exception: pass
            out.append({"publishedAt_ist": ts, "headline": title, "source": tag, "url": link})
        return out
    except Exception:
        return []

@app.post("/sf/run")
def sf_run(body: Dict[str, Any], x_api_key: Optional[str] = Header(None)):
    if API_KEYS and (x_api_key not in API_KEYS): raise HTTPException(401, "bad api key")
    plan = body.get("plan", []); results = []
    for step in plan:
        op = step.get("op")
        try:
            if op == "ensureToken":
                j = dhan("/v2/RenewToken", {})
                if j.get("ok") and j["data"].get("accessToken"):
                    con = pg(); cur = con.cursor()
                    cur.execute("INSERT INTO tokens(name,token,expiry) VALUES('DHAN',%s,%s) "
                                "ON CONFLICT (name) DO UPDATE SET token=EXCLUDED.token, expiry=EXCLUDED.expiry",
                                (j["data"]["accessToken"], j["data"].get("expiryTime")))
                    cur.close(); con.close()
                results.append({"op": op, **j})
            elif op == "getQuotes":
                results.append({"op": op, **dhan("/v2/market/quote", {"instruments": step.get("instruments", [])})})
            elif op == "getOHLC":
                results.append({"op": op, **dhan("/v2/market/ohlc", {
                    "instrument": step.get("instrument"),
                    "interval": step.get("interval"),
                    "from": step.get("from"),
                    "to": step.get("to"),
                })})
            elif op == "placeOrder":
                p = {k:v for k,v in step.items() if k!="op"}
                results.append({"op": op, **dhan("/v2/orders", p)})
            elif op == "getNews":
                results.append({"op": op, "ok": True, "items": news(step.get("q",""), int(step.get("limit",20)))})
            elif op == "getRegulatory":
                out = rss(os.getenv("SEBI_RSS","https://www.sebi.gov.in/sebirss.xml"),"SEBI") + \
                      rss(os.getenv("NSE_RSS","https://www.nseindia.com/rss-feed"),"NSE") + \
                      rss(os.getenv("RBI_RSS","https://www.rbi.org.in/pressreleases_rss.xml"),"RBI")
                results.append({"op": op, "ok": True, "items": out})
            else:
                results.append({"op": op, "ok": False, "error":"unknown op"})
        except Exception as e:
            results.append({"op": op, "ok": False, "error": str(e)})
    return {"ok": True,
            "ts_ist": dt.datetime.now(dt.timezone(dt.timedelta(hours=5,minutes=30))).isoformat(),
            "results": results, "meta": {"sources": ["dhan","newsapi","rss"]}}
'''
(ROOT/"api"/"main.py").write_text(MAIN, encoding="utf-8")

# 4) normalize universe/fno.csv to NSE: format
fno = ROOT/"universe"/"fno.csv"
if fno.exists():
    lines = [x.strip() for x in fno.read_text(encoding="utf-8").splitlines() if x.strip()]
else:
    lines = ["NSE:RELIANCE","NSE:HDFCBANK","NSE:TCS"]
def norm(s): return s if s.startswith("NSE:") else f"NSE:{s}"
fno.write_text("\n".join(norm(s) for s in lines) + "\n", encoding="utf-8")

# 5) render.yaml updates (v2 WS + env vars + cron)
ry_path = ROOT/"render.yaml"
ry = ry_path.read_text(encoding="utf-8") if ry_path.exists() else ""
ry = ry.replace("wss://live.dhan.co/ws/marketfeed", "wss://api-feed.dhan.co")
# add common envs if missing (simple append method to avoid YAML indentation issues)
def add_env(block, key, value=None, sync=False):
    line = f"      - key: {key}\n"
    if value is not None: line += f"        value: {value}\n"
    if sync: line += f"        sync: false\n"
    return block + line
if "DHAN_CLIENT_ID" not in ry: ry = ry.replace("X_API_KEYS\n        sync: false", "X_API_KEYS\n        sync: false\n      - key: DHAN_CLIENT_ID\n        sync: false")
if "DHAN_ACCESS_TOKEN" not in ry: ry = ry.replace("X_API_KEYS\n        sync: false", "X_API_KEYS\n        sync: false\n      - key: DHAN_ACCESS_TOKEN\n        sync: false")
if "NEWSAPI_KEY" not in ry: ry = ry.replace("X_API_KEYS\n        sync: false", "X_API_KEYS\n        sync: false\n      - key: NEWSAPI_KEY\n        sync: false")
if "SEBI_RSS" not in ry: ry = ry.replace("UNIVERSE_FILE\n        value: /opt/render/project/src/universe/fno.csv",
                                         "UNIVERSE_FILE\n        value: /opt/render/project/src/universe/fno.csv\n      - key: SEBI_RSS\n        value: https://www.sebi.gov.in/sebirss.xml")
if "NSE_RSS" not in ry: ry = ry.replace("SEBI_RSS", "SEBI_RSS\n      - key: NSE_RSS\n        value: https://www.nseindia.com/rss-feed")
if "RBI_RSS" not in ry: ry = ry.replace("NSE_RSS", "NSE_RSS\n      - key: RBI_RSS\n        value: https://www.rbi.org.in/pressreleases_rss.xml")
if "TZ" not in ry: ry = ry.replace("healthCheckPath: /healthz", "healthCheckPath: /healthz\n    envVars:\n      - key: TZ\n        value: Asia/Kolkata")

if "type: cron" not in ry:
    ry = ry.rstrip() + textwrap.dedent("""
      - type: cron
        name: stockfriend-dhan-rotate
        runtime: python
        plan: free
        region: singapore
        schedule: "55 3 * * *"
        rootDir: jobs
        buildCommand: pip install -U pip && pip install -r requirements.txt
        startCommand: python rotate_token.py
        envVars:
          - key: DATABASE_URL
            fromDatabase: { name: market-db, property: connectionString }
          - key: DHAN_CLIENT_ID
            sync: false
          - key: DHAN_ACCESS_TOKEN
            sync: false
          - key: TZ
            value: Asia/Kolkata
""")
ry_path.write_text(ry, encoding="utf-8")

# 6) rotate job files
(ROOT/"jobs"/"requirements.txt").write_text("requests==2.32.3\npsycopg2-binary==2.9.9\npython-dateutil==2.9.0\n", encoding="utf-8")
(ROOT/"jobs"/"rotate_token.py").write_text(
    "import os, requests, psycopg2\nDB=os.getenv('DATABASE_URL'); CID=os.getenv('DHAN_CLIENT_ID'); TOK=os.getenv('DHAN_ACCESS_TOKEN')\n"
    "r=requests.post('https://api.dhan.co/v2/RenewToken', headers={'access-token':TOK,'dhanClientId':CID}, timeout=20)\n"
    "j=r.json()\ncon=psycopg2.connect(DB); con.autocommit=True; cur=con.cursor()\n"
    "cur.execute(\"CREATE TABLE IF NOT EXISTS tokens(name text primary key, token text not null, expiry timestamptz)\")\n"
    "cur.execute(\"INSERT INTO tokens(name,token,expiry) VALUES('DHAN',%s,%s) ON CONFLICT (name) DO UPDATE SET token=EXCLUDED.token, expiry=EXCLUDED.expiry\", (j.get('accessToken'), j.get('expiryTime')))\n"
    "cur.close(); con.close()\nprint('rotated ->', j.get('expiryTime'))\n",
    encoding="utf-8"
)

print("autofix: done")
