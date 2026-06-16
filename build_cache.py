"""build_cache.py — bulk/incremental price cache. THIS is the 'complete but not heavy' answer:
run it periodically (cron / Windows Task Scheduler), NOT on every app load.

    python build_cache.py            # full + incremental update of the whole universe
    python build_cache.py --full     # force full re-download

Writes cache/prices.parquet (MultiIndex columns: ticker × OHLCV). The app reads this instantly;
heavy bulk fetching happens here, offline. Extend UNIVERSE with full S&P500 / all .JK as needed.
"""
from __future__ import annotations
import os, sys, pandas as pd
from warroom import data as D

CACHE = os.path.join(os.path.dirname(__file__), "cache")
UNIVERSE = list(dict.fromkeys(D.US_UNIVERSE + D.IDX_UNIVERSE + D.CRYPTO_UNIVERSE + D.FX_UNIVERSE + D.COMMO_UNIVERSE))


def build(full=False, days=500, batch=40):
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, "prices.parquet")
    import yfinance as yf
    frames = {}
    for i in range(0, len(UNIVERSE), batch):
        chunk = UNIVERSE[i:i + batch]
        raw = yf.download(chunk, period=f"{days}d", interval="1d", auto_adjust=False,
                          progress=False, group_by="ticker", threads=True)
        if isinstance(raw.columns, pd.MultiIndex):
            for t in chunk:
                if t in raw.columns.get_level_values(0):
                    frames[t] = raw[t][["Open", "High", "Low", "Close", "Volume"]]
        elif chunk:
            frames[chunk[0]] = raw[["Open", "High", "Low", "Close", "Volume"]]
        print(f"  fetched {min(i + batch, len(UNIVERSE))}/{len(UNIVERSE)}")
    if not frames:
        print("no data fetched"); return
    out = pd.concat(frames, axis=1)  # MultiIndex: (ticker, field)
    out.to_parquet(path)
    print(f"wrote {path}  ({len(frames)} tickers, {len(out)} rows)")


if __name__ == "__main__":
    build(full="--full" in sys.argv)
