"""warroom/policy.py — Fed rate-path (market-implied) + inflation signal-vs-noise + bait detector.

Answers 'does a 75bps hike make sense / is it even priced?' without guessing. Two truth-tellers:

1) THE CURVE. Short-end Treasuries ≈ the market's expected average funds rate. If the 1Y sits only
   ~30-40bps over the funds rate, the market is pricing ~1 hike — NOT three. A loud '75bps / 3x hikes'
   call against a calm curve is BAIT: a positioning trap. The bond market rarely lies about policy;
   narratives do.

2) THE RIGHT INFLATION GAUGE. Read the Fed off SIGNAL (trimmed-mean / median / sticky PCE — smooth,
   geopolitics-resistant; the measure a Warsh-style Fed actually targets), not NOISE (headline CPI,
   oil spikes). If trimmed-mean is near target and flat/falling, there is no inflation problem to hike
   into — regardless of an oil-driven headline blip. The switch only flips if the SIGNAL trends up
   like 2021-22.

It also classifies falling oil as supply (disinflation-good) vs demand (recession-bad) by cross-
referencing real income, so 'disinflation' isn't naively read as risk-on when it's demand collapse.
Precise probabilities need Fed funds futures (CME) — this is the curve-implied first order.
"""
from __future__ import annotations

# series fetched for this module (added to the FRED pull)
POLICY_SERIES = ["DGS1MO", "DGS3MO", "DGS6MO", "DGS1", "DGS2", "DFEDTARU", "DFEDTARL"]
INFL_SIGNAL_SERIES = ["PCETRIM12M159SFRBDAL", "MEDCPIM158SFRBCLE", "CORESTICKM159SFRBATL"]


def series_ids():
    return POLICY_SERIES + INFL_SIGNAL_SERIES


def _last(fred, sid):
    s = fred.get(sid)
    if s is None or len(s) == 0:
        return None
    try:
        return float(s.dropna().iloc[-1])
    except Exception:
        return None


def _ago(fred, sid, n):
    s = fred.get(sid)
    if s is None:
        return None
    s = s.dropna()
    if len(s) <= n:
        return None
    try:
        return float(s.iloc[-1 - n])
    except Exception:
        return None


def rate_path(fred):
    """Market-implied policy bias from the short-end curve vs the funds rate."""
    up, lo = _last(fred, "DFEDTARU"), _last(fred, "DFEDTARL")
    ffr = (up + lo) / 2 if (up is not None and lo is not None) else (up if up is not None else lo)
    if ffr is None:
        ffr = _last(fred, "EFFR")
    y1, y2 = _last(fred, "DGS1"), _last(fred, "DGS2")
    m6, m3 = _last(fred, "DGS6MO"), _last(fred, "DGS3MO")
    anchor = y1 if y1 is not None else (m6 if m6 is not None else y2)
    if ffr is None or anchor is None:
        return None
    spread_1y = (y1 - ffr) if y1 is not None else None
    spread_2y = (y2 - ffr) if y2 is not None else None
    near = (m6 - ffr) if m6 is not None else spread_1y
    implied = round((spread_1y if spread_1y is not None else near) / 0.25, 1)  # rough # of 25bps over ~1y
    if near is None:
        bias = "unclear"
    elif near <= -0.15:
        bias = "cuts priced"
    elif near >= 0.45:
        bias = "multiple hikes priced"
    elif near >= 0.12:
        bias = "~1 hike priced"
    else:
        bias = "on hold"
    return {"ffr_mid": round(ffr, 2), "y1": y1, "y2": y2, "m6": m6, "m3": m3,
            "spread_1y_bps": round(spread_1y * 100) if spread_1y is not None else None,
            "spread_2y_bps": round(spread_2y * 100) if spread_2y is not None else None,
            "implied_25s": implied, "bias": bias}


def hike_priced(rate, bps=75):
    """Is a one-shot hike of `bps` (e.g. 75 = 3×25) consistent with the curve?"""
    if not rate or rate.get("spread_1y_bps") is None:
        return None
    s = rate["spread_1y_bps"]
    need = bps  # to price ~3 hikes over a year the 1Y would sit ~+50-75bps over funds
    if s >= need - 10:
        return {"priced": True, "note": f"curve prices ~{rate['implied_25s']}×25bps — broadly consistent with a +{bps}bps path"}
    if s <= 0:
        return {"priced": False, "note": f"curve prices ZERO net hikes (1Y {s:+d}bps vs funds) — a +{bps}bps hike is fully offside; if anything cuts are leaning"}
    return {"priced": False, "note": f"curve prices only ~{rate['implied_25s']}×25bps (1Y {s:+d}bps over funds) — a +{bps}bps (3×) hike is NOT what the bond market is pricing"}


