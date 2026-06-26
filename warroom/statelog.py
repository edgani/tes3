"""warroom/statelog.py — "what changed" engine (real-time adaptation surface).

Each run snapshots the decision-relevant state (dual-quad, posture, shock, VIX regime,
flip-hazard, top conviction names+direction, live feeds) to data/state_history.json, then
diffs the current run against the PRIOR run. The diff is what you act on — it tells you what
shifted since you last looked, instead of re-reading the whole board.

No history yet → baseline saved, nothing to diff. Re-running with no change → "stance intact".
"""
from __future__ import annotations
import os, json, datetime as dt

HIST = os.path.join("data", "state_history.json")
_MAX = 60


def _posture(quad):
    q = str(quad or "")
    if "1" in q: return "Risk-On (Quad1 growth↑ infl↓)"
    if "2" in q: return "Reflation (Quad2 growth↑ infl↑)"
    if "3" in q: return "Caution (Quad3 growth↓ infl↑)"
    if "4" in q: return "Risk-Off (Quad4 growth↓ infl↓)"
    return "—"


def _vixbucket(v):
    try:
        v = float(v)
    except Exception:
        return "—"
    if v < 15: return "calm <15"
    if v < 20: return "normal 15-20"
    if v < 27: return "elevated 20-27"
    return "stress >27"


def snapshot_state(d):
    reg = d.get("regime", {}) or {}
    conv = [(s["ticker"], s.get("_dir")) for s in (d.get("conviction") or [])[:6] if s.get("_dir") in ("Long", "Short")]
    vix = d.get("vix")
    return {
        "ts": dt.datetime.now().isoformat(timespec="seconds"),
        "squad": reg.get("structural"), "mquad": reg.get("monthly"),
        "posture": _posture(reg.get("structural")),
        "shock": d.get("shock_prob"), "vix": vix, "vixb": _vixbucket(vix),
        "flip": float(reg.get("flip_hazard", 0) or 0),
        "conv": conv, "feeds": d.get("feeds_status", {}) or {},
    }


def diff_state(prev, curr):
    if not prev:
        return []
    ev = []  # (severity, text)
    if prev.get("squad") != curr.get("squad"):
        ev.append(("high", f"Regime shift (structural): {prev.get('squad')} → {curr.get('squad')}"))
    if prev.get("posture") != curr.get("posture"):
        ev.append(("high", f"Risk posture flip: {prev.get('posture')} → {curr.get('posture')}"))
    if prev.get("mquad") != curr.get("mquad"):
        ev.append(("med", f"Monthly quad: {prev.get('mquad')} → {curr.get('mquad')}"))
    order = {"low": 0, "moderate": 1, "elevated": 2}
    if prev.get("shock") != curr.get("shock"):
        up = order.get(curr.get("shock"), 0) > order.get(prev.get("shock"), 0)
        sev = "high" if (up and curr.get("shock") == "elevated") else "med"
        ev.append((sev, f"Shock probability: {prev.get('shock')} → {curr.get('shock')}"))
    if prev.get("vixb") != curr.get("vixb"):
        ev.append(("med", f"VIX regime: {prev.get('vixb')} → {curr.get('vixb')} (VIX {curr.get('vix')})"))
    pf, cf = prev.get("flip", 0), curr.get("flip", 0)
    if (pf < 0.35) != (cf < 0.35) or abs(cf - pf) >= 0.25:
        ev.append(("med", f"Flip-hazard: {pf:.2f} → {cf:.2f}"))
    pmap = {t: dx for t, dx in prev.get("conv", [])}
    cmap = {t: dx for t, dx in curr.get("conv", [])}
    for t, dx in cmap.items():
        if t not in pmap:
            ev.append(("low", f"New conviction: {t} {dx}"))
        elif pmap[t] != dx:
            ev.append(("high", f"{t} flipped {pmap[t]} → {dx}"))
    for t in pmap:
        if t not in cmap:
            ev.append(("low", f"Dropped from conviction: {t}"))
    pf_, cf_ = prev.get("feeds", {}), curr.get("feeds", {})
    for k, v in cf_.items():
        if v and not pf_.get(k):
            ev.append(("low", f"Feed live: {k}"))
        elif (not v) and pf_.get(k):
            ev.append(("low", f"Feed dropped: {k}"))
    sev_rank = {"high": 0, "med": 1, "low": 2}
    return sorted(ev, key=lambda e: sev_rank[e[0]])


def record_and_diff(d, path=None):
    """Load history, diff current vs prior run, append current, persist. Returns (changes, prev_ts)."""
    path = path or HIST
    hist = []
    try:
        if os.path.exists(path):
            hist = json.load(open(path)) or []
    except Exception:
        hist = []
    prev = hist[-1] if hist else None
    curr = snapshot_state(d)
    changes = diff_state(prev, curr)
    hist.append(curr)
    hist = hist[-_MAX:]
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        json.dump(hist, open(path, "w"))
    except Exception:
        pass
    return changes, (prev.get("ts") if prev else None)
