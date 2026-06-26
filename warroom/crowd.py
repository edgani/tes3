"""warroom/crowd.py — measure the herd, so you can front-run it.

Your whole thesis is being early vs the FOMO crowd — which requires SEEING the crowd. This gauges
positioning froth from price-derived breadth (no paid sentiment feed needed): % of the universe
above its 50DMA + average RSI + average extension. Extreme heat = euphoria (fade / reversal risk);
extreme cold = capitulation (contrarian accumulation). Per-name froth feeds the decision brain.
(Precise retail sentiment — put/call, AAII, fund flows — would sharpen this once a feed is wired.)
"""
from __future__ import annotations


def _rsi(c, n=14):
    if len(c) <= n:
        return 50.0
    d = c.diff()
    up = d.clip(lower=0).rolling(n).mean().iloc[-1]
    dn = (-d.clip(upper=0)).rolling(n).mean().iloc[-1]
    if not dn:
        return 100.0 if up else 50.0
    return float(100 - 100 / (1 + up / dn))


def market_crowd(us_prices):
    above = 0
    rsis = []
    n = 0
    for t, df in (us_prices or {}).items():
        if df is None or len(df) < 55 or str(t).startswith("^"):
            continue
        c = df["Close"]
        ma = c.rolling(50).mean().iloc[-1]
        if ma == ma:
            above += 1 if c.iloc[-1] > ma else 0
            rsis.append(_rsi(c))
            n += 1
    if n < 5:
        return None
    pct_above = 100.0 * above / n
    avg_rsi = sum(rsis) / len(rsis)
    heat = round(0.5 * pct_above + 0.5 * avg_rsi)
    if heat >= 72:
        state, verdict = "euphoria", "crowd is euphoric — fade strength / tighten; reversal risk rising. Late to go long here."
    elif heat <= 32:
        state, verdict = "capitulation", "crowd has capitulated — contrarian accumulation zone; the herd is selling the lows."
    else:
        state, verdict = "neutral", "no crowd extreme — positioning is mid-range."
    return {"heat": heat, "pct_above50": round(pct_above), "avg_rsi": round(avg_rsi), "state": state, "verdict": verdict}


def name_crowd(df, direction="Long"):
    if df is None or len(df) < 55:
        return None
    c = df["Close"]
    rsi = _rsi(c)
    ma = c.rolling(50).mean().iloc[-1]
    sd = c.rolling(50).std().iloc[-1] or 1
    ext = (c.iloc[-1] - ma) / sd
    if rsi >= 70 or ext > 2:
        return {"state": "frothy", "rsi": round(rsi)}
    if rsi <= 32 or ext < -2:
        return {"state": "washed", "rsi": round(rsi)}
    return {"state": "neutral", "rsi": round(rsi)}
