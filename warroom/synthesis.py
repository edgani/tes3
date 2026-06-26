"""warroom/synthesis.py — the decision brain.

Every other module is a SENSOR. This one is the integrator: it takes all the layer signals already
attached to a setup (walk-forward gate, timing/anti-FOMO, intervention, mechanical/rebalance,
regime alignment, TF confluence, crowd, liquidity) plus market-wide context (month-end flow,
vol-target deleveraging) and resolves them into ONE call:

    ACT · ACT-SMALL · WAIT · AVOID · EXIT-WATCH

with the layers that AGREE (for) vs CONFLICT (against), and a confidence that reflects how
unanimous the layers are (high agreement → high confidence; a split book → low).
"""
from __future__ import annotations


def decide(s, ctx=None):
    ctx = ctx or {}
    direction = s.get("_dir")
    if direction not in ("Long", "Short"):
        return None
    votes = []  # (layer, signed_weight, note)

    g = (s.get("gate") or {}).get("status")
    if g == "PASS":
        votes.append(("gate", 2.0, "walk-forward PASS"))
    elif g == "FAIL":
        votes.append(("gate", -2.0, "failed OOS validation"))

    t = s.get("timing") or {}
    fomo = t.get("anti_fomo", "")
    if "EARLY" in fomo:
        votes.append(("timing", 2.0, "early — ahead of crowd"))
    elif "ON-TIME" in fomo:
        votes.append(("timing", 1.0, "on-time entry"))
    elif "LATE" in fomo:
        votes.append(("timing", -2.0, "late / FOMO — don't chase"))
    if str(t.get("phase", "")).startswith("Distribution"):
        votes.append(("cycle", -1.0, "distribution phase"))

    iv = s.get("intervention") or {}
    ivk = iv.get("kind", "")
    if ivk.startswith("FX-intervention") or ivk == "ARA-ARB":
        lvl = iv.get("level")
        if lvl == "high":
            votes.append(("intervention", -3.0, "high intervention / auto-reject risk"))
        elif lvl == "elevated":
            votes.append(("intervention", -1.5, "elevated intervention risk"))
        elif lvl == "note":
            votes.append(("intervention", 0.5, "intervention is a tailwind here"))
    elif ivk == "event":
        votes.append(("event", -0.5, "CB decision risk near"))

    if s.get("mechanical"):
        votes.append(("rebalance", 0.5, "scheduled rebalance — be positioned ahead"))
    me = ctx.get("month_end")
    if isinstance(me, dict):
        d_ = me.get("direction", "")
        if "SELL" in d_ and direction == "Long":
            votes.append(("month-end", -1.0, "month-end equity selling"))
        elif "BUY" in d_ and direction == "Long":
            votes.append(("month-end", 1.0, "month-end equity buying"))
        elif "SELL" in d_ and direction == "Short":
            votes.append(("month-end", 1.0, "month-end selling aids short"))
    vt = ctx.get("vol_target")
    if isinstance(vt, dict) and direction == "Long":
        votes.append(("vol-target", -1.0, "vol-target deleveraging pressure"))

    posture = str(ctx.get("posture", ""))
    if posture:
        on = "On" in posture or "on" in posture
        off = "Off" in posture or " defensive" in posture.lower()
        if (on and direction == "Long") or (off and direction == "Short"):
            votes.append(("regime", 1.0, "aligned with regime"))
        elif (off and direction == "Long") or (on and direction == "Short"):
            votes.append(("regime", -1.0, "against regime"))

    cf = s.get("conf") or {}
    if cf.get("conviction") == "STRONG":
        votes.append(("confluence", 1.0, "multi-TF aligned"))
    elif cf.get("conviction") == "PARTIAL":
        votes.append(("confluence", 0.3, "TF partially aligned"))

    cr = s.get("crowd") or {}
    if cr.get("state") == "frothy" and direction == "Long":
        votes.append(("crowd", -1.5, "crowd already euphoric here"))
    elif cr.get("state") == "washed" and direction == "Long":
        votes.append(("crowd", 1.0, "crowd capitulated — contrarian"))
    elif cr.get("state") == "frothy" and direction == "Short":
        votes.append(("crowd", 1.0, "shorting into euphoria"))

    lq = s.get("liquidity") or {}
    if lq.get("illiquid"):
        votes.append(("liquidity", -1.0, "thin — exit at size is hard"))

    # price-action / volume-truth (read the tape first; volume is the truth)
    pa = s.get("pa") or {}
    vv, er, ch = pa.get("vol_verdict", ""), pa.get("effort_result", ""), pa.get("character", "")
    if pa:
        if "distribution" in vv and direction == "Long":
            votes.append(("volume", -2.0, "heavy-volume selling — distribution"))
        elif "real demand" in vv and direction == "Long":
            votes.append(("volume", 1.5, "heavy-volume buying — real demand"))
        elif "weak rally" in vv and direction == "Long":
            votes.append(("volume", -1.0, "light-volume rally — suspect"))
        elif "no buyers" in vv and direction == "Long":
            votes.append(("volume", 0.5, "light-volume drop — not aggressive selling"))
        if "real demand" in vv and direction == "Short":
            votes.append(("volume", -1.5, "heavy-volume buying works against the short"))
        if er == "absorption":
            votes.append(("absorption", 1.0, "absorption — smart money soaking supply/demand"))
        if "capitulation" in ch and direction == "Long":
            votes.append(("character", 1.0, "capitulation washout — contrarian"))
        elif "euphoria" in ch and direction == "Long":
            votes.append(("character", -1.5, "blow-off euphoria — fade, don't chase"))
        elif "blow-off" in ch and direction == "Short":
            votes.append(("character", 1.0, "shorting into a blow-off"))

    # swing structure (tops/bottoms, neckline breaks) — the objective chart pattern
    st = s.get("structure") or {}
    patt, brk, tr = st.get("pattern", ""), st.get("broke"), st.get("trend", "")
    if st:
        if brk == "down" and direction == "Long":
            votes.append(("structure", -2.5 if "distribution" in vv else -2.0, "distribution top — neckline broken"))
        elif brk == "up" and direction == "Long":
            votes.append(("structure", 1.5, "accumulation base — broke out"))
        elif brk == "down" and direction == "Short":
            votes.append(("structure", 1.5, "shorting a confirmed neckline break"))
        if "topping" in patt and brk is None and direction == "Long":
            votes.append(("structure", -0.5, "topping — multiple tests, watch the neckline"))
        if tr.startswith("downtrend") and direction == "Long":
            votes.append(("trend-struct", -1.0, "fighting a downtrend (lower highs/lows)"))
        elif tr.startswith("uptrend") and direction == "Long":
            votes.append(("trend-struct", 0.5, "with the uptrend"))

    net = sum(w for _, w, _ in votes)
    fav = [(l, n) for l, w, n in votes if w > 0]
    against = [(l, n) for l, w, n in votes if w < 0]

    hard_avoid = (ivk.startswith("FX-intervention") or ivk == "ARA-ARB") and iv.get("level") == "high"
    exiting = "LATE" in fomo and str(t.get("phase", "")).startswith("Distribution")
    if exiting:
        call = "EXIT-WATCH"
    elif hard_avoid:
        call = "AVOID"
    elif net >= 4:
        call = "ACT"
    elif net >= 1.5:
        call = "ACT-SMALL"
    elif net >= -1:
        call = "WAIT"
    else:
        call = "AVOID"

    tot = sum(abs(w) for _, w, _ in votes) or 1
    agree = abs(net) / tot
    conf = "high" if agree >= 0.6 else ("medium" if agree >= 0.3 else "low")

    # staged plan (rule-based lifecycle) for an actionable call
    plan = ""
    if call in ("ACT", "ACT-SMALL"):
        half = "full size" if call == "ACT" else "half size"
        plan = f"scale in {half} now; add on pullback to entry zone; move stop to breakeven at +1R; take 1/3 at target, trail the rest under the TREND band"
    elif call == "WAIT":
        plan = "no edge yet — wait for the conflicting layer(s) to clear or price to reach the entry zone"
    elif call == "AVOID":
        plan = "stand aside — risk layers outweigh the setup"
    elif call == "EXIT-WATCH":
        plan = "manage the exit — scale out into strength, tighten stop ahead of the crowd"

    return {"call": call, "net": round(net, 1), "confidence": conf,
            "for": fav, "against": against, "n_for": len(fav), "n_against": len(against),
            "plan": plan}
