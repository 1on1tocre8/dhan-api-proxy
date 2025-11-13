
import os, requests, psycopg2, datetime as dt

DB = os.getenv("DATABASE_URL")
DHAN_CLIENT_ID = os.getenv("DHAN_CLIENT_ID")
ACCESS_TOKEN = os.getenv("DHAN_ACCESS_TOKEN")

def store(token, expiry):
    con = psycopg2.connect(DB)
    con.autocommit = True
    cur = con.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS tokens (
        name text primary key,
        token text not null,
        expiry timestamptz
    )""")
    cur.execute("""
    INSERT INTO tokens(name, token, expiry)
    VALUES('DHAN', %s, %s)
    ON CONFLICT (name) DO UPDATE SET token=EXCLUDED.token, expiry=EXCLUDED.expiry
    """, (token, expiry))
    cur.close(); con.close()

def main():
    url = "https://api.dhan.co/v2/RenewToken"
    headers = {"access-token": ACCESS_TOKEN, "dhanClientId": DHAN_CLIENT_ID}
    r = requests.post(url, headers=headers, timeout=20)
    r.raise_for_status()
    j = r.json()
    token = j.get("accessToken")
    expiry = j.get("expiryTime")
    if not token:
        raise SystemExit("no token in response: %r" % j)
    store(token, expiry)
    print("rotated", expiry)

if __name__ == "__main__":
    main()
