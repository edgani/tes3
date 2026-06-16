"""warroom/secular_map.py — secular bottleneck thesis map.
ENCODES the two attachments: (1) AI Infrastructure Roadmap timeline + Next-Gen GPU-HBM roadmap,
(2) AI Buildout Supply Chain (12 layers + power + thermal). Beneficiary tickers = thesis map
(public companies), not a forecast. Feeds the Bottleneck tab + Alpha Center watchlist.
"""
CHAIN = ["GPU compute", "Networking", "Power / grid", "Cooling / photonics"]

# ATTACHMENT 1a: AI Infrastructure Roadmap
ROADMAP = [
    {"era": "Now",  "tech": "Memory + optical transceivers", "bottleneck": "HBM + optics",
     "tickers": ["MU", "COHR", "LITE", "FN", "CRDO", "ALAB"]},
    {"era": "2027", "tech": "800V power + early CPO", "bottleneck": "power delivery + co-packaged optics",
     "tickers": ["VRT", "ETN", "MPWR", "VICR", "COHR", "CRDO"]},
    {"era": "2028", "tech": "PLP + scale-up optical", "bottleneck": "panel-level packaging",
     "tickers": ["AMKR", "ASX", "COHR", "ANET"]},
    {"era": "2029", "tech": "Glass substrates + HBM5", "bottleneck": "substrate + memory",
     "tickers": ["GLW", "MU", "AMAT", "LRCX"]},
    {"era": "2030", "tech": "Optical I/O chiplets + embedded cooling", "bottleneck": "optical I/O + thermal",
     "tickers": ["AVGO", "MRVL", "VRT", "FN"]},
    {"era": "2031", "tech": "3D DRAM + microfluidic cooling", "bottleneck": "3D memory + cooling",
     "tickers": ["MU", "AMAT", "VRT", "ENTG"]},
]
# ATTACHMENT 1b: Next-Gen GPU-HBM roadmap (KAIST/TERA)
GPU_HBM = [
    {"arch": "Rubin (2026)",        "power": "800 W",   "hbm": "HBM4x8",  "bw": "16/32 TB/s",   "total_power": "2,200 W"},
    {"arch": "Feynman (2029)",      "power": "900 W",   "hbm": "HBM5x8",  "bw": "48 TB/s",      "total_power": "4,400 W"},
    {"arch": "Post-Feynman (2032)", "power": "1,000 W", "hbm": "HBM6x16", "bw": "128/256 TB/s", "total_power": "5,920 W"},
    {"arch": "Next-Gen (2035)",     "power": "1,200 W", "hbm": "HBM7x32", "bw": "1,024 TB/s",   "total_power": "15,360 W"},
]
# ATTACHMENT 2: AI Buildout Supply Chain (12 layers, bedrock L12)
SUPPLY_CHAIN = [
    {"n": 1,  "layer": "Application",              "tickers": ["MSFT", "GOOGL", "CRM", "NOW"]},
    {"n": 2,  "layer": "AI Model",                 "tickers": ["MSFT", "GOOGL", "META"]},
    {"n": 3,  "layer": "Software Infrastructure",  "tickers": ["NVDA", "SNOW", "DDOG"]},
    {"n": 4,  "layer": "Cloud Infrastructure",     "tickers": ["AMZN", "MSFT", "GOOGL", "NBIS", "ORCL"]},
    {"n": 5,  "layer": "Compute Hardware",         "tickers": ["NVDA", "AMD", "AVGO", "MRVL"]},
    {"n": 6,  "layer": "Memory (HBM)",             "tickers": ["MU"]},
    {"n": 7,  "layer": "Interconnect (optics/CPO)", "tickers": ["ANET", "COHR", "LITE", "FN", "CRDO", "ALAB"]},
    {"n": 8,  "layer": "Advanced Packaging",       "tickers": ["AMKR", "ASX", "GLW"]},
    {"n": 9,  "layer": "Semiconductor Foundry",    "tickers": ["TSM", "INTC", "GFS"]},
    {"n": 10, "layer": "Semiconductor Equipment",  "tickers": ["AMAT", "LRCX", "KLAC", "ASML", "MKSI", "ENTG"]},
    {"n": 11, "layer": "Semiconductor Materials",  "tickers": ["ENTG", "ATI", "MTRN"]},
    {"n": 12, "layer": "Critical Minerals (bedrock)", "tickers": ["MP", "ATI", "FCX"]},
]
POWER_RAIL = {"name": "Power infrastructure (atoms)", "sub": "generation · grid · DC power · power semis",
              "tickers": ["VRT", "ETN", "PWR", "GEV", "CEG", "VST", "NRG", "TLN", "HUBB", "ON", "WOLF"]}
THERMAL_RAIL = {"name": "Thermal management", "sub": "air -> direct-chip -> immersion -> two-phase -> microfluidic",
                "tickers": ["VRT", "ETN"]}
THEMES = [
    {"name": "AI power", "bottleneck": "Grid / substations", "crowding": "mid",
     "note": "GPU -> networking -> power (now). Beneficiary: utility capex, transformers, power electronics."},
    {"name": "Silicon photonics / CPO", "bottleneck": "CPO / packaging", "crowding": "early",
     "note": "Networking -> optical interconnect (2027-28 CPO). Beneficiary: co-packaged optics, coherent transceivers."},
    {"name": "HBM / 3D DRAM", "bottleneck": "Memory stacking", "crowding": "mid",
     "note": "HBM4 -> HBM7, 8 -> 32 stacks by 2035. Beneficiary: HBM makers, packaging, equipment."},
    {"name": "Glass substrates", "bottleneck": "Panel-level packaging", "crowding": "early",
     "note": "2028-29 PLP + glass-core substrates. Beneficiary: substrate, advanced packaging."},
    {"name": "Embedded / microfluidic cooling", "bottleneck": "Thermal density", "crowding": "early",
     "note": "Total power 2.2kW -> 15.4kW per module by 2035 -> cooling is the wall."},
    {"name": "Space supply chain", "bottleneck": "Metallurgy / composites", "crowding": "uncrowded",
     "note": "Launch cadence -> materials. Beneficiary: titanium/superalloys, composites, thermal/RF."},
]
SUPPLIER_LAYERS = {
    "Layer 1 — obvious": [{"t": "RKLB", "tag": "crowded"}, {"t": "ASTS", "tag": "crowded"}, {"t": "LUNR", "tag": "crowded"}],
    "Layer 3-4 — hidden": [{"t": "ATI", "tag": "uncrowded", "note": "titanium/superalloys"},
                           {"t": "MTRN", "tag": "uncrowded", "note": "beryllium/coatings"},
                           {"t": "PKE", "tag": "uncrowded", "note": "composites"},
                           {"t": "KTOS", "tag": "semi-crowded", "note": "propulsion/hypersonics"}],
}

def map():
    return {"chain": CHAIN, "roadmap": ROADMAP, "gpu_hbm": GPU_HBM, "supply_chain": SUPPLY_CHAIN,
            "power_rail": POWER_RAIL, "thermal_rail": THERMAL_RAIL, "themes": THEMES, "suppliers": SUPPLIER_LAYERS}

def thesis_tickers():
    out = set()
    for r in ROADMAP: out.update(r["tickers"])
    for l in SUPPLY_CHAIN: out.update(l["tickers"])
    out.update(POWER_RAIL["tickers"])
    return sorted(out)
