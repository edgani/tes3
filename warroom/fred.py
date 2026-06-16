"""warroom/fred.py — FRED fetch via fredgraph CSV (FREE, no API key). Returns {series_id: Series}.
Offline/sandbox -> empty dict; GIPEngine + funding then degrade to price-proxy gracefully.
"""
from __future__ import annotations
import io, urllib.request, pandas as pd

# series GIPEngine + liquidity/funding read
GIP_SERIES = ["INDPRO","RSAFS","PAYEMS","ISMNO","MANEMP","HOUST","UNRATE","ICSA",
              "CPIAUCSL","CPILFESL","PPIACO","T5YIE","FEDFUNDS","DFF","M2SL"]
LIQ_SERIES = ["WALCL","WTREGEN","RRPONTSYD","WRESBAL","EFFR","DFEDTARU","SOFR","IORB"]

def fetch_one(series_id, days=1500):
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    try:
        with urllib.request.urlopen(url, timeout=12) as r:
            df = pd.read_csv(io.BytesIO(r.read()))
        df.columns = ["date", "val"]; df["val"] = pd.to_numeric(df["val"], errors="coerce")
        df["date"] = pd.to_datetime(df["date"]); 
        return df.dropna().set_index("date")["val"].tail(days)
    except Exception:
        return None

def fetch(series_ids=None, days=1500):
    ids = series_ids or (GIP_SERIES + LIQ_SERIES)
    out = {}
    for sid in ids:
        s = fetch_one(sid, days)
        if s is not None and len(s):
            out[sid] = s
    return out
