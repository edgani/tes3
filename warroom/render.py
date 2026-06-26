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
    cf = s.get("conf"); cfh = ""
    if isinstance(cf, dict) and cf.get("conviction"):
        cfh = f"<div class='wr-sub' style='margin-top:3px;'>TF confluence: {cf['conviction']} {cf.get('alignment_pct',0):.0f}% · {cf.get('hold','')}</div>"
    return (f"<div class='wr-card'><div class='wr-ctop'>{_b(s['_dir'], k)}"
            f"<span class='wr-tkr wr-mono'>{s['ticker']}</span><span class='wr-sub'>${s['px']}</span>"
            f"<span class='wr-score wr-mono'>{s['score']:.1f}</span></div>"
            f"<div class='wr-why'>{levels}. <span class='k'>RS</span> {s['rs']:+.0f}% · {s['form'].lower()}.</div>{cfh}{_decision(s)}{_pa_line(s)}{_struct_line(s)}{_idioflag(s)}{_ivflag(s)}{_mechflag(s)}{_timing(s)}</div>")


def _livenote(label, val):
    return f"<div class='wr-note'><span class='k'>{label} (live feed):</span> {_short(val, 130)}</div>" if val is not None else ""


def _ivflag(s):
    iv = s.get("intervention")
    if not isinstance(iv, dict):
        return ""
    col = {"high": "#e8a39b", "elevated": "#d8c08a", "note": "#9aa3ad", "low": "#9aa3ad"}.get(iv.get("level"), "#9aa3ad")
    bk = "red" if iv.get("level") == "high" else ("amb" if iv.get("level") == "elevated" else "gry")
    lbl = {"FX-intervention": "INTERVENTION", "FX-intervention-active": "INTERVENTION LIVE",
           "ARA-ARB": "ARA/ARB", "event": "EVENT"}.get(iv.get("kind", ""), "RISK")
    return f"<div class='wr-sub' style='margin-top:3px;'>{_b(lbl, bk)} <span style='color:{col};'>{iv.get('msg','')}</span></div>"


def _mechflag(s):
    m = s.get("mechanical")
    if not isinstance(m, dict):
        return ""
    bk = "amb" if m.get("level") == "elevated" else "gry"
    col = "#d8c08a" if m.get("level") == "elevated" else "#9aa3ad"
    return f"<div class='wr-sub' style='margin-top:3px;'>{_b('REBALANCE', bk)} <span style='color:{col};'>{m.get('msg','')}</span></div>"


def _coherence_panel(d):
    dr = d.get("drivers", {}) or {}
    summ = dr.get("summary", {}) or {}
    off, stq = summ.get("offside", []), summ.get("stretched", [])
    flips, dec = summ.get("regime_flips", []), summ.get("decoupled", [])
    if not off and not stq and not flips:
        if dr.get("assets"):
            tail = f" ({len(dec)} decoupled — drivers not explaining them)" if dec else ""
            return ("<div class='wr-lbl'>Cross-asset coherence</div><div class='wr-card' style='margin-bottom:16px;'>"
                    f"<span class='wr-why'>All tracked assets in line with their drivers — no cross-asset divergence right now.{tail}</span></div>")
        return ""
    rows = ""
    for r in flips:
        rows += f"<div class='wr-sub' style='margin-top:3px;'>{_b('REGIME','red')} <span style='color:#cf9a92;'>{r['note']}</span></div>"
    for r in off:
        rows += f"<div class='wr-sub' style='margin-top:3px;'>{_b('OFFSIDE','red')} <span style='color:#cf9a92;'>{r['note']}</span></div>"
    for r in stq:
        rows += f"<div class='wr-sub' style='margin-top:3px;'>{_b('STRETCHED','amb')} <span style='color:#d8c08a;'>{r['note']}</span></div>"
    if dec:
        rows += f"<div class='wr-note' style='margin-top:4px;'>Decoupled (low R², coherence N/A): {', '.join(r['display'] for r in dec[:6])}</div>"
    return ("<div class='wr-lbl'>Cross-asset coherence — who's offside vs their driver (who's lying)</div>"
            f"<div class='wr-card' style='margin-bottom:16px;border-left:3px solid #b5453b;'>{rows}</div>")


