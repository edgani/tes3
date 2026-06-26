"""warroom/structure.py — objective swing structure: tops/bottoms, level tests, neckline breaks.

The mechanical version of what chartists draw by hand ("triple tops, broke neckline"). Finds swing
pivots, the levels tested repeatedly (resistance/support), the neckline (the swing low between tops /
high between bottoms), and whether price has BROKEN it. A multi-test top whose neckline breaks is
distribution confirmed; a multi-test base that breaks out is accumulation confirmed. Pair with the
volume-truth read (a break on heavy volume is high-conviction; on light volume, suspect/false).
Detecting the structure is objective; whether the pattern PAYS is a walk-forward question — that
discipline is what separates a real edge from a well-marketed lucky call.
"""
from __future__ import annotations
import numpy as np


def _pivots(df, k=3):
    h, l = df["High"].values, df["Low"].values
    hi, lo = [], []
    for i in range(k, len(df) - k):
        if h[i] == max(h[i - k:i + k + 1]):
            hi.append((i, float(h[i])))
        if l[i] == min(l[i - k:i + k + 1]):
            lo.append((i, float(l[i])))
    return hi, lo


def _trend(hi, lo):
    if len(hi) >= 2 and len(lo) >= 2:
        hh = hi[-1][1] > hi[-2][1]
        hl = lo[-1][1] > lo[-2][1]
        lh = hi[-1][1] < hi[-2][1]
        ll = lo[-1][1] < lo[-2][1]
        if hh and hl:
            return "uptrend (higher highs + higher lows)"
        if lh and ll:
            return "downtrend (lower highs + lower lows)"
    return "range / transition"


def read(df, lookback=140, tol=0.03):
    if df is None or len(df) < 50 or not {"High", "Low", "Close"}.issubset(df.columns):
        return None
    d = df.tail(lookback)
    hi, lo = _pivots(d, k=3)
    if len(hi) < 2 or len(lo) < 2:
        return None
    close = float(d["Close"].iloc[-1])
    trend = _trend(hi, lo)

    # resistance: cluster of swing highs near the top
    top = max(h for _, h in hi)
    res_tests = [h for _, h in hi if abs(h / top - 1) <= tol]
    n_res = len(res_tests)
    res = float(np.mean(res_tests))
    # support: cluster of swing lows near the bottom
    bot = min(l for _, l in lo)
    sup_tests = [l for _, l in lo if abs(l / bot - 1) <= tol]
    n_sup = len(sup_tests)
    sup = float(np.mean(sup_tests))

    pattern = None
    broke = None
    # topping: >=2 tests of resistance, neckline = lowest swing low between first & last test
    top_idxs = [i for i, h in hi if abs(h / top - 1) <= tol]
    if n_res >= 2 and len(top_idxs) >= 2:
        lo_between = [l for i, l in lo if top_idxs[0] <= i <= top_idxs[-1]]
        neckline = min(lo_between) if lo_between else sup
        if close < neckline:
            pattern = f"distribution top — {n_res} tests of {res:.1f}, broke neckline {neckline:.1f}"
            broke = "down"
        else:
            pattern = f"topping — {n_res} tests of {res:.1f}, neckline {neckline:.1f} intact"
    # bottoming: >=2 tests of support, neckline = highest swing high between
    bot_idxs = [i for i, l in lo if abs(l / bot - 1) <= tol]
    if broke is None and n_sup >= 2 and len(bot_idxs) >= 2:
        hi_between = [h for i, h in hi if bot_idxs[0] <= i <= bot_idxs[-1]]
        neckline = max(hi_between) if hi_between else res
        if close > neckline:
            pattern = f"accumulation base — {n_sup} tests of {sup:.1f}, broke out {neckline:.1f}"
            broke = "up"
        else:
            pattern = f"basing — {n_sup} tests of {sup:.1f}, neckline {neckline:.1f} intact"
    if pattern is None:
        pattern = trend

    dist_res = (res / close - 1) * 100 if res > close else None
    dist_sup = (close / sup - 1) * 100 if sup < close else None
    return {"trend": trend, "pattern": pattern, "broke": broke,
            "resistance": round(res, 2), "res_tests": n_res, "support": round(sup, 2), "sup_tests": n_sup,
            "dist_to_res_pct": round(dist_res, 1) if dist_res is not None else None,
            "dist_to_sup_pct": round(dist_sup, 1) if dist_sup is not None else None}
