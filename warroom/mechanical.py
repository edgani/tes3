"""warroom/mechanical.py — scheduled & rule-driven (mechanical) flow detection.

Unlike intervention (reactive surprise), these flows are CALENDAR/rule-driven and therefore
anticipatable — you can be positioned before the forced flow hits:
  • Index reconstitution / rebalance — S&P quarterly, Russell (June), IDX LQ45/IDX30 review.
  • Triple/quad-witching — 3rd Friday of Mar/Jun/Sep/Dec.
  • Month/quarter-end rebalancing — pension / 60-40 / risk-parity trim winners back to target.
  • Vol-target / risk-parity / CTA deleveraging — vol spike forces mechanical selling into weakness.
  • Commodity index roll — GSCI/DBC roll window (~5th-9th business day).
Dates/levels are heuristic and editable; estimators are direction+timing (magnitude needs AUM data).
"""
from __future__ import annotations
import calendar, datetime as dt
import numpy as np, pandas as pd


def _third_friday(y, m):
    d = dt.date(y, m, 1)
    while d.weekday() != 4:
        d += dt.timedelta(days=1)
    return d + dt.timedelta(days=14)


def _next(cands, today):
    fut = [d for d in cands if d >= today]
    return min(fut) if fut else None


def _next_witching(today):
    return _next([_third_friday(y, m) for y in (today.year, today.year + 1) for m in (3, 6, 9, 12)], today)


def _next_russell(today):
    out = []
    for y in (today.year, today.year + 1):
        d = dt.date(y, 6, 30)
        while d.weekday() != 4:
            d -= dt.timedelta(days=1)
        out.append(d)
    return _next(out, today)


def _next_idx_review(today):
    return _next([dt.date(y, m, 1) for y in (today.year, today.year + 1) for m in (2, 8)], today)


def rebalance_tag(ticker, market, today=None):
    """Per-instrument scheduled-rebalance proximity (≤5-7 days), or None."""
    today = today or dt.date.today()
    ev = []
    if market == "US":
        w = _next_witching(today)
        if w and 0 <= (w - today).days <= 5:
            ev.append(("triple-witching + S&P quarterly rebalance", (w - today).days, w))
        r = _next_russell(today)
        if r and 0 <= (r - today).days <= 7:
            ev.append(("Russell reconstitution", (r - today).days, r))
    elif market == "IHSG":
        x = _next_idx_review(today)
        if x and 0 <= (x - today).days <= 7:
            ev.append(("LQ45 / IDX30 review effective", (x - today).days, x))
    elif market == "Commodities":
        bd = int(np.busday_count(today.replace(day=1), today)) + 1
        if 5 <= bd <= 9:
            ev.append(("GSCI / commodity index roll window", 0, None))
    if not ev:
        return None
    name, n, d = sorted(ev, key=lambda e: e[1])[0]
    when = f"in {n}d ({d})" if d else "active now"
    return {"level": "elevated" if n <= 2 else "note", "kind": "rebalance",
            "msg": f"{name} {when} — forced index flows + volume spike. Position ahead; don't get run over at the print."}


def month_end_flow(allpx, today=None):
    """60/40 + risk-parity month-end rebalance direction from SPY vs TLT MTD performance."""
    today = today or dt.date.today()
    dom_left = calendar.monthrange(today.year, today.month)[1] - today.day
    spy = allpx.get("SPY")
    if spy is None or len(spy) < 25:
        return None

    def mtd(df):
        c = df["Close"]
        try:
            m = c[c.index.to_period("M") == pd.Period(today, freq="M")]
            if len(m) > 1:
                return float(c.iloc[-1] / m.iloc[0] - 1)
        except Exception:
            pass
        return float(c.iloc[-1] / c.iloc[-min(len(c) - 1, 15)] - 1)

    spy_mtd = mtd(spy)
    tlt = allpx.get("TLT")
    spread = spy_mtd - (mtd(tlt) if tlt is not None and len(tlt) > 25 else 0.0)
    if dom_left <= 5:
        if spread > 0.02:
            return {"phase": "into month-end", "direction": "SELL equities", "level": "elevated",
                    "note": f"equities outperformed bonds +{spread*100:.1f}% MTD → 60/40 & risk-parity mechanically trim equities into month-end (~{dom_left}d left). Headwind now → tailwind early next month."}
        if spread < -0.02:
            return {"phase": "into month-end", "direction": "BUY equities", "level": "elevated",
                    "note": f"equities lagged bonds {spread*100:.1f}% MTD → rebalancers mechanically ADD equities into month-end (~{dom_left}d). Tailwind now."}
        return {"phase": "into month-end", "direction": "neutral", "level": "note",
                "note": f"~{dom_left}d to month-end; equity-bond spread {spread*100:+.1f}% MTD — modest rebalance flow."}
    if today.day <= 3:
        return {"phase": "early month", "direction": "inflows", "level": "note",
                "note": "start-of-month allocation inflows (401k / SIP) — typical seasonal tailwind."}
    return None


def vol_target_pressure(vix, vix_series=None):
    """Vol-target / risk-parity / CTA mechanical deleveraging flag on a vol spike."""
    if vix is None:
        return None
    try:
        v = float(vix)
    except Exception:
        return None
    chg = None
    if vix_series is not None and len(vix_series) > 6:
        try:
            chg = float(v / vix_series.iloc[-6] - 1)
        except Exception:
            pass
    if v >= 26 and (chg is None or chg > 0.25):
        tail = f" (+{chg*100:.0f}% / 5d)" if chg else ""
        return {"level": "elevated", "kind": "vol-target",
                "note": f"VIX {v:.0f}{tail} — vol-target / risk-parity / CTA funds mechanically DE-LEVER (sell into weakness), amplifying downside. Expect forced selling on further vol spikes; fade the panic only once it stalls."}
    return None
