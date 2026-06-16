"""
War Room — entry point.  Run:  streamlit run app.py

Architecture:
  • Design + ranking  = mine (warroom/render.py, warroom/compute.py) — verdict-first mockup.
  • Formula engines   = your zip (engines/, gcfis/) called as providers: Hedgeye GIP (structural+
    monthly), Hedgeye Risk Range, GEX/greeks, methodology (Citrini/Yves/Soros/Coatue/Druck via
    thought_process), lead-lag (Granger+TE) + supply-chain-graph for propagation, value-based LPM.
  • NO old UI, NO old ticker-filter/elimination pipeline.
Data: parquet cache (build_cache.py) → yfinance live → synthetic fallback. FRED via fredgraph (no key).
"""
import streamlit as st
from warroom import data as D, compute as C, render as R, fred as F


def main():
    st.set_page_config(page_title="War Room", layout="wide", initial_sidebar_state="collapsed")
    with st.spinner("Loading prices + running engines…"):
        us, source = D.load(D.US_UNIVERSE)
        idx, _ = D.load(D.IDX_UNIVERSE)
        cp, _ = D.load(D.CRYPTO_UNIVERSE)
        fxp, _ = D.load(D.FX_UNIVERSE)
        commo, _ = D.load(D.COMMO_UNIVERSE)
        fred = F.fetch()  # empty offline -> GIP/funding degrade to proxy
        d = C.run(us, idx, cp, fxp, commo, fred)
    tabs = st.tabs(["Command Center", "Alpha Center", "US Stocks", "Crypto", "Commodities",
                    "FX", "IHSG", "Flow", "Bottleneck", "Market State"])
    with tabs[0]: R.command_center(d, source)
    with tabs[1]: R.alpha(d)
    with tabs[2]: R.us_stocks(d)
    with tabs[3]: R.crypto(d)
    with tabs[4]: R.commodities(d)
    with tabs[5]: R.fx(d)
    with tabs[6]: R.ihsg(d)
    with tabs[7]: R.flow(d)
    with tabs[8]: R.bottleneck(d)
    with tabs[9]: R.market_state(d)


if __name__ == "__main__":
    main()
