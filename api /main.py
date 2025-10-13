from fastapi import FastAPI, Header, HTTPException, Query, Response
from typing import Optional
from pathlib import Path
from utils import pg, kv, check_key

app = FastAPI(title="Stockfriend API")

@app.get("/health")
def health(x_api_key: Optional[str] = Header(None)):
    if not check_key(x_api_key):
        raise HTTPException(401, "bad key")
    return {"status":"ok"}

@app.get("/universe")
def universe(name: str = Query("fno"), x_api_key: Optional[str] = Header(None)):
    if not check_key(x_api_key):
        raise HTTPException(401, "bad key")
    return ["RELIANCE","TCS","INFY"]  # placeholder

@app.get("/snapshot")
def snapshot(symbols: str, x_api_key: Optional[str] = Header(None)):
    if not check_key(x_api_key):
        raise HTTPException(401, "bad key")
    return []  # read from KV in the worker

@app.get("/bars")
def bars(symbol: str, tf: str = Query("1m"), limit: int = 500, x_api_key: Optional[str] = Header(None)):
    if not check_key(x_api_key):
        raise HTTPException(401, "bad key")
    return []  # query Postgres aggregated table

@app.get("/signals")
def signals(rule: str, timeframe: str = Query("1m"), universe: str = "fno", max_results: int = 20, x_api_key: Optional[str] = Header(None)):
    if not check_key(x_api_key):
        raise HTTPException(401, "bad key")
    return []  # run rule logic

# Public URL for ChatGPT to fetch the Action schema (one-URL setup)
@app.get("/action-openapi.yaml", include_in_schema=False)
def action_openapi_yaml():
    path = Path(__file__).parent / ".." / "openapi" / "stockfriend-action.yaml"
    return Response(content=path.read_text(encoding="utf-8"), media_type="text/yaml")
