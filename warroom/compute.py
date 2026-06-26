"""warroom/compute.py — orchestrator. MY ranking/structure; zip engines = formula providers.
Every engine call is wrapped: a rewel engine degrades to a flagged note, never crashes the app.
"""
from __future__ import annotations
import os, json, numpy as np, pandas as pd

from warroom import data as D
from warroom.lpm import lpm_features, money_flow
from warroom import funding_stress as FS
from warroom import intervention as INT
from warroom import timing as TIM
from warroom import risk as RISK
from warroom import mechanical as MECH
from warroom import synthesis as SYN
from warroom import crowd as CROWD
from warroom import liquidity as LIQ
from warroom import macro_data as MD
from warroom import policy as POL
from warroom import drivers as DRV
from warroom import price_action as PA
from warroom import structure as ST
from warroom import rotation as ROT
from warroom import beta_play as BP
from warroom import themes as TH
from warroom import secular_map as SEC

_DATADIR = os.path.join(os.path.dirname(__file__), "..", "data")

_DIAG = []  # observability: genuine exceptions (NOT no-signal None returns) collected per run


def _try(fn, default=None):
    try:
        return fn()
    except Exception as e:
        try:
            import re as _re, traceback as _tb
            eng = ""
            for ln in reversed(_tb.format_exc().splitlines()):
                if any(p in ln for p in ("engines/", "gcfis/", "warroom/")):
                    m = _re.search(r"([\w./-]+\.py)", ln)
                    if m:
                        eng = m.group(1).split("/")[-1]
                        break
            _DIAG.append({"engine": eng or type(e).__name__, "error": f"{type(e).__name__}: {str(e)[:120]}"})
        except Exception:
            _DIAG.append({"engine": "?", "error": str(e)[:120]})
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
                    "flip": ""})
        out["divergence"] = "divergent" if out["structural"] != out["monthly"] else "aligned"
        out["struct_probs"] = dict(getattr(r, "structural_probs", {}) or {})
        out["month_probs"] = dict(getattr(r, "monthly_probs", {}) or {})
        fh = getattr(r, "flip_hazard", None)
        out["flip_hazard"] = round(float(fh() if callable(fh) else (fh or 0)), 2)
        _cl = {t: us[t]["Close"] for t in us if us.get(t) is not None}
        out["regime_transition"] = _try(lambda: __import__("engines.regime_transition_engine", fromlist=["run_regime_transition"]).run_regime_transition(r, _cl, fred))
        out["change_detect"] = _try(lambda: __import__("gcfis.engines.change_detection", fromlist=["run_change_detection"]).run_change_detection({"spx": _cl.get("SPY")}, 60))
    else:
        out.update(_proxy_quad(us))
        out["struct_probs"], out["month_probs"], out["flip_hazard"] = {}, {}, 0.0
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
def _verdict(setups):
    L = sum(1 for s in setups if s["_dir"] == "Long"); S = sum(1 for s in setups if s["_dir"] == "Short")
    if L > S: return "Risk-on", "grn"
    if S > L: return "Risk-off", "red"
    return "Mixed", "amb"