def _coherence_table(d):
    assets = (d.get("drivers", {}) or {}).get("assets") or []
    if not assets:
        return ""
    cmap = {"offside": "#cf6157", "stretched": "#c9a227", "in-line": "#5a8a6b", "decoupled": "#8b95a0"}
    rows = ""
    for r in assets:
        col = cmap.get(r["status"], "#9aa3ad")
        bstr = ", ".join(f"{c} \u03b2{b:+.2f}" for c, b in (r.get("betas") or {}).items())
        rows += (f"<div class='wr-row'><span class='wr-sub' style='min-width:150px;color:#cbd3da;'>{r['display']}</span>"
                 f"<span class='wr-mono' style='color:{col};min-width:150px;'>{r['std_resid']:+.1f}\u03c3 · R\u00b2 {r['r2']:.2f} · {r['status']}</span>"
                 f"<span class='wr-sub' style='color:#8b95a0;'>{bstr or r['driver_text']}</span></div>")
    return ("<div class='wr-lbl' style='margin-top:12px;'>Cross-asset driver coherence — empirical betas (residual vs factor model)</div>"
            f"<div class='wr-rows'>{rows}</div>")


def _policy_panel(d):
    p = d.get("policy") or {}
    if not p:
        return ""
    r = p.get("rate") or {}
    inf = p.get("inflation") or {}
    hp = p.get("hike_75_priced") or {}
    oil = p.get("oil") or {}
    rows = []
    if r:
        s1 = r.get("spread_1y_bps")
        rows.append(f"<span class='k'>Market-implied policy:</span> <b>{r.get('bias','')}</b> "
                    f"(1Y {('%+d' % s1 + 'bps vs funds') if s1 is not None else 'n/a'}, ~{r.get('implied_25s','?')}×25bps priced; funds {r.get('ffr_mid','?')}%)")
    if hp:
        rows.append(f"<span class='k'>Is +75bps priced?</span> <b style='color:{'#cf6157' if not hp.get('priced') else '#5a8a6b'};'>"
                    f"{'NO' if not hp.get('priced') else 'YES'}</b> — {hp.get('note','')}")
    if inf:
        rows.append(f"<span class='k'>Inflation signal (trimmed-mean):</span> {inf.get('trimmed_mean','?')}% "
                    f"(6m trend {('%+.2f' % inf['trend_6m']) if inf.get('trend_6m') is not None else 'n/a'}) — {inf.get('regime','')}")
    if oil:
        rows.append(f"<span class='k'>Oil read:</span> {oil.get('note','')}")
    if p.get("fed_lean"):
        rows.append(f"<span class='k'>Data-coherent Fed lean:</span> {p['fed_lean']}")
    body = "".join(f"<div class='wr-why' style='margin-top:3px;'>{x}</div>" for x in rows)
    bait = p.get("bait")
    bait_html = (f"<div class='wr-note' style='margin-top:6px;'>{_b('BAIT', 'red')} "
                 f"<span style='color:#cf9a92;'>{bait}</span></div>") if bait else ""
    return ("<div class='wr-lbl'>Policy &amp; narrative — rate-path vs the story (don't get baited)</div>"
            f"<div class='wr-card' style='margin-bottom:16px;border-left:3px solid #c9a227;'>{body}{bait_html}</div>")


def _macro_links(d):
    mac = d.get("macro", {}) or {}
    ind = mac.get("indicators") or []
    if not ind:
        return ""
    ks = mac.get("kshape")
    bl = mac.get("broken_links") or []
    kk = "red" if (ks and ks["score"] >= 50) else ("amb" if (ks and ks["score"] >= 25) else "grn")
    bl_s = " · ".join(f"{i['label']} ({i['value']})" for i in bl[:6]) if bl else "none — chain intact"
    head = (f"{_b('K-SHAPE ' + str(ks['score']) + '/100', kk)} <span class='k'>{ks['danger']} broken · "
            f"{ks['warning']} stressed / {ks['total']} tracked — {ks['label']}</span>") if ks else ""
    return ("<div class='wr-lbl'>Macro chain — broken-link scanner (recession / K-shape)</div>"
            "<div class='wr-card' style='margin-bottom:16px;border-left:3px solid #b5453b;'>"
            f"<div class='wr-why'>{head}</div>"
            f"<div class='wr-note' style='margin-top:4px;'><span style='color:#cf9a92;'>Broken links:</span> {bl_s}</div></div>")


def _macro_dashboard(d):
    ind = (d.get("macro", {}) or {}).get("indicators") or []
    if not ind:
        return ""
    by = {}
    for i in ind:
        by.setdefault(i["cluster"], []).append(i)
    cmap = {"ok": "#5a8a6b", "warning": "#c9a227", "danger": "#cf6157", "n/a": "#6b7280"}
    blocks = ""
    for c in ["Consumer", "Labor", "Housing", "Inflation", "Growth", "Credit", "Rates", "Liquidity"]:
        items = by.get(c)
        if not items:
            continue
        rows = "".join(f"<div class='wr-row'><span class='wr-sub' style='min-width:210px;color:#cbd3da;'>{i['label']}</span>"
                       f"<span class='wr-mono' style='color:{cmap.get(i['status'], '#9aa3ad')};font-weight:600;'>{i['value']}</span></div>"
                       for i in items)
        blocks += f"<div class='wr-lbl'>{c}</div><div class='wr-rows'>{rows}</div>"
    return "<div class='wr-lbl' style='margin-top:12px;'>Macro indicators — full relevant chain</div>" + blocks


