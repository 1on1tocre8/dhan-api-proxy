import os, psycopg2, redis

def pg():
    return psycopg2.connect(os.getenv("DATABASE_URL"))

def kv():
    return redis.from_url(os.getenv("KEYVALUE_URL"))

API_KEYS = set((os.getenv("X_API_KEYS") or "").split(","))

def check_key(key):
    return (not API_KEYS) or (key in API_KEYS)
