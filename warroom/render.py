"""warroom/render.py — mockup-faithful renderers (single HTML block per section). 10 tabs."""
from __future__ import annotations
import streamlit as st

CSS = """
<style>
#MainMenu, header[data-testid="stHeader"], footer {visibility:hidden;}
.stApp {background:#0d1015;}
.block-container {padding-top:1.1rem; padding-bottom:2rem; max-width:1080px;}
html, body, [class*="css"] {font-family:-apple-system,'Segoe UI',Roboto,Helvetica,sans-serif;}
.stTabs [data-baseweb="tab-list"]{gap:1px; border-bottom:0.5px solid #232a32; flex-wrap:wrap;}
.stTabs [data-baseweb="tab"]{color:#6b7682; font-size:12.5px; padding:6px 10px;}
.stTabs [aria-selected="true"]{color:#e8edf2;}
.wr-mono{font-family:'SF Mono','Roboto Mono',ui-monospace,monospace;}
.wr-top{display:flex;align-items:center;gap:8px;margin-bottom:10px;}
.wr-top b{font-size:14px;font-weight:600;color:#e8edf2;} .wr-top span{font-size:12px;color:#6b7682;}
.wr-hero{border:0.5px solid #2a3038;border-radius:14px;padding:16px 20px;background:#12161d;margin-bottom:16px;}
.wr-herotop{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;flex-wrap:wrap;}
.wr-sub{font-size:13px;color:#9aa6b2;} .wr-tk{font-size:11px;color:#6b7682;}
.wr-quad{font-size:24px;font-weight:600;color:#e8edf2;line-height:1;}
.wr-quad2{font-size:16px;font-weight:600;color:#c4ccd4;line-height:1;}
.wr-lbl{font-size:11px;color:#6b7682;margin:0 0 7px 2px;}
.wr-badge{font-size:11px;font-weight:600;padding:4px 11px;border-radius:8px;white-space:nowrap;}
.b-grn{color:#9adcc0;background:#15332a;} .b-red{color:#f0a0a0;background:#3a1f22;}
.b-amb{color:#e7c389;background:#33280f;} .b-inf{color:#9cc3e7;background:#13283a;} .b-gry{color:#9aa6b2;background:#1b212a;}
.wr-bar{height:6px;background:#1b212a;border-radius:3px;overflow:hidden;margin-top:5px;}
.wr-barfill{height:100%;}
.wr-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(116px,1fr));gap:8px;margin-bottom:16px;}
.wr-tile{background:#161b22;border-radius:8px;padding:10px 12px;}
.wr-tv{font-size:18px;font-weight:600;color:#e8edf2;line-height:1.1;margin-top:3px;}
.wr-chip{font-size:11px;margin-top:5px;}
.c-red{color:#e89a9a;} .c-grn{color:#8fd3b8;} .c-amb{color:#e0bd86;} .c-sub{color:#9aa6b2;}
.wr-card{background:#12161d;border:0.5px solid #232a32;border-radius:8px;padding:10px 12px;margin-bottom:8px;}
.wr-ctop{display:flex;align-items:center;gap:8px;margin-bottom:6px;flex-wrap:wrap;}
.wr-tkr{font-size:15px;font-weight:600;color:#e8edf2;}
.wr-score{margin-left:auto;font-size:14px;font-weight:600;color:#e8edf2;}
.wr-why{font-size:12px;color:#9aa6b2;line-height:1.6;} .wr-why .k{color:#6b7682;}
.wr-rows{background:#12161d;border:0.5px solid #232a32;border-radius:8px;overflow:hidden;}
.wr-row{display:flex;align-items:center;gap:10px;padding:9px 12px;border-bottom:0.5px solid #1b212a;font-size:12px;}
.wr-row:last-child{border-bottom:none;}
.wr-chain{background:#161b22;border-radius:8px;padding:12px;margin-bottom:16px;}
.wr-node{font-size:12px;padding:5px 11px;border-radius:8px;background:#12161d;margin:0 2px 4px 0;display:inline-block;}
.n-src{border:0.5px solid #2a3038;color:#e8edf2;} .n-red{border:0.5px solid #5a2a2e;color:#e89a9a;}
.n-amb{border:0.5px solid #5a4520;color:#e0bd86;} .n-grn{border:0.5px solid #234b3a;color:#8fd3b8;}
.wr-note{color:#6b7682;font-size:11px;}
.wr-flowbar{height:8px;border-radius:4px;background:#1b212a;overflow:hidden;flex:1;}
</style>
"""

_DIRK = {"Long": "grn", "Short": "red", "Watch": "amb"}
def _b(t, k): return f"<span class='wr-badge b-{k}'>{t}</span>"
def _fmt(v, n=2):
    try:
        return "—" if v is None else f"{float(v):.{n}f}"
    except Exception:
        return str(v)
