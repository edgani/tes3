"""warroom/walkforward.py — signal validation harness (no look-ahead).

A TOOL, not a claim. Feed it any signal (rate-path bias, inflation trend, driver residual, a setup
score) plus the asset's price history, and it tests whether the signal at time t predicts the forward
return t -> t+h. It enforces no look-ahead (signal at t aligned only with the return that follows),
reports the information coefficient (Spearman), hit rate, long-short forward spread, the IC t-stat,
out-of-sample stability across folds, and a trial-count-aware (deflated) significance note so you
don't fool yourself after testing many signals. Synthetic data only proves it runs — real verdicts
need your real history.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

try:
    from scipy import stats
    _HAVE_SCIPY = True
except Exception:
    _HAVE_SCIPY = False


def _spearman(a, b):
    if _HAVE_SCIPY:
        ic, p = stats.spearmanr(a, b)
        return float(ic), float(p)
    ar = pd.Series(a).rank().values
    br = pd.Series(b).rank().values
    ic = float(np.corrcoef(ar, br)[0, 1])
    n = len(a)
    t = ic * np.sqrt(max(n - 2, 1)) / np.sqrt(max(1 - ic ** 2, 1e-9))
    # 2-sided normal approx p
    p = float(2 * (1 - 0.5 * (1 + np.math.erf(abs(t) / np.sqrt(2)))))
    return ic, p


def forward_returns(prices, horizon=5):
    return prices.shift(-horizon) / prices - 1


def _r(x):
    return round(float(x) * 100, 2) if x is not None and pd.notna(x) else None


def evaluate(signal, prices, horizon=5, min_obs=60):
    """Overall predictive stats of `signal` for forward `horizon`-day returns of `prices`."""
    fwd = forward_returns(prices, horizon)
    d = pd.concat([pd.Series(signal).rename("sig"), fwd.rename("fwd")], axis=1).dropna()
    if len(d) < min_obs:
        return {"error": "insufficient overlap", "n": int(len(d))}
    ic, p = _spearman(d["sig"].values, d["fwd"].values)
    n = len(d)
    t_ic = ic * np.sqrt(max(n - 2, 1)) / np.sqrt(max(1 - ic ** 2, 1e-9))
    hit = float(((d["sig"] > 0) == (d["fwd"] > 0)).mean())
    lr = d.loc[d["sig"] > 0, "fwd"].mean()
    sr = d.loc[d["sig"] < 0, "fwd"].mean()
    spread = (lr - sr) if (pd.notna(lr) and pd.notna(sr)) else None
    return {"n": n, "horizon": horizon, "ic": round(ic, 3), "ic_p": round(p, 4),
            "t_stat": round(float(t_ic), 2), "hit_rate": round(hit, 3),
            "long_fwd_pct": _r(lr), "short_fwd_pct": _r(sr), "spread_pct": _r(spread)}


def walk_forward(signal, prices, horizon=5, n_folds=5):
    """Out-of-sample stability: IC computed per chronological fold (no look-ahead)."""
    fwd = forward_returns(prices, horizon)
    d = pd.concat([pd.Series(signal).rename("sig"), fwd.rename("fwd")], axis=1).dropna()
    if len(d) < n_folds * 30:
        return {"error": "insufficient data for folds", "n": int(len(d))}
    folds = np.array_split(np.arange(len(d)), n_folds)
    ics = []
    for f in folds:
        sub = d.iloc[f]
        if len(sub) < 15:
            continue
        ic, _ = _spearman(sub["sig"].values, sub["fwd"].values)
        ics.append(round(float(ic), 3))
    pos = sum(1 for x in ics if x > 0)
    return {"fold_ics": ics, "mean_ic": round(float(np.mean(ics)), 3) if ics else None,
            "ic_sign_consistency": f"{pos}/{len(ics)} folds positive", "n_folds": len(ics)}


def deflated_note(ic, n, n_trials=1):
    """Trial-count-aware significance: shrink the IC t-stat threshold for multiple testing."""
    if n < 3:
        return "n too small"
    t = ic * np.sqrt(n - 2) / np.sqrt(max(1 - ic ** 2, 1e-9))
    # Bonferroni-style critical t for n_trials tested signals (approx, 2-sided ~5%)
    crit = 1.96 + 0.5 * np.log(max(n_trials, 1))
    verdict = "SURVIVES" if abs(t) >= crit else "does NOT survive"
    return f"IC t-stat {t:.2f} vs deflated crit {crit:.2f} ({n_trials} trials) — {verdict} multiple-testing"


def report(signal, prices, horizon=5, n_trials=1):
    """One-shot text report combining the above. Print this when validating on real data."""
    ev = evaluate(signal, prices, horizon)
    if ev.get("error"):
        return ev
    wf = walk_forward(signal, prices, horizon)
    ev["walk_forward"] = wf
    ev["deflated"] = deflated_note(ev["ic"], ev["n"], n_trials)
    ev["verdict"] = ("PREDICTIVE" if (ev["ic_p"] < 0.05 and ev["t_stat"] >= 2 and
                                      isinstance(wf.get("mean_ic"), float) and np.sign(wf["mean_ic"]) == np.sign(ev["ic"]))
                     else "NOT PROVEN — IC weak or unstable OOS")
    return ev
