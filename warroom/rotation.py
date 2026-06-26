"""warroom/rotation.py — fast money-rotation map (RRG-style) + crypto risk-curve.

Markets rotate fast; the goal is to catch where capital is FLOWING before it's obvious, so you don't
stay anchored to yesterday's leaders. For each asset we measure relative strength vs a benchmark (is
it out/under-performing) and RS momentum (is that improving or fading), then place it in a rotation
quadrant:
  IMPROVING  (underperforming but accelerating) -> money starting to flow IN — rotate in EARLY
  LEADING    (outperforming + accelerating)      -> already the obvious leader (crowd is here)
  WEAKENING  (outperforming but fading)          -> money starting to leave — rotate OUT
  LAGGING    (underperforming + fading)           -> avoid
Rotation is clockwise improving->leading->weakening->lagging. The edge is IMPROVING (early) and
WEAKENING (early exit). Crypto gets its own risk-curve read: alts vs BTC tells you if risk is
rotating DOWN the curve (alt season) or fleeing UP to BTC.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

SECTORS = {"XLK": "Tech", "XLE": "Energy", "XLF": "Financials", "XLV": "Health", "XLI": "Industrials",
           "XLY": "Discretionary", "XLP": "Staples", "XLU": "Utilities", "XLB": "Materials",
           "XLRE": "Real estate", "XLC": "Communications"}
STYLES = {"IWM": "Small-cap", "IWD": "Value", "IWF": "Growth", "MTUM": "Momentum"}
CLASSES = {"SPY": "US equity", "GLD": "Gold", "USO": "Oil", "CPER": "Copper", "DBC": "Commodities",
           "TLT": "Long bonds", "HYG": "Credit", "BTC-USD": "Bitcoin"}
CRYPTO = {"ETH-USD": "Ethereum", "SOL-USD": "Solana", "BNB-USD": "BNB"}


def _state(a, b, n=50, mom_lb=10):
    d = pd.concat([a.rename("a"), b.rename("b")], axis=1).dropna()
    if len(d) < n + mom_lb + 2:
        return None
    rs = d["a"] / d["b"]
    base = rs.rolling(n).mean()
    ratio = float(rs.iloc[-1] / base.iloc[-1] - 1)            # RS vs its own trend
    mom = float(rs.iloc[-1] / rs.iloc[-mom_lb - 1] - 1)        # RS momentum
    if ratio >= 0 and mom >= 0:
        q = "leading"
    elif ratio >= 0 and mom < 0:
        q = "weakening"
    elif ratio < 0 and mom < 0:
        q = "lagging"
    else:
        q = "improving"
    return {"rs": round(ratio * 100, 2), "mom": round(mom * 100, 2), "quadrant": q}


def _group(allpx, members, bench_tkr, n=50, mom_lb=10):
    bench = allpx.get(bench_tkr)
    if bench is None:
        return []
    bc = bench["Close"]
    out = []
    for tkr, name in members.items():
        df = allpx.get(tkr)
        if df is None or tkr == bench_tkr:
            continue
        st = _state(df["Close"], bc, n, mom_lb)
        if st:
            out.append({"ticker": tkr, "name": name, **st})
    return out


def compute(allpx):
    res = {}
    res["sectors"] = _group(allpx, SECTORS, "SPY")
    res["styles"] = _group(allpx, STYLES, "SPY")
    # asset classes vs SPY as the risk benchmark (absolute leadership across the macro book)
    res["classes"] = _group(allpx, {k: v for k, v in CLASSES.items() if k != "SPY"}, "SPY")
    res["crypto"] = _group(allpx, CRYPTO, "BTC-USD", n=40, mom_lb=7)

    def inflow(items):
        imp = sorted([x for x in items if x["quadrant"] == "improving"], key=lambda z: -z["mom"])
        lead = sorted([x for x in items if x["quadrant"] == "leading"], key=lambda z: -z["mom"])
        return imp, lead

    def outflow(items):
        return sorted([x for x in items if x["quadrant"] == "weakening"], key=lambda z: z["mom"])

    allitems = res["sectors"] + res["styles"] + res["classes"]
    imp, lead = inflow(allitems)
    res["rotating_in"] = imp[:6]
    res["leaders"] = lead[:6]
    res["rotating_out"] = outflow(allitems)[:6]
    # fast movers (high |momentum| = fast rotation, don't get left behind)
    res["fast"] = sorted(allitems, key=lambda z: -abs(z["mom"]))[:5]

    # crypto risk-curve: are alts rotating in (alt season) or fleeing to BTC?
    alts = res["crypto"]
    if alts:
        strong = [a for a in alts if a["quadrant"] in ("leading", "improving")]
        weak = [a for a in alts if a["quadrant"] in ("lagging", "weakening")]
        if len(strong) >= max(1, len(alts) // 2) and len(strong) >= len(weak):
            curve = "risk rotating DOWN the curve — alts outperforming BTC (alt-season behaviour)"
        elif len(weak) > len(strong):
            curve = "flight UP to BTC — alts lagging, risk-off within crypto"
        else:
            curve = "mixed — no clear crypto rotation"
        res["crypto_curve"] = {"verdict": curve, "members": alts}
    return res