def _short(x, n=120):
    try:
        if x is None: return "—"
        if isinstance(x, dict):
            parts = []
            for k, v in list(x.items())[:4]:
                vv = f"{v:.2f}" if isinstance(v, float) else str(v)
                parts.append(f"{k}={vv}")
            return ", ".join(parts)[:n]
        if isinstance(x, (int, float, str)): return str(x)[:n]
        for a in ("label", "state", "regime", "summary", "verdict"):
            if hasattr(x, a): return str(getattr(x, a))[:n]
        return str(x)[:n]
    except Exception:
        return "—"
def _tile(label, value, chip="", ck="sub"):
    c = f"<div class='wr-chip c-{ck}'>{chip}</div>" if chip else ""
    return f"<div class='wr-tile'><div class='wr-tk'>{label}</div><div class='wr-tv wr-mono'>{value}</div>{c}</div>"
def _dmax(d):
    s = [r.get("score", 0) for r in d.get("conviction", []) + d.get("watchlist", [])]
    return max(s) if s else 1.0


def _causal5(r, reg):
    rs, acc, ac, f, dr = r.get("rs63", 0), r.get("accumulation", 0), r.get("accel", 0), r.get("formation", "").lower(), r["_dir"]
    changed = ("momentum accelerating" if ac > 0 else "momentum decelerating") + f" ({ac:+.0f}% 21d vs 63d)"
    trapped = ("late momentum longs" if dr == "Short" else "underweight allocators" if dr == "Long" else "both sides undecided")
    must = ("forced de-risk / margin" if dr == "Short" else "underexposed allocators chasing" if dr == "Long" else "awaiting trigger")
    inval = ("loses TRADE low / RS turns negative" if dr == "Long" else "reclaims TRADE high / RS turns positive" if dr == "Short" else "needs formation + RS confirmation")
    return (f"<span class='k'>Why now:</span> {reg['structural']}, RS {rs:+.0f}% vs SPY, {f} formation, accumulation {acc}. "
            f"<span class='k'>What changed:</span> {changed}. "
            f"<span class='k'>Trapped:</span> {trapped}. <span class='k'>Must buy:</span> {must}. "
            f"<span class='k'>Invalidates:</span> {inval}.")


def _conv_card(r, dmax, reg, extra=""):
    disp = 10 * r.get("score", 0) / dmax if dmax else 0
    rr = f"RR {r.get('lrr',0):.1f}–{r.get('trr',0):.1f}"
    vs = f" · {r['vol_state']}" if r.get("vol_state") else ""
    sz = r.get("size"); szhtml = ""
    if sz:
        vb = f" · VIX {sz['vix_bucket']}" if sz.get("vix_bucket") else ""
        szhtml = f"<div class='wr-sub' style='margin-top:4px;'>size ~{sz['sized_bps']}bps (Hedgeye VIX×quad{vb})</div>"
    return (f"<div class='wr-card'><div class='wr-ctop'>{_b(r['_dir'], _DIRK.get(r['_dir'],'inf'))}"
            f"<span class='wr-tkr wr-mono'>{r['ticker']}</span><span class='wr-sub'>{rr}{vs}</span>"
            f"<span class='wr-score wr-mono'>{disp:.1f}</span></div><div class='wr-why'>{_causal5(r, reg)}</div>{szhtml}{extra}</div>")


def _setup_card(s):
    k = _DIRK.get(s["_dir"], "inf")
    levels = (f"<span class='k'>entry</span> {s['entry']} · <span class='k'>stop</span> {s['stop']} · <span class='k'>target</span> {s['target']}"
              if s["_dir"] in ("Long", "Short") else f"<span class='k'>watch zone</span> {s['entry']}")
    return (f"<div class='wr-card'><div class='wr-ctop'>{_b(s['_dir'], k)}"
            f"<span class='wr-tkr wr-mono'>{s['ticker']}</span><span class='wr-sub'>${s['px']}</span>"
            f"<span class='wr-score wr-mono'>{s['score']:.1f}</span></div>"
            f"<div class='wr-why'>{levels}. <span class='k'>RS</span> {s['rs']:+.0f}% · {s['form'].lower()}.</div></div>")


