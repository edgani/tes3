"""
app.py — War Room (self-contained). Design = the original mockups. Logic/ranking = MINE.
From the old zip ONLY quant FORMULAS/METRICS were re-implemented clean (Hedgeye Risk Range,
GIP/quad acceleration, value-based LPM) — NO old UI, NO old ticker-filter/ranking pipeline.

Run:  pip install -r requirements.txt  &&  streamlit run app.py
Deps: streamlit, pandas, numpy, yfinance (yfinance live; synthetic fallback so it always renders).
Honesty: factor/RS screen + regime, not a return forecast. Feed-gated lenses (gamma, foreign Type-F,
on-chain, FRED rates) are flagged, not faked.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
import streamlit as st

import data as D
import regime as R
import ranking as RK
import secular_map as BN
from lpm import lpm_features, money_flow


# ----------------------------------------------------------------- compute (testable)
def _cmf(df, n=20):
    h = pd.to_numeric(df["High"], errors="coerce"); l = pd.to_numeric(df["Low"], errors="coerce")
    c = pd.to_numeric(df["Close"], errors="coerce"); v = pd.to_numeric(df["Volume"], errors="coerce").fillna(0)
    rng = (h - l).replace(0, np.nan)
    clv = (((c - l) - (h - c)) / rng).clip(-1, 1).fillna(0)
    s = (clv * v).rolling(n).sum() / v.rolling(n).sum().replace(0, np.nan)
    val = float(s.iloc[-1]) if len(s.dropna()) else 0.0
    return val, ("buying" if val > 0.05 else "selling" if val < -0.05 else "neutral")


def compute(us_prices, idx_prices):
    out = {}
    reg = R.assess(us_prices, D.US_UNIVERSE)
    out["regime"] = reg
    rows = RK.compute_rows(us_prices, reg, D.US_UNIVERSE)
    out["rows"] = rows
    out["scanned"] = len([t for t in D.US_UNIVERSE if t not in RK.MACRO_ONLY])
    out["conviction"] = rows[:4]
    out["watchlist"] = rows[4:12]

    # market state (mine)
    bull = sum(1 for r in rows if r["formation"] == "BULLISH")
    bear = sum(1 for r in rows if r["formation"] == "BEARISH")
    n = len(rows) or 1
    out["market"] = {"bull": bull, "bear": bear, "n": len(rows),
                     "pct_bull": round(100 * bull / n), "breadth": reg["breadth"]}
    out["leaders"] = sorted(rows, key=lambda r: r["rs63"], reverse=True)[:8]

    # US lens (honest price/RS metrics; gamma needs options feed)
    vols = [r for r in rows]
    out["us_lens"] = {
        "trend_bull": f"{round(100*bull/n)}%",
        "rs_leaders": sum(1 for r in rows if r["rs63"] > 0),
        "picks": len(rows),
    }

    # IDX bandar — value-based LPM (my lpm.py) + self-computed CMF + AD direction
    idx = []
    for t, df in (idx_prices or {}).items():
        try:
            lf = lpm_features(df, scaling="value_typical", span=20)
            adl = money_flow(df, "value_typical").cumsum()
            rising = bool(adl.iloc[-1] > adl.iloc[-min(21, len(adl))])
            cmf_val, cmf_state = _cmf(df)
            idx.append({"ticker": t, "state": lf.get("state"), "lpm": lf.get("lpm"),
                        "adl_rising": rising, "cmf": round(cmf_val, 3), "cmf_state": cmf_state})
        except Exception:
            continue
    out["idx"] = idx
    out["bn"] = BN.map()
    return out


# ----------------------------------------------------------------- design system (faithful to mockups)
CSS = """
<style>
#MainMenu, header[data-testid="stHeader"], footer {visibility:hidden;}
.stApp {background:#0d1015;}
.block-container {padding-top:1.1rem; padding-bottom:2rem; max-width:1080px;}
html, body, [class*="css"] {font-family:-apple-system,'Segoe UI',Roboto,Helvetica,sans-serif;}
.stTabs [data-baseweb="tab-list"]{gap:2px; border-bottom:0.5px solid #232a32;}
.stTabs [data-baseweb="tab"]{color:#6b7682; font-size:13px; padding:6px 12px;}
.stTabs [aria-selected="true"]{color:#e8edf2;}
.wr-mono{font-family:'SF Mono','Roboto Mono',ui-monospace,monospace;}
.wr-top{display:flex;align-items:center;gap:8px;margin-bottom:10px;}
.wr-top b{font-size:14px;font-weight:600;color:#e8edf2;} .wr-top span{font-size:12px;color:#6b7682;}
.wr-pills{display:flex;gap:6px;margin-bottom:16px;flex-wrap:wrap;}
.wr-pill{font-size:12px;padding:4px 12px;border-radius:8px;}
.wr-pill.on{background:#12161d;border:0.5px solid #2a3038;color:#e8edf2;}
.wr-pill.off{background:transparent;border:0.5px solid #232a32;color:#6b7682;}
.wr-hero{border:0.5px solid #2a3038;border-radius:14px;padding:16px 20px;background:#12161d;margin-bottom:16px;}
.wr-herotop{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;flex-wrap:wrap;}
.wr-sub{font-size:13px;color:#9aa6b2;} .wr-tk{font-size:11px;color:#6b7682;}
.wr-quad{font-size:26px;font-weight:600;color:#e8edf2;line-height:1;}
.wr-lbl{font-size:11px;color:#6b7682;margin:0 0 7px 2px;}
.wr-badge{font-size:11px;font-weight:600;padding:4px 11px;border-radius:8px;white-space:nowrap;}
.b-grn{color:#9adcc0;background:#15332a;} .b-red{color:#f0a0a0;background:#3a1f22;}
.b-amb{color:#e7c389;background:#33280f;} .b-inf{color:#9cc3e7;background:#13283a;}
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
.wr-why{font-size:12px;color:#9aa6b2;line-height:1.55;} .wr-why .k{color:#6b7682;}
.wr-rows{background:#12161d;border:0.5px solid #232a32;border-radius:8px;overflow:hidden;}
.wr-row{display:flex;align-items:center;gap:10px;padding:9px 12px;border-bottom:0.5px solid #1b212a;font-size:12px;}
.wr-row:last-child{border-bottom:none;}
.wr-chain{background:#161b22;border-radius:8px;padding:12px;margin-bottom:16px;}
.wr-node{font-size:12px;padding:5px 11px;border-radius:8px;background:#12161d;margin-right:2px;}
.n-src{border:0.5px solid #2a3038;color:#e8edf2;} .n-red{border:0.5px solid #5a2a2e;color:#e89a9a;}
.n-amb{border:0.5px solid #5a4520;color:#e0bd86;} .n-grn{border:0.5px solid #234b3a;color:#8fd3b8;}
.wr-note{color:#6b7682;font-size:11px;}
</style>
"""

_DIRK = {"Long": "grn", "Short": "red", "Watch": "amb"}
def _badge(t, k): return f"<span class='wr-badge b-{k}'>{t}</span>"
def _tile(label, value, chip="", ck="sub"):
    c = f"<div class='wr-chip c-{ck}'>{chip}</div>" if chip else ""
    return f"<div class='wr-tile'><div class='wr-tk'>{label}</div><div class='wr-tv wr-mono'>{value}</div>{c}</div>"

def _causal(r):
    rs = r.get("rs63", 0); acc = r.get("accumulation", 0); f = r.get("formation", "").lower()
    inval = ("loses TRADE low / RS turns negative" if r["_dir"] == "Long"
             else "reclaims TRADE high / RS turns positive" if r["_dir"] == "Short"
             else "needs formation + RS confirmation")
    return (f"<span class='k'>Why:</span> RS {'+' if rs>=0 else ''}{rs:.0f}% vs SPY, {f} formation, "
            f"accumulation {acc}. <span class='k'>Invalidates:</span> {inval}.")

def _dmax(d):
    s = [r.get("score", 0) for r in d.get("conviction", []) + d.get("watchlist", [])]
    return max(s) if s else 1.0

def _conv_card(r, dmax, extra=""):
    disp = 10 * r.get("score", 0) / dmax if dmax else 0
    rr = f"RR {r.get('lrr',0):.1f}–{r.get('trr',0):.1f}"
    return (f"<div class='wr-card'><div class='wr-ctop'>{_badge(r['_dir'], _DIRK.get(r['_dir'],'inf'))}"
            f"<span class='wr-tkr wr-mono'>{r['ticker']}</span><span class='wr-sub'>{rr}</span>"
            f"<span class='wr-score wr-mono'>{disp:.1f}</span></div><div class='wr-why'>{_causal(r)}</div>{extra}</div>")


# ----------------------------------------------------------------- renderers
def render_command_center(d, source):
    reg = d["regime"]; g, i, b = reg["growth_z"], reg["infl_z"], reg["breadth"]
    conf = int(min(95, 50 + abs(g) * 1.2 + abs(i) * 1.0))
    pcol = "#e07a5f" if reg["defensive"] else "#1d9e75"
    flip = ("Flips risk-on if → growth accel turns positive + breadth thrust &gt;55%" if reg["defensive"]
            else "Flips defensive if → growth accel rolls over + breadth &lt;45%")
    pills = "".join(f"<span class='wr-pill {'on' if m=='US equities' else 'off'}'>{m}</span>"
                    for m in ["US equities", "Crypto", "IHSG", "FX", "Commodities"])
    drivers = (_tile("Growth accel", f"{g:+.1f}", ("↓ Slowing" if g < 0 else "↑ Rising"), "red" if g < 0 else "grn")
               + _tile("Inflation accel", f"{i:+.1f}", ("↑ Rising" if i > 0 else "↓ Easing"), "amb" if i > 0 else "grn")
               + _tile("Breadth", f"{b}%", ("↓ &lt;50d weak" if b < 50 else "↑ healthy"), "red" if b < 50 else "grn")
               + _tile("Bullish", f"{d['market']['bull']}", "formations", "grn")
               + _tile("Bearish", f"{d['market']['bear']}", "formations", "red")
               + _tile("Posture", reg["posture"][:4], reg["posture"], "red" if reg["defensive"] else "grn"))
    dmax = _dmax(d)
    cards = "".join(_conv_card(r, dmax) for r in d["conviction"])
    html = (f"<div class='wr-top'><b>War room</b><span>Command center</span></div>"
            f"<div class='wr-pills'>{pills}</div>"
            f"<div class='wr-hero'><div class='wr-herotop'>"
            f"<div><div class='wr-tk'>Regime — US equities</div>"
            f"<div style='display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;'>"
            f"<span class='wr-quad'>{reg['quad']}</span><span class='wr-sub'>{reg['quad_desc']}</span></div></div>"
            f"{_badge('Posture · ' + reg['posture'], 'red' if reg['defensive'] else 'grn')}</div>"
            f"<div style='display:flex;gap:18px;flex-wrap:wrap;align-items:center;margin-top:14px;'>"
            f"<div style='flex:1;min-width:170px;'><div class='wr-tk'>Conviction · {conf}%</div>"
            f"<div class='wr-bar'><div class='wr-barfill' style='width:{conf}%;background:{pcol};'></div></div></div>"
            f"<div style='flex:2;min-width:210px;' class='wr-sub'>{flip}</div></div>"
            f"<div style='margin-top:12px;padding-top:11px;border-top:0.5px solid #1b212a;' class='wr-sub'>"
            f"Δ: {reg['posture']} — growth accel {g:+.1f}, inflation accel {i:+.1f}, breadth {b}%</div></div>"
            f"<div class='wr-lbl'>Why — regime drivers (GIP acceleration)</div><div class='wr-grid'>{drivers}</div>"
            f"<div class='wr-lbl'>What to do — highest conviction</div>{cards}"
            f"<div class='wr-note'>Data: {source} · risk range = Hedgeye RV-based (σ×√n×basis) · GIP from price proxies · not advice.</div>")
    st.markdown(CSS + html, unsafe_allow_html=True)


def render_alpha(d):
    dmax = _dmax(d)
    funnel = (_tile("Scanned", d["scanned"]) + _tile("Ranked", len(d["rows"]))
              + _tile("Conviction", len(d["conviction"])) + _tile("Watchlist", len(d["watchlist"])))
    cards = "".join(_conv_card(r, dmax) for r in d["conviction"])
    rows = ""
    for r in d["watchlist"]:
        disp = 10 * r.get("score", 0) / dmax if dmax else 0
        rows += (f"<div class='wr-row'><span class='wr-mono' style='font-weight:600;min-width:56px;color:#e8edf2;'>{r['ticker']}</span>"
                 f"{_badge(r['_dir'], _DIRK.get(r['_dir'],'inf'))}<span class='wr-mono' style='color:#9aa6b2;'>{disp:.1f}</span>"
                 f"<span style='color:#9aa6b2;'>RS {r.get('rs63',0):+.0f}% · accum {r.get('accumulation',0)}</span></div>")
    html = (f"<div class='wr-top'><b>Alpha center</b><span>competitive ranking · my engine</span></div>"
            f"<div class='wr-grid'>{funnel}</div>"
            f"<div class='wr-lbl'>Highest conviction</div>{cards}"
            f"<div class='wr-lbl'>Watchlist</div><div class='wr-rows'>{rows}</div>")
    st.markdown(CSS + html, unsafe_allow_html=True)


def render_us(d):
    u = d["us_lens"]
    tiles = (_tile("Trend bull", u["trend_bull"], "of US picks", "grn")
             + _tile("RS leaders", u["rs_leaders"], "vs SPY", "grn")
             + _tile("Picks", u["picks"], "ranked", "sub"))
    longs = [r for r in d["conviction"] + d["watchlist"] if r["_dir"] in ("Long", "Short")][:4]
    dmax = _dmax(d)
    cards = "".join(_conv_card(r, dmax) for r in longs)
    html = (f"<div class='wr-top'><b>US stocks</b><span>price / RS lens</span></div>"
            f"<div class='wr-lbl'>US internals</div><div class='wr-grid'>{tiles}</div>"
            f"<div class='wr-lbl'>Conviction · US</div>{cards}"
            f"<div class='wr-note'>Price/RS + Hedgeye risk range. Dealer gamma/vanna/charm needs an options-chain feed (not faked).</div>")
    st.markdown(CSS + html, unsafe_allow_html=True)


def render_idx(d):
    rows = ""
    for r in d["idx"]:
        stt = r.get("state", "n/a"); k = {"accumulation": "grn", "distribution": "red"}.get(stt, "amb")
        rising = "A/D ↑" if r.get("adl_rising") else "A/D ↓"
        rows += (f"<div class='wr-row'><span class='wr-mono' style='font-weight:600;min-width:78px;color:#e8edf2;'>{r['ticker']}</span>"
                 f"{_badge(stt, k)}<span class='wr-sub'>{rising} · CMF {r.get('cmf',0):.2f} ({r.get('cmf_state','—')})</span></div>")
    body = f"<div class='wr-rows'>{rows}</div>" if rows else "<div class='wr-note'>No IDX data.</div>"
    html = (f"<div class='wr-top'><b>IHSG</b><span>BandarMetrics · value-based LPM (fixed)</span></div>"
            f"<div class='wr-lbl'>Accumulation / distribution per name</div>{body}"
            f"<div class='wr-note' style='margin-top:8px;'>LPM = value-based CLV×Vol×Price (calibrate_lpm.py locks it to BandarMetrics). "
            f"Foreign Flow / Corr_F / Par_F need IDX broker Type-F data.</div>")
    st.markdown(CSS + html, unsafe_allow_html=True)


def render_market_state(d):
    m = d["market"]
    tiles = (_tile("Breadth", f"{m['breadth']}%", "&gt;50d", "grn" if m['breadth'] >= 50 else "red")
             + _tile("Bullish", m["bull"], "formations", "grn") + _tile("Bearish", m["bear"], "formations", "red")
             + _tile("% bull", f"{m['pct_bull']}%", "of ranked", "sub"))
    rows = ""
    for r in d["leaders"]:
        rows += (f"<div class='wr-row'><span class='wr-mono' style='font-weight:600;min-width:56px;color:#e8edf2;'>{r['ticker']}</span>"
                 f"<span class='wr-sub'>RS {r.get('rs63',0):+.0f}% · {r.get('formation','')}</span></div>")
    html = (f"<div class='wr-top'><b>Market state</b><span>breadth &amp; leadership</span></div>"
            f"<div class='wr-grid'>{tiles}</div><div class='wr-lbl'>RS leadership</div><div class='wr-rows'>{rows}</div>")
    st.markdown(CSS + html, unsafe_allow_html=True)


def render_bottleneck(d):
    bn = d["bn"]; nodes = bn["chain"]
    ncls = ["n-src", "n-src", "n-amb", "n-red"]
    chain = "<div class='wr-chain'><div style='display:flex;align-items:center;gap:6px;flex-wrap:wrap;font-size:12px;'>"
    for j, n in enumerate(nodes):
        chain += f"<span class='wr-node {ncls[j] if j < len(ncls) else 'n-src'}'>{n}</span>"
        if j < len(nodes) - 1: chain += "<span class='wr-sub'>→</span>"
    chain += ("</div><div class='wr-note' style='margin-top:8px;'>Bottleneck migration (Citrini / Aschenbrenner): "
              "constraint moves downstream — atoms &gt; bits.</div></div>")
    themes = ""
    ck = {"uncrowded": "grn", "early": "grn", "mid": "amb", "semi-crowded": "amb", "crowded": "red"}
    for t in bn["themes"]:
        themes += (f"<div class='wr-card'><div class='wr-ctop'><span class='wr-tkr' style='font-size:13px;'>{t['name']}</span>"
                   f"<div style='margin-left:auto;display:flex;gap:6px;'>{_badge(t['bottleneck'],'inf')}"
                   f"{_badge('crowding: '+t['crowding'], ck.get(t['crowding'],'amb'))}</div></div>"
                   f"<div class='wr-why'>{t['note']}</div></div>")
    sup = "<div class='wr-chain'>"
    for layer, names in bn["suppliers"].items():
        chips = ""
        for it in names:
            kk = ck.get(it["tag"], "amb")
            note = f" · {it['note']}" if it.get("note") else ""
            chips += f"<span class='wr-node n-{ 'grn' if kk=='grn' else 'red' if kk=='red' else 'amb'}' style='margin:0 6px 6px 0;display:inline-block;'><span class='wr-mono'>{it['t']}</span> {it['tag']}{note}</span>"
        sup += f"<div class='wr-tk' style='margin-bottom:6px;'>{layer}</div><div style='margin-bottom:10px;'>{chips}</div>"
    sup += "</div>"
    html = (f"<div class='wr-top'><b>Bottleneck &amp; moonshot</b><span>secular · supplier graph</span></div>"
            f"<div class='wr-lbl'>Bottleneck migration</div>{chain}"
            f"<div class='wr-lbl'>Secular themes</div>{themes}"
            f"<div class='wr-lbl'>Supplier graph — space (from your docs)</div>{sup}"
            f"<div class='wr-note'>Curated thesis map (Citrini / Aschenbrenner / Serenity / SpaceX-suppliers). Hidden layer feeds Alpha Center watchlist.</div>")
    st.markdown(CSS + html, unsafe_allow_html=True)


# ----------------------------------------------------------------- app
def main():
    st.set_page_config(page_title="War Room", layout="wide", initial_sidebar_state="collapsed")
    with st.spinner("Loading prices + running engines…"):
        us, source = D.load(D.US_UNIVERSE)
        idx, _ = D.load(D.IDX_UNIVERSE)
        d = compute(us, idx)
    tabs = st.tabs(["Command Center", "Alpha Center", "US Stocks", "IHSG Bandar", "Market State", "Bottleneck & Moonshot"])
    with tabs[0]: render_command_center(d, source)
    with tabs[1]: render_alpha(d)
    with tabs[2]: render_us(d)
    with tabs[3]: render_idx(d)
    with tabs[4]: render_market_state(d)
    with tabs[5]: render_bottleneck(d)


if __name__ == "__main__":
    main()
