"""warroom/compute.py — orchestrator. MY ranking/structure; zip engines = formula providers.
Every engine call is wrapped: a rewel engine degrades to a flagged note, never crashes the app.
"""
from __future__ import annotations
import os, json, numpy as np, pandas as pd

from warroom import data as D
from warroom.lpm import lpm_features, money_flow
from warroom import funding_stress as FS
from warroom import secular_map as SEC

_DATADIR = os.path.join(os.path.dirname(__file__), "..", "data")


def _try(fn, default=None):
    try:
        return fn()
    except Exception:
        return default


def _q(s):
    s = str(s or "").upper().replace("QUAD", "Q").strip()
    return {"Q1": "Quad 1", "Q2": "Quad 2", "Q3": "Quad 3", "Q4": "Quad 4"}.get(s, str(s) or "Quad ?")


def _ret(c, n):
    return float(c.iloc[-1] / c.iloc[-1 - n] - 1) if len(c) > n else 0.0


# ---------------- regime: real GIP (structural + monthly) via GIPEngine, proxy fallback ----------------
def _proxy_quad(us):
    def acc(tickers):
        v = [(_ret(us[t]["Close"], 63) - _ret(us[t]["Close"], 126)) for t in tickers if us.get(t) is not None and len(us[t]) > 131]
        return float(np.mean(v)) if v else 0.0
    g = acc(["SOXX", "COPX", "XLI", "IWM"]) - acc(["XLU", "XLP", "TLT"]); i = acc(["USO", "DBC", "GLD"])
    quad = ("Quad 1" if (g > 0 and i <= 0) else "Quad 2" if (g > 0 and i > 0) else "Quad 3" if (g <= 0 and i > 0) else "Quad 4")
    return {"structural": quad, "monthly": quad, "operating": quad, "divergence": "aligned",
            "g_struct": round(g * 100, 2), "i_struct": round(i * 100, 2),
            "g_month": round(g * 100, 2), "i_month": round(i * 100, 2), "flip": "", "source": "price-proxy"}


def _regime(us, fred):
    out = {"structural": "Quad ?", "monthly": "Quad ?", "operating": "", "divergence": "", "flip": "",
           "g_struct": 0, "i_struct": 0, "g_month": 0, "i_month": 0, "source": "price-proxy"}

    def run():
        from engines.gip_engine import GIPEngine
        closes = {t: us[t]["Close"] for t in us}   # _safe expects Series, not DataFrame
        return GIPEngine().run(fred or {}, closes)
    r = _try(run)
    if r is not None:
        proxy_share = float(getattr(r, "proxy_share", 1.0) or 1.0)
        out.update({"structural": _q(r.structural_quad), "monthly": _q(r.monthly_quad),
                    "operating": getattr(r, "operating_regime", "") or "",
                    "g_struct": round(float(getattr(r, "structural_g", 0)), 2),
                    "i_struct": round(float(getattr(r, "structural_i", 0)), 2),
                    "g_month": round(float(getattr(r, "monthly_g", 0)), 2),
                    "i_month": round(float(getattr(r, "monthly_i", 0)), 2),
                    "source": "FRED · live" if proxy_share < 0.5 else "price-proxy (no FRED)",
                    "flip": str(_try(lambda: r.flip_hazard(), "") or "")})
        out["divergence"] = "divergent" if out["structural"] != out["monthly"] else "aligned"
    else:
        out.update(_proxy_quad(us))
    above = tot = 0
    for t in D.US_NAMES:
        d = us.get(t)
        if d is not None and len(d) > 50:
            tot += 1; above += int(d["Close"].iloc[-1] > d["Close"].tail(50).mean())
    out["breadth"] = round(100 * above / tot) if tot else 0
    out["defensive"] = out["structural"] in ("Quad 3", "Quad 4") or out["breadth"] < 45
    out["posture"] = "Defensive" if out["defensive"] else "Risk-on"
    # quad explainer (why / flips / next)
    out["explain"] = str(_try(lambda: __import__("engines.quad_explainer", fromlist=["explain_quad"]).explain_quad(r, None, None), "") or "")
    return out


# ---------------- ranking (MINE) + real Hedgeye risk range ----------------
def _accum(df):
    adl = money_flow(df, "value_typical").cumsum(); d = adl.diff()
    base = float(d.abs().tail(60).mean()) + 1e-9
    return int(np.clip(float(d.tail(20).mean()) / base * 50, -100, 100))


def _rr(df, t):
    from gcfis.engines.risk_range_hedgeye import compute_risk_range
    return compute_risk_range(df, t)