def _xcard(s, dmax):
    disp = 10 * s.get("score", 0) / dmax if dmax else 0
    k = _DIRK.get(s["_dir"], "inf")
    lvl = (f"<span class='k'>entry</span> {s['entry']} · <span class='k'>stop</span> {s['stop']} · <span class='k'>target</span> {s['target']}"
           if s["_dir"] in ("Long", "Short") else f"watch {s['entry']}")
    fw = f" <span class='k'>· frameworks:</span> {', '.join(s['frameworks'][:4])}" if s.get("frameworks") else ""
    sz = s.get("size"); szh = f" · size ~{sz['sized_bps']}bps" if sz else ""
    g = s.get("gate"); gate_badge = ""; gh = ""
    if g and g.get("status"):
        gk = "grn" if g["status"] == "PASS" else "red"
        gate_badge = _b(f"WF {g['status']} {g.get('score','')}", gk)
        gh = f" <span class='k'>· gate:</span> wf {g.get('wf','?')} / mc {g.get('mc','?')}"
    return (f"<div class='wr-card'><div class='wr-ctop'>{_b(s['_dir'], k)}"
            f"<span class='wr-tkr wr-mono'>{s['ticker']}</span>"
            f"<span class='wr-badge b-gry'>{s.get('market','')}</span>{gate_badge}"
            f"<span class='wr-sub'>${s['px']}</span><span class='wr-score wr-mono'>{disp:.1f}</span></div>"
            f"<div class='wr-why'>{lvl}. <span class='k'>RS</span> {s['rs']:+.0f}% · accel {s.get('accel',0):+.0f}% · {s['form'].lower()}{fw}{szh}{gh}.</div></div>")


def _probrow(probs):
    if not probs:
        return "<span class='wr-note'>quad probabilities need FRED (live on your machine).</span>"
    order = ["Q1", "Q2", "Q3", "Q4"]; mx = max(probs.values()) or 1
    cells = ""
    for q in order:
        p = probs.get(q, 0); w = int(100 * p / mx)
        cells += (f"<div style='flex:1;'><div class='wr-tk'>{q} {p*100:.0f}%</div>"
                  f"<div class='wr-bar'><div class='wr-barfill' style='width:{w}%;background:#6b7682;'></div></div></div>")
    return f"<div style='display:flex;gap:10px;'>{cells}</div>"


