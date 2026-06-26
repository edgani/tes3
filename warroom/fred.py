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
    try:
        from warroom.macro_data import series_ids as _macro_ids
        from warroom.policy import series_ids as _policy_ids
        macro = list(dict.fromkeys(_macro_ids() + _policy_ids()))
    except Exception:
        macro = []
    # 1) robust loader from the repo: FRED API key -> fredgraph CSV -> DBnomics -> synthetic, parquet-cached
    out = {}
    try:
        from data.fred_loader import load_fred_bundle
        b = load_fred_bundle()
        series = (b or {}).get("series") if isinstance(b, dict) else None
        if isinstance(series, dict):
            out = {k: v for k, v in series.items() if v is not None and len(v) > 0}
    except Exception:
        pass
    # 1b) ensure the FULL relevant-macro set is present — fetch any the loader missed
    if out:
        for sid in macro:
            if sid not in out:
                s = fetch_one(sid, days)
                if s is not None and len(s):
                    out[sid] = s
        return out
    # 2) fallback: anonymous fredgraph CSV (no key) for the full relevant set, de-duped
    ids = series_ids or list(dict.fromkeys(GIP_SERIES + LIQ_SERIES + macro))
    for sid in ids:
        s = fetch_one(sid, days)
        if s is not None and len(s):
            out[sid] = s
    return out
