"""ranking.py - MY competitive conviction engine (NOT the old zip's filter). Per-ticker:
RS vs SPY, momentum, formation, crowding, value-based accumulation (A/D), Hedgeye risk range.
Score = setup STRENGTH (always positive), regime-tilted, crowding-penalized. Honest: RS/momentum
factor screen, not a return forecast."""
from __future__ import annotations
import numpy as np, pandas as pd
from risk_range import ranges
from lpm import money_flow

MACRO_ONLY = {"SPY","IWM","XLI","XLY","XHB","UUP","HYG","TLT","DBC","SOXX"}  # proxies, not tradeable picks here

def _accum(df):
    adl = money_flow(df, "value_typical").cumsum()
    d = adl.diff()
    recent = float(d.tail(20).mean()); base = float(d.abs().tail(60).mean()) + 1e-9
    return int(np.clip(recent/base*50, -100, 100))

def compute_rows(prices, regime, universe):
    spy = prices.get("SPY")
    spy_m = (lambda n: float(spy["Close"].iloc[-1]/spy["Close"].iloc[-1-n]-1)) if spy is not None and len(spy) > 70 else (lambda n: 0.0)
    rows = []
    for t in universe:
        d = prices.get(t)
        if d is None or len(d) < 80 or t in MACRO_ONLY:
            continue
        c = d["Close"]
        def r(n): return float(c.iloc[-1]/c.iloc[-1-n]-1) if len(c) > n else 0.0
        mom63, rs63 = r(63), (r(63) - spy_m(63))
        sma20, sma50 = float(c.tail(20).mean()), float(c.tail(50).mean())
        above50 = c.iloc[-1]/sma50 - 1; trend = sma20/sma50 - 1
        crowding = max(0.0, r(20)); vol = float(c.pct_change().tail(20).std()*np.sqrt(252))
        formation = "BULLISH" if (trend > 0 and above50 > 0) else "BEARISH" if (trend < 0 and above50 < 0) else "NEUTRAL"
        direction = "Long" if formation == "BULLISH" and rs63 > 0 else "Short" if formation == "BEARISH" and rs63 < 0 else "Watch"
        rr = ranges(d)
        strength = abs(rs63)*2.2 + abs(mom63)*1.0 + abs(above50)*0.7
        if regime["defensive"]:
            strength += 0.15 if direction == "Short" else (-0.08 if direction == "Long" else 0); strength -= vol*0.10
        else:
            strength += 0.15 if direction == "Long" else (-0.08 if direction == "Short" else 0)
        strength -= crowding*0.45
        if direction == "Watch": strength *= 0.6
        rows.append({"ticker":t, "_dir":direction, "score":round(max(strength,0)*10,2),
                     "formation":formation, "rs63":round(rs63*100,1), "accumulation":_accum(d),
                     "lrr":rr["trade"][0], "trr":rr["trade"][1], "trend_band":rr["trend"], "close":rr["close"]})
    rows.sort(key=lambda x: x["score"], reverse=True)
    return rows
