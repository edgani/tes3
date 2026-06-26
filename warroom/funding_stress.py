"""funding_stress.py - Funding / Liquidity Stress Engine (FRED). Per Edward's framing:
EFFR is the real-time heartbeat of dollar liquidity, but RELATIVE/DEVIATION carries the edge,
never standalone. Composite 0-100 stress score feeds Liquidity Regime + crash/bottom flags.

Live: pulls FRED (no key needed via fredgraph CSV). Sandbox/offline: synthetic fallback (flagged).
Stress rules (encoded from the essay):
  EFFR > target upper            -> reserve/liquidity stress
  EFFR - SOFR widening           -> funding distortion
  EFFR rising fast               -> reserve tightness
  reserves down  + RRP down      -> real liquidity tightening
"""
from __future__ import annotations
import io, urllib.request
import numpy as np, pandas as pd

_IDS = {"effr": "EFFR", "upper": "DFEDTARU", "sofr": "SOFR",
        "rrp": "RRPONTSYD", "reserves": "WRESBAL", "tga": "WTREGEN"}

def _fred(series_id, days=400):
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            df = pd.read_csv(io.BytesIO(r.read()))
        df.columns = ["date", "val"]
        df["val"] = pd.to_numeric(df["val"], errors="coerce")
        return df.set_index("date")["val"].dropna().tail(days)
    except Exception:
        return None

def _synth():
    idx = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=120)
    m = len(idx)
    eff = pd.Series(4.33 + np.cumsum(np.random.default_rng(1).normal(0, 0.004, m)), index=idx)
    return {"effr": eff, "upper": pd.Series(4.50, index=idx), "sofr": eff - 0.02,
            "rrp": pd.Series(np.linspace(400, 180, m), index=idx),
            "reserves": pd.Series(np.linspace(3.3e6, 3.0e6, m), index=idx),
            "tga": pd.Series(np.linspace(700, 820, m), index=idx)}

def _last(s): return float(s.iloc[-1]) if s is not None and len(s) else np.nan
def _ago(s, n): return float(s.iloc[-1 - n]) if s is not None and len(s) > n else np.nan
def _trend(s, n=20):  # >0 rising, <0 falling (normalized)
    if s is None or len(s) <= n: return 0.0
    return float((s.iloc[-1] - s.tail(n).mean()) / (abs(s.tail(n).mean()) + 1e-9))

def assess(days=300):
    data = {k: _fred(v, days) for k, v in _IDS.items()}
    live = all(data[k] is not None and len(data[k]) for k in ("effr", "upper", "sofr"))
    src = "FRED · live"
    if not live:
        data = _synth(); src = "synthetic · demo (set FRED access for live)"
    effr, upper, sofr = _last(data["effr"]), _last(data["upper"]), _last(data["sofr"])
    dev = effr - upper                                   # >0 = above ceiling = stress
    spread = effr - sofr                                 # funding distortion
    roc = effr - _ago(data["effr"], 5)                   # rate of change
    res_tr, rrp_tr = _trend(data.get("reserves")), _trend(data.get("rrp"))
    # composite (HEURISTIC PRIOR — validate OOS on real FRED). Normal EFFR sits ~10-20bps below
    # ceiling = neutral; stress builds as EFFR nears/exceeds ceiling, SOFR distorts, or EFFR jumps.
    score = 50.0
    score += max(0.0, dev + 0.05) * 500      # acute: within 5bps of / above ceiling
    score += max(0.0, spread - 0.01) * 400   # acute: EFFR-SOFR distortion beyond 1bp
    score += max(0.0, roc) * 250             # reserve tightness: EFFR rising fast
    score += 5 if (res_tr < 0 and rrp_tr < 0) else 0   # slow tightening: both draining
    score -= max(0.0, -(dev + 0.25)) * 80    # deep below ceiling = mild easing
    score = int(np.clip(score, 0, 100))
    label = "stress" if score >= 65 else "easing" if score <= 35 else "neutral"
    sig = []
    if dev > 0.0: sig.append("EFFR above target ceiling")
    if spread > 0.03: sig.append("EFFR–SOFR distortion")
    if roc > 0.03: sig.append("EFFR rising fast")
    if res_tr < 0 and rrp_tr < 0: sig.append("reserves + RRP draining")
    if not sig: sig.append("funding orderly")
    return {"source": src, "score": score, "label": label,
            "effr": round(effr, 3), "dev_bps": round(dev * 100, 1),
            "spread_bps": round(spread * 100, 1), "signals": sig,
            "crash_nudge": score >= 70, "bottom_block": score >= 55}
