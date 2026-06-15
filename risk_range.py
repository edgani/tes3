"""risk_range.py - Hedgeye-style Risk Range: width = basis * sigma_daily * sqrt(n) per duration.
Reimplemented clean (RV-based, McCullough method). TRADE/TREND/TAIL by horizon n + basis window."""
from __future__ import annotations
import numpy as np, pandas as pd

def ranges(df, sig_win=30):
    c = pd.to_numeric(df["Close"], errors="coerce")
    ret = np.log(c/c.shift(1))
    sigma = float(ret.tail(sig_win).std())
    if not np.isfinite(sigma) or sigma <= 0: sigma = 0.02
    last = float(c.iloc[-1]); sma20 = float(c.tail(20).mean()); sma63 = float(c.tail(63).mean())
    def band(basis, n): w = basis*sigma*np.sqrt(n); return (round(basis-w,2), round(basis+w,2))
    return {"trade": band(last, 2), "trend": band(sma20, 12), "tail": band(sma63, 30),
            "close": round(last,2), "sigma": round(sigma,4)}