def command_center(d, source):
    reg = d["regime"]; fund = d.get("funding", {})
    gs, isr, b = reg["g_struct"], reg["i_struct"], reg["breadth"]
    conf = int(min(95, 50 + abs(gs) * 1.0 + abs(isr) * 0.8))
    pcol = "#e07a5f" if reg["defensive"] else "#1d9e75"
    dvg = reg.get("divergence", "")
    dvg_badge = _b(f"Structural vs Monthly: {dvg}", "amb" if dvg == "divergent" else "gry")
    flip = reg.get("flip") or ("Flips risk-on if growth accel turns positive + breadth > 55%" if reg["defensive"]
                               else "Flips defensive if growth accel rolls over + breadth < 45%")
    fscore = fund.get("score", "—"); flab = fund.get("label", "—")
    drivers = (_tile("Growth (struct)", f"{gs:+.1f}", ("↓ Slowing" if gs < 0 else "↑ Rising"), "red" if gs < 0 else "grn")
               + _tile("Inflation (struct)", f"{isr:+.1f}", ("↑ Rising" if isr > 0 else "↓ Easing"), "amb" if isr > 0 else "grn")
               + _tile("Liquidity / funding", f"{fscore}", flab, {"stress": "red", "easing": "grn"}.get(flab, "amb"))
               + _tile("Shock prob", d.get("shock_prob", "—"), "VIX-based", {"elevated": "red", "moderate": "amb"}.get(d.get("shock_prob"), "grn"))
               + _tile("Breadth", f"{b}%", ("↓ <50d" if b < 50 else "↑ healthy"), "red" if b < 50 else "grn")
               + _tile("Bullish", d["market"]["bull"], "formations", "grn")
               + _tile("Bearish", d["market"]["bear"], "formations", "red"))
    dmax = _dmax(d)
    cards = "".join(_xcard(r, dmax) for r in d["conviction"])
    bits = []
    if d.get("hmm"): bits.append(f"<span class='k'>HMM regime:</span> {_short(d['hmm'],40)}")
    if d.get("forward") is not None: bits.append(f"<span class='k'>Forward macro:</span> {_short(d['forward'],60)}")
    if d.get("crash") is not None: bits.append(f"<span class='k'>Crash/bottom:</span> {_short(d['crash'],60)}")
    bits.append(f"<span class='k'>VIX:</span> {d.get('vix','—')}")
    state_html = (f"<div class='wr-lbl'>Regime state — HMM · forward · shock (engines)</div>"
                  f"<div class='wr-rows' style='margin-bottom:16px;'><div class='wr-row'>"
                  f"<span class='wr-why'>{' &nbsp;·&nbsp; '.join(bits)}</span></div></div>")
    quad_html = (f"<div class='wr-lbl'>Quad path — next-quad probability (Hedgeye GIP)</div>"
                 f"<div class='wr-card' style='margin-bottom:16px;'>"
                 f"<div class='wr-tk' style='margin-bottom:6px;'>Structural</div>{_probrow(reg.get('struct_probs',{}))}"
                 f"<div class='wr-tk' style='margin:12px 0 6px;'>Monthly</div>{_probrow(reg.get('month_probs',{}))}"
                 f"<div class='wr-sub' style='margin-top:12px;'><span class='k' style='color:#6b7682;'>Flip hazard:</span> {reg.get('flip_hazard',0)*100:.0f}% chance of quad change</div></div>")
    # propagation chain (restored to CC)
    edges = d.get("bottleneck", {}).get("leadlag", [])
    if edges:
        chain = " ".join(f"<span class='wr-node n-src wr-mono'>{e['leader']}→{e['follower']} ({e.get('lag','?')}d)</span>" for e in edges[:4])
        chsrc = "lead-lag (Granger+TE, discovered)"
    else:
        nodes = ["GPU compute", "Networking", "Power / grid", "Cooling / photonics"]; ncls = ["n-src", "n-src", "n-amb", "n-red"]
        chain = "<span class='wr-sub'>→</span>".join(f"<span class='wr-node {ncls[j]}'>{n}</span>" for j, n in enumerate(nodes))
        chsrc = "bottleneck migration (Citrini / Aschenbrenner)"
    xa = d.get("xasset")
    xa_html = f"<div class='wr-note' style='margin-top:6px;'><span class='k'>Cross-asset coherence:</span> {_short(xa, 90)}</div>" if xa else ""
    html = (f"<div class='wr-top'><b>War room</b><span>Command center</span></div>"
            f"<div class='wr-hero'><div class='wr-herotop'>"
            f"<div><div class='wr-tk'>Regime — US equities · {reg.get('source','')}</div>"
            f"<div style='display:flex;align-items:baseline;gap:14px;flex-wrap:wrap;margin-top:2px;'>"
            f"<span class='wr-quad'>Structural {reg['structural']}</span>"
            f"<span class='wr-quad2'>Monthly {reg['monthly']}</span></div>"
            f"<div class='wr-sub' style='margin-top:4px;'>{reg.get('operating','')}</div></div>"
            f"{_b('Posture · ' + reg['posture'], 'red' if reg['defensive'] else 'grn')}</div>"
            f"<div style='margin-top:10px;'>{dvg_badge}</div>"
            f"<div style='display:flex;gap:18px;flex-wrap:wrap;align-items:center;margin-top:14px;'>"
            f"<div style='flex:1;min-width:170px;'><div class='wr-tk'>Conviction · {conf}%</div>"
            f"<div class='wr-bar'><div class='wr-barfill' style='width:{conf}%;background:{pcol};'></div></div></div>"
            f"<div style='flex:2;min-width:210px;' class='wr-sub'>{flip}</div></div></div>"
            f"<div class='wr-lbl'>Why — regime drivers (Hedgeye GIP: structural + monthly)</div><div class='wr-grid'>{drivers}</div>"
            f"{state_html}"
            f"{quad_html}"
            f"<div class='wr-lbl'>What to do — highest conviction</div>{cards}"
            f"<div class='wr-lbl'>The edge — propagation</div><div class='wr-chain'>"
            f"<div style='display:flex;align-items:center;gap:6px;flex-wrap:wrap;'>{chain}</div>"
            f"<div class='wr-note' style='margin-top:8px;'>{chsrc}. 2nd-order tell: cooling / optical lag semis ~2–3 weeks — watch VRT/COHR after a SMH move.</div>"
            f"{xa_html}</div>"
            f"<div class='wr-note'>Data: {source} · GIP {reg.get('source','')} · risk range = Hedgeye TRADE/TREND/TAIL · not advice.</div>")
    st.markdown(CSS + html, unsafe_allow_html=True)


def alpha(d):
    dmax = _dmax(d)
    funnel = (_tile("Scanned", d["scanned"]) + _tile("Ranked", d.get("ranked", 0))
              + _tile("Conviction", len(d["conviction"])) + _tile("Watchlist", len(d["watchlist"])))
    cards = "".join(_xcard(r, dmax) for r in d["conviction"]) or "<div class='wr-note'>no long/short setups.</div>"
    rows = ""
    for r in d["watchlist"]:
        disp = 10 * r.get("score", 0) / dmax if dmax else 0
        rows += (f"<div class='wr-row'><span class='wr-mono' style='font-weight:600;min-width:62px;color:#e8edf2;'>{r['ticker']}</span>"
                 f"{_b(r['_dir'], _DIRK.get(r['_dir'],'inf'))}<span class='wr-badge b-gry'>{r.get('market','')}</span>"
                 f"<span class='wr-mono' style='color:#9aa6b2;'>{disp:.1f}</span>"
                 f"<span style='color:#9aa6b2;'>RS {r.get('rs',0):+.0f}% · entry {r.get('entry','')}</span></div>")
    val = d.get("validation", {})
    val_html = (f"<div class='wr-note' style='margin-bottom:4px;'>Walk-forward + MC-100x gatekeeper: "
                f"{val.get('passed',0)}/{val.get('checked',0)} conviction setups PASS (anti-overfit). Each card shows its WF gate.</div>") if val.get("checked") else ""
    html = (f"<div class='wr-top'><b>Alpha center</b><span>cross-market competitive ranking</span></div>"
            f"<div class='wr-grid'>{funnel}</div><div class='wr-lbl'>Highest conviction — best across all markets</div>{val_html}{cards}"
            f"<div class='wr-lbl'>Watchlist</div><div class='wr-rows'>{rows}</div>")
    st.markdown(CSS + html, unsafe_allow_html=True)

