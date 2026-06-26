"""warroom/liquidity.py — exit feasibility.

You want to exit FIRST — but that needs liquidity to exit INTO. This estimates average daily $ (or
Rp) volume and flags names too thin to leave at size, especially IDX / small-caps. Anticipating the
exit signal is moot if the fill isn't there. (Magnitude/slippage at a precise position size needs
real ADV + order-book depth; this is the first-order screen.)
"""
from __future__ import annotations


def _fmt(v, unit):
    if v >= 1e12:
        return f"{unit}{v/1e12:.1f}T"
    if v >= 1e9:
        return f"{unit}{v/1e9:.1f}B"
    if v >= 1e6:
        return f"{unit}{v/1e6:.1f}M"
    return f"{unit}{v/1e3:.0f}K"


def assess(ticker, df):
    if df is None or len(df) < 20 or "Volume" not in df:
        return None
    v = df["Volume"].tail(20)
    c = df["Close"].tail(20)
    adv = float((v * c).mean())
    if adv <= 0:
        return None
    idr = str(ticker).endswith(".JK")
    unit = "Rp" if idr else "$"
    illiquid = adv < (2e9 if idr else 3e6)
    moderate = adv < (2e10 if idr else 3e7)
    tier = "thin — exit at size is slow/costly" if illiquid else ("moderate depth" if moderate else "deep / liquid")
    return {"adv": adv, "adv_fmt": _fmt(adv, unit), "illiquid": illiquid, "tier": tier}
