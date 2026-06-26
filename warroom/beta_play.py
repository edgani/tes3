"""warroom/beta_play.py — tiered, cross-asset beta-play finder with a live viability filter.

When a theme leader is extended (Micron/Samsung/SK for memory, Nvidia for AI, gold, oil, copper, BTC),
the move rotates to second-order names. This organizes candidates into TIERS by role — most-direct,
bottleneck/second-order, picks-and-shovels/defensive — like a hand analysis, but every name is then
VALIDATED live and data-driven, so you see whether it's genuinely a viable entry NOW (not just a name
on a list):

  REAL EXPOSURE  — beta to the leader controlling for the broad market (SPY) + R². Low R² -> not real.
  ROOM TO RUN    — lagged the leader's run (catch-up left) vs already caught up / extended.
  TRADEABLE      — enough liquidity to size.

Covers every asset class: semis/memory, precious metals & miners, energy, copper, uranium, crypto.
Curated tier maps are the structural seed (verify fundamentals); the statistical filter is the honest
live layer. The generic find_beta_plays() works for ANY leader (a .JK name, an FX pair, a token).
"""
from __future__ import annotations
import numpy as np
import pandas as pd

# theme -> {leader, tiers: {tier_label: [(ticker, role)]}}  (roles are curated; verify fundamentals)
THEME_MAP = {
    "Memory / HBM (MU · Samsung · SK)": {"leader": "MU", "tiers": {
        "Tier 1 — most direct, still reasonable": [
            ("LRCX", "memory equipment pure-play"),
            ("AMAT", "diversified but memory strength; MU agreements = visibility"),
            ("ENTG", "materials play, less cyclical than equipment")],
        "Tier 2 — packaging bottleneck": [
            ("AMKR", "advanced packaging, less hyped than TSM"),
            ("TSM", "already expensive — only if you believe AI infra 5-10yr")],
        "Tier 3 — picks & shovels (defensive)": [
            ("KLAC", "yield = critical; recurring revenue > equipment sales"),
            ("MKSI", "under-the-radar vacuum / subsystems"),
            ("ACLS", "ion implant — narrower, leveraged to memory capex")]}},
    "AI compute (NVDA · AVGO)": {"leader": "NVDA", "tiers": {
        "Tier 1 — most direct": [("AVGO", "custom ASIC + networking"), ("MRVL", "custom silicon / optics"), ("AMD", "GPU #2")],
        "Tier 2 — interconnect / packaging": [("ALAB", "PCIe/CXL retimers"), ("CRDO", "active electrical cables")],
        "Tier 3 — picks & shovels": [("VRT", "thermal/power infra"), ("MPWR", "power management")]}},
    "Power / electrification (VST · CEG)": {"leader": "VST", "tiers": {
        "Tier 1 — most direct": [("CEG", "nuclear IPP"), ("GEV", "grid + gas turbines")],
        "Tier 2 — equipment": [("ETN", "electrical equipment"), ("POWL", "switchgear")],
        "Tier 3 — defensive": [("NEE", "regulated + renewables")]}},
    "Uranium / nuclear (CCJ)": {"leader": "CCJ", "tiers": {
        "Tier 1 — most direct": [("UEC", "US uranium"), ("URA", "sector ETF")],
        "Tier 2 — developers (leverage)": [("DNN", "Denison"), ("NXE", "NexGen")],
        "Tier 3 — reactors (long-dated)": [("OKLO", "SMR developer"), ("SMR", "NuScale")]}},
    "Gold / precious (GLD)": {"leader": "GLD", "tiers": {
        "Tier 1 — direct": [("SLV", "silver — higher beta to the metal"), ("GDX", "senior gold miners")],
        "Tier 2 — operating leverage": [("GDXJ", "junior miners — leveraged"), ("SIL", "silver miners"), ("AEM", "Agnico")],
        "Tier 3 — defensive / royalty": [("FNV", "royalty — lower risk"), ("WPM", "streaming"), ("NEM", "largest producer")]}},
    "Oil / energy (USO)": {"leader": "USO", "tiers": {
        "Tier 1 — direct": [("XLE", "integrated majors"), ("XOP", "E&P — higher beta")],
        "Tier 2 — services (leverage)": [("OIH", "oil services ETF"), ("SLB", "largest service co"), ("HAL", "Halliburton")],
        "Tier 3 — income / defensive": [("AMLP", "midstream MLP — income, less price beta")]}},
    "Copper / electrification (CPER)": {"leader": "CPER", "tiers": {
        "Tier 1 — direct": [("FCX", "Freeport — copper bellwether"), ("COPX", "copper miners ETF")],
        "Tier 2 — leverage": [("SCCO", "Southern Copper")]}},
    "Bitcoin ecosystem (BTC)": {"leader": "BTC-USD", "tiers": {
        "Tier 1 — direct proxy": [("IBIT", "spot ETF"), ("MSTR", "levered BTC treasury")],
        "Tier 2 — miners (operating leverage)": [("MARA", "miner"), ("RIOT", "miner"), ("CLSK", "miner")],
        "Tier 3 — infrastructure": [("COIN", "exchange")]}},
    "Indonesia banks (BBCA.JK)": {"leader": "BBCA.JK", "tiers": {
        "Tier 1 — big-cap peers": [("BMRI.JK", "Bank Mandiri"), ("BBRI.JK", "BRI — retail/micro")],
        "Tier 2 — higher beta": [("BBNI.JK", "BNI — more cyclical")]}},
    "Indonesia coal / energy (ADRO.JK)": {"leader": "ADRO.JK", "tiers": {
        "Tier 1 — coal peers": [("BUMI.JK", "Bumi Resources — high beta"), ("HUMI.JK", "Humpuss")]}},
    "Indonesia metals / EV (ANTM.JK)": {"leader": "ANTM.JK", "tiers": {
        "Tier 1 — metals peers": [("MDKA.JK", "Merdeka — copper/gold"), ("AMMN.JK", "Amman — copper/gold")]}},
}


