"""analyze_track.py — interrogate the forward-test track record for a REAL edge (not data-mining).

Run after you've accumulated closed trades (aim 30-50+):
    python analyze_track.py

It answers the questions an allocator asks:
  • Is mean return significantly > 0 (t-test + bootstrap CI), or is it noise?
  • Does the edge SURVIVE higher transaction costs (5/10/20/30 bps)?
  • Does the walk-forward GATE actually work — do PASS signals beat FAIL?
  • Does the edge hold per market / per direction / per regime (quad), or live in one lucky bucket?
  • Does higher conviction score → better outcome (monotonic), or is the score meaningless?

Verdict-first. Honest about sample size and multiple-testing.
"""
from __future__ import annotations
import os, sys, math
import pandas as pd, numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from warroom import tracker as TR

try:
    from scipy import stats as _ss
except Exception:
    _ss = None


def _recost(closed, entry, exit_, direction, stop, bps):
    sign = np.where(direction == "Long", 1.0, -1.0)
    ret = sign * (exit_ - entry) / entry - bps / 1e4
    risk = (np.abs(entry - stop) / entry).replace(0, np.nan)
    return ret, ret / risk


def _stats(rets):
    rets = pd.Series(rets).astype(float).dropna()
    n = len(rets)
    if n == 0:
        return {}
    wins, losses = rets[rets > 0], rets[rets <= 0]
    eq = (1 + rets).cumprod()
    dd = (eq / eq.cummax() - 1).min()
    d = {"n": n, "win_rate": 100 * len(wins) / n, "avg_ret": 100 * rets.mean(),
         "expectancy_pct": 100 * rets.mean(), "total_ret": 100 * (eq.iloc[-1] - 1),
         "profit_factor": (wins.sum() / abs(losses.sum())) if losses.sum() != 0 else float("inf"),
         "sharpe_pertrade": (rets.mean() / rets.std() * math.sqrt(n)) if rets.std() else 0.0,
         "max_dd": 100 * dd}
    if _ss is not None and n >= 3 and rets.std() > 0:
        t, p = _ss.ttest_1samp(rets, 0.0)
        d["t_stat"], d["p_value"] = t, p
    # bootstrap 90% CI on mean return
    if n >= 5:
        rng = np.random.default_rng(7)
        boot = [rng.choice(rets, n, replace=True).mean() for _ in range(2000)]
        d["ci90_low"], d["ci90_high"] = 100 * np.percentile(boot, 5), 100 * np.percentile(boot, 95)
    return d


def _line(label, d):
    if not d:
        return f"  {label:24} (no data)"
    extra = ""
    if "p_value" in d:
        extra = f" · t={d['t_stat']:+.2f} p={d['p_value']:.3f}"
    if "ci90_low" in d:
        extra += f" · CI90[{d['ci90_low']:+.2f}%,{d['ci90_high']:+.2f}%]"
    pf = "inf" if d["profit_factor"] == float("inf") else f"{d['profit_factor']:.2f}"
    return (f"  {label:24} n={d['n']:<4} win={d['win_rate']:.0f}% exp={d['expectancy_pct']:+.2f}% "
            f"PF={pf} tot={d['total_ret']:+.1f}% Shp={d['sharpe_pertrade']:+.2f} DD={d['max_dd']:.1f}%{extra}")