def _lens_rows(items, fmt):
    return "".join(fmt(r) for r in items) or "<div class='wr-row'><span class='wr-note'>feed needed for this lens.</span></div>"


def _need(label, what):
    return _tile(label, "—", "needs " + what, "sub")


def us_stocks(d):
    L = d.get("us_lens", {}); setups = L.get("setups", []); gamma = L.get("gamma", [])
    head = ("<div class='wr-row'><span class='wr-tk' style='min-width:58px;'>Ticker</span>"
            "<span class='wr-tk' style='flex:1;'>Gamma</span><span class='wr-tk' style='flex:1;'>Vanna</span>"
            "<span class='wr-tk' style='flex:1;'>Charm</span><span class='wr-tk' style='flex:1;'>Composite</span>"
            "<span class='wr-tk'>Max-pain</span></div>")
    grows = ""
    for g in gamma:
        comp = g.get("composite", "—"); cc = "grn" if "BULL" in comp.upper() else "red" if "BEAR" in comp.upper() else "sub"
        grows += (f"<div class='wr-row'><span class='wr-mono' style='font-weight:600;min-width:58px;color:#e8edf2;'>{g['ticker']}</span>"
                  f"<span class='wr-sub' style='flex:1;'>{g['gamma']}</span>"
                  f"<span class='wr-sub' style='flex:1;'>{g['vanna']}</span>"
                  f"<span class='wr-sub' style='flex:1;'>{g['charm']}</span>"
                  f"<span style='flex:1;'>{_b(comp, cc)}</span>"
                  f"<span class='wr-mono' style='color:#9aa6b2;'>{g['max_pain']}</span></div>")
    cards = "".join(_setup_card(s) for s in setups) or "<div class='wr-note'>no setups.</div>"
    html = (f"<div class='wr-top'><b>US stocks</b><span>per-ticker gamma · vanna · charm</span></div>"
            f"<div style='margin-bottom:14px;'>{_b('US · ' + L.get('verdict','—'), L.get('vcolor','amb'))}</div>"
            f"<div class='wr-lbl'>Dealer greeks — per ticker (price/vol proxy)</div><div class='wr-rows' style='margin-bottom:14px;'>{head}{grows}</div>"
            f"<div class='wr-lbl'>Setups — entry / stop / target (Hedgeye risk range)</div>{cards}"
            f"<div class='wr-note'>Per-ticker greeks = price/vol proxy (greeks_proxy engine): gamma/vanna/charm/composite/max-pain from realized-vol structure + VIX, no chain. Real signed GEX needs an options chain (yfinance_options, live on your machine). Entry/stop/target = Hedgeye TRADE/TREND.</div>")
    st.markdown(CSS + html, unsafe_allow_html=True)


def crypto(d):
    L = d.get("crypto", {}); setups = L.get("setups", []); dom = L.get("btc_dom"); vr = L.get("vol_regime")
    tiles = (_tile("BTC dominance", (f"{dom:+.0f}%" if dom is not None else "—"), "BTC vs alts 30d", "amb" if dom is not None else "sub")
             + _tile("Vol regime", vr or "—", "BTC RV 20d vs 90d", "red" if vr == "elevated" else "grn" if vr == "compressed" else "sub"))
    cards = "".join(_setup_card(s) for s in setups) or "<div class='wr-note'>no setups.</div>"
    html = (f"<div class='wr-top'><b>Crypto</b><span>dominance · vol · setups</span></div>"
            f"<div style='margin-bottom:14px;'>{_b('Crypto · ' + L.get('verdict','—'), L.get('vcolor','amb'))}</div>"
            f"<div class='wr-lbl'>Lens (price-derived)</div><div class='wr-grid'>{tiles}</div>"
            f"<div class='wr-lbl'>Setups — entry / stop / target</div>{cards}"
            f"<div class='wr-note'>On-chain (MVRV) / funding / stablecoin / liquidation need a feed (defillama / exchange / Deribit) — shown as absent, not faked. Dominance, vol, setups are price-derived.</div>")
    st.markdown(CSS + html, unsafe_allow_html=True)