def _theme_graph_panel(d):
    tg = d.get("theme_graph") or {}
    ranked = tg.get("ranked") or []
    if not ranked:
        return ""
    scol = {"hot": "#cf6157", "weakening": "#c97a45", "heating": "#c9a227", "early": "#6b9bd5", "cold": "#6b7682"}
    heat = "".join(
        f"<span class='wr-node wr-mono' style='border-color:{scol.get(x['state'],'#6b7682')};color:{scol.get(x['state'],'#9aa3ad')};'>"
        f"{x['theme']} {x['heat']} · {x['state']}</span>" for x in ranked)
    nd = tg.get("next_dots") or []
    chains = tg.get("chains") or []
    bridges = tg.get("bridges") or []
    arrow = ("<div class='wr-why' style='margin-top:6px;'><span class='k'>Where it's heading (capital tracing the graph):</span> "
             + " · ".join(f"{c}" for c in chains) + "</div>") if chains else ""
    dots = ("<div class='wr-note' style='margin-top:3px;'>Next dots (rotation targets): "
            + ", ".join(f"{x['from']}→<b>{x['to']}</b> ({x['to_state']})" for x in nd) + "</div>") if nd else ""
    br = ("<div class='wr-note' style='margin-top:3px;'>Bridge names (sit across themes — connected plays): "
          + ", ".join(f"{b['ticker']} [{'·'.join(t.split(' / ')[0].split(' ')[0] for t in b['themes'])}]" for b in bridges) + "</div>") if bridges else ""
    return ("<div class='wr-lbl'>Connect the dots — theme graph &amp; where the complex is heading</div>"
            f"<div class='wr-card' style='margin-bottom:16px;border-left:3px solid #8e6bd5;'>"
            f"<div style='display:flex;flex-wrap:wrap;gap:6px;'>{heat}</div>{arrow}{dots}{br}</div>")


def _beta_plays_panel(d):
    bp = d.get("beta_plays") or {}
    if not bp:
        return ""
    vcol = {"QUALIFIES": ("grn", "#7fa88f"), "MARGINAL": ("amb", "#d8c08a"),
            "REJECT": ("red", "#cf9a92"), "NO DATA": ("gry", "#8b95a0")}
    blocks = ""
    for theme, info in bp.items():
        body = ""
        for tlabel, rows in (info.get("tiers") or {}).items():
            body += f"<div class='wr-tk' style='margin:6px 0 2px;color:#cbd3da;'>{tlabel}</div>"
            for x in rows:
                bk, c = vcol.get(x["verdict"], ("gry", "#9aa3ad"))
                body += (f"<div class='wr-sub' style='margin-top:2px;'>{_b(x['verdict'], bk)} "
                         f"<span class='wr-mono' style='color:#e8edf2;'>{x['ticker']}</span> "
                         f"<span style='color:#9aa6b2;'>— {x['role']}</span> "
                         f"<span style='color:{c};'>· {x['why']}</span></div>")
        blocks += (f"<div class='wr-card' style='margin-bottom:10px;'><div class='wr-ctop'>"
                   f"<span class='wr-tkr' style='font-size:13px;'>{theme}</span>"
                   f"<span class='wr-sub' style='margin-left:auto;'>leader {info.get('leader')} +{info.get('leader_run_pct')}% / 60d</span></div>{body}</div>")
    return ("<div class='wr-lbl'>Beta-play finder — tiered derivatives of extended leaders (live viability-filtered)</div>" + blocks +
            "<div class='wr-note'>Tiers + roles are curated structure (verify fundamentals); the verdict is live & data-driven — "
            "real \u03b2 + R\u00b2 to the leader (not narrative) \u00b7 lagged = room \u00b7 liquid = tradeable. Walk-forward before sizing.</div>")


