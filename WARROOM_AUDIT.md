# WAR ROOM — DEEP RE-AUDIT (verdict-first)

Audit terhadap: (a) desain awal yang gue suggest + attachment pertama, (b) zip lama (137 engine), (c) pertanyaan quad multi-horizon.

---

## 1. ALIGNMENT vs DESAIN AWAL — verdict: SKELETON match, tapi BELUM lengkap

Desain awal gue (dari transcript) = **5 hukum + 9 tab**. Status sekarang:

**5 hukum desain:**
| Hukum | Status sekarang |
|---|---|
| 1. Satu verdict di atas | ✅ ada (hero Quad + posture + conviction bar) |
| 2. Inverted pyramid | ✅ verdict → driver → conviction → data |
| 3. Conviction 3-5 + watchlist ≤10, kompetitif | ✅ ranking gue |
| 4. Tiap nama rantai sebab **5 bagian** (why now / what changed / who's trapped / who must buy / invalidation) | ⚠️ **CUMA 2** (why + invalidates). Kurang: what-changed, who's-trapped, who-must-buy |
| 5. Warna = makna | ✅ |

**9 tab rencana awal vs sekarang:**
| Tab | Rencana awal | Sekarang |
|---|---|---|
| Command Center | verdict + 5 driver (Growth/Inflation/**Liquidity**/**Shock**/Breadth) + conviction + **propagation chain** | ⚠️ ada tapi driver-nya beda + **propagation chain ke-drop** dari CC |
| Alpha Center | funnel + conviction + watchlist | ✅ |
| US Stocks | **GEX/vanna/charm/dark pool** | ⚠️ cuma price/RS lens (greeks belum) |
| Crypto | on-chain/stablecoin/funding/liquidation | ❌ **gak ada tab** |
| IHSG | BandarMetrics Corr_F/Par_F + flow regime + broker entropy | ⚠️ LPM doang (regime/entropy belum) |
| Commodities | inventory/curve/shipping | ❌ **gak ada tab** |
| FX | carry/DXY/rate diff | ❌ **gak ada tab** |
| Bottleneck | propagation graph node-link + secular + supplier | ⚠️ curated map (engine graph belum) |
| Flow | capital rotation | ❌ **gak ada tab** |

**Verdict:** bahasa desain & hierarki SUDAH sesuai. Tapi gue **memangkas kelengkapan** — 4 tab hilang (Crypto/Commodities/FX/Flow), causal card kurang 3 elemen, CC kehilangan propagation + Liquidity/Shock tile.

---

## 2. QUAD MULTI-HORIZON — jawaban: lu BENER, gue cuma punya 1 dari 3

Hedgeye GIP = 3 scope. Cek `engines/gip_engine.py v9`:

- **Structural quad** → ADA di engine (`structural_quad, structural_probs, structural_conf, structural_g, structural_i`)
- **Monthly quad** → ADA (`monthly_quad, monthly_probs, monthly_conf, monthly_g, monthly_i`) + `divergence`, `operating_regime` ("Structural Q3 / Monthly Q2"), `policy_score`, `flip_hazard()`
- **Global quad (50-country)** → ❌ TIDAK ADA di zip ini (`global_quad_engine.py` kosong; ada di build lu yang lebih lama / repo `edgani/tes`)

API: `GIPEngine().run(fred, prices)` → butuh data FRED (CPI/PCE/INDPRO/UNRATE dll). Di mesin lu bisa real (FRED gratis tanpa key), offline → price-proxy.
Bonus: `quad_explainer.explain_quad(gip, transition, narrative)` → "kenapa quad ini / apa yang ngubah / ke mana next" — pas buat hero "flips if".

**Yang gue pakai sekarang:** 1 quad price-proxy doang (akselerasi komoditas/sektor). Makanya `inflation accel -35.4` = artefak komoditas, BUKAN CPI. **Fix:** wire `GIPEngine` (real FRED) → langsung dapat Structural + Monthly + divergence. Global = perlu dibangun / dari repo lain.

---

## 3. A-Z: YANG GUE BUANG PADAHAL PENTING (pakai ~5 dari 137 engine)

### CROWN JEWELS (wajib masuk, high-value, verified)
- `gcfis/engines/leadlag_discovery.py` — Granger + Transfer Entropy + FDR, returns-based, no-lookahead → **propagation chain yang REAL** (bukan hardcode)
- `engines/supply_chain_graph_real.py` — NetworkX supplier→customer + betweenness (chokepoint) + forward/reverse BFS → **bottleneck/supplier graph engine**
- `engines/treasury_liquidity.py` — TGA/RRP/SOFR **FREE no-key** + `gcfis/engines/liquidity.py` (NetLiq = FedBS−TGA−RRP) → lengkapi funding engine gue
- `gcfis/engines/crash_bottom.py` — crash-pressure composite + crash-type + **BOTTOM detection** (yang gue mau bangun, ternyata UDAH ADA)
- `gcfis/engines/shock.py` — P(shock/regime-break)
- `data/bottleneck_reference.json` (1,243 baris) — photonics_12_layer, consensus_heatmap, catalyst_timeline, ma_watchlist, nvidia_playbook, entry_prices

### OPTIONS / GREEKS (lu sebut — gue buang SEMUA)
`gex_engine`, `spotgamma_gex_engine` (real chain), `gamma_engine`, `greeks_proxy`, `options_greeks_engine` (vanna/charm calendar + gamma wall), `vanna_charm_flows`, `vanna_proxy_engine`, `charm_proxy_engine`, `volga_proxy`, `odte_monitor/enhanced`, `schadner_iv` (closed-form IV ~10-50x), `yfinance_options` (**REAL chain**), `karsan_vol_scanner`, `cem_karsan_universal`, `vrp_scanner`, `volsignals_regime`, `spotgamma_levels`, `tier1alpha_model`

### METHODOLOGY / TOKOH (lu sebut — gue buang)
`leopold_methodology` (Aschenbrenner OOM), `methodology_pack` (Yves/Soros/Schadner/Druckenmiller/tier1alpha/profplum99), `thought_process_engine` (Citrini/Hedgeye orchestrator), `coatue_methodology`, `yves_engine`, `boombust_engine`+`reflexivity_engine` (Soros), `smart_money_tracker` (13F), `aaii_scraper`

### REGIME / QUAD
`gip_engine` (structural+monthly), `quad_explainer`, `regime_transition_engine` (ripeness/inflection), `gcfis/change_detection` (Druckenmiller), `gcfis/forward_macro` (market-implied forward G/I — fix quad latency), `gcfis/regime_hmm` (Gaussian HMM), `markov_regime_engine_v3` (HSMM+BOCPD), `duration_hmm_engine`

### RISK RANGE / SIZING
`risk_range_engine` (REAL Hedgeye v39), `risk_range_v20` (Pine port), `gcfis/risk_range_hedgeye` (MQA v25.1 port), `vix_bucket_engine`, `hedgeye_position_sizing` (VIX×Quad×Conviction), `fractional_kelly_engine`, `portfolio_sizing`

### FLOW / IDX (bandarmologi)
`gcfis/flow_regime` (regime-aware foreign flow), `gcfis/broker_flow` (BRAIN intent), `gcfis/flow_type` (4-way + absorption), `maker_framework` (IDX maker roadmap), `ihsg_specialist_v38` (goreng phase), `real_flow_engine` (CVD), `onchain_engine`+`defillama_scraper`, `gcfis/crypto` (L10)

### PROPAGATION / NARRATIVE
`cascade_engine`, `chain_reaction_v2`, `transmission_engine`, `interconnect_engine`, `gcfis/narrative`, `narrative_engine`, `bottleneck_discovery_v3`, `gcfis/bottleneck_engine`(+migration), `gcfis/asymmetric_discovery`, `discovery_brain`, `alpha_scanner`, `gcfis/surge`, `squeeze_scanner`, `frontrun_engine`

### VALIDATION (anti-overfit — penting buat "edge beneran")
`walkforward_engine`+`walkforward_backtest_engine` (MC gatekeeper), `validation_engine` (overfit detect), `simulation_engine` (Monte Carlo)

### ⛔ JANGAN PAKAI (logika filter ticker yang lu tolak)
`gcfis/competitive_ranking_engine` (eliminate/score), `gcfis/elimination` ("buang sampah"), `alpha_gatekeeper`, semua `pages_lib/` + `components/` + `app.py` lama (UI lama). Ranking tetap PUNYA GUE.

### DATA
`data/ihsg_conglomerates.json`, `data/chain_reactions.json`, `data/extended_universe.json`

---

## 4. ROADMAP REINTEGRASI (engine → desain gue, urut prioritas)

**Tier 1 — fix yang lu tunjuk langsung:**
1. Wire `GIPEngine` real FRED → Structural + Monthly quad + divergence di hero (+ `quad_explainer` buat "flips if")
2. Buang pill non-fungsional; pastiin tab = nav
3. Real Hedgeye risk range (`risk_range_engine`/`gcfis risk_range_hedgeye`) gantiin reimpl gue
4. Causal card → lengkapi jadi 5 bagian (why/what-changed/trapped/must-buy/invalidation) via `gcfis/narrative`

**Tier 2 — kelengkapan tab:**
5. US Stocks: greeks (`gex`/`vanna_charm`/`schadner_iv`, real chain via `yfinance_options`)
6. Tambah tab Crypto (`gcfis/crypto`+`onchain`), Commodities (`fx_commodity_driver`), FX (`fx_carry`+USD), Flow (capital rotation)
7. IHSG: `gcfis/flow_regime` + `broker_flow` + `ihsg_specialist` (Corr_F/Par_F/entropy)
8. Liquidity: gabung `treasury_liquidity`+`gcfis/liquidity` ke funding engine gue
9. Crash/bottom: `gcfis/crash_bottom`+`shock` → CC + bottom-confirm

**Tier 3 — intelligence layer:**
10. Bottleneck: `supply_chain_graph_real` + `leadlag_discovery` + `bottleneck_reference.json` → propagation graph REAL
11. Methodology enrichment: `thought_process` (Citrini/Yves/Soros/Coatue/Druck) per conviction card
12. Sizing: `hedgeye_position_sizing` (VIX×Quad) + `fractional_kelly`
13. Validation: `walkforward`+`validation_engine` (label edge OOS)

**Arsitektur tetap:** desain mockup gue + ranking gue. Engine zip dipanggil sebagai **penyedia formula/metrik** — BUKAN pipeline filter lama.
