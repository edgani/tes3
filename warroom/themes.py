"""warroom/themes.py — theme graph: connect the dots across interconnected themes + direction.

Themes aren't silos. Memory/HBM enables AI compute; AI compute enables robotics and humanoids, and
demands power, cooling, networking; quantum sits parallel as the next compute frontier; power pulls
uranium and copper. This encodes that directed graph, measures each theme's HEAT (relative strength +
momentum of its names), and traces from the hot nodes along the edges to the ADJACENT themes that
aren't hot YET — i.e. where capital is likely to rotate next. It also surfaces BRIDGE names that sit
in multiple themes (the highest-conviction connected plays) and a direction read of where the whole
complex is heading. The graph is curated structure; the heat and direction are data-driven.
"""
from __future__ import annotations
import numpy as np

# theme -> {tickers, links: [(downstream_theme, relationship)]}
THEME_GRAPH = {
    "Memory / HBM": {"tickers": ["MU", "WDC", "STX", "LRCX", "AMAT", "KLAC", "ENTG", "AMKR"],
                     "links": [("AI compute", "enables")]},
    "AI compute": {"tickers": ["NVDA", "AVGO", "AMD", "MRVL", "SMCI", "ALAB", "CRDO"],
                   "links": [("Robotics / physical AI", "enables"), ("Autonomous / humanoid", "enables"),
                             ("Power / datacenter", "demands"), ("Cooling / thermal", "demands"),
                             ("Networking / optics", "demands"), ("Quantum", "frontier-parallel")]},
    "Networking / optics": {"tickers": ["ANET", "CRDO", "ALAB", "AVGO", "MRVL"], "links": []},
    "Cooling / thermal": {"tickers": ["VRT", "ETN"], "links": [("Power / datacenter", "demands")]},
    "Power / datacenter": {"tickers": ["VST", "CEG", "GEV", "ETN", "POWL", "NEE"],
                           "links": [("Uranium / nuclear", "demands"), ("Grid / electrification", "demands")]},
    "Uranium / nuclear": {"tickers": ["CCJ", "UEC", "URA", "DNN", "NXE", "OKLO", "SMR"], "links": []},
    "Grid / electrification": {"tickers": ["ETN", "POWL", "GEV", "FCX"], "links": [("Copper / materials", "demands")]},
    "Copper / materials": {"tickers": ["FCX", "CPER", "SCCO", "COPX"], "links": []},
    "Robotics / physical AI": {"tickers": ["TSLA", "ISRG", "ROK", "SERV", "PATH", "TER"],
                               "links": [("Autonomous / humanoid", "overlaps")]},
    "Autonomous / humanoid": {"tickers": ["TSLA", "NVDA", "SERV", "PATH"], "links": []},
    "Quantum": {"tickers": ["IONQ", "RGTI", "QBTS", "ARQQ"], "links": []},
    "Defense tech": {"tickers": ["KTOS", "PLTR", "AVAV"], "links": [("Robotics / physical AI", "overlaps")]},
}


def _heat(allpx, tickers, bench="SPY"):
    bd = allpx.get(bench)
    if bd is None or len(bd) < 70:
        return None
    bc = bd["Close"]
    b60 = float(bc.iloc[-1] / bc.iloc[-60] - 1)
    b10 = float(bc.iloc[-1] / bc.iloc[-10] - 1)
    rss, moms = [], []
    for t in tickers:
        df = allpx.get(t)
        if df is None or len(df) < 70:
            continue
        c = df["Close"]
        rss.append(float(c.iloc[-1] / c.iloc[-60] - 1) - b60)
        moms.append(float(c.iloc[-1] / c.iloc[-10] - 1) - b10)
    if len(rss) < 2:
        return None
    rs, mom = float(np.mean(rss)), float(np.mean(moms))
    heat = int(round(50 + 50 * np.tanh(4 * rs + 3 * mom)))
    return {"rs": round(rs * 100, 1), "mom": round(mom * 100, 1), "heat": heat,
            "score": rs + 0.5 * mom, "n": len(rss)}


def connect_dots(allpx, bench="SPY"):
    heats = {}
    for theme, spec in THEME_GRAPH.items():
        h = _heat(allpx, spec["tickers"], bench)
        if h:
            heats[theme] = h
    if not heats:
        return {}
    ranked = sorted(heats.items(), key=lambda kv: -kv[1]["score"])
    n = len(ranked)
    for i, (theme, h) in enumerate(ranked):
        pct = i / n
        if pct < 0.25:
            h["state"] = "weakening" if h["mom"] < 0 else "hot"
        elif pct < 0.5:
            h["state"] = "heating"
        elif pct < 0.75:
            h["state"] = "early"
        else:
            h["state"] = "cold"
    hot = {t for t, h in heats.items() if h["state"] in ("hot", "weakening")}
    heating = {t for t, h in heats.items() if h["state"] in ("hot", "heating")}

    # next dots: downstream of a hot/heating theme that isn't hot yet = rotation target
    next_dots = []
    for theme in heating:
        for ds, rel in THEME_GRAPH.get(theme, {}).get("links", []):
            if ds in heats and ds not in hot:
                next_dots.append({"from": theme, "to": ds, "rel": rel,
                                  "to_state": heats[ds]["state"], "to_heat": heats[ds]["heat"]})
    # de-dup by target, keep best source
    seen = {}
    for nd in sorted(next_dots, key=lambda x: -x["to_heat"]):
        seen.setdefault(nd["to"], nd)
    next_dots = list(seen.values())

    # direction chains: hot -> linked heating -> linked early
    chains = []
    for theme in [t for t, h in ranked if h["state"] == "hot"]:
        for ds, rel in THEME_GRAPH.get(theme, {}).get("links", []):
            if ds in heats and heats[ds]["state"] in ("heating", "early"):
                chains.append(f"{theme} \u2192 {ds} ({heats[ds]['state']})")

    # bridge tickers: appear in >=2 themes, weighted to hot/heating themes
    from collections import Counter
    cnt = Counter()
    for theme, spec in THEME_GRAPH.items():
        w = 2 if theme in heating else 1
        for t in spec["tickers"]:
            cnt[t] += w
    bridges = [{"ticker": t, "themes": [th for th, sp in THEME_GRAPH.items() if t in sp["tickers"]]}
               for t, c in cnt.most_common() if len([th for th, sp in THEME_GRAPH.items() if t in sp["tickers"]]) >= 2][:6]

    return {"ranked": [{"theme": t, **h} for t, h in ranked],
            "next_dots": next_dots[:6], "chains": chains[:6], "bridges": bridges}