def _rotation_panel(d):
    r = d.get("rotation") or {}
    if not r:
        return ""
    def chips(items, color):
        return " · ".join(f"<span style='color:{color};'>{x['name']} ({x['mom']:+.1f})</span>" for x in items) or "<span class='wr-note'>none</span>"
    rin = r.get("rotating_in") or []
    lead = r.get("leaders") or []
    rout = r.get("rotating_out") or []
    fast = r.get("fast") or []
    cc = r.get("crypto_curve") or {}
    fast_str = ", ".join(f"{x['name']} {x['mom']:+.1f}" for x in fast)
    rows = (f"<div class='wr-why'><span class='k'>Rotating IN (early — money starting to flow):</span> {chips(rin, '#7fa88f')}</div>"
            f"<div class='wr-why' style='margin-top:3px;'><span class='k'>Leaders (crowd already here):</span> {chips(lead, '#9fb8a8')}</div>"
            f"<div class='wr-why' style='margin-top:3px;'><span class='k'>Rotating OUT (money leaving):</span> {chips(rout, '#cf9a92')}</div>"
            f"<div class='wr-note' style='margin-top:4px;'>Fastest movers (don't get left behind): {fast_str}</div>")
    if cc:
        rows += f"<div class='wr-why' style='margin-top:5px;'><span class='k'>Crypto risk-curve:</span> {cc.get('verdict','')}</div>"
    return ("<div class='wr-lbl'>Rotation map — where capital is flowing (adapt fast)</div>"
            f"<div class='wr-card' style='margin-bottom:16px;border-left:3px solid #5b9bd5;'>{rows}</div>")


def _struct_line(s):
    st = s.get("structure")
    if not isinstance(st, dict):
        return ""
    brk = st.get("broke")
    if brk == "down":
        col, bk = "#cf9a92", "red"
    elif brk == "up":
        col, bk = "#7fa88f", "grn"
    else:
        col, bk = "#c8ccd2", "gry"
    return f"<div class='wr-sub' style='margin-top:3px;'>{_b('STRUCT', bk)} <span style='color:{col};'>{st.get('pattern','')}</span></div>"


def _pa_line(s):
    pa = s.get("pa")
    if not isinstance(pa, dict):
        return ""
    vv, er = pa.get("vol_verdict", ""), pa.get("effort_result", "")
    if "distribution" in vv or "weak rally" in vv:
        col, bk = "#cf9a92", "red"
    elif "real demand" in vv or er == "absorption":
        col, bk = "#7fa88f", "grn"
    else:
        col, bk = "#c8ccd2", "gry"
    return f"<div class='wr-sub' style='margin-top:3px;'>{_b('TAPE', bk)} <span style='color:{col};'>{pa.get('summary','')}</span></div>"


def _idioflag(s):
    nc = s.get("name_coh")
    if not isinstance(nc, dict):
        return ""
    z = nc.get("idio_z", 0)
    if abs(z) < 1.5:
        return ""
    return (f"<div class='wr-sub' style='margin-top:3px;'>{_b('IDIO', 'amb')} "
            f"<span style='color:#d8c08a;'>moving {z:+.1f}\u03c3 vs market (\u03b2 {nc.get('beta_mkt')}, R\u00b2 {nc.get('r2')}) — name-specific catalyst, not just beta</span></div>")


def _decision(s):
    dec = s.get("decision")
    if not isinstance(dec, dict):
        return ""
    call = dec.get("call", "")
    ck = {"ACT": "grn", "ACT-SMALL": "grn", "WAIT": "amb", "AVOID": "red", "EXIT-WATCH": "amb"}.get(call, "gry")
    fa = ", ".join(l for l, _ in dec.get("for", [])[:5]) or "—"
    ag = ", ".join(l for l, _ in dec.get("against", [])[:5]) or "—"
    plan = dec.get("plan", "")
    return (f"<div class='wr-sub' style='margin-top:5px;'>{_b(call, ck)} <span class='k'>conf {dec.get('confidence','')}</span> · "
            f"<span style='color:#7fa88f;'>for: {fa}</span> · <span style='color:#cf9a92;'>against: {ag}</span></div>"
            + (f"<div class='wr-sub' style='margin-top:2px;'><span class='k'>Plan:</span> {plan}</div>" if plan else ""))


def _timing(s):
    t = s.get("timing")
    if not isinstance(t, dict):
        return ""
    fomo = t.get("anti_fomo", "")
    fcol = "#4ea36b" if "EARLY" in fomo else ("#d8c08a" if "ON-TIME" in fomo else "#e8a39b")
    hd = f" · ~{t['hold_days_est']}d to target" if t.get("hold_days_est") else ""
    return (f"<div class='wr-sub' style='margin-top:3px;'><span class='k'>Horizon:</span> {t.get('horizon','')}{hd} · "
            f"<span class='k'>phase:</span> {t.get('phase','')} · <span style='color:{fcol};font-weight:600;'>{fomo}</span></div>"
            f"<div class='wr-sub' style='margin-top:2px;'><span class='k'>Entry:</span> {t.get('entry_timing','')}</div>"
            f"<div class='wr-sub' style='margin-top:2px;'><span class='k'>Exit watch:</span> {t.get('exit_watch','')}</div>")


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
    cf = s.get("conf"); cfh = ""
    if isinstance(cf, dict) and cf.get("conviction"):
        cfh = f" <span class='k'>· TF:</span> {cf['conviction']} {cf.get('alignment_pct',0):.0f}%"
    return (f"<div class='wr-card'><div class='wr-ctop'>{_b(s['_dir'], k)}"
            f"<span class='wr-tkr wr-mono'>{s['ticker']}</span>"
            f"<span class='wr-badge b-gry'>{s.get('market','')}</span>{gate_badge}"
            f"<span class='wr-sub'>${s['px']}</span><span class='wr-score wr-mono'>{disp:.1f}</span></div>"
            f"<div class='wr-why'>{lvl}. <span class='k'>RS</span> {s['rs']:+.0f}% · accel {s.get('accel',0):+.0f}% · {s['form'].lower()}{fw}{szh}{gh}{cfh}.</div>{_decision(s)}{_pa_line(s)}{_struct_line(s)}{_idioflag(s)}{_ivflag(s)}{_mechflag(s)}{_timing(s)}</div>")


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


