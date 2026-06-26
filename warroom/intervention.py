"""warroom/intervention.py — per-instrument intervention / event-risk flags.

Scoped by design: a flag attaches to the AFFECTED instrument's own setup and surfaces only
there (no global alarm). It is direction-aware — a Long USD/JPY into the BoJ zone is a threat
(it gets reversed); a Short is a tailwind. Zones are heuristic and EDITABLE (levels drift), and
are backed by a level-independent statistical stretch + an active-reversal detector so the flag
still fires when hardcoded levels go stale or when an intervention has just hit.
"""
from __future__ import annotations
import datetime as dt

# FX pairs prone to central-bank intervention. `side` = the setup direction that INVITES
# intervention (the one that gets reversed). `zone` = approx level band where the CB acts.
FX_ZONES = {
    "USDJPY=X": {"name": "USD/JPY", "cb": "BoJ", "side": "Long", "zone": (155, 162), "acute": 158,
                 "levels": [152, 160], "note": "BoJ sells USD / buys JPY near these levels → sharp reversal down"},
    "USDIDR=X": {"name": "USD/IDR", "cb": "Bank Indonesia", "side": "Long", "zone": (16300, 17000), "acute": 16500,
                 "levels": [16300, 16500], "note": "BI defends the rupiah / smooths volatility on rapid IDR weakness"},
}

# BEI symmetric auto-reject (ARA/ARB) tiers by price (Rp) — approx 2024+ rules, editable.
def _araarb_pct(price):
    if price < 200: return 0.35
    if price <= 5000: return 0.25
    return 0.20

# Scheduled CB decision dates (approx 2026, editable). Event risk = decision/intervention window.
CB_EVENTS = {
    "FOMC": ["2026-01-28", "2026-03-18", "2026-04-29", "2026-06-17", "2026-07-29", "2026-09-16", "2026-10-28", "2026-12-09"],
    "BoJ": ["2026-01-23", "2026-03-19", "2026-04-28", "2026-06-16", "2026-07-31", "2026-09-18", "2026-10-30", "2026-12-18"],
    "BI-RDG": ["2026-06-17", "2026-07-22", "2026-08-19", "2026-09-16", "2026-10-21", "2026-11-18", "2026-12-16"],
}


def _days_to_next_event(cal_keys, today=None):
    today = today or dt.date.today()
    best, which = None, None
    for k in cal_keys:
        for ds in CB_EVENTS.get(k, []):
            try:
                d = dt.date.fromisoformat(ds)
            except Exception:
                continue
            if d >= today:
                n = (d - today).days
                if best is None or n < best:
                    best, which = n, (k, ds)
    return best, which


def _stretch(df):
    """Level-independent signature: z-score of price vs 50DMA + 10-day one-way move + last-bar move."""
    c = df["Close"].dropna()
    if len(c) < 55:
        return 0.0, 0.0, 0.0
    ma = c.rolling(50).mean().iloc[-1]; sd = c.rolling(50).std().iloc[-1]
    z = float((c.iloc[-1] - ma) / sd) if sd else 0.0
    chg10 = float(c.iloc[-1] / c.iloc[-11] - 1) if len(c) > 11 else 0.0
    last = float(c.iloc[-1] / c.iloc[-2] - 1) if len(c) > 1 else 0.0
    return z, chg10, last


def assess(ticker, df, market, direction):
    """Return an intervention flag for THIS instrument, or None. Direction-aware."""
    if df is None or len(df) < 20:
        return None
    px = float(df["Close"].iloc[-1])

    # 1) FX central-bank intervention
    if ticker in FX_ZONES:
        z = FX_ZONES[ticker]; lo, _ = z["zone"]
        sigz, chg10, last = _stretch(df)
        in_zone = px >= lo
        score = (2 if px >= z["acute"] else 1) if in_zone else 0
        if sigz >= 2 and chg10 > 0:
            score += 1                       # rapid one-way weakness amplifies
        # active-reversal: in/near zone AND a sharp counter-move on the last bar (intervention just hit)
        if in_zone and last <= -0.012:
            return {"level": "high", "kind": "FX-intervention-active", "cb": z["cb"],
                    "msg": f"Possible {z['cb']} intervention UNDERWAY — {z['name']} reversed {last*100:+.1f}% from the zone ({px:,.0f}). Counter-move can extend fast; do not fade a {direction} into it."}
        if score <= 0:
            return None
        aligned = (direction == z["side"])
        if not aligned:
            return {"level": "note", "kind": "FX-intervention", "cb": z["cb"],
                    "msg": f"{z['cb']} intervention zone ({px:,.0f}, watch {z['levels']}) — but you're {direction}; intervention would be a tailwind here, not a threat."}
        lvl = "high" if score >= 2 else "elevated"
        return {"level": lvl, "kind": "FX-intervention", "cb": z["cb"],
                "msg": f"{z['cb']} intervention zone (px {px:,.0f}, watch {z['levels']}). {z['note']}. A {direction} here risks a policy-driven reversal — size down / tighten / don't chase."}

    # 2) IDX auto-reject (ARA/ARB) proximity
    if ticker.endswith(".JK") and len(df) >= 2:
        prev = float(df["Close"].iloc[-2])
        if prev > 0:
            mv = px / prev - 1
            band = _araarb_pct(px)
            prox = abs(mv) / band
            if prox >= 0.7:
                hitting = "ARA (upper limit)" if mv > 0 else "ARB (lower limit)"
                lvl = "high" if prox >= 0.9 else "elevated"
                return {"level": lvl, "kind": "ARA-ARB",
                        "msg": f"Near {hitting}: today {mv*100:+.1f}% vs ±{band*100:.0f}% auto-reject band ({prox*100:.0f}% used). Liquidity can vanish at the band — fills/exits unreliable; bandar can pin or gap it."}
    return None


def event_tag(ticker, market):
    """Light CB-event proximity tag (≤5 days) for rate/FX-sensitive instruments."""
    if ticker == "USDJPY=X":
        keys = ["FOMC", "BoJ"]
    elif ticker == "USDIDR=X":
        keys = ["FOMC", "BI-RDG"]
    elif market == "FX" or ticker in ("GLD", "DX-Y.NYB"):
        keys = ["FOMC"]
    elif market == "US":
        keys = ["FOMC"]
    elif market == "IHSG":
        keys = ["BI-RDG", "FOMC"]
    else:
        return None
    n, which = _days_to_next_event(keys)
    if n is None or n > 5:
        return None
    k, ds = which
    return {"level": "elevated" if n <= 2 else "note", "kind": "event",
            "msg": f"{k} decision in {n}d ({ds}) — event/decision risk; expect a vol pop, size accordingly."}