def commodities(d):
    L = d.get("commo", {}); setups = L.get("setups", []); gb = L.get("gold_bias"); ct = L.get("complex_trend")
    tiles = (_tile("Gold bias", gb or "—", "DXY × real-yield", "amb" if gb else "sub")
             + _tile("Complex trend", ct or "—", "DBC vs 50d", "grn" if ct == "up" else "red" if ct == "down" else "sub"))
    cards = "".join(_setup_card(s) for s in setups) or "<div class='wr-note'>no setups.</div>"
    html = (f"<div class='wr-top'><b>Commodities</b><span>bias · trend · setups</span></div>"
            f"<div style='margin-bottom:14px;'>{_b('Commodities · ' + L.get('verdict','—'), L.get('vcolor','amb'))}</div>"
            f"<div class='wr-lbl'>Lens (price-derived)</div><div class='wr-grid'>{tiles}</div>"
            f"<div class='wr-lbl'>Setups — entry / stop / target</div>{cards}"
            f"<div class='wr-note'>Curve shape (backwardation) / inventory / shipping need a futures + COT feed — absent, not faked. Bias/trend/setups are price-derived.</div>")
    st.markdown(CSS + html, unsafe_allow_html=True)


def fx(d):
    L = d.get("fx", {}); setups = L.get("setups", []); dt = L.get("dxy_trend"); dm = L.get("dxy_mom")
    tiles = (_tile("DXY trend", dt or "—", "vs 50d", "red" if dt == "rising" else "grn" if dt == "falling" else "sub")
             + _tile("DXY momentum", (f"{dm:+.1f}%" if dm is not None else "—"), "21d", "sub"))
    cards = "".join(_setup_card(s) for s in setups) or "<div class='wr-note'>no setups.</div>"
    html = (f"<div class='wr-top'><b>FX</b><span>DXY · momentum · setups</span></div>"
            f"<div style='margin-bottom:14px;'>{_b('FX · ' + L.get('verdict','—'), L.get('vcolor','amb'))}</div>"
            f"<div class='wr-lbl'>Lens (price-derived)</div><div class='wr-grid'>{tiles}</div>"
            f"<div class='wr-lbl'>Setups — entry / stop / target</div>{cards}"
            f"<div class='wr-note'>Carry / rate-differential need FRED rates (engine: fx_carry) — absent, not faked. DXY trend/momentum + setups are price-derived.</div>")
    st.markdown(CSS + html, unsafe_allow_html=True)


def ihsg(d):
    L = d.get("idx", {}); rows = L.get("rows", []); setups = L.get("setups", [])
    acc_n = sum(1 for r in rows if r.get("state") == "accumulation"); st_n = sum(1 for r in rows if r.get("stage"))
    tiles = (_tile("Flow state", L.get("verdict", "—"), f"{acc_n}/{len(rows)} accumulating", L.get("vcolor", "amb"))
             + _tile("LPM", "value-based", "A/D divergence", "sub")
             + _tile("Adoption stage", f"{st_n} scored", "accumulation engine", "sub"))
    lpm_rows = "".join(f"<div class='wr-row'><span class='wr-mono' style='font-weight:600;min-width:78px;color:#e8edf2;'>{r['ticker']}</span>"
                       f"{_b(r.get('state','n/a'), {'accumulation':'grn','distribution':'red'}.get(r.get('state'),'amb'))}"
                       + (f"<span class='wr-badge b-gry'>{r['stage']}</span>" if r.get('stage') else "")
                       + f"<span class='wr-sub'>{'A/D ↑' if r.get('adl_rising') else 'A/D ↓'} · LPM {_fmt(r.get('lpm'),0)}</span></div>" for r in rows)
    cards = "".join(_setup_card(s) for s in setups) or "<div class='wr-note'>no long setups right now.</div>"
    html = (f"<div class='wr-top'><b>IHSG</b><span>BandarMetrics · long-only</span></div>"
            f"<div style='margin-bottom:14px;'>{_b('IHSG · ' + L.get('verdict','—'), L.get('vcolor','amb'))}</div>"
            f"<div class='wr-lbl'>Bandar lens</div><div class='wr-grid'>{tiles}</div>"
            f"<div class='wr-lbl'>Accumulation / distribution (value-based LPM + adoption stage)</div><div class='wr-rows' style='margin-bottom:14px;'>{lpm_rows}</div>"
            f"<div class='wr-lbl'>Setups — long-only (IDX has no short)</div>{cards}"
            f"<div class='wr-note'>IDX is long-only — no short setups. LPM value-based + adoption stage are live. Corr_F / Par_F / flow-regime / broker-entropy need IDX broker Type-F data (engines present: flow_regime, broker_flow) — absent, not faked. Entry/stop = Hedgeye risk range.</div>")
    st.markdown(CSS + html, unsafe_allow_html=True)