def _setups(prices, bench_t=None, names=None, n=8, long_only=False):
    bench = prices.get(bench_t) if bench_t else None
    bm = (lambda k: _ret(bench["Close"], k)) if (bench is not None and len(bench) > 70) else (lambda k: 0.0)
    rows = []
    for t in (names or list(prices)):
        d = prices.get(t)
        if d is None or len(d) < 80 or t == bench_t:
            continue
        c = d["Close"]
        rs = _ret(c, 63) - bm(63); mom = _ret(c, 63); acc = _ret(c, 21) - _ret(c, 63)
        sma20, sma50 = float(c.tail(20).mean()), float(c.tail(50).mean())
        above50, trend = c.iloc[-1] / sma50 - 1, sma20 / sma50 - 1
        form = "BULLISH" if (trend > 0 and above50 > 0) else "BEARISH" if (trend < 0 and above50 < 0) else "NEUTRAL"
        direction = "Long" if (form == "BULLISH" and rs > 0) else "Short" if (form == "BEARISH" and rs < 0) else "Watch"
        if long_only and direction == "Short":
            direction = "Watch"
        rr = _try(lambda: _rr(d, t))
        if rr and isinstance(rr, dict) and "trade" in rr:
            tl, th = rr["trade"]["lrr"], rr["trade"]["trr"]
            nl, nh = rr.get("trend", {}).get("lrr"), rr.get("trend", {}).get("trr")
        else:
            p0 = float(c.iloc[-1]); tl, th = round(p0 * 0.985, 2), round(p0 * 1.015, 2); nl, nh = round(p0 * 0.95, 2), round(p0 * 1.05, 2)
        px = round(float(c.iloc[-1]), 2)
        tl = round(tl, 2); th = round(th, 2)
        nl = round(nl, 2) if nl else None; nh = round(nh, 2) if nh else None
        if direction == "Long":
            stop = min(tl, round(px * 0.97, 2))
            target = max(nh if nh else px, round(px * 1.06, 2))
            entry = f"{stop}–{px}"
        elif direction == "Short":
            stop = max(th, round(px * 1.03, 2))
            target = min(nl if nl else px, round(px * 0.94, 2))
            entry = f"{px}–{stop}"
        else:
            stop, target, entry = None, None, f"{tl}–{th}"
        strength = abs(rs) * 2.2 + abs(mom) + abs(above50) * 0.7
        conf = None
        if isinstance(rr, dict) and "trade" in rr:
            conf = _try(lambda: __import__("engines.confluence_engine", fromlist=["multi_tf_confluence"]).multi_tf_confluence(
                rr.get("trade", {}).get("phase"), rr.get("trend", {}).get("phase"), rr.get("tail", {}).get("phase")))
        rows.append({"ticker": t, "_dir": direction, "px": px, "entry": entry, "stop": stop, "target": target,
                     "rs": round(rs * 100, 1), "accel": round(acc * 100, 1), "form": form, "conf": conf, "score": round(max(strength, 0) * 10, 1)})
    rows.sort(key=lambda x: (x["_dir"] != "Watch", x["score"]), reverse=True)
    return rows[:n]


def _us_gamma(us, names):
    import re
    clean = lambda s: re.sub(r"[^\x00-\x7F]+", "", str(s)).strip() if s is not None else "—"
    vix = _vix(us)
    closes = {t: us[t]["Close"] for t in us if us.get(t) is not None}
    gp = _try(lambda: __import__("engines.greeks_proxy", fromlist=["GreeksProxy"]).GreeksProxy().analyze_multi(list(names), closes, vix, 0.0, "Q3"))
    out = []
    for t in names:
        g = (gp or {}).get(t) if isinstance(gp, dict) else None
        d = us.get(t); c = d["Close"] if d is not None else None
        if isinstance(g, dict) and g.get("ok"):
            out.append({"ticker": t, "px": round(float(g.get("price", 0)), 2), "gamma": clean(g.get("gamma")),
                        "vanna": clean(g.get("vanna")), "charm": clean(g.get("charm")),
                        "composite": clean(g.get("composite")), "max_pain": g.get("max_pain"), "rv": g.get("rvol_20d")})
        elif c is not None and len(c) > 40:
            sma20 = float(c.tail(20).mean()); px = float(c.iloc[-1]); rv = float(c.pct_change().tail(20).std() * (252 ** 0.5))
            out.append({"ticker": t, "px": round(px, 2), "gamma": ("short gamma" if px < sma20 else "long gamma"),
                        "vanna": "—", "charm": "—", "composite": "—", "max_pain": round(sma20, 2), "rv": round(rv * 100, 0)})
    return out


def _us_lens(us):
    names = [t for t in D.US_NAMES if us.get(t) is not None]
    setups = _setups(us, "SPY", names, 8)
    v, vc = _verdict(setups)
    return {"setups": setups, "gamma": _us_gamma(us, [s["ticker"] for s in setups[:6]]), "verdict": v, "vcolor": vc}


def _crypto_lens(cp):
    setups = _setups(cp, "BTC-USD", list(cp), 6)
    btc, eth, sol = cp.get("BTC-USD"), cp.get("ETH-USD"), cp.get("SOL-USD")
    dom = None
    if btc is not None and eth is not None:
        alt = _ret(eth["Close"], 30) + (_ret(sol["Close"], 30) if sol is not None else _ret(eth["Close"], 30))
        dom = round((_ret(btc["Close"], 30) * 2 - alt) * 100, 1)
    vr = None
    if btc is not None and len(btc) > 90:
        rv = float(btc["Close"].pct_change().tail(20).std() * (252 ** 0.5)); rv90 = float(btc["Close"].pct_change().tail(90).std() * (252 ** 0.5))
        vr = "elevated" if rv > rv90 else "compressed"
    v, vc = _verdict(setups)
    return {"setups": setups, "btc_dom": dom, "vol_regime": vr, "verdict": v, "vcolor": vc}


