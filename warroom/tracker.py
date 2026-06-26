"""warroom/tracker.py — forward-test logger (the track-record engine).

Integrity rules (this is what makes it allocator-credible):
  • Point-in-time: a signal is logged with the timestamp + price AT GENERATION. Never edited after.
  • No look-ahead: an outcome is resolved ONLY from bars dated strictly AFTER the signal date.
  • Path-dependent: WIN/LOSS decided by which of {target, stop} the OHLC path touches first
    (if both touch in the same bar → counted as LOSS, the conservative assumption).
  • Net of cost: realized return subtracts a configurable round-trip cost (bps).
  • Idempotent: re-running the same day does not double-log (signal_id = date|ticker|dir).

A real track record takes calendar time: on day 1 everything is OPEN; outcomes accrue as you
re-run over days/weeks. That is the honest mechanism — not a backtest dressed up as live P&L.
"""
from __future__ import annotations
import os, sqlite3, hashlib, datetime as dt
import pandas as pd

DB = os.path.join("data", "track_record.db")


def _conn(path=DB):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    c = sqlite3.connect(path)
    c.execute("""CREATE TABLE IF NOT EXISTS signals(
        signal_id TEXT PRIMARY KEY, gen_date TEXT, ticker TEXT, market TEXT, direction TEXT,
        entry_px REAL, stop REAL, target REAL, score REAL, gate_status TEXT, gate_score REAL,
        regime_struct TEXT, regime_monthly TEXT, why TEXT,
        status TEXT DEFAULT 'OPEN', close_date TEXT, exit_px REAL, ret_pct REAL, r_multiple REAL, bars_held INTEGER, horizon TEXT, decision TEXT, anti_fomo TEXT)""")
    for col in ("horizon", "decision", "anti_fomo"):
        try:
            c.execute(f"ALTER TABLE signals ADD COLUMN {col} TEXT")
        except Exception:
            pass
    return c


def _sid(gen_date, ticker, direction):
    return hashlib.sha1(f"{gen_date}|{ticker}|{direction}".encode()).hexdigest()[:16]


def log_signals(conviction, regime, path=DB, gen_date=None):
    """Insert today's conviction signals point-in-time. INSERT OR IGNORE → idempotent per day."""
    gen_date = gen_date or dt.date.today().isoformat()
    c = _conn(path); n = 0
    for s in (conviction or []):
        if s.get("_dir") not in ("Long", "Short") or s.get("stop") is None or s.get("target") is None:
            continue
        sid = _sid(gen_date, s["ticker"], s["_dir"])
        g = s.get("gate") or {}
        why = f"RS {s.get('rs',0):+.0f}% · accel {s.get('accel',0):+.0f}% · {s.get('form','')}"
        hz = (s.get("timing") or {}).get("horizon")
        dec = (s.get("decision") or {}).get("call")
        af = (s.get("timing") or {}).get("anti_fomo")
        af = af.split(" —")[0] if af else None
        cur = c.execute("INSERT OR IGNORE INTO signals(signal_id,gen_date,ticker,market,direction,entry_px,stop,target,score,gate_status,gate_score,regime_struct,regime_monthly,why,horizon,decision,anti_fomo) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (sid, gen_date, s["ticker"], s.get("market", ""), s["_dir"], float(s["px"]),
                         float(s["stop"]), float(s["target"]), float(s.get("score", 0)),
                         g.get("status"), g.get("score"), regime.get("structural"), regime.get("monthly"), why, hz, dec, af))
        n += cur.rowcount
    c.commit(); c.close()
    return n


def update_outcomes(prices_map, path=DB, cost_bps=10.0):
    """Resolve OPEN signals using bars strictly AFTER gen_date (path-dependent, no look-ahead)."""
    c = _conn(path)
    rows = c.execute("SELECT signal_id,gen_date,ticker,direction,entry_px,stop,target FROM signals WHERE status='OPEN'").fetchall()
    closed = 0
    for sid, gd, tk, d, entry, stop, target in rows:
        df = (prices_map or {}).get(tk)
        if df is None or len(df) == 0:
            continue
        try:
            idx = pd.to_datetime(df.index)
            fut = df[idx > pd.Timestamp(gd)]
        except Exception:
            continue
        if fut.empty:
            continue
        outcome = exit_px = close_date = None; held = 0
        for i, (ts, bar) in enumerate(fut.iterrows(), 1):
            hi, lo = float(bar["High"]), float(bar["Low"])
            if d == "Long":
                hit_s, hit_t = lo <= stop, hi >= target
            else:
                hit_s, hit_t = hi >= stop, lo <= target
            if hit_s and hit_t:
                outcome, exit_px = "LOSS", stop          # both in one bar → conservative
            elif hit_t:
                outcome, exit_px = "WIN", target
            elif hit_s:
                outcome, exit_px = "LOSS", stop
            if outcome:
                close_date = str(ts.date() if hasattr(ts, "date") else ts)[:10]; held = i; break
        if not outcome:
            continue
        sign = 1.0 if d == "Long" else -1.0
        ret = sign * (exit_px - entry) / entry - cost_bps / 1e4
        risk = abs(entry - stop) / entry
        r = ret / risk if risk else 0.0
        c.execute("UPDATE signals SET status=?,close_date=?,exit_px=?,ret_pct=?,r_multiple=?,bars_held=? WHERE signal_id=?",
                  (outcome, close_date, exit_px, ret, r, held, sid))
        closed += 1
    c.commit(); c.close()
    return closed


def _df(path=DB):
    c = _conn(path)
    try:
        return pd.read_sql_query("SELECT * FROM signals", c)
    finally:
        c.close()


def performance(path=DB):
    df = _df(path)
    if df.empty:
        return {"total": 0, "open": 0, "closed": 0}
    closed = df[df["status"].isin(["WIN", "LOSS"])].copy()
    out = {"total": len(df), "open": int((df["status"] == "OPEN").sum()), "closed": len(closed)}
    if closed.empty:
        return out
    rets = closed["ret_pct"].astype(float)
    wins = rets[rets > 0]; losses = rets[rets <= 0]
    eq = (1 + rets).cumprod()
    dd = (eq / eq.cummax() - 1).min()
    out.update({
        "win_rate": round(100 * len(wins) / len(closed), 1),
        "avg_ret": round(100 * rets.mean(), 2),
        "avg_win": round(100 * wins.mean(), 2) if len(wins) else 0.0,
        "avg_loss": round(100 * losses.mean(), 2) if len(losses) else 0.0,
        "expectancy_R": round(closed["r_multiple"].astype(float).mean(), 2),
        "profit_factor": round(wins.sum() / abs(losses.sum()), 2) if losses.sum() != 0 else float("inf"),
        "total_ret": round(100 * (eq.iloc[-1] - 1), 2),
        "sharpe": round(rets.mean() / rets.std() * (len(rets) ** 0.5), 2) if rets.std() else 0.0,
        "max_dd": round(100 * dd, 2),
        "equity": [round(float(x), 4) for x in eq.tolist()],
    })
    return out


def open_positions(path=DB):
    df = _df(path)
    return df[df["status"] == "OPEN"].sort_values("gen_date", ascending=False).to_dict("records") if not df.empty else []


def closed_trades(path=DB):
    df = _df(path)
    return df[df["status"].isin(["WIN", "LOSS"])].sort_values("close_date", ascending=False).to_dict("records") if not df.empty else []