def flow(d):
    items = d.get("flow", [])
    mx = max((abs(r["flow"]) for r in items), default=1) or 1
    rows = ""
    for r in items:
        w = int(50 * abs(r["flow"]) / mx); col = "#1d9e75" if r["flow"] >= 0 else "#e07a5f"
        rows += (f"<div class='wr-row'><span style='min-width:80px;color:#e8edf2;'>{r['name']}</span>"
                 f"<span class='wr-mono' style='min-width:48px;color:#9aa6b2;'>{r['ticker']}</span>"
                 f"<div class='wr-flowbar'><div style='height:100%;width:{w}%;background:{col};'></div></div>"
                 f"<span class='wr-mono' style='min-width:54px;text-align:right;color:{col};'>{r['flow']:+.1f}%</span></div>")
    html = (f"<div class='wr-top'><b>Flow</b><span>capital rotation (21d relative)</span></div>"
            f"<div class='wr-lbl'>Where capital is rotating</div><div class='wr-rows'>{rows}</div>"
            f"<div class='wr-note' style='margin-top:8px;'>Rotation from 21d sector ETF momentum. Green = inflow leadership, red = outflow.</div>")
    st.markdown(CSS + html, unsafe_allow_html=True)


def bottleneck(d):
    bn = d.get("bottleneck", {}); m = bn.get("map", {})
    ck = {"uncrowded": "grn", "early": "grn", "mid": "amb", "semi-crowded": "amb", "crowded": "red"}
    nodes = m.get("chain", ["GPU compute", "Networking", "Power / grid", "Cooling / photonics"]); ncls = ["n-src", "n-src", "n-amb", "n-red"]
    chain = "<span class='wr-sub'>→</span>".join(f"<span class='wr-node {ncls[j] if j<len(ncls) else 'n-src'}'>{n}</span>" for j, n in enumerate(nodes))
    # AI infra roadmap timeline (attachment 1a)
    road = ""
    for r in m.get("roadmap", []):
        tk = " ".join(f"<span class='wr-node n-src wr-mono'>{x}</span>" for x in r.get("tickers", []))
        road += (f"<div class='wr-card'><div class='wr-ctop'><span class='wr-tkr wr-mono' style='font-size:13px;min-width:46px;'>{r['era']}</span>"
                 f"<span class='wr-sub'>{r['tech']}</span><div style='margin-left:auto;'>{_b(r['bottleneck'],'amb')}</div></div>"
                 f"<div style='margin-top:5px;'>{tk}</div></div>")
    # GPU-HBM scaling table (attachment 1b)
    gh = ("<div class='wr-rows'><div class='wr-row'><span class='wr-tk' style='min-width:118px;'>Architecture</span>"
          "<span class='wr-tk' style='flex:1;'>GPU / HBM</span><span class='wr-tk'>Bandwidth</span>"
          "<span class='wr-tk' style='min-width:72px;text-align:right;'>Total pwr</span></div>")
    for g in m.get("gpu_hbm", []):
        gh += (f"<div class='wr-row'><span class='wr-mono' style='min-width:118px;color:#e8edf2;'>{g['arch']}</span>"
               f"<span class='wr-sub' style='flex:1;'>{g['power']} · {g['hbm']}</span>"
               f"<span class='wr-mono' style='color:#9aa6b2;'>{g['bw']}</span>"
               f"<span class='wr-mono' style='min-width:72px;text-align:right;color:#e0bd86;'>{g['total_power']}</span></div>")
    gh += "</div>"
    # 12-layer supply chain (attachment 2)
    sc = "<div class='wr-rows'>"
    for l in m.get("supply_chain", []):
        chips = " ".join(f"<span class='wr-node n-src wr-mono'>{x}</span>" for x in l.get("tickers", []))
        sc += (f"<div class='wr-row'><span class='wr-mono' style='min-width:26px;color:#6b7682;'>L{l['n']}</span>"
               f"<span style='min-width:148px;color:#e8edf2;font-size:12px;'>{l['layer']}</span><span style='flex:1;'>{chips}</span></div>")
    sc += "</div>"
    pr, tr = m.get("power_rail", {}), m.get("thermal_rail", {})
    p_chips = " ".join(f"<span class='wr-node n-amb wr-mono'>{x}</span>" for x in pr.get("tickers", []))
    rails = (f"<div class='wr-card'><div class='wr-ctop'><span class='wr-tkr' style='font-size:13px;'>{pr.get('name','Power')}</span>"
             f"<span class='wr-sub'>{pr.get('sub','')}</span></div><div style='margin-top:5px;'>{p_chips}</div></div>"
             f"<div class='wr-card'><div class='wr-ctop'><span class='wr-tkr' style='font-size:13px;'>{tr.get('name','Thermal')}</span>"
             f"<span class='wr-sub'>{tr.get('sub','')}</span></div></div>")
    edges = bn.get("leadlag", [])
    ll = ("".join(f"<span class='wr-node n-grn wr-mono'>{e['leader']}→{e['follower']} · {e.get('lag','?')}d</span>" for e in edges)
          if edges else "<span class='wr-note'>lead-lag: needs ≥2yr multi-ticker history (Granger+TE+FDR) — populates on real data.</span>")
    disc = d.get("discovery", {})
    sq = "".join(f"<span class='wr-node n-amb wr-mono'>{x.get('ticker')}</span>" for x in (disc.get("squeeze") or [])) or "<span class='wr-note'>no squeeze candidates in universe.</span>"
    themes = ""
    for t in m.get("themes", []):
        themes += (f"<div class='wr-card'><div class='wr-ctop'><span class='wr-tkr' style='font-size:13px;'>{t['name']}</span>"
                   f"<div style='margin-left:auto;display:flex;gap:6px;'>{_b(t['bottleneck'],'inf')}{_b('crowding: '+t['crowding'], ck.get(t['crowding'],'amb'))}</div></div>"
                   f"<div class='wr-why'>{t['note']}</div></div>")
    sup = "<div class='wr-chain'>"
    for layer, names in m.get("suppliers", {}).items():
        chips = "".join(f"<span class='wr-node n-{'grn' if ck.get(it['tag'])=='grn' else 'red' if ck.get(it['tag'])=='red' else 'amb'}'><span class='wr-mono'>{it['t']}</span> {it['tag']}{(' · '+it['note']) if it.get('note') else ''}</span>" for it in names)
        sup += f"<div class='wr-tk' style='margin-bottom:6px;'>{layer}</div><div style='margin-bottom:10px;'>{chips}</div>"
    sup += "</div>"
    html = (f"<div class='wr-top'><b>Bottleneck &amp; moonshot</b><span>roadmap · supply chain · propagation</span></div>"
            f"<div class='wr-lbl'>Bottleneck migration</div><div class='wr-chain'><div style='display:flex;align-items:center;gap:6px;flex-wrap:wrap;'>{chain}</div>"
            f"<div class='wr-note' style='margin-top:8px;'>atoms &gt; bits — constraint moves downstream.</div></div>"
            f"<div class='wr-lbl'>AI infrastructure roadmap — what to research to outperform</div>{road}"
            f"<div class='wr-lbl'>Next-gen GPU-HBM scaling — power is the wall (2.2kW → 15.4kW/module)</div>{gh}"
            f"<div class='wr-lbl'>AI buildout supply chain — 12 layers (bedrock = critical minerals)</div>{sc}"
            f"<div class='wr-lbl'>Cross-cutting rails</div>{rails}"
            f"<div class='wr-lbl'>Discovered lead-lag</div><div class='wr-chain'>{ll}</div>"
            f"<div class='wr-lbl'>Squeeze / pre-conditioning watch</div><div class='wr-chain'>{sq}</div>"
            f"<div class='wr-lbl'>Secular themes</div>{themes}"
            f"<div class='wr-lbl'>Supplier graph — space (hidden layer)</div>{sup}"
            f"<div class='wr-note'>Roadmap + 12-layer encoded from your attachments. Engines: leadlag_discovery, supply_chain_graph_real, squeeze_scanner, bottleneck_discovery_v3, asymmetric_discovery.</div>")
    st.markdown(CSS + html, unsafe_allow_html=True)


def market_state(d):
    m = d["market"]
    tiles = (_tile("Breadth", f"{m['breadth']}%", "&gt;50d", "grn" if m['breadth'] >= 50 else "red")
             + _tile("Bullish", m["bull"], "formations", "grn") + _tile("Bearish", m["bear"], "formations", "red")
             + _tile("% bull", f"{m['pct_bull']}%", "of ranked", "sub"))
    rows = "".join(f"<div class='wr-row'><span class='wr-mono' style='font-weight:600;min-width:56px;color:#e8edf2;'>{r['ticker']}</span>"
                   f"<span class='wr-sub'>RS {r.get('rs63',0):+.0f}% · {r.get('formation','')}</span></div>" for r in d.get("leaders", []))
    html = (f"<div class='wr-top'><b>Market state</b><span>breadth &amp; leadership</span></div>"
            f"<div class='wr-grid'>{tiles}</div><div class='wr-lbl'>RS leadership</div><div class='wr-rows'>{rows}</div>")
    st.markdown(CSS + html, unsafe_allow_html=True)
