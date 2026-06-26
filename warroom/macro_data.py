"""warroom/macro_data.py — the complete relevant-macro registry + broken-link scanner.

Operationalizes Ricky's thesis: "find the one broken link in the economic chain → K-shape." It
tracks the FULL chain of leading indicators (not a subset) and flags the links flashing red.
Consumer health leads — real disposable income going negative (the screenshot) is the canary:
consumer runs out of money → spending falls → earnings miss → layoffs → recession.

Each series: (label, cluster, transform, direction, warn, danger).
  transform: 'yoy' (vs ~1yr ago, monthly), 'level' (latest), 'chg' (vs prior obs)
  direction: +1 higher = healthier, -1 higher = worse
Thresholds are heuristic and editable. FRED series IDs — fetched by build_feeds / fred loader.
"""
from __future__ import annotations

REGISTRY = {
    # ── Consumer health (leads the cycle; the screenshot's theme) ──
    "DSPIC96":      ("Real disposable income (YoY)", "Consumer", "yoy", +1, 1.0, 0.0),
    "PCEC96":       ("Real consumer spending (YoY)", "Consumer", "yoy", +1, 1.0, 0.0),
    "PSAVERT":      ("Personal saving rate", "Consumer", "level", +1, 4.0, 3.0),
    "DRCCLACBS":    ("Credit-card delinquency", "Consumer", "level", -1, 2.8, 3.6),
    "UMCSENT":      ("Consumer sentiment (UMich)", "Consumer", "level", +1, 70, 60),
    # ── Labor ──
    "PAYEMS":       ("Nonfarm payrolls (YoY)", "Labor", "yoy", +1, 1.0, 0.0),
    "UNRATE":       ("Unemployment rate", "Labor", "level", -1, 4.3, 4.8),
    "ICSA":         ("Initial jobless claims", "Labor", "level", -1, 260000, 300000),
    "JTSJOL":       ("Job openings JOLTS (YoY)", "Labor", "yoy", +1, 0.0, -10.0),
    # ── Housing ──
    "HOUST":        ("Housing starts (YoY)", "Housing", "yoy", +1, 0.0, -10.0),
    "MORTGAGE30US": ("30y mortgage rate", "Housing", "level", -1, 6.8, 7.5),
    # ── Inflation (Fed's actual target is PCE) ──
    "PCEPILFE":     ("Core PCE — Fed target (YoY)", "Inflation", "yoy", -1, 2.5, 3.5),
    "CPIAUCSL":     ("CPI (YoY)", "Inflation", "yoy", -1, 3.0, 4.0),
    "MICH":         ("Inflation expectations (UMich)", "Inflation", "level", -1, 3.2, 4.0),
    "T5YIE":        ("5y breakeven inflation", "Inflation", "level", -1, 2.5, 3.0),
    # ── Growth / manufacturing ──
    "INDPRO":       ("Industrial production (YoY)", "Growth", "yoy", +1, 0.5, 0.0),
    "RSAFS":        ("Retail sales (YoY)", "Growth", "yoy", +1, 1.5, 0.0),
    # ── Credit / financial conditions ──
    "BAMLH0A0HYM2": ("High-yield credit spread", "Credit", "level", -1, 4.0, 5.5),
    "NFCI":         ("Financial conditions (NFCI)", "Credit", "level", -1, 0.0, 0.35),
    # ── Yield curve (single best recession signal) ──
    "T10Y2Y":       ("Yield curve 10y-2y", "Rates", "level", +1, 0.2, 0.0),
    "T10Y3M":       ("Yield curve 10y-3m", "Rates", "level", +1, 0.2, 0.0),
    # ── Liquidity / policy ──
    "WALCL":        ("Fed balance sheet (YoY)", "Liquidity", "yoy", +1, 0.0, -8.0),
    "M2SL":         ("M2 money supply (YoY)", "Liquidity", "yoy", +1, 2.0, 0.0),
}


def series_ids():
    return list(REGISTRY.keys())


def _signal(series, tf):
    s = series.dropna()
    if len(s) < 2:
        return None
    last = float(s.iloc[-1])
    if tf == "yoy":
        if len(s) <= 12:
            return None
        base = float(s.iloc[-13])
        return (last / base - 1) * 100 if base else None
    if tf == "chg":
        return last - float(s.iloc[-2])
    return last  # level


def _status(val, direction, warn, danger):
    if val is None:
        return "n/a"
    if direction > 0:
        return "danger" if val <= danger else ("warning" if val <= warn else "ok")
    return "danger" if val >= danger else ("warning" if val >= warn else "ok")


def compute(fred_series):
    fred_series = fred_series or {}
    out = []
    for sid, (label, cluster, tf, dr, warn, danger) in REGISTRY.items():
        s = fred_series.get(sid)
        if s is None or len(s) == 0:
            continue
        val = _signal(s, tf)
        if val is None:
            continue
        out.append({"id": sid, "label": label, "cluster": cluster, "transform": tf,
                    "value": round(val, 2), "status": _status(val, dr, warn, danger)})
    return out


def broken_links(indicators):
    return [i for i in indicators if i["status"] == "danger"]


def kshape_score(indicators):
    if not indicators:
        return None
    d = sum(1 for i in indicators if i["status"] == "danger")
    w = sum(1 for i in indicators if i["status"] == "warning")
    n = len(indicators)
    score = round(100 * (d + 0.5 * w) / n)
    label = ("chain breaking — K-shape risk high" if score >= 50 else
             "stress building — watch the broken links" if score >= 25 else
             "chain intact")
    return {"score": score, "danger": d, "warning": w, "total": n, "label": label}
