"""warroom/price_action.py — volume-truth (effort vs result) + move-character (velocity/emotion).

Price-action FIRST, macro as confirmation. Volume is the truth: a drop on heavy volume is
distribution; a drop on light volume is just absent buyers (often exhaustion). The CHARACTER of the
move — slow grind vs fast panic, range expanding vs contracting, where in the range — tells you what
the crowd is FEELING. This answers the tape-reading questions directly (why are they selling? fast or
slow? is volume confirming?) instead of reaching for a data story to justify the move after the fact.

effort = volume vs its average ; result = price distance achieved vs ATR.
  high effort + small result  -> ABSORPTION (smart money soaking supply/demand)
  high effort + big result    -> CONVICTION (real distribution if down, real demand if up)
  low effort + big result     -> NO-SUPPLY / NO-DEMAND (thin, suspect, easy to reverse)
  low effort + small result   -> QUIET
"""
from __future__ import annotations
import numpy as np
import pandas as pd


def _atr(df, n=14):
    h, l, c = df["High"], df["Low"], df["Close"]
    pc = c.shift(1)
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    v = float(tr.tail(n).mean())
    return v if v == v else None


def read(df, lookback=5):
    if df is None or len(df) < 30 or not {"High", "Low", "Close", "Volume"}.issubset(df.columns):
        return None
    c, v, h, l = df["Close"], df["Volume"], df["High"], df["Low"]
    if float(v.tail(20).mean() or 0) <= 0:
        return None

    # ---- volume-truth: effort vs result ----
    vol_ratio = float(v.tail(lookback).mean() / v.tail(20).mean())
    ret = float(c.iloc[-1] / c.iloc[-lookback - 1] - 1)
    atr = _atr(df)
    result_atr = abs(c.iloc[-1] - c.iloc[-lookback - 1]) / (atr * np.sqrt(lookback)) if atr else 0.0
    direction = "up" if ret >= 0 else "down"
    high_eff, low_eff = vol_ratio > 1.4, vol_ratio < 0.7
    big_res, small_res = result_atr > 1.0, result_atr < 0.5
    if high_eff and small_res:
        effort_result = "absorption"
    elif high_eff and big_res:
        effort_result = "conviction"
    elif low_eff and big_res:
        effort_result = "no-supply/no-demand"
    elif low_eff and small_res:
        effort_result = "quiet"
    else:
        effort_result = "neutral"
    if direction == "down":
        vol_verdict = ("distribution — selling on heavy volume" if high_eff else
                       "no buyers — light-volume drift, not aggressive selling (possible exhaustion)" if low_eff else
                       "orderly decline")
    else:
        vol_verdict = ("real demand — buying on heavy volume" if high_eff else
                       "weak rally — light volume, suspect" if low_eff else
                       "orderly advance")

    # ---- move-character: velocity / range / position / emotion ----
    vol_d = float(c.pct_change().dropna().tail(60).std()) * np.sqrt(lookback)
    velocity = max(-5.0, min(5.0, ret / vol_d)) if vol_d else 0.0            # signed sigma of the move
    atr_s, atr_l = _atr(df, 5), _atr(df, 20)
    range_exp = (atr_s / atr_l) if (atr_s and atr_l) else 1.0
    hi, lo = float(h.tail(20).max()), float(l.tail(20).min())
    pos = (float(c.iloc[-1]) - lo) / (hi - lo) if hi > lo else 0.5
    emotion = int(round(100 * (0.4 * min(abs(velocity), 3) / 3 + 0.35 * min(vol_ratio, 3) / 3 + 0.25 * min(range_exp, 2) / 2)))
    fast, expand = abs(velocity) > 1.5, range_exp > 1.3
    if direction == "down" and fast and expand and pos < 0.25:
        character = "panic / capitulation"
    elif direction == "up" and fast and expand and pos > 0.75:
        character = "blow-off / euphoria"
    elif effort_result == "absorption":
        character = "absorption / churn — smart money active"
    elif (not fast) and range_exp < 0.9:
        character = "grind / base — low emotion"
    else:
        character = "trending — orderly"

    return {"direction": direction, "vol_ratio": round(vol_ratio, 2), "effort_result": effort_result,
            "vol_verdict": vol_verdict, "velocity": round(velocity, 2), "range_exp": round(range_exp, 2),
            "pos_in_range": round(pos, 2), "emotion": emotion, "character": character,
            "summary": f"{vol_verdict}; {character} (emotion {emotion}/100, {velocity:+.1f}\u03c3)"}


def market_character(allpx, leader="SPY"):
    df = allpx.get(leader)
    return read(df) if df is not None else None