def _whatchanged(d):
    ch = d.get("whatchanged") or []
    prev = d.get("whatchanged_prev_ts")
    import datetime as _dt
    gap = "last run"
    if prev:
        try:
            mins = int((_dt.datetime.now() - _dt.datetime.fromisoformat(prev)).total_seconds() // 60)
            gap = f"{mins}m ago" if mins < 90 else (f"{mins//60}h ago" if mins < 1440 else f"{mins//1440}d ago")
        except Exception:
            pass
    sevb = {"high": _b("SHIFT", "red"), "med": _b("WATCH", "amb"), "low": _b("note", "gry")}
    txtcol = {"high": "#e8a39b", "med": "#d8c08a", "low": "#9aa3ad"}
    if prev is None:
        head, body, accent = "Real-time adaptation", "<span class='wr-note'>Baseline saved — regime shifts will surface here next session.</span>", "#2a3038"
    elif not ch:
        head, body, accent = "What changed", f"<span class='wr-note'>No regime change since last run ({gap}). Stance intact — nothing to adjust.</span>", "#2a3038"
    else:
        accent = "#c0504d" if any(s == "high" for s, _ in ch) else ("#c9a227" if any(s == "med" for s, _ in ch) else "#2a3038")
        rows = "".join(f"<div class='wr-row'>{sevb[s]}<span style='color:{txtcol[s]};'>{t}</span></div>" for s, t in ch[:8])
        head, body = f"What changed · vs {gap}", f"<div class='wr-rows'>{rows}</div>"
    return (f"<div class='wr-lbl' style='margin-top:0;'>{head}</div>"
            f"<div class='wr-card' style='margin-bottom:16px;border-left:3px solid {accent};'>{body}</div>")


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
    rt = reg.get("regime_transition"); cd = reg.get("change_detect"); _ba = d.get("batch_a", {})
    if rt is not None: bits.append(f"<span class='k'>Transition:</span> {_short(rt,38)}")
    if cd is not None: bits.append(f"<span class='k'>Change-pt:</span> {_short(cd,38)}")
    if _ba.get('keith') is not None: bits.append(f"<span class='k'>Keith:</span> {_short(_ba['keith'],38)}")
    if _ba.get('reflexivity') is not None: bits.append(f"<span class='k'>Reflexivity:</span> {_short(_ba['reflexivity'],38)}")
    if _ba.get('boombust') is not None: bits.append(f"<span class='k'>Boom/bust:</span> {_short(_ba['boombust'],38)}")
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
    ba = d.get("batch_a", {})
    nar = ba.get("narrative") or {}; scn = ba.get("scenarios") or {}; trn = ba.get("transmission") or {}; csc = ba.get("cascade") or {}
    narr_html = ""
    if isinstance(nar, dict) and (nar.get("headline") or nar.get("narrative")):
        _hl = (nar.get('headline', '') or '').encode('ascii', 'ignore').decode().strip()
        _nb = (nar.get('narrative', '') or '').encode('ascii', 'ignore').decode().strip()
        narr_html = (f"<div class='wr-lbl'>Macro narrative (engine)</div>"
                     f"<div class='wr-card' style='margin-bottom:16px;'><div class='wr-why'><b>{_hl}</b><br>{_nb}</div>"
                     + (f"<div class='wr-sub' style='margin-top:6px;'>Change-point: {_short(nar.get('change_point_alert'),80)}</div>" if nar.get('change_point_alert') else "")
                     + (f"<div class='wr-sub' style='margin-top:4px;'>Dominant scenario: <b>{scn.get('dominant_scenario','')}</b></div>" if isinstance(scn, dict) and scn.get('dominant_scenario') else "")
                     + "</div>")
    chain_html = ""
    if (isinstance(trn, dict) and trn) or (isinstance(csc, dict) and csc):
        chain_html = (f"<div class='wr-lbl'>Broken-chain / contagion — transmission + cascade</div>"
                      f"<div class='wr-card' style='margin-bottom:16px;'><div class='wr-why'>"
                      f"Transmission: {_short(trn,90)}. Cascade: {_short(csc,90)}.</div>"
                      f"<div class='wr-note' style='margin-top:4px;'>broken link in the economic chain → K-shape. Engines: transmission_engine, cascade_engine.</div></div>")
    mc = d.get("market_character")
    mc_html = ""
    if isinstance(mc, dict):
        mc_html = ("<div class='wr-lbl'>Tape read — what the move is actually doing (volume = truth, macro only confirms)</div>"
                   "<div class='wr-card' style='margin-bottom:16px;border-left:3px solid #6b7da8;'>"
                   f"<div class='wr-why'>SPY: {mc.get('summary','')}</div>"
                   f"<div class='wr-note' style='margin-top:3px;'>effort/result: {mc.get('effort_result','')} \u00b7 position-in-range {mc.get('pos_in_range','')} \u00b7 volume {mc.get('vol_ratio','')}x avg \u00b7 emotion {mc.get('emotion','')}/100</div></div>")
    mech = d.get("mechanical", {}) or {}
    _me, _vt = mech.get("month_end"), mech.get("vol_target")
    _mp = []
    if isinstance(_me, dict):
        _mp.append(f"<span class='k'>Month-end:</span> <b>{_me.get('direction','')}</b> — {_me.get('note','')}")
    if isinstance(_vt, dict):
        _mp.append(f"<span class='k'>Vol-target:</span> {_vt.get('note','')}")
    mech_html = ""
    if _mp:
        mech_html = ("<div class='wr-lbl'>Mechanical flows — scheduled / rule-driven (anticipatable)</div>"
                     "<div class='wr-card' style='margin-bottom:16px;border-left:3px solid #c9a227;'>"
                     + "".join(f"<div class='wr-why'>{p}</div>" for p in _mp) + "</div>")
    cm = d.get("crowd_market")
    crowd_html = ""
    if isinstance(cm, dict):
        _hk = "red" if cm["state"] == "euphoria" else ("grn" if cm["state"] == "capitulation" else "gry")
        crowd_html = ("<div class='wr-lbl'>Crowd positioning — where the herd is (front-run it)</div>"
                      f"<div class='wr-card' style='margin-bottom:16px;'>{_b(cm['state'].upper(), _hk)} "
                      f"<span class='wr-why'>heat {cm['heat']}/100 · {cm['pct_above50']}% above 50DMA · avg RSI {cm['avg_rsi']} — {cm['verdict']}</span></div>")
    html = (f"<div class='wr-top'><b>War room</b><span>Command center</span></div>"
            f"{_whatchanged(d)}"
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
            f"{mc_html}{_rotation_panel(d)}{_theme_graph_panel(d)}{narr_html}{chain_html}{_macro_links(d)}{_policy_panel(d)}{_coherence_panel(d)}{mech_html}{crowd_html}"
            f"<div class='wr-lbl'>What to do — highest conviction</div>{cards}"
            f"<div class='wr-lbl'>The edge — propagation</div><div class='wr-chain'>"
            f"<div style='display:flex;align-items:center;gap:6px;flex-wrap:wrap;'>{chain}</div>"
            f"<div class='wr-note' style='margin-top:8px;'>{chsrc}. 2nd-order tell: cooling / optical lag semis ~2–3 weeks — watch VRT/COHR after a SMH move.</div>"
            f"{xa_html}</div>"
            f"<div class='wr-note'><span class='k'>Live feeds:</span> {(', '.join(k for k,v in d.get('feeds_status',{}).items() if v)) or 'none — run build_feeds.py (+ FRED_API_KEY) on a networked machine'}</div>"
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
            f"{_livenote('On-chain', L.get('onchain'))}"
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
            f"{_livenote('COT positioning', L.get('cot'))}"
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
            f"{_livenote('Carry / rate-diff', L.get('carry'))}"
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
            f"{_livenote('Type-F foreign flow (Corr_F / Par_F)', L.get('typef'))}"
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
    _ba = d.get("batch_a", {}); _fr = _ba.get("frontrun") or {}
    _frn = (_fr.get("boarding_now") or [])[:6] if isinstance(_fr, dict) else []
    fr_html = "".join(f"<span class='wr-node n-grn wr-mono'>{(x.get('ticker') if isinstance(x, dict) else x)}</span>" for x in _frn) or "<span class='wr-note'>front-run: none boarding now.</span>"
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
            f"<div class='wr-lbl'>Front-run watch — boarding now (frontrun_engine)</div><div class='wr-chain'>{fr_html}</div>"
            f"<div class='wr-lbl'>Secular themes</div>{themes}"
            f"<div class='wr-lbl'>Supplier graph — space (hidden layer)</div>{sup}"
            f"{_beta_plays_panel(d)}"
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
            f"<div class='wr-grid'>{tiles}</div>" + _macro_dashboard(d) + _coherence_table(d) + f"<div class='wr-lbl'>RS leadership</div><div class='wr-rows'>{rows}</div>")
    st.markdown(CSS + html, unsafe_allow_html=True)


def _spark(vals, w=300, h=46):
    if not vals or len(vals) < 2:
        return ""
    lo, hi = min(vals), max(vals); rng = (hi - lo) or 1
    pts = " ".join(f"{i/(len(vals)-1)*w:.1f},{h-(v-lo)/rng*(h-4)-2:.1f}" for i, v in enumerate(vals))
    col = "#4ea36b" if vals[-1] >= vals[0] else "#c0504d"
    return f"<svg width='{w}' height='{h}' viewBox='0 0 {w} {h}'><polyline points='{pts}' fill='none' stroke='{col}' stroke-width='1.5'/></svg>"


def track_record(perf, opos, closed):
    if not perf or perf.get("total", 0) == 0:
        html = ("<div class='wr-top'><b>Track record</b><span>forward test</span></div>"
                "<div class='wr-note'>No signals logged yet. Each run logs that day's conviction point-in-time; "
                "outcomes accrue as you re-run over days. This is where provable P&L starts.</div>")
        st.markdown(CSS + html, unsafe_allow_html=True); return
    cn = perf.get("closed", 0)
    if cn == 0:
        verdict = _b(f"Building — {perf.get('open',0)} open · 0 closed", "amb"); stats = ""
    else:
        tr = perf.get("total_ret", 0)
        verdict = _b(f"Net {tr:+.1f}% · {perf.get('win_rate',0):.0f}% win · {perf.get('expectancy_R',0):+.2f}R exp", "grn" if tr >= 0 else "red")
        stats = ("<div class='wr-grid'>"
                 + _tile("Win rate", f"{perf['win_rate']:.0f}%", f"{cn} closed", "grn" if perf['win_rate'] >= 50 else "amb")
                 + _tile("Expectancy", f"{perf['expectancy_R']:+.2f}R", "per trade", "sub")
                 + _tile("Profit factor", f"{perf['profit_factor']}", "wins/losses", "sub")
                 + _tile("Total return", f"{perf['total_ret']:+.1f}%", "net of cost", "grn" if perf['total_ret'] >= 0 else "red")
                 + _tile("Sharpe", f"{perf['sharpe']}", "per-trade", "sub")
                 + _tile("Max DD", f"{perf['max_dd']:.1f}%", "peak-to-trough", "red")
                 + "</div>"
                 + f"<div class='wr-card' style='margin:8px 0 16px;'>{_spark(perf.get('equity', []))}<div class='wr-sub'>equity curve — closed trades, net of cost</div></div>")
    op = "".join(f"<div class='wr-row'><span class='wr-mono' style='font-weight:600;min-width:58px;color:#e8edf2;'>{r['ticker']}</span>"
                 f"{_b(r['direction'], _DIRK.get(r['direction'],'inf'))}<span class='wr-badge b-gry'>{r.get('market','')}</span>"
                 f"<span class='wr-sub'>entry {r['entry_px']:g} · stop {r['stop']:g} · target {r['target']:g} · since {r['gen_date']}</span></div>"
                 for r in (opos or [])[:12]) or "<span class='wr-note'>none open.</span>"
    cl = "".join(f"<div class='wr-row'><span class='wr-mono' style='font-weight:600;min-width:58px;color:#e8edf2;'>{r['ticker']}</span>"
                 f"{_b(r['status'], 'grn' if r['status']=='WIN' else 'red')}"
                 f"<span class='wr-mono' style='color:{'#4ea36b' if (r.get('ret_pct') or 0)>=0 else '#c0504d'};'>{(r.get('ret_pct') or 0)*100:+.1f}% ({(r.get('r_multiple') or 0):+.2f}R)</span>"
                 f"<span class='wr-sub'>{r.get('bars_held','?')}d · {r.get('close_date','')}</span></div>"
                 for r in (closed or [])[:15]) or "<span class='wr-note'>none closed yet — outcomes accrue as bars print.</span>"
    html = (f"<div class='wr-top'><b>Track record</b><span>forward test · point-in-time</span></div>"
            f"<div style='margin-bottom:14px;'>{verdict}</div>{stats}"
            f"<div class='wr-lbl'>Open positions ({perf.get('open',0)})</div><div class='wr-rows' style='margin-bottom:14px;'>{op}</div>"
            f"<div class='wr-lbl'>Closed trades ({cn})</div><div class='wr-rows'>{cl}</div>"
            f"<div class='wr-note'>Forward test on free data. Logged at generation (point-in-time), resolved only on later bars (no look-ahead), net of 10bps round-trip. A credible record needs weeks of daily runs — but this is real, provable P&L, not a backtest.</div>")
    st.markdown(CSS + html, unsafe_allow_html=True)


def risk_health(d):
    r = d.get("risk", {}) or {}
    diag = d.get("diagnostics", {}) or {}
    asof = d.get("data_asof", {}) or {}
    fs = d.get("feeds_status", {}) or {}
    lim = r.get("limits", {}) or {}
    if r.get("n", 0) == 0:
        risk_html = "<div class='wr-note'>No sized conviction positions to risk-assess this run.</div>"; verdict = _b("no book", "gry")
    else:
        br = r.get("breaches", [])
        verdict = _b(f"{len(br)} limit breach" + ("es" if len(br) != 1 else ""), "red") if br else _b("within all risk limits", "grn")
        grid = ("<div class='wr-grid'>"
                + _tile("Gross / Net", f"{r['gross_bps']} / {r['net_bps']:+d}", f"bps · {r['n_long']}L {r['n_short']}S", "sub")
                + _tile("Portfolio heat", f"{r['heat_pct']:.1f}%", "equity at risk if all stops hit", "red" if r['heat_pct'] > lim.get('heat_pct', 99) else "grn")
                + _tile("1d VaR 95%", (f"{r['var_pct']:.1f}%" if r.get('var_pct') is not None else "—"), (f"CVaR {r['cvar_pct']:.1f}%" if r.get('cvar_pct') is not None else "hist-sim"), "red" if (r.get('var_pct') or 0) > lim.get('var_pct', 99) else "sub")
                + _tile("Avg correlation", (f"{r['avg_corr']:.2f}" if r.get('avg_corr') is not None else "—"), "book diversification", "red" if (r.get('avg_corr') or 0) > lim.get('avg_corr', 9) else "grn")
                + _tile("Max name", f"{r['max_name_bps']}", f"bps · top3 {r['top3_bps']}", "amb" if r['max_name_bps'] > lim.get('name_bps', 9999) else "sub")
                + "</div>")
        bh = ("".join(f"<div class='wr-row'>{_b('BREACH','red')}<span style='color:#e8a39b;'>{b}</span></div>" for b in br)) if br else "<span class='wr-note'>exposure, heat, correlation and VaR all within limits.</span>"
        risk_html = grid + f"<div class='wr-lbl'>Limit checks</div><div class='wr-rows'>{bh}</div>"
    nf = diag.get("failures", 0)
    hverd = _b("all engines clean", "grn") if nf == 0 else _b(f"{nf} engine error(s)", "amb")
    stale = asof.get("stale_days")
    fresh = f"data as-of {asof.get('date')} ({stale}d old)" if asof.get('date') else "data freshness unknown"
    fresh_b = _b("stale data", "red") if (stale or 0) > 4 else _b("data current", "grn")
    feeds_live = [k for k, v in fs.items() if v]
    feed_line = "live feeds: " + (", ".join(feeds_live) if feeds_live else "none (proxy mode — run build_feeds.py)")
    byeng = diag.get("by_engine", {})
    byeng_line = " · ".join(f"{k}×{v}" for k, v in byeng.items()) if byeng else ""
    errs = "".join(f"<div class='wr-row'><span class='wr-mono' style='color:#d8c08a;min-width:150px;'>{e['engine']}</span><span class='wr-sub'>{e['error']}</span></div>" for e in diag.get("samples", [])) or "<span class='wr-note'>no engine exceptions this run.</span>"
    html = (f"<div class='wr-top'><b>Risk & Health</b><span>portfolio risk · observability</span></div>"
            f"<div class='wr-lbl' style='margin-top:0;'>Portfolio risk — conviction book</div>"
            f"<div style='margin-bottom:10px;'>{verdict}</div>{risk_html}"
            f"<div class='wr-lbl'>System health</div><div style='margin-bottom:8px;'>{hverd} &nbsp; {fresh_b}</div>"
            f"<div class='wr-note'>{fresh} · {feed_line}</div>"
            + (f"<div class='wr-note'>failing engines: {byeng_line}</div>" if byeng_line else "")
            + f"<div class='wr-lbl'>Engine exceptions (no longer silent)</div><div class='wr-rows'>{errs}</div>"
            f"<div class='wr-note'>Risk limits are guidance, not advice. Engine errors here would otherwise be swallowed — if a panel elsewhere is unexpectedly blank, check here.</div>")
    st.markdown(CSS + html, unsafe_allow_html=True)