def _commo_lens(commo, us):
    setups = _setups(commo, "DBC", list(commo), 6)
    dxy = us.get("UUP"); gld = commo.get("GLD")
    if gld is None:
        gld = us.get("GLD")
    gb = _try(lambda: __import__("engines.fx_commodity_driver_engine", fromlist=["gold_bias"]).gold_bias(
        ("up" if dxy is not None and dxy["Close"].iloc[-1] > dxy["Close"].tail(20).mean() else "down"),
        0.0, _ret(gld["Close"], 30) if gld is not None else 0.0, False), None)
    if isinstance(gb, dict):
        gb = gb.get("label") or gb.get("bias")
    dbc = commo.get("DBC")
    ctrend = ("up" if dbc is not None and dbc["Close"].iloc[-1] > dbc["Close"].tail(50).mean() else "down") if dbc is not None else None
    v, vc = _verdict(setups)
    return {"setups": setups, "gold_bias": gb, "complex_trend": ctrend, "verdict": v, "vcolor": vc}


def _fx_lens(fx):
    dxy = fx.get("DX-Y.NYB")
    dt = ("rising" if dxy is not None and dxy["Close"].iloc[-1] > dxy["Close"].tail(50).mean() else "falling") if dxy is not None else None
    dm = round(_ret(dxy["Close"], 21) * 100, 1) if dxy is not None else None
    setups = _setups(fx, "DX-Y.NYB", list(fx), 6)
    for s in setups:
        s["ticker"] = s["ticker"].replace("=X", "").replace("DX-Y.NYB", "DXY")
    v, vc = _verdict(setups)
    return {"setups": setups, "dxy_trend": dt, "dxy_mom": dm, "verdict": v, "vcolor": vc}


