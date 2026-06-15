# War Room — self-contained

Design = the original mockups. Ranking/logic = mine. From the old zip ONLY quant formulas were
re-implemented clean (Hedgeye RV risk range, GIP/quad acceleration, value-based LPM). No old UI,
no old ticker-filter pipeline, no heavy deps.

## Run
```bash
pip install -r requirements.txt
streamlit run app.py
```
yfinance live; synthetic fallback so it always renders (flagged in the header note).

## Files (all mine / clean)
- app.py ............ Streamlit, mockup design, 6 tabs
- data.py .......... yfinance + synthetic loader
- regime.py ........ GIP/quad via cross-asset acceleration (price-implied)
- risk_range.py .... Hedgeye RV risk range  width = basis · σ_daily · √n  (TRADE/TREND/TAIL)
- ranking.py ....... competitive conviction (RS / momentum / formation / crowding / accumulation)
- lpm.py ........... value-based Liquidity Pressure Model (fixed) + calibrate_lpm.py
- funding_stress.py  EFFR/SOFR/RRP/reserves funding-stress score (FRED; deviation-based)
- secular_map.py ... curated secular/supplier map from your attachments

## Tabs
Command Center · Alpha Center · US Stocks · IHSG Bandar · Market State · Bottleneck & Moonshot

## Honest gaps (flagged, not faked)
Dealer gamma (options feed), IDX foreign Type-F, crypto on-chain, FX/FRED rates — next once feeds wired.
