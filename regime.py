"""regime.py - GIP/quad from cross-asset PRICE PROXIES using ACCELERATION (2nd derivative),
the Hedgeye GIP idea. Reimplemented clean (no FRED here -> price-implied, flagged in UI)."""
from __future__ import annotations
import numpy as np, pandas as pd
from data import GROWTH_B, DEF_B, INFL_B

def _roc(c, n):
    return float(c.iloc[-1]/c.iloc[-1-n]-1) if len(c) > n else 0.0

def _accel(prices, tickers, fast=63, slow=126):
    """basket acceleration = mean(ROC_fast - ROC_slow) across the basket = 2nd-derivative proxy."""
    vals = []
    for t in tickers:
        d = prices.get(t)
        if d is not None and len(d) > slow + 5:
            vals.append(_roc(d["Close"], fast) - _roc(d["Close"], slow))
    return float(np.mean(vals)) if vals else 0.0

def assess(prices, universe):
    g_acc = _accel(prices, GROWTH_B) - _accel(prices, DEF_B)
    i_acc = _accel(prices, INFL_B)
    above = tot = 0
    for t in universe:
        d = prices.get(t)
        if d is not None and len(d) > 50:
            tot += 1; above += int(d["Close"].iloc[-1] > d["Close"].tail(50).mean())
    breadth = round(100*above/tot) if tot else 0
    g_up, i_up = g_acc > 0, i_acc > 0
    quad = ("Quad 1" if (g_up and not i_up) else "Quad 2" if (g_up and i_up)
            else "Quad 3" if (not g_up and i_up) else "Quad 4")
    desc = {"Quad 1":"Growth accelerating · inflation slowing","Quad 2":"Growth accelerating · inflation accelerating",
            "Quad 3":"Growth slowing · inflation accelerating","Quad 4":"Growth slowing · inflation slowing"}[quad]
    defensive = (not g_up) and (i_up or breadth < 50)
    return {"quad":quad, "quad_desc":desc, "growth_z":round(g_acc*100,2), "infl_z":round(i_acc*100,2),
            "breadth":breadth, "posture":"Defensive" if defensive else "Risk-on", "defensive":defensive}