def _idx_flow(idx):
    rows = []
    for t, df in (idx or {}).items():
        try:
            lf = lpm_features(df, scaling="value_typical", span=20)
            adl = money_flow(df, "value_typical").cumsum()
            rising = bool(adl.iloc[-1] > adl.iloc[-min(21, len(adl))])
            stage = _try(lambda: __import__("gcfis.engines.accumulation", fromlist=["run_accumulation"]).run_accumulation(
                t, df["Close"], df["Close"], df["Volume"], None, None, None, None, None, False))
            slbl = None
            if isinstance(stage, dict):
                slbl = stage.get("stage") or stage.get("adoption_stage") or stage.get("label")
            rows.append({"ticker": t, "state": lf.get("state"), "lpm": lf.get("lpm"), "adl_rising": rising, "stage": slbl})
        except Exception:
            continue
    setups = _setups(idx, None, list(idx), 8, long_only=True)   # IDX has no short
    acc = sum(1 for r in rows if r.get("state") == "accumulation")
    v = ("Accumulation" if acc > len(rows) / 2 else "Distribution" if acc < len(rows) / 3 else "Mixed")
    vc = "grn" if v == "Accumulation" else "red" if v == "Distribution" else "amb"
    return {"rows": rows, "setups": setups, "verdict": v, "vcolor": vc}

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
def run(us, idx, crypto, fx, commo, fred=None, feeds=None):
    _DIAG.clear()
    reg = _regime(us, fred)
    rows = _rank(us, reg)
    quad = reg["structural"]
    out = {
        "regime": reg, "rows": rows,
        "scanned": len(D.US_NAMES), "conviction": rows[:4], "watchlist": rows[4:12],
        "methodology": _methodology(us, quad),
        "us_lens": _us_lens(us),
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
    # CROSS-MARKET competitive ranking (vision: best across ALL markets, not US-only)
    pool = []
    for mkt, key in [("US", "us_lens"), ("Crypto", "crypto"), ("Commodities", "commo"), ("FX", "fx"), ("IHSG", "idx")]:
        for s in (out.get(key, {}).get("setups") or []):
            if s["_dir"] in ("Long", "Short"):
                s2 = dict(s); s2["market"] = mkt
                s2["frameworks"] = out["methodology"].get(s["ticker"], []) if mkt == "US" else []
                pool.append(s2)
    pool.sort(key=lambda x: x["score"], reverse=True)
    out["ranked"] = len(pool)
    out["conviction"] = pool[:5]
    out["watchlist"] = pool[5:14]
    allpx = {}
    for dd in (us, idx, crypto, fx, commo):
        for k, v in (dd or {}).items():
            allpx.setdefault(k, v)
    dmax = max([r["score"] for r in out["conviction"]] or [1]) or 1
    for r in out["conviction"]:
        disp01 = (10 * r["score"] / dmax) / 10.0
        rrd = _try(lambda: _rr(allpx[r["ticker"]], r["ticker"])) if r["ticker"] in allpx else None
        r["size"] = _sizing_full(r["ticker"], reg["structural"], vix, disp01, rrd)
    out["xasset"] = _xasset(us, commo)
    out["shock_prob"] = "elevated" if vix > 22 else "moderate" if vix > 17 else "low"
    out["batch_a"] = _batch_a(us, commo, reg, vix, fred)
    # complete relevant-macro chain + broken-link scanner (recession / K-shape)
    _ind = _try(lambda: MD.compute(fred)) or []
    out["macro"] = {"indicators": _ind,
                    "broken_links": _try(lambda: MD.broken_links(_ind)) or [],
                    "kshape": _try(lambda: MD.kshape_score(_ind))}
    # Fed rate-path (market-implied) + inflation signal-vs-noise + bait detector
    _oil = allpx.get("USO")
    _oil_yoy = _try(lambda: (float(_oil["Close"].iloc[-1]) / float(_oil["Close"].iloc[-252]) - 1) * 100) if (_oil is not None and len(_oil) > 252) else None
    _rinc = next((i["value"] for i in _ind if i["id"] == "DSPIC96"), None)
    out["policy"] = _try(lambda: POL.synthesize(fred, _oil_yoy, (_rinc is not None and _rinc < 0)))
    # cross-asset driver coherence (who's offside vs their mythic variable)
    _drv = _try(lambda: DRV.compute(allpx, fred)) or []
    out["drivers"] = {"assets": _drv, "summary": _try(lambda: DRV.coherence_summary(_drv)) or {}}
    out["market_character"] = _try(lambda: PA.market_character(allpx, "SPY"))
    out["rotation"] = _try(lambda: ROT.compute(allpx)) or {}
    out["beta_plays"] = _try(lambda: BP.analyze_themes(allpx)) or {}
    out["theme_graph"] = _try(lambda: TH.connect_dots(allpx)) or {}
    # live feeds (from build_feeds.py snapshot) → fill feed-gated lens slots; empty = graceful proxy
    feeds = feeds or {}
    out["feeds_status"] = {k: (feeds.get(k) is not None) for k in ("fred", "fx_carry", "typef", "onchain", "cot", "gex", "finra")}
    if feeds.get("fx_carry") is not None:
        out["fx"]["carry"] = feeds["fx_carry"]
    elif fred:
        out["fx"]["carry"] = _try(lambda: __import__("engines.fx_carry_engine", fromlist=["analyze_fx_carry"]).analyze_fx_carry(fred, ["EURUSD", "USDJPY", "GBPUSD", "AUDUSD", "USDIDR"]))
    if feeds.get("typef") is not None:
        out["idx"]["typef"] = feeds["typef"]
    if feeds.get("onchain") is not None:
        out["crypto"]["onchain"] = feeds["onchain"]
    if feeds.get("cot") is not None:
        out["commo"]["cot"] = feeds["cot"]
    if feeds.get("gex") is not None:
        out["us_lens"]["gex_live"] = feeds["gex"]
    if feeds.get("finra") is not None:
        out["us_lens"]["finra"] = feeds["finra"]
    # market-wide context for the decision brain
    _vixs = _try(lambda: us["^VIX"]["Close"] if us.get("^VIX") is not None else None)
    _me = _try(lambda: MECH.month_end_flow(allpx))
    _vt = _try(lambda: MECH.vol_target_pressure(vix, _vixs))
    out["mechanical"] = {"month_end": _me, "vol_target": _vt}
    out["crowd_market"] = _try(lambda: CROWD.market_crowd(us))
    _posture = "Risk-On" if str(reg.get("structural", "")).strip()[-1:] in ("1", "2") else "Risk-Off"
    if reg.get("defensive"):
        _posture = "Risk-Off / defensive"
    _ctx = {"month_end": _me, "vol_target": _vt, "posture": _posture}

    # per-instrument sensors (intervention, mechanical, timing, crowd, liquidity) → decision synthesis
    _fr = out.get("batch_a", {}).get("frontrun") or {}
    _frset = set((x.get("ticker") if isinstance(x, dict) else x) for x in (_fr.get("boarding_now") or [])) if isinstance(_fr, dict) else set()

    def _tag(s, mk):
        df = allpx.get(s["ticker"])
        iv = _try(lambda: INT.assess(s["ticker"], df, mk, s.get("_dir")))
        ev = _try(lambda: INT.event_tag(s["ticker"], mk))
        if iv or ev:
            s["intervention"] = iv or ev
        mt = _try(lambda: MECH.rebalance_tag(s["ticker"], mk, None))
        if mt:
            s["mechanical"] = mt
        if s.get("_dir") in ("Long", "Short") and s.get("target") is not None and df is not None:
            rrd = _try(lambda: _rr(df, s["ticker"]))
            tm = _try(lambda: TIM.assess(s["ticker"], df, s["_dir"], s.get("px"), s.get("stop"), s.get("target"), rrd, _frset))
            if tm:
                s["timing"] = tm
        cr = _try(lambda: CROWD.name_crowd(df, s.get("_dir")))
        if cr:
            s["crowd"] = cr
        lq = _try(lambda: LIQ.assess(s["ticker"], df))
        if lq:
            s["liquidity"] = lq
        dec = _try(lambda: SYN.decide(s, _ctx))
        if dec:
            s["decision"] = dec
        nc = _try(lambda: DRV.name_coherence(allpx, s["ticker"], mk))
        if nc:
            s["name_coh"] = nc
        pa = _try(lambda: PA.read(df))
        if pa:
            s["pa"] = pa
        stc = _try(lambda: ST.read(df))
        if stc:
            s["structure"] = stc

    _mkt = {"us_lens": "US", "crypto": "Crypto", "commo": "Commodities", "fx": "FX", "idx": "IHSG"}
    for _key, _mk in _mkt.items():
        for s in (out.get(_key, {}).get("setups") or []):
            _tag(s, _mk)
    for s in out.get("conviction", []):
        _tag(s, s.get("market", ""))
    # walk-forward + Monte-Carlo 100x gatekeeper (anti-overfit) on conviction setups
    vset = {r["ticker"]: {"ticker": r["ticker"], "direction": r["_dir"], "entry": r["px"], "stop": r["stop"], "target": r["target"]}
            for r in out["conviction"] if r["_dir"] in ("Long", "Short") and r["ticker"] in allpx}
    gate = _try(lambda: __import__("engines.walkforward_backtest_engine", fromlist=["batch_gatekeeper"]).batch_gatekeeper(list(vset), allpx, vset, None)) or {}
    if isinstance(gate, dict):
        for r in out["conviction"]:
            g = gate.get(r["ticker"])
            if isinstance(g, dict):
                r["gate"] = {"status": g.get("gate_status"), "score": g.get("combined_gate_score"),
                             "wf": g.get("walkforward_score"), "mc": g.get("mc_score"),
                             "stop_adj": g.get("optimal_stop_adj"), "target_adj": g.get("optimal_target_adj")}
        out["validation"] = {"checked": len(vset),
                             "passed": sum(1 for g in gate.values() if isinstance(g, dict) and g.get("gate_status") == "PASS")}
    else:
        out["validation"] = {"checked": 0, "passed": 0}
    # funding nudge
    if out["funding"].get("crash_nudge"):
        reg["posture"], reg["defensive"] = "Defensive", True
    # portfolio risk layer (conviction book)
    out["risk"] = _try(lambda: RISK.portfolio(out.get("conviction", []), allpx)) or {"n": 0}
    # data freshness
    try:
        import datetime as _dt
        last = max((pd.to_datetime(df.index[-1]).date() for df in allpx.values() if df is not None and len(df)), default=None)
        out["data_asof"] = {"date": str(last) if last else None, "stale_days": ((_dt.date.today() - last).days if last else None)}
    except Exception:
        out["data_asof"] = {"date": None, "stale_days": None}
    # observability: engine exceptions this run (NOT no-signal None returns)
    from collections import Counter as _Counter
    out["diagnostics"] = {"failures": len(_DIAG),
                          "by_engine": dict(_Counter(x["engine"] for x in _DIAG).most_common(12)),
                          "samples": _DIAG[:10]}
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


def _xasset(us, commo):
    """cross-asset coherence (validated engine; OHLCV-derived daily % changes)."""
    def r(d, k=1):
        return float(d["Close"].iloc[-1] / d["Close"].iloc[-1 - k] - 1) if d is not None and len(d) > k else 0.0
    def pick(*dfs):
        for x in dfs:
            if x is not None:
                return x
        return None
    snap = {"gold": r(pick(commo.get("GLD"), us.get("GLD"))), "silver": r(commo.get("SLV")),
            "oil": r(pick(commo.get("USO"), us.get("USO"))), "spx": r(us.get("SPY")),
            "dollar": r(us.get("UUP")), "bonds": r(us.get("TLT")), "vix": r(us.get("^VIX"))}
    return _try(lambda: __import__("gcfis.engines.cross_asset", fromlist=["run_cross_asset"]).run_cross_asset(snap))


def _snap(us, commo):
    def r(d, k=1):
        return float(d["Close"].iloc[-1] / d["Close"].iloc[-1 - k] - 1) if d is not None and len(d) > k else 0.0
    def pick(*dfs):
        for x in dfs:
            if x is not None:
                return x
        return None
    return {"gold": r(pick(commo.get("GLD"), us.get("GLD"))), "silver": r(commo.get("SLV")),
            "oil": r(pick(commo.get("USO"), us.get("USO"))), "spx": r(us.get("SPY")),
            "dollar": r(us.get("UUP")), "bonds": r(us.get("TLT")), "vix": r(us.get("^VIX")),
            "copper": r(us.get("COPX")), "hy": r(us.get("HYG"))}


def _sizing_full(ticker, quad, vix, conviction01, rr_data):
    """full Hedgeye sizing (VIX x Quad x Conviction x RR); fallback to vix-bucket."""
    q = "Q" + str(quad)[-1]
    res = _try(lambda: __import__("engines.hedgeye_position_sizing", fromlist=["calculate_position_size"]).calculate_position_size(
        ticker, q, vix, conviction01, rr_data, None, False, 0.0))
    if isinstance(res, dict):
        for k in ("size_bps", "target_bps", "position_bps", "bps", "sized_bps"):
            if res.get(k) is not None:
                bps = round(float(res[k]))
                if 5 <= bps <= 1500:
                    return {"sized_bps": bps, "vix_bucket": res.get("vix_bucket") or res.get("bucket"), "engine": "hedgeye"}
                break
    return _sizing(conviction01 * 10, quad, vix)


def _batch_a(us, commo, reg, vix, fred=None):
    closes = {t: us[t]["Close"] for t in us if us.get(t) is not None}
    q = "Q" + str(reg.get("structural", "Quad 3"))[-1]
    snap = _snap(us, commo)
    imp = lambda mod, fn: __import__(mod, fromlist=[fn])
    o = {}
    o["reflexivity"] = _try(lambda: imp("engines.reflexivity_engine", "run_reflexivity").run_reflexivity(closes, fred, q))
    o["boombust"] = _try(lambda: imp("engines.boombust_engine", "classify_stage").classify_stage(closes, fred, None, q))
    o["keith"] = _try(lambda: imp("engines.keith_signal_sync", "get_keith_summary").get_keith_summary())
    o["coatue"] = _try(lambda: imp("engines.coatue_methodology", "run_coatue_scan").run_coatue_scan(list(closes)[:30], closes))
    o["narrative"] = _try(lambda: imp("engines.narrative_engine", "generate_macro_narrative").generate_macro_narrative(snap))
    o["scenarios"] = _try(lambda: imp("engines.narrative_engine", "generate_scenarios").generate_scenarios(snap))
    o["transmission"] = _try(lambda: imp("engines.transmission_engine", "run_transmission").run_transmission(closes, q, 5.0))
    o["cascade"] = _try(lambda: imp("engines.cascade_engine", "run_all_cascades").run_all_cascades(closes, None, None))
    o["seasonality"] = _try(lambda: imp("engines.seasonality_engine", "compute_universe_seasonality").compute_universe_seasonality(closes))
    o["cri"] = _try(lambda: imp("engines.cri_v2_engine", "CRIv2Engine").CRIv2Engine().batch(us))
    o["frontrun"] = _try(lambda: imp("engines.frontrun_engine", "FrontRunEngine").FrontRunEngine().run(us))
    return o