def _rank(us, regime):
    spy = us.get("SPY")
    spym = (lambda n: _ret(spy["Close"], n)) if (spy is not None and len(spy) > 70) else (lambda n: 0.0)
    rows = []
    for t in D.US_NAMES:
        d = us.get(t)
        if d is None or len(d) < 80:
            continue
        c = d["Close"]
        mom63, rs63 = _ret(c, 63), _ret(c, 63) - spym(63)
        sma20, sma50 = float(c.tail(20).mean()), float(c.tail(50).mean())
        above50, trend = c.iloc[-1] / sma50 - 1, sma20 / sma50 - 1
        accel = _ret(c, 21) - _ret(c, 63)
        crowding = max(0.0, _ret(c, 20)); vol = float(c.pct_change().tail(20).std() * np.sqrt(252))
        form = "BULLISH" if (trend > 0 and above50 > 0) else "BEARISH" if (trend < 0 and above50 < 0) else "NEUTRAL"
        direction = "Long" if (form == "BULLISH" and rs63 > 0) else "Short" if (form == "BEARISH" and rs63 < 0) else "Watch"
        rr = _try(lambda: _rr(d, t))
        if rr and isinstance(rr, dict) and "trade" in rr:
            lrr, trr = rr["trade"]["lrr"], rr["trade"]["trr"]; vstate = rr.get("vol_state", "")
            tr_band = (rr.get("trend", {}).get("lrr"), rr.get("trend", {}).get("trr"))
        else:
            px = float(c.iloc[-1]); lrr, trr, vstate, tr_band = round(px * .97, 2), round(px * 1.03, 2), "", (None, None)
        strength = abs(rs63) * 2.2 + abs(mom63) + abs(above50) * 0.7
        strength += (0.15 if ((direction == "Short") == regime["defensive"]) else -0.05)
        strength -= crowding * 0.45
        if direction == "Watch":
            strength *= 0.6
        rows.append({"ticker": t, "_dir": direction, "score": round(max(strength, 0) * 10, 2),
                     "formation": form, "rs63": round(rs63 * 100, 1), "accel": round(accel * 100, 1),
                     "accumulation": _accum(d), "crowding": round(crowding * 100, 1), "vol": round(vol, 2),
                     "vol_state": vstate, "lrr": lrr, "trr": trr, "trend_band": tr_band, "close": round(float(c.iloc[-1]), 2)})
    rows.sort(key=lambda x: x["score"], reverse=True)
    return rows


def _methodology(us, quad):
    def run():
        from engines.thought_process_engine import analyze_multi, get_top_theses
        names = [t for t in D.US_NAMES if us.get(t) is not None]
        res = analyze_multi(names, prices={t: us[t]["Close"] for t in names}, quad=quad.replace("Quad ", "Q").replace(" ", ""), vix=20.0)
        th = get_top_theses(res, top_n=12)
        return {t["ticker"]: t.get("matched_frameworks", []) for t in th}
    return _try(run, {}) or {}


# ---------------- lenses ----------------
def _us_lens(us, gex_names):
    g = _try(lambda: __import__("engines.gex_engine", fromlist=["analyze_multi"]).analyze_multi(
        gex_names, {t: us[t] for t in gex_names if us.get(t) is not None}, 20.0), {}) or {}
    rows = []
    for t, gg in (g.items() if isinstance(g, dict) else []):
        if not isinstance(gg, dict):
            continue
        reg = gg.get("regime") or gg.get("gamma_regime") or gg.get("state") or "—"
        num = next((f"{k} {gg[k]:,.0f}" for k in ("net_gex", "gex", "total_gex", "zero_gamma", "gamma_flip") if isinstance(gg.get(k), (int, float))), "")
        rows.append({"ticker": t, "regime": reg, "metric": num})
    return rows


def _crypto_lens(cp):
    rows = []
    for t in cp:
        d = cp.get(t)
        if d is None or len(d) < 40:
            continue
        c = d["Close"]; trend = "up" if c.iloc[-1] > c.tail(30).mean() else "down"
        rows.append({"ticker": t, "ret30": round(_ret(c, 30) * 100, 1), "trend": trend})
    return rows


def _commo_lens(commo, us):
    out = {}
    dxy = us.get("UUP")
    gld = commo.get("GLD")
    if gld is None:
        gld = us.get("GLD")
    out["gold"] = _try(lambda: __import__("engines.fx_commodity_driver_engine", fromlist=["gold_bias"]).gold_bias(
        ("up" if dxy is not None and dxy["Close"].iloc[-1] > dxy["Close"].tail(20).mean() else "down"),
        0.0, _ret(gld["Close"], 30) if gld is not None else 0.0, False), None)
    rows = []
    for t in commo:
        d = commo.get(t)
        if d is None or len(d) < 40:
            continue
        c = d["Close"]
        rows.append({"ticker": t, "ret30": round(_ret(c, 30) * 100, 1),
                     "trend": "up" if c.iloc[-1] > c.tail(30).mean() else "down"})
    return {"rows": rows, "gold_bias": out.get("gold")}