def inflation_signal(fred):
    """Underlying inflation trend from smooth measures (the Warsh switch)."""
    tm = _last(fred, "PCETRIM12M159SFRBDAL")
    tm6 = _ago(fred, "PCETRIM12M159SFRBDAL", 6)
    sticky = _last(fred, "CORESTICKM159SFRBATL")
    sticky6 = _ago(fred, "CORESTICKM159SFRBATL", 6)
    if tm is None and sticky is None:
        return None
    core = tm if tm is not None else sticky
    base = tm6 if (tm is not None and tm6 is not None) else sticky6
    trend = (core - base) if (core is not None and base is not None) else None
    rising = trend is not None and trend > 0.2
    falling = trend is not None and trend < -0.2
    if core is None:
        regime = "unclear"
    elif core >= 3.0 and rising:
        regime = "re-accelerating — real inflation problem (Warsh switch ON → hawkish justified)"
    elif core <= 2.6 and not rising:
        regime = "near target, not rising — no inflation problem (hawkish call unsupported)"
    elif rising:
        regime = "drifting up — watch for re-acceleration"
    else:
        regime = "contained"
    return {"trimmed_mean": tm, "sticky": sticky, "trend_6m": round(trend, 2) if trend is not None else None,
            "rising": rising, "falling": falling, "regime": regime}


def oil_classify(oil_yoy, real_income_neg):
    """Falling oil: supply (disinflation-good) vs demand (recession-bad)?"""
    if oil_yoy is None:
        return None
    if oil_yoy >= 0:
        return {"kind": "rising", "note": "oil firm — inflation tailwind, not the current debate"}
    if real_income_neg:
        return {"kind": "demand", "note": "oil falling WITH negative real income → demand destruction (recessionary disinflation). 'Cheap oil' is not a clean risk-on tailwind — it's the K-shape."}
    return {"kind": "supply", "note": "oil falling without a demand crack → supply-led disinflation (genuine tailwind, dovish-friendly)"}


def fed_probabilities(cme_implied=None, rate=None):
    """Market-implied probability of the next Fed move.

    PRECISE path needs CME FedWatch (Fed funds futures). Pass `cme_implied` as the implied-rate dict
    from your CME feed, e.g. {"2026-07-29": {"prob_hike": 0.18, "prob_hold": 0.77, "prob_cut": 0.05},
    ...} and this returns it cleaned. Without it, there is NO clean probability — fall back to the
    curve-implied direction in rate_path() (a bias, not a probability). This function never fabricates
    a number; it returns source='cme' when given real data, else source='curve_proxy' / None.
    """
    if isinstance(cme_implied, dict) and cme_implied:
        nxt = sorted(cme_implied.keys())[0]
        return {"source": "cme", "meeting": nxt, "implied": cme_implied[nxt], "all": cme_implied}
    if rate and rate.get("bias"):
        return {"source": "curve_proxy", "note": f"no CME feed — curve-implied bias only: {rate['bias']} "
                f"(~{rate.get('implied_25s','?')}\u00d725bps over ~1y). Plug CME FedWatch for true probabilities."}
    return None


def synthesize(fred, oil_yoy=None, real_income_neg=None):
    rate = rate_path(fred)
    infl = inflation_signal(fred)
    oil = oil_classify(oil_yoy, real_income_neg)
    hp = hike_priced(rate, 75) if rate else None
    # data-coherent Fed lean
    lean = "unclear"
    if infl and rate:
        if infl.get("rising") and (infl.get("trimmed_mean") or 0) >= 3.0:
            lean = "hawkish IS supported — underlying inflation re-accelerating"
        elif real_income_neg and not infl.get("rising"):
            lean = "dovish — growth weakening, underlying inflation contained; next move leans cut/hold, not hike"
        else:
            lean = "on hold — no clear push either way in the clean data"
    # bait verdict: a hawkish narrative vs a calm curve + benign signal
    bait = None
    if rate and infl and hp is not None and not hp.get("priced") and not infl.get("rising"):
        bait = ("BAIT RISK: the loud hawkish call (75bps / 3× hikes) is NOT priced by the curve and is "
                "NOT supported by the underlying inflation signal. Likely a positioning trap — fade the "
                "narrative, the short end is telling the truth. Flip only if trimmed-mean starts trending up.")
    return {"rate": rate, "inflation": infl, "oil": oil, "hike_75_priced": hp, "fed_lean": lean, "bait": bait}