def _beta_to_leader(cand, lead, bench, n=120):
    d = pd.concat([cand.rename("c"), lead.rename("l"), bench.rename("b")], axis=1).dropna().tail(n)
    if len(d) < 40:
        return None
    Y = d["c"].values
    X = np.column_stack([np.ones(len(d)), d["l"].values, d["b"].values])
    try:
        beta, *_ = np.linalg.lstsq(X, Y, rcond=None)
    except Exception:
        return None
    resid = Y - X @ beta
    ss_res, ss_tot = float((resid ** 2).sum()), float(((Y - Y.mean()) ** 2).sum())
    return float(beta[1]), (1 - ss_res / ss_tot if ss_tot > 0 else 0.0)


def _viability(tkr, df, leader, lr, br, lead_run, n=120, run_window=60):
    if df is None or len(df) < n:
        return {"verdict": "NO DATA", "why": "not loaded — add to universe to validate"}
    res = _beta_to_leader(df["Close"].pct_change(), lr, br, n)
    if res is None:
        return {"verdict": "NO DATA", "why": "insufficient history"}
    b_lead, r2 = res
    cand_run = float(df["Close"].iloc[-1] / df["Close"].iloc[-run_window] - 1)
    lag = lead_run - cand_run
    adv = float((df["Volume"] * df["Close"]).tail(20).mean()) if "Volume" in df else 0.0
    liquid = adv > (2e9 if str(tkr).endswith(".JK") else 3e6)
    room = lag > 0.02
    real = b_lead > 0.4 and r2 > 0.2
    if not real:
        verdict, why = "REJECT", f"\u03b2 {b_lead:.2f} / R\u00b2 {r2:.2f} — weak link to the theme right now (not a real co-mover)"
    elif not room and lag < -0.05:
        verdict, why = "REJECT", f"\u03b2 {b_lead:.2f} but already outran {leader} by {-lag*100:.0f}% — caught up / extended"
    elif room and liquid:
        verdict, why = "QUALIFIES", f"\u03b2 {b_lead:.2f} (R\u00b2 {r2:.2f}), lagged {lag*100:.0f}% (room), liquid"
    elif room and not liquid:
        verdict, why = "MARGINAL", f"\u03b2 {b_lead:.2f}, lagged {lag*100:.0f}% but thin (ADV ${adv/1e6:.1f}M)"
    else:
        verdict, why = "MARGINAL", f"\u03b2 {b_lead:.2f} (R\u00b2 {r2:.2f}), little room (lag {lag*100:+.0f}%)"
    return {"verdict": verdict, "why": why, "beta": round(b_lead, 2), "r2": round(r2, 2), "lag_pct": round(lag * 100, 1)}


def analyze_themes(allpx, bench="SPY"):
    bd = allpx.get(bench)
    if bd is None:
        return {}
    br = bd["Close"].pct_change()
    out = {}
    for theme, spec in THEME_MAP.items():
        leader = spec["leader"]
        lead = allpx.get(leader)
        if lead is None or len(lead) < 120:
            continue
        lr = lead["Close"].pct_change()
        lead_run = float(lead["Close"].iloc[-1] / lead["Close"].iloc[-60] - 1)
        tiers = {}
        for tlabel, members in spec["tiers"].items():
            rows = []
            for tkr, role in members:
                if tkr == leader:
                    continue
                v = _viability(tkr, allpx.get(tkr), leader, lr, br, lead_run)
                rows.append({"ticker": tkr, "role": role, **v})
            if rows:
                tiers[tlabel] = rows
        if tiers:
            out[theme] = {"leader": leader, "leader_run_pct": round(lead_run * 100, 1), "tiers": tiers}
    return out


def find_beta_plays(leader, allpx, bench="SPY", n=120, run_window=60):
    """Generic statistical scan for ANY leader (a .JK name, FX pair, token) — co-movers with room."""
    lead, bd = allpx.get(leader), allpx.get(bench)
    if lead is None or bd is None or len(lead) < n:
        return None
    lr, br = lead["Close"].pct_change(), bd["Close"].pct_change()
    lead_run = float(lead["Close"].iloc[-1] / lead["Close"].iloc[-run_window] - 1)
    out = []
    for tkr, df in allpx.items():
        if tkr in (leader, bench) or str(tkr).startswith("^") or df is None or len(df) < n:
            continue
        v = _viability(tkr, df, leader, lr, br, lead_run, n, run_window)
        if v["verdict"] in ("QUALIFIES", "MARGINAL"):
            out.append({"ticker": tkr, **v})
    out.sort(key=lambda x: -(x.get("beta", 0) * (1 + max(x.get("lag_pct", 0) / 100, 0))))
    return {"leader": leader, "leader_run_pct": round(lead_run * 100, 1), "candidates": out[:10]}
