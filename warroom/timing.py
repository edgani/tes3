"""warroom/timing.py — anticipation & timing layer.

Goal: be the one who anticipates and enters/exits AHEAD of the crowd — not chase FOMO.
For each setup it answers four things:
  • Time horizon   — TRADE (days) / TREND (weeks) / TAIL (months) + an estimated days-to-target.
  • Cycle phase    — Accumulation/base · Early markup · Mid markup · Late/extended · Distribution.
  • Entry timing   — anti-FOMO verdict: EARLY (ahead of crowd) / ON-TIME / LATE (FOMO zone, don't chase).
  • Exit anticipation — when to scale out BEFORE the herd (TREND ceiling, RSI stretch, distribution).

Direction-aware (a Long extended into highs is FOMO; a Short into the same highs may be early).
Uses price structure (extension vs 50DMA, RSI, 60d range position, 20d momentum, ATR) + the Hedgeye
TRADE/TREND/TAIL risk-range bands when available, and cross-references the front-run engine.
"""
from __future__ import annotations
import numpy as np, pandas as pd


def _rsi(c, n=14):
    if len(c) <= n:
        return 50.0
    d = c.diff()
    up = d.clip(lower=0).rolling(n).mean().iloc[-1]
    dn = (-d.clip(upper=0)).rolling(n).mean().iloc[-1]
    if not dn:
        return 100.0 if up else 50.0
    return float(100 - 100 / (1 + up / dn))


def _atr(df, n=14):
    h, l, c = df["High"], df["Low"], df["Close"]
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    v = tr.rolling(n).mean().iloc[-1]
    return float(v) if v == v else float((h.iloc[-1] - l.iloc[-1]))


def assess(ticker, df, direction, entry, stop, target, rr=None, frontrun=None):
    if df is None or len(df) < 60 or direction not in ("Long", "Short"):
        return None
    c = df["Close"].dropna()
    px = float(c.iloc[-1])
    ma20 = float(c.rolling(20).mean().iloc[-1])
    ma50 = float(c.rolling(50).mean().iloc[-1])
    sd50 = max(float(c.rolling(50).std().iloc[-1] or 0), px * 0.008)   # vol floor → z-score can't explode on tight bases
    ext = (px - ma50) / sd50
    pct = px / ma50 - 1
    rsi = _rsi(c)
    lo60, hi60 = float(c.tail(60).min()), float(c.tail(60).max())
    rngpos = (px - lo60) / ((hi60 - lo60) or 1)
    mom20 = float(px / c.iloc[-21] - 1) if len(c) > 21 else 0.0
    atr = _atr(df) or (px * 0.02)

    sgn = 1 if direction == "Long" else -1
    dext = ext * sgn                      # directional stretch: + = already moved your way (extended)
    dpct = pct * sgn                      # directional % vs 50DMA — guards against tiny-move false "extended"
    drng = rngpos if direction == "Long" else (1 - rngpos)
    dmom = mom20 * sgn
    fr = frontrun or set()

    # --- cycle phase + anti-FOMO entry verdict (z-stretch AND a real % move required for "extended") ---
    if dext <= 0.5 and drng <= 0.55 and 38 <= rsi <= 60:
        phase, fomo, entry_t = "Accumulation / base", "EARLY — ahead of crowd", "accumulate / scale in before the move"
    elif dext <= 1.4 and drng <= 0.82 and dmom > 0:
        phase, fomo, entry_t = "Early markup", "ON-TIME — trend young", "enter; crowd not fully in yet"
    elif (dext > 1.8 and dpct > 0.04) or (direction == "Long" and rsi >= 74) or (direction == "Short" and rsi <= 26) or (drng > 0.93 and dpct > 0.04):
        phase, fomo, entry_t = "Late / extended", "LATE — FOMO zone", f"don't chase — wait pullback toward {ma20:,.2f} (20DMA) / entry zone"
    elif dext > 1.4 and dmom <= 0:
        phase, fomo, entry_t = "Distribution / stalling", "LATE — crowd already in", "prepare exit; momentum fading at the highs"
    else:
        phase, fomo, entry_t = "Mid markup", "ON-TIME", "enter on strength or a shallow dip"
    if (ticker in fr) and "EARLY" not in fomo:
        entry_t += " · front-run: boarding now"

    # --- time horizon (Hedgeye TRADE / TREND / TAIL) ---
    horizon = "TREND (weeks)"
    if isinstance(rr, dict) and "trend" in rr:
        t_trr = (rr.get("trade") or {}).get("trr")
        ta_trr = (rr.get("tail") or {}).get("trr")
        if t_trr and abs(target - entry) <= abs(t_trr - entry) * 1.1:
            horizon = "TRADE (days)"
        elif ta_trr and abs(target - entry) >= abs(ta_trr - entry) * 0.8:
            horizon = "TAIL (months)"
    hdays = int(min(150, max(2, round(abs(target - entry) / atr)))) if atr > 0 else None

    # --- exit anticipation (scale out BEFORE the herd) ---
    ex = []
    if isinstance(rr, dict):
        ceil = (rr.get("trend") or {}).get("trr") if direction == "Long" else (rr.get("trend") or {}).get("lrr")
        if ceil:
            dist = (ceil - px) / px * sgn
            if 0 <= dist <= 0.02:
                ex.append("at TREND ceiling — scale out into strength")
    if (direction == "Long" and rsi >= 75) or (direction == "Short" and rsi <= 25):
        ex.append(f"RSI {rsi:.0f} stretched — trail / take partials")
    if dext > 2.2:
        ex.append("over-extended vs 50DMA — mean-reversion risk")
    if phase.startswith("Distribution"):
        ex.append("distribution signs — exit ahead of the herd")
    exit_watch = " · ".join(ex) if ex else "hold while structure intact; exit on TREND break or target"

    return {"horizon": horizon, "hold_days_est": hdays, "phase": phase,
            "anti_fomo": fomo, "entry_timing": entry_t, "exit_watch": exit_watch,
            "rsi": round(rsi), "ext": round(float(ext), 2)}
