"""warroom/drivers.py — cross-asset driver coherence via EMPIRICAL factor regression.

Upgrade over hand-weighted drivers: economic priors choose the FACTORS (justified), the DATA
estimates the loadings (betas) by rolling OLS. For each asset we regress its daily returns on its
driver returns over a trailing window, then judge today's stance by the STANDARDIZED RESIDUAL — how
many residual-sigma the recent move sits from what the factor model predicts. This is a real
statistical anomaly measure, not a guessed sigma. Three gates:
  • R² (fit quality) — if drivers don't explain the asset now (low R²) it's DECOUPLED → coherence N/A.
  • standardized residual — |z|>2 OFFSIDE (rich/cheap vs model), |z|>1 STRETCHED, else in-line.
  • sign check — empirical beta vs economic prior; if inverted, the relationship itself has flipped.
Factors are price proxies (always available); real-yield (DFII10) + breakeven (T10YIE) layer onto
gold/BTC when FRED is present. Single names use a market-model (market + size) → idiosyncratic z.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

# asset: (display, driver_text, [(ticker, kind, prior_sign)], idiosyncratic)
#   kind: "px" = price proxy (pct_change), "fred_diff" = FRED level differenced
DRIVER_MAP = {
    "GLD":       ("Gold (XAU)", "real rates - dollar", [("TLT", "px", +1), ("DX-Y.NYB", "px", -1)], False),
    "SLV":       ("Silver (XAG)", "gold + copper - dollar", [("GLD", "px", +1), ("CPER", "px", +1), ("DX-Y.NYB", "px", -1)], False),
    "CPER":      ("Copper", "global growth - dollar", [("SPY", "px", +1), ("DX-Y.NYB", "px", -1), ("DBC", "px", +1)], False),
    "USO":       ("Oil (WTI)", "demand/growth - dollar", [("SPY", "px", +1), ("DX-Y.NYB", "px", -1)], False),
    "DBC":       ("Broad commodities", "growth - dollar", [("SPY", "px", +1), ("DX-Y.NYB", "px", -1)], False),
    "UNG":       ("Natural gas", "weather/storage (idiosyncratic)", [("DBC", "px", +1)], True),
    "WEAT":      ("Wheat", "weather/supply (idiosyncratic)", [("DBC", "px", +1)], True),
    "URA":       ("Uranium", "secular nuclear (idiosyncratic)", [("SPY", "px", +1)], True),
    "SPY":       ("US equity (SPY)", "rates + credit + growth", [("TLT", "px", +1), ("HYG", "px", +1), ("CPER", "px", +1)], False),
    "IWM":       ("US small-cap (IWM)", "rates + credit + growth", [("TLT", "px", +1), ("HYG", "px", +1), ("CPER", "px", +1)], False),
    "DX-Y.NYB":  ("Dollar (DXY)", "US yields - risk (+ oil tested)", [("TLT", "px", -1), ("SPY", "px", -1), ("USO", "px", +1)], False),
    "EURUSD=X":  ("EUR/USD", "inverse dollar", [("DX-Y.NYB", "px", -1)], False),
    "USDJPY=X":  ("USD/JPY", "US yields + risk", [("TLT", "px", -1), ("SPY", "px", +1)], False),
    "GBPUSD=X":  ("GBP/USD", "inverse dollar + risk", [("DX-Y.NYB", "px", -1), ("SPY", "px", +1)], False),
    "AUDUSD=X":  ("AUD/USD", "commodities + risk - dollar", [("CPER", "px", +1), ("SPY", "px", +1), ("DX-Y.NYB", "px", -1)], False),
    "USDIDR=X":  ("USD/IDR", "dollar - commodities - risk", [("DX-Y.NYB", "px", +1), ("DBC", "px", -1), ("SPY", "px", -1)], False),
    "BTC-USD":   ("Bitcoin", "liquidity - dollar + risk", [("TLT", "px", +1), ("DX-Y.NYB", "px", -1), ("SPY", "px", +1)], False),
    "ETH-USD":   ("Ethereum", "BTC + risk", [("BTC-USD", "px", +1), ("SPY", "px", +1)], False),
    "SOL-USD":   ("Solana", "BTC beta", [("BTC-USD", "px", +1)], False),
    "MSTR":      ("MSTR (BTC proxy)", "BTC levered", [("BTC-USD", "px", +1)], False),
    "COIN":      ("Coinbase", "BTC + risk", [("BTC-USD", "px", +1), ("SPY", "px", +1)], False),
    "__IHSG__":  ("IHSG (composite)", "-USD/IDR + commodities + EM risk", [("USDIDR=X", "px", -1), ("DBC", "px", +1), ("SPY", "px", +1)], False),
}
# extra real-rate / breakeven factors layered on when FRED present
FRED_FACTORS = {
    "GLD":     [("DFII10", "fred_diff", -1), ("T10YIE", "fred_diff", +1)],
    "BTC-USD": [("DFII10", "fred_diff", -1)],
    "SLV":     [("DFII10", "fred_diff", -1)],
}
_DLAB = {"TLT": "rates", "DX-Y.NYB": "USD", "SPY": "risk", "CPER": "copper", "DBC": "commodities",
         "HYG": "credit", "GLD": "gold", "BTC-USD": "BTC", "USDIDR=X": "USD/IDR",
         "DFII10": "real-yield", "T10YIE": "breakeven"}

WINDOW = 150   # trailing trading days for the regression
RECENT = 21    # recent window for the standardized residual


def _ihsg_proxy(allpx):
    jk = [allpx[t]["Close"].dropna() for t in allpx
          if str(t).endswith(".JK") and allpx.get(t) is not None and len(allpx[t]) > 30]
    if len(jk) < 2:
        return None
    norm = [s / s.iloc[0] for s in jk]
    return pd.concat(norm, axis=1).mean(axis=1).to_frame("Close")


def _ret(allpx, fred, ihsg, ticker, kind):
    if kind == "fred_diff":
        s = (fred or {}).get(ticker)
        return s.diff() if (s is not None and len(s) > 30) else None
    df = ihsg if ticker == "__IHSG__" else allpx.get(ticker)
    if df is None or "Close" not in df:
        return None
    return df["Close"].pct_change()


def _regress(y, Xdf):
    d = pd.concat([y.rename("y"), Xdf], axis=1).dropna()
    if len(d) < 40:
        return None
    Y = d["y"].values
    cols = [c for c in d.columns if c != "y"]
    M = d[cols].values
    A = np.column_stack([np.ones(len(M)), M])
    try:
        beta, *_ = np.linalg.lstsq(A, Y, rcond=None)
    except Exception:
        return None
    resid = Y - A @ beta
    ss_res = float((resid ** 2).sum())
    ss_tot = float(((Y - Y.mean()) ** 2).sum())
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
    sigma = float(resid.std())
    return {"beta": beta, "cols": cols, "r2": r2, "sigma": sigma, "resid": resid}


def _factor_frame(allpx, fred, ihsg, facs):
    cols = {}
    priors = {}
    for tkr, kind, sign in facs:
        r = _ret(allpx, fred, ihsg, tkr, kind)
        if r is None:
            continue
        name = _DLAB.get(tkr, tkr)
        cols[name] = r
        priors[name] = sign
    if not cols:
        return None, None
    return pd.DataFrame(cols), priors


def compute(allpx, fred=None):
    ihsg = _ihsg_proxy(allpx)
    res = []
    for asset, (disp, dtext, facs, idio) in DRIVER_MAP.items():
        y = _ret(allpx, fred, ihsg, asset, "px")
        if y is None:
            continue
        allf = list(facs) + FRED_FACTORS.get(asset, [])
        Xdf, priors = _factor_frame(allpx, fred, ihsg, allf)
        if Xdf is None:
            continue
        reg = _regress(y.tail(WINDOW), Xdf.tail(WINDOW))
        if reg is None:
            continue
        sigma, resid, r2 = reg["sigma"], reg["resid"], reg["r2"]
        std_resid = float(resid[-RECENT:].sum() / (sigma * np.sqrt(RECENT))) if sigma > 0 else 0.0
        std_resid = max(-6.0, min(6.0, std_resid))
        betas = {c: round(float(b), 2) for c, b in zip(reg["cols"], reg["beta"][1:])}
        flips = [c for c in betas if priors.get(c) and np.sign(betas[c]) and np.sign(betas[c]) != np.sign(priors[c]) and abs(betas[c]) > 0.15] if r2 >= 0.15 else []
        if r2 < 0.15:
            status = "decoupled"
        elif idio:
            status = "in-line"
        elif abs(std_resid) > 2:
            status = "offside"
        elif abs(std_resid) > 1:
            status = "stretched"
        else:
            status = "in-line"
        rich = "rich" if std_resid > 0 else "cheap"
        bstr = ", ".join(f"{c} \u03b2{betas[c]:+.2f}" for c in betas)
        if status == "decoupled":
            note = f"{disp} DECOUPLED from drivers (R\u00b2 {r2:.2f}) — factor model doesn't explain it now; coherence unreliable"
        elif status in ("offside", "stretched"):
            note = f"{disp} {std_resid:+.1f}\u03c3 vs factor model ({rich} vs {dtext}; R\u00b2 {r2:.2f}; {bstr})"
        else:
            note = f"{disp} in line ({std_resid:+.1f}\u03c3, R\u00b2 {r2:.2f})"
        if flips:
            note += f" — REGIME: {', '.join(flips)} beta inverted vs prior"
        res.append({"asset": asset, "display": disp, "driver_text": dtext, "std_resid": round(std_resid, 2),
                    "r2": round(r2, 2), "betas": betas, "flips": flips, "status": status,
                    "idiosyncratic": idio, "note": note})
    order = {"offside": 0, "stretched": 1, "decoupled": 2, "in-line": 3}
    res.sort(key=lambda r: (order.get(r["status"], 9), -abs(r["std_resid"])))
    return res


def coherence_summary(results):
    off = [r for r in results if r["status"] == "offside"]
    stq = [r for r in results if r["status"] == "stretched"]
    dec = [r for r in results if r["status"] == "decoupled"]
    flips = [r for r in results if r["flips"]]
    return {"offside": off, "stretched": stq, "decoupled": dec, "regime_flips": flips,
            "n_offside": len(off), "n_stretched": len(stq), "n_decoupled": len(dec), "n_total": len(results)}


def name_coherence(allpx, ticker, market):
    """Single-name market model → idiosyncratic z (is the move name-specific vs the market?)."""
    ihsg = _ihsg_proxy(allpx)
    y = _ret(allpx, None, ihsg, ticker, "px")
    if y is None:
        return None
    facs = [("__IHSG__", "px", +1)] if market == "IHSG" else [("SPY", "px", +1), ("IWM", "px", +1)]
    Xdf, _ = _factor_frame(allpx, None, ihsg, facs)
    if Xdf is None:
        return None
    reg = _regress(y.tail(WINDOW), Xdf.tail(WINDOW))
    if reg is None:
        return None
    sigma, resid, r2 = reg["sigma"], reg["resid"], reg["r2"]
    idio_z = float(resid[-RECENT:].sum() / (sigma * np.sqrt(RECENT))) if sigma > 0 else 0.0
    idio_z = max(-6.0, min(6.0, idio_z))
    beta_mkt = round(float(reg["beta"][1]), 2)
    return {"idio_z": round(idio_z, 2), "beta_mkt": beta_mkt, "r2": round(r2, 2)}
