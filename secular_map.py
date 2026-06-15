"""bottleneck.py - secular bottleneck + supplier-graph map. CURATED from Edward's attachments
(Citrini bottleneck-migration, Aschenbrenner OOM, Serenity dependency-graph, SpaceX suppliers).
This is a thesis map (no live feed) feeding the Bottleneck tab. My own structure, not the zip's."""

CHAIN = ["GPU compute", "Networking", "Power / grid", "Cooling / photonics"]

THEMES = [
    {"name":"AI power", "bottleneck":"Grid / substations", "crowding":"mid",
     "note":"GPU → networking → power (now). Beneficiary: utility capex, transformers, power electronics."},
    {"name":"Silicon photonics", "bottleneck":"CPO / packaging", "crowding":"early",
     "note":"Networking → optical interconnect. Beneficiary: co-packaged optics, coherent transceivers, substrate."},
    {"name":"Space supply chain", "bottleneck":"Metallurgy / composites", "crowding":"uncrowded",
     "note":"Launch cadence → materials. Beneficiary: titanium/superalloys, composites, thermal/RF."},
]

# supplier graph for the space theme (layered: obvious vs hidden) + valuation/crowding tags
SUPPLIER_LAYERS = {
    "Layer 1 — obvious": [{"t":"RKLB","tag":"crowded"},{"t":"ASTS","tag":"crowded"},{"t":"LUNR","tag":"crowded"}],
    "Layer 3-4 — hidden": [{"t":"ATI","tag":"uncrowded","note":"titanium/superalloys · ~13x '26"},
                            {"t":"MTRN","tag":"uncrowded","note":"beryllium/coatings · niche"},
                            {"t":"PKE","tag":"uncrowded","note":"composites · ultra-underfollowed"},
                            {"t":"KTOS","tag":"semi-crowded","note":"propulsion/hypersonics · premium"}],
}

def map():
    return {"chain": CHAIN, "themes": THEMES, "suppliers": SUPPLIER_LAYERS}
