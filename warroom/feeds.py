"""warroom/feeds.py — load the live-feed snapshot built by build_feeds.py.
No snapshot (sandbox / not built yet) → empty dict; every lens degrades to its price proxy.
"""
from __future__ import annotations
import os, pickle

SNAP = os.path.join("data", "feeds_snapshot.pkl")


def load_feeds():
    try:
        if os.path.exists(SNAP):
            with open(SNAP, "rb") as f:
                d = pickle.load(f)
            return d if isinstance(d, dict) else {}
    except Exception:
        pass
    return {}


def status(feeds):
    keys = ["fred", "fx_carry", "typef", "onchain", "cot", "gex", "finra"]
    return {k: (feeds.get(k) is not None) for k in keys}
