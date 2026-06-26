"""warroom/data.py — universe + OHLCV loader.
Complete-but-light: reads a local parquet cache first (built by build_cache.py, bulk/incremental),
then live yfinance, then deterministic synthetic so the app ALWAYS renders.
"""
from __future__ import annotations
import os, numpy as np, pandas as pd

_CACHE = os.path.join(os.path.dirname(__file__), "..", "cache")

# --- universes (macro proxies first; GIP/regime needs them) ---
MACRO_PROXY = ["SPY", "IWM", "XLI", "XLY", "XHB", "USO", "GLD", "UUP", "TLT", "IEF", "DBC", "HYG", "^VIX",
               "XLK", "XLE", "XLF", "XLV", "XLP", "XLU", "XLB", "XLRE", "XLC", "IWD", "IWF", "MTUM"]
# US: liquid leaders + the AI-buildout supply-chain beneficiaries (from the roadmap/12-layer attachments)
US_NAMES = ["NVDA", "AMD", "AVGO", "MRVL", "SMH", "SOXX", "MU", "TSM", "INTC",
            "ANET", "COHR", "LITE", "FN", "CRDO", "ALAB", "AMKR", "GLW",
            "AMAT", "LRCX", "KLAC", "ENTG", "MKSI",
            "VRT", "ETN", "PWR", "GEV", "CEG", "VST", "NRG", "TLN", "HUBB", "ON",
            "MP", "ATI", "MTRN", "KTOS",
            "MSFT", "GOOGL", "AMZN", "META", "ORCL", "NBIS", "CRM", "NOW",
            "AAPL", "ARKK", "XLE", "XLU", "XLP", "COPX"]
def _dynamic_us():
    import os, json
    try:
        d = json.load(open(os.path.join(os.path.dirname(__file__), "..", "data", "extended_universe.json")))
        ks = list((d.get("tier_2_discovered") or {}).keys()) + list((d.get("tier_3_user_requested") or {}).keys())
        return [k.upper() for k in ks if isinstance(k, str) and k.isalpha() and 1 <= len(k) <= 5 and k.upper() not in US_NAMES and k.upper() != "HYNIX"]
    except Exception:
        return []
US_NAMES = US_NAMES + _dynamic_us()            # adaptive: merge engine-discovered tickers
# cross-asset beta-play candidates (precious/miners, energy, copper, crypto-miners, nuclear) for the beta-play finder
BETA_UNIVERSE = ["ACLS", "GDX", "GDXJ", "SIL", "FNV", "WPM", "NEM", "GOLD", "AEM",
                 "XOP", "OIH", "SLB", "HAL", "AMLP", "FCX", "COPX", "SCCO",
                 "MARA", "RIOT", "CLSK", "DNN", "NXE", "OKLO", "SMR"]
# adjacent-theme names for the theme graph (quantum, robotics/automation, defense-tech)
THEME_EXT = ["IONQ", "RGTI", "QBTS", "ARQQ", "TSLA", "ISRG", "ROK", "SERV", "PATH", "TER", "NNDM", "KTOS"]
US_UNIVERSE = list(dict.fromkeys(MACRO_PROXY + US_NAMES + BETA_UNIVERSE + THEME_EXT))
IDX_UNIVERSE = ["BBCA.JK", "BMRI.JK", "BBRI.JK", "BBNI.JK", "TLKM.JK", "ASII.JK", "BUMI.JK",
                "ADRO.JK", "ANTM.JK", "MDKA.JK", "GOTO.JK", "AMMN.JK", "BREN.JK", "HUMI.JK"]
CRYPTO_UNIVERSE = ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "COIN", "IBIT", "MSTR"]
FX_UNIVERSE = ["DX-Y.NYB", "EURUSD=X", "USDJPY=X", "GBPUSD=X", "AUDUSD=X", "USDIDR=X"]
COMMO_UNIVERSE = ["GLD", "SLV", "USO", "UNG", "CPER", "DBC", "WEAT", "URA"]

def _synth(t, n=420):
    idx = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=int(n))
    m = len(idx)
    r = np.random.default_rng(abs(hash(t)) % (2**32))
    rets = r.normal(r.uniform(-0.0008, 0.0013), r.uniform(0.011, 0.032), m)
    c = 100 * np.exp(np.cumsum(rets)); intr = np.abs(r.normal(0, 0.018, m)) * c; loc = r.uniform(.2, .8, m)
    h = c + intr * (1 - loc); l = c - intr * loc; o = l + (h - l) * r.uniform(.2, .8, m)
    v = (r.uniform(1e6, 6e7, m) * (1 + np.abs(rets) / 0.02 * 0.5)).round()
    return pd.DataFrame({"Open": o, "High": h, "Low": l, "Close": c, "Volume": v}, index=idx)

def _from_cache(tickers):
    out = {}
    path = os.path.join(_CACHE, "prices.parquet")
    if not os.path.exists(path):
        return out
    try:
        df = pd.read_parquet(path)
        for t in tickers:
            if t in df.columns.get_level_values(0):
                d = df[t][["Open","High","Low","Close","Volume"]].dropna()
                if len(d) > 80:
                    out[t] = d
    except Exception:
        pass
    return out

def load(tickers, days=420):
    tickers = list(dict.fromkeys(tickers))
    cached = _from_cache(tickers)
    missing = [t for t in tickers if t not in cached]
    if not missing:
        return cached, "cache · parquet"
    try:
        import yfinance as yf
        raw = yf.download(missing, period=f"{days}d", interval="1d", auto_adjust=False,
                          progress=False, group_by="ticker", threads=True)
        if isinstance(raw.columns, pd.MultiIndex):
            for t in missing:
                if t in raw.columns.get_level_values(0):
                    d = raw[t][["Open","High","Low","Close","Volume"]].dropna()
                    if len(d) > 80: cached[t] = d
        elif missing:
            d = raw[["Open","High","Low","Close","Volume"]].dropna()
            if len(d) > 80: cached[missing[0]] = d
        if len(cached) >= max(4, len(tickers)//2):
            src = "cache + yfinance" if _from_cache(tickers) else "yfinance · live"
            for t in tickers:
                cached.setdefault(t, _synth(t, days))
            return cached, src
    except Exception:
        pass
    for t in tickers:
        cached.setdefault(t, _synth(t, days))
    return cached, ("synthetic · demo (no live feed)" if not _from_cache(tickers) else "cache + synthetic")
