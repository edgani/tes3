# War Room

Verdict-first cross-asset intelligence. Design + ranking = mine; formula engines = your zip
(Hedgeye GIP structural+monthly, Hedgeye Risk Range, GEX/greeks, methodology Citrini/Yves/Soros/
Coatue/Druckenmiller, lead-lag Granger+TE, supply-chain-graph, value-based LPM). No old UI, no old
ticker-filter pipeline.

## Run
    pip install -r requirements.txt
    python build_cache.py          # optional: bulk price cache (complete + fast). Re-run nightly.
    streamlit run app.py

yfinance live; synthetic fallback so it always renders. FRED via fredgraph (no API key).

## Structure
    app.py                 entry (10 tabs)
    build_cache.py         bulk/incremental price cache  ← complete-but-light data
    warroom/               MY code
      data.py  fred.py  compute.py  render.py  lpm.py  funding_stress.py  secular_map.py  calibrate_lpm.py
    engines/               zip formula engines (kept)
    gcfis/                 zip gcfis engines (kept)
    data/                  JSON assets (bottleneck_reference, ihsg_conglomerates, …)

## Tabs
Command Center (dual-quad: Structural + Monthly + divergence, 5-part causal, propagation) ·
Alpha Center · US Stocks (gamma) · Crypto · Commodities · FX · IHSG (LPM) · Flow (rotation) ·
Bottleneck (lead-lag + supplier graph) · Market State

## Honest gaps (flagged, not faked)
Global (50-country) quad not in this zip. Real signed GEX/vanna/charm, IDX foreign Type-F, crypto
on-chain, FX/FRED rates, futures curve — need feeds; engines are present and wired to activate.
