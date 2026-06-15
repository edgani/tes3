"""data.py - OHLCV loader: yfinance live, deterministic synthetic fallback so it ALWAYS runs."""
from __future__ import annotations
import numpy as np, pandas as pd

US_UNIVERSE = ["NVDA","ARKK","XLE","VST","CEG","VRT","ANET","SMH","AAPL","MSFT","GLD",
               "TLT","XLU","XLP","HYG","USO","DBC","COPX","SOXX","IWM","XLI","XLY","XHB","UUP","SPY"]
IDX_UNIVERSE = ["BBCA.JK","BMRI.JK","BBRI.JK","TLKM.JK","ASII.JK","BUMI.JK","ANTM.JK","HUMI.JK"]
# baskets for GIP-style quad (price proxies)
GROWTH_B, DEF_B, INFL_B, USD_B = ["SOXX","COPX","XLI","IWM"], ["XLU","XLP","TLT"], ["USO","DBC","GLD"], ["UUP"]

def _synth(t, n=420):
    r = np.random.default_rng(abs(hash(t)) % (2**32))
    rets = r.normal(r.uniform(-0.0008,0.0013), r.uniform(0.011,0.032), n)
    c = 100*np.exp(np.cumsum(rets)); intr = np.abs(r.normal(0,0.018,n))*c; loc = r.uniform(0.2,0.8,n)
    h = c+intr*(1-loc); l = c-intr*loc; o = l+(h-l)*r.uniform(0.2,0.8,n)
    v = (r.uniform(1e6,6e7,n)*(1+np.abs(rets)/0.02*0.5)).round()
    return pd.DataFrame({"Open":o,"High":h,"Low":l,"Close":c,"Volume":v},
                        index=pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=n))

def load(tickers, days=420):
    tickers = list(dict.fromkeys(tickers))
    try:
        import yfinance as yf
        raw = yf.download(tickers, period=f"{days}d", interval="1d", auto_adjust=False,
                          progress=False, group_by="ticker", threads=True)
        out = {}
        if isinstance(raw.columns, pd.MultiIndex):
            for t in tickers:
                if t in raw.columns.get_level_values(0):
                    d = raw[t][["Open","High","Low","Close","Volume"]].dropna()
                    if len(d) > 80: out[t] = d
        else:
            d = raw[["Open","High","Low","Close","Volume"]].dropna()
            if len(d) > 80: out[tickers[0]] = d
        if len(out) >= max(4, len(tickers)//2): return out, "yfinance · live"
    except Exception: pass
    return {t: _synth(t, days) for t in tickers}, "synthetic · demo (no live feed)"
