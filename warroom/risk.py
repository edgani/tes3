"""warroom/risk.py — portfolio-level risk for the conviction book.

Answers the allocator's first question: how much can this book lose, and is the risk concentrated?
  • Exposure   — gross / net (bps of equity), long vs short split.
  • Concentration — largest single name, top-3, count.
  • Heat        — total capital-at-risk if EVERY stop is hit (Σ size×stop-distance), in % of equity.
  • Correlation — avg pairwise correlation of the (direction-adjusted) names: many names but high
                  correlation = one bet wearing a disguise.
  • VaR / CVaR  — 1-day 95% historical-simulation loss on the actual position-weighted book.
Flags any limit breach. Limits are editable.
"""
from __future__ import annotations
import numpy as np, pandas as pd

LIMITS = {"gross_bps": 1500, "name_bps": 400, "heat_pct": 6.0, "avg_corr": 0.60, "var_pct": 4.0}


def _bps(s):
    return float((s.get("size") or {}).get("sized_bps") or 0)


def portfolio(conviction, allpx, limits=None):
    L = {**LIMITS, **(limits or {})}
    names = [s for s in (conviction or []) if s.get("_dir") in ("Long", "Short") and _bps(s) > 0]
    if not names:
        return {"n": 0}
    longs = [s for s in names if s["_dir"] == "Long"]
    shorts = [s for s in names if s["_dir"] == "Short"]
    gross = sum(_bps(s) for s in names)
    net = sum(_bps(s) * (1 if s["_dir"] == "Long" else -1) for s in names)
    sizes = sorted((_bps(s) for s in names), reverse=True)
    max_name, top3 = (sizes[0] if sizes else 0), sum(sizes[:3])

    # portfolio heat: Σ position% × stop-distance% = total equity lost if all stops trigger
    heat = 0.0
    for s in names:
        px, stop = s.get("px"), s.get("stop")
        if px and stop and px > 0:
            heat += (_bps(s) / 10000.0) * (abs(px - stop) / px)
    heat_pct = heat * 100.0

    # direction-adjusted daily returns for correlation + VaR
    rets = {}
    for s in names:
        df = allpx.get(s["ticker"])
        if df is not None and len(df) > 30:
            r = df["Close"].pct_change().dropna().tail(120)
            rets[s["ticker"]] = r * (1 if s["_dir"] == "Long" else -1)
    avg_corr = var_pct = cvar_pct = None
    if len(rets) >= 2:
        R = pd.DataFrame(rets).dropna()
        if len(R) > 20:
            cm = R.corr().values
            iu = np.triu_indices_from(cm, 1)
            avg_corr = float(np.nanmean(cm[iu])) if len(iu[0]) else None
            bmap = {s["ticker"]: _bps(s) for s in names}
            port = np.zeros(len(R))
            for c in R.columns:
                port += (bmap.get(c, 0) / 10000.0) * R[c].values   # daily % P&L of the book
            q5 = np.percentile(port, 5)
            var_pct = float(-q5 * 100)
            tail = port[port <= q5]
            cvar_pct = float(-tail.mean() * 100) if len(tail) else var_pct

    breaches = []
    if gross > L["gross_bps"]: breaches.append(f"gross {gross:.0f}bps > {L['gross_bps']}bps cap")
    if max_name > L["name_bps"]: breaches.append(f"max name {max_name:.0f}bps > {L['name_bps']}bps cap")
    if heat_pct > L["heat_pct"]: breaches.append(f"heat {heat_pct:.1f}% > {L['heat_pct']}% (too much at risk if stopped)")
    if avg_corr is not None and avg_corr > L["avg_corr"]: breaches.append(f"avg corr {avg_corr:.2f} > {L['avg_corr']} (book is crowded / undiversified)")
    if var_pct is not None and var_pct > L["var_pct"]: breaches.append(f"1d VaR {var_pct:.1f}% > {L['var_pct']}% cap")

    return {"n": len(names), "n_long": len(longs), "n_short": len(shorts),
            "gross_bps": round(gross), "net_bps": round(net),
            "long_bps": round(sum(_bps(s) for s in longs)), "short_bps": round(sum(_bps(s) for s in shorts)),
            "max_name_bps": round(max_name), "top3_bps": round(top3),
            "heat_pct": round(heat_pct, 2),
            "avg_corr": round(avg_corr, 2) if avg_corr is not None else None,
            "var_pct": round(var_pct, 2) if var_pct is not None else None,
            "cvar_pct": round(cvar_pct, 2) if cvar_pct is not None else None,
            "breaches": breaches, "limits": L}
