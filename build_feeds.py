"""build_feeds.py — fetch all LIVE feeds once → data/feeds_snapshot.pkl (dashboard reads it, stays fast).

Run on a machine WITH network (sandbox blocks idx.co.id / fred / defillama / cftc):
    export FRED_API_KEY=your_key            # FRED (you have this)
    # optional: export FLASHALPHA_API_KEY=...   # signed GEX (else yfinance options proxy)
    python build_feeds.py

Feeds (all PUBLIC except FRED key): FRED macro, FX carry (FRED rates), IDX Type-F foreign flow
(idx.co.id), crypto on-chain (DefiLlama), COT positioning (CFTC), options chain → GEX (yfinance),
FINRA short-volume (dark-pool proxy). Each is defensive: a failure just leaves that feed empty.
First IDX Type-F warm-up (~120 sessions) is slow once, then per-day CSV cached.
"""
from __future__ import annotations
import os, sys, pickle, json, datetime as dt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from warroom import data as D

OUT = os.path.join("data", "feeds_snapshot.pkl")
STATUS = os.path.join("data", "feeds_status.json")


def _try(label, fn):
    try:
        v = fn()
        ok = v is not None and (not hasattr(v, "__len__") or len(v) > 0)
        print(f"  [{'OK ' if ok else '— '}] {label}" + ("" if ok else "  (empty)"))
        return v if ok else None
    except Exception as e:
        print(f"  [ERR] {label}: {type(e).__name__}: {e}")
        return None


def main():
    feeds, status = {}, {}
    print("Fetching live feeds → snapshot…")

    # 1) FRED macro (key from env) — robust loader (API → fredgraph → DBnomics)
    def fred():
        from data.fred_loader import load_fred_bundle
        b = load_fred_bundle()
        return (b or {}).get("series")
    feeds["fred"] = _try("FRED macro", fred)

    # 2) FX carry / rate differential (needs FRED rates)
    def fx_carry():
        from engines.fx_carry_engine import analyze_fx_carry
        pairs = ["EURUSD", "USDJPY", "GBPUSD", "AUDUSD", "USDIDR"]
        return analyze_fx_carry(feeds.get("fred") or {}, pairs)
    feeds["fx_carry"] = _try("FX carry (FRED rates)", fx_carry)

    # 3) IDX Type-F foreign flow (idx.co.id) → Corr_F / Par_F / flow-regime
    def typef():
        from gcfis.feeds.typef_idx import build_typef
        data, st = build_typef(D.IDX_UNIVERSE, days=120, cache_dir=os.path.join("data", "typef_cache"))
        print(f"        typef status: {st}")
        return data
    feeds["typef"] = _try("IDX Type-F foreign flow", typef)

    # 4) Crypto on-chain (DefiLlama)
    def onchain():
        from engines.live_data_engine import fetch_onchain_defillama
        return fetch_onchain_defillama({"BTC-USD": "bitcoin", "ETH-USD": "ethereum", "SOL-USD": "solana"})
    feeds["onchain"] = _try("Crypto on-chain (DefiLlama)", onchain)

    # 5) COT positioning (CFTC) — commodities + FX
    def cot():
        from engines.cftc_cot_scraper import get_all_signals
        return get_all_signals()
    feeds["cot"] = _try("CFTC COT positioning", cot)

    # 6) Options chain → GEX (yfinance; or FlashAlpha if key set)
    def gex():
        from engines.live_data_engine import fetch_options_yf, fetch_flashalpha_gex
        top = ["NVDA", "AMD", "AVGO", "MRVL", "MU", "SMH", "MSFT", "META", "AAPL", "AMZN"]
        fa = os.environ.get("FLASHALPHA_API_KEY", "")
        if fa:
            return {"source": "flashalpha", "data": fetch_flashalpha_gex(top, fa, max_calls=10)}
        return {"source": "yfinance", "data": fetch_options_yf(top, max_tickers=10, max_workers=4)}
    feeds["gex"] = _try("Options chain → GEX", gex)

    # 7) FINRA short-volume (dark-pool proxy)
    def finra():
        from engines.live_data_engine import fetch_finra_short_volume
        top = ["NVDA", "AMD", "AVGO", "MRVL", "MU", "MSFT", "META", "AAPL"]
        return fetch_finra_short_volume(top, lookback_days=20)
    feeds["finra"] = _try("FINRA short-volume", finra)

    feeds["_saved_at"] = dt.datetime.now().isoformat(timespec="seconds")
    os.makedirs("data", exist_ok=True)
    with open(OUT, "wb") as f:
        pickle.dump(feeds, f)
    status = {k: (feeds.get(k) is not None) for k in feeds if not k.startswith("_")}
    status["saved_at"] = feeds["_saved_at"]
    with open(STATUS, "w") as f:
        json.dump(status, f, indent=2)
    live = sum(1 for k, v in status.items() if k != "saved_at" and v)
    print(f"\nSaved {OUT} — {live}/{len(status)-1} feeds live. Dashboard will now use them.")


if __name__ == "__main__":
    main()