def _fx_lens(fx):
    rows = []
    for t in fx:
        d = fx.get(t)
        if d is None or len(d) < 40:
            continue
        c = d["Close"]
        rows.append({"ticker": t.replace("=X", "").replace("DX-Y.NYB", "DXY"),
                     "ret30": round(_ret(c, 30) * 100, 1),
                     "trend": "up" if c.iloc[-1] > c.tail(30).mean() else "down"})
    return rows


def _idx_flow(idx):
    rows = []
    congs = _try(lambda: json.load(open(os.path.join(_DATADIR, "ihsg_conglomerates.json"))), {})
    for t, df in (idx or {}).items():
        try:
            lf = lpm_features(df, scaling="value_typical", span=20)
            adl = money_flow(df, "value_typical").cumsum()
            rising = bool(adl.iloc[-1] > adl.iloc[-min(21, len(adl))])
            rows.append({"ticker": t, "state": lf.get("state"), "lpm": lf.get("lpm"), "adl_rising": rising})
        except Exception:
            continue
    return rows


def _flow_rotation(us):
    buckets = {"Semis": "SMH", "Growth": "ARKK", "Energy": "XLE", "Utilities": "XLU",
               "Staples": "XLP", "Gold": "GLD", "Bonds": "TLT", "Credit": "HYG"}
    rows = []
    for name, tk in buckets.items():
        d = us.get(tk)
        if d is None or len(d) < 25:
            continue
        rows.append({"name": name, "ticker": tk, "flow": round(_ret(d["Close"], 21) * 100, 1)})
    rows.sort(key=lambda x: x["flow"], reverse=True)
    return rows


def _funding(fred):
    f = FS.assess()
    f["treasury"] = _try(lambda: __import__("engines.treasury_liquidity", fromlist=["analyze_liquidity"]).analyze_liquidity(fred or {}), None)
    return f


def _bottleneck(us):
    closes = {t: us[t]["Close"] for t in us if us.get(t) is not None}
    leadlag = _try(lambda: __import__("gcfis.engines.leadlag_discovery", fromlist=["run_leadlag_discovery"]).run_leadlag_discovery(closes), None)
    graph = _try(lambda: __import__("engines.supply_chain_graph_real", fromlist=["run_supply_chain_analysis"]).run_supply_chain_analysis(closes, None), None)
    ref = _try(lambda: json.load(open(os.path.join(_DATADIR, "bottleneck_reference.json"))), {}) or {}
    edges = []
    if isinstance(leadlag, dict):
        for e in (leadlag.get("edges") or leadlag.get("lead_lag") or [])[:6]:
            if isinstance(e, dict):
                edges.append({"leader": e.get("leader"), "follower": e.get("follower"),
                              "lag": e.get("lag"), "conf": e.get("confidence")})
    return {"map": SEC.map(), "leadlag": edges, "graph": graph,
            "ref_themes": list(ref.get("consensus_heatmap", {}).keys())[:6] if isinstance(ref.get("consensus_heatmap"), dict) else [],
            "photonics": ref.get("photonics_12_layer", []) if isinstance(ref.get("photonics_12_layer"), list) else []}


# ---------------- top-level ----------------
def run(us, idx, crypto, fx, commo, fred=None):
    reg = _regime(us, fred)
    rows = _rank(us, reg)
    quad = reg["structural"]
    out = {
        "regime": reg, "rows": rows,
        "scanned": len(D.US_NAMES), "conviction": rows[:4], "watchlist": rows[4:12],
        "methodology": _methodology(us, quad),
        "us_lens": _us_lens(us, [t for t in ["NVDA", "SMH", "ANET", "VRT", "AAPL", "MSFT"] if us.get(t) is not None]),
        "crypto": _crypto_lens(crypto), "commo": _commo_lens(commo, us), "fx": _fx_lens(fx),
        "idx": _idx_flow(idx), "flow": _flow_rotation(us), "funding": _funding(fred),
        "bottleneck": _bottleneck(us),
    }
    bull = sum(1 for r in rows if r["formation"] == "BULLISH")
    bear = sum(1 for r in rows if r["formation"] == "BEARISH"); n = len(rows) or 1
    out["market"] = {"bull": bull, "bear": bear, "breadth": reg["breadth"], "pct_bull": round(100 * bull / n)}
    out["leaders"] = sorted(rows, key=lambda r: r["rs63"], reverse=True)[:8]
    # extra engine wirings (defensive)
    vix = _vix(us)
    out["vix"] = round(vix, 1)
    out["hmm"] = _hmm(us, reg["breadth"], vix)
    out["forward"] = _forward_macro(us)
    out["crash"] = _crash(us, vix)
    out["discovery"] = _discovery(us, vix)
    dmax = max([r["score"] for r in out["conviction"]] or [1]) or 1
    for r in out["conviction"]:
        r["size"] = _sizing(10 * r["score"] / dmax, reg["structural"], vix)
    # funding nudge
    if out["funding"].get("crash_nudge"):
        reg["posture"], reg["defensive"] = "Defensive", True
    return out


