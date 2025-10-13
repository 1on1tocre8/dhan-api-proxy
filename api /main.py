from fastapi import FastAPI, Header, HTTPException, Query
from typing import Optional
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
    # TODO: read from table/universe file
    return ["RELIANCE","TCS","INFY"]

@app.get("/snapshot")
def snapshot(symbols: str, x_api_key: Optional[str] = Header(None)):
    if not check_key(x_api_key):
        raise HTTPException(401, "bad key")
    # TODO: get from KV cache populated by worker
    return []

@app.get("/bars")
def bars(symbol: str, tf: str = Query("1m"), limit: int = 500, x_api_key: Optional[str] = Header(None)):
    if not check_key(x_api_key):
        raise HTTPException(401, "bad key")
    # TODO: query Postgres aggregated table
    return []

@app.get("/signals")
def signals(rule: str, timeframe: str = Query("1m"), universe: str = "fno", max_results: int = 20, x_api_key: Optional[str] = Header(None)):
    if not check_key(x_api_key):
        raise HTTPException(401, "bad key")
    # TODO: run rule logic on latest bars
    return []