def analyze(path=None):
    path = path or TR.DB
    if not os.path.exists(path):
        print(f"No track-record DB at {path}. Run the dashboard first to log signals."); return
    df = TR._df(path)
    closed = df[df["status"].isin(["WIN", "LOSS"])].copy()
    print("=" * 78)
    print(f"TRACK-RECORD ANALYSIS  ·  {path}")
    print("=" * 78)
    print(f"Logged: {len(df)} total · {int((df['status']=='OPEN').sum())} open · {len(closed)} closed")
    if len(closed) < 10:
        print("\nVERDICT: INSUFFICIENT DATA. Need ~30-50+ closed trades before any edge claim is meaningful.")
        print("Keep running the dashboard daily; outcomes accrue as bars print.")
        return

    for col in ("entry_px", "exit_px", "stop", "ret_pct", "r_multiple", "score"):
        closed[col] = pd.to_numeric(closed[col], errors="coerce")

    base = _stats(closed["ret_pct"])
    print("\n— OVERALL (net of logged 10bps) —")
    print(_line("all closed", base))

    # 1) cost sensitivity — does the edge survive friction?
    print("\n— COST SENSITIVITY (does edge survive friction?) —")
    for bps in (5, 10, 20, 30):
        ret, _ = _recost(closed, closed["entry_px"], closed["exit_px"], closed["direction"], closed["stop"], bps)
        s = _stats(ret)
        print(f"  {bps:>2}bps: exp={s.get('expectancy_pct',0):+.2f}%  PF={'inf' if s.get('profit_factor')==float('inf') else format(s.get('profit_factor',0),'.2f')}  tot={s.get('total_ret',0):+.1f}%")

    # 2) gate validation — PASS should beat FAIL, else the gate is theater
    print("\n— WALK-FORWARD GATE VALIDATION (PASS should beat FAIL) —")
    for g in ("PASS", "FAIL", None):
        sub = closed[closed["gate_status"] == g] if g else closed[closed["gate_status"].isna()]
        if len(sub):
            print(_line(f"gate={g or 'none'}", _stats(sub["ret_pct"])))

    # 3) per market / direction / regime — is the edge broad or one lucky bucket?
    dims = [("market", "MARKET"), ("direction", "DIRECTION"), ("regime_struct", "REGIME (quad)"), ("horizon", "TIME HORIZON")]
    for col, lbl in (("decision", "DECISION CALL"), ("anti_fomo", "ENTRY TIMING (anti-FOMO)")):
        if col in closed.columns and closed[col].notna().any():
            dims.append((col, lbl))
    for dim, lbl in dims:
        print(f"\n— BY {lbl} —")
        for k, sub in closed.groupby(dim):
            if len(sub) >= 3:
                print(_line(str(k), _stats(sub["ret_pct"])))

    # 4) conviction monotonicity — higher score should mean better outcome
    print("\n— BY CONVICTION SCORE (higher should be better) —")
    try:
        closed["bucket"] = pd.qcut(closed["score"], q=min(3, closed["score"].nunique()), duplicates="drop")
        for k, sub in closed.groupby("bucket"):
            if len(sub) >= 3:
                print(_line(f"score {k}", _stats(sub["ret_pct"])))
    except Exception:
        print("  (not enough score variation to bucket)")

    # VERDICT
    print("\n" + "=" * 78)
    sig = base.get("p_value", 1) < 0.05 and base.get("ci90_low", -1) > 0
    survives = True
    ret20, _ = _recost(closed, closed["entry_px"], closed["exit_px"], closed["direction"], closed["stop"], 20)
    survives = _stats(ret20).get("expectancy_pct", -1) > 0
    g_pass = closed[closed["gate_status"] == "PASS"]["ret_pct"]
    g_fail = closed[closed["gate_status"] == "FAIL"]["ret_pct"]
    gate_works = (len(g_pass) >= 5 and len(g_fail) >= 5 and g_pass.mean() > g_fail.mean())
    enough = len(closed) >= 30
    verdict = "REAL EDGE (provisional)" if (sig and survives and enough) else "NOT PROVEN YET"
    print(f"VERDICT: {verdict}")
    print(f"  • sample ≥30:           {'yes' if enough else f'NO ({len(closed)})'}")
    print(f"  • mean ret sig >0:      {'yes' if sig else 'no'} (need p<0.05 AND bootstrap CI90 low >0)")
    print(f"  • survives 20bps:       {'yes' if survives else 'no'}")
    print(f"  • gate PASS>FAIL:       {'yes' if gate_works else 'inconclusive (need ≥5 each)'}")
    print(f"  • buckets tested: market/direction/regime/score → mind multiple-testing; treat sub-splits as hypotheses, not proof.")
    print("=" * 78)


if __name__ == "__main__":
    analyze(sys.argv[1] if len(sys.argv) > 1 else None)