# ============================================================ EXTRA ENGINE WIRINGS (defensive)
def _vix(us):
    v = float(_try(lambda: float(us["^VIX"]["Close"].iloc[-1]), 20.0) or 20.0)
    return v if 5.0 <= v <= 60.0 else 20.0   # guard against synthetic/bogus VIX


def _hmm(us, breadth, vix):
    def run():
        from gcfis.engines.regime_hmm import run_regime_hmm
        spy = us.get("SPY")
        ir = spy["Close"].pct_change().dropna()
        r = run_regime_hmm(ir, 4, breadth / 100.0, None, vix, 7, None)
        if isinstance(r, dict):
            return r.get("state") or r.get("label") or r.get("regime")
        return getattr(r, "state", None) or getattr(r, "label", None)
    return _try(run)


def _forward_macro(us):
    def run():
        from gcfis.engines.forward_macro import run_forward_macro
        def r(t, n): 
            d = us.get(t); return float(d["Close"].iloc[-1] / d["Close"].iloc[-1 - n] - 1) if d is not None and len(d) > n else 0.0
        gi = {"copper_gold": r("COPX", 63) - r("GLD", 63), "smallcap": r("IWM", 63), "cyclicals": r("XLI", 63), "hy": r("HYG", 63)}
        ii = {"oil": r("USO", 63), "commodities": r("DBC", 63), "breakevens": r("DBC", 21), "dollar": -r("UUP", 63)}
        return run_forward_macro(gi, ii)
    return _try(run)


def _crash(us, vix):
    def run():
        from gcfis.engines.internals import run_internals
        from gcfis.engines.shock import run_shock
        from gcfis.engines.crash_bottom import run_crash_bottom
        closes = {t: us[t]["Close"] for t in us if us.get(t) is not None}
        spy = us.get("SPY"); ir = spy["Close"].pct_change().dropna()
        internals = run_internals(closes, "SPY")
        shock = run_shock({"vix": vix}, ir, 0.94)
        systemic = {"shock": shock, "vix": vix}
        return run_crash_bottom(systemic, internals, {})
    return _try(run)


def _sizing(score_disp, quad, vix):
    """conviction (0-10 disp) -> position size bps, scaled by Hedgeye VIX bucket."""
    base = float(min(100.0, max(15.0, score_disp * 12.0)))
    out = {"base_bps": round(base), "vix_bucket": None, "sized_bps": round(base)}
    def run():
        from engines.vix_bucket_engine import classify_vix_bucket, apply_vix_position_sizing
        b = classify_vix_bucket(vix); out["vix_bucket"] = b if isinstance(b, str) else str(b)
        s = apply_vix_position_sizing(b, base)
        out["sized_bps"] = round(float(s)) if isinstance(s, (int, float)) else round(base)
    _try(run)
    return out


def _discovery(us, vix):
    closes = {t: us[t]["Close"] for t in us if us.get(t) is not None}
    sq = _try(lambda: __import__("engines.squeeze_scanner", fromlist=["scan_squeezes"]).scan_squeezes(list(closes), closes, None))
    bd = _try(lambda: __import__("engines.bottleneck_discovery_v3", fromlist=["run_bottleneck_discovery_v3"]).run_bottleneck_discovery_v3(closes, None, None))
    am = _try(lambda: __import__("gcfis.engines.asymmetric_discovery", fromlist=["run_discovery"]).run_discovery(extra_tickers=list(closes), top=10))
    sq_rows = []
    if isinstance(sq, dict):
        for t, v in list(sq.items())[:6]:
            sq_rows.append({"ticker": t, "score": (v.get("squeeze_score") if isinstance(v, dict) else v)})
    elif isinstance(sq, list):
        sq_rows = [{"ticker": x.get("ticker"), "score": x.get("score")} for x in sq[:6] if isinstance(x, dict)]
    return {"squeeze": sq_rows, "bottleneck": bd, "asymmetric": am}
