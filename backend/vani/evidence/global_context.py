"""Global context about Indian sellers on VANI calls (from the evidence book) and a
short brief about THIS seller, both written into the LLM brain's system prompt so
it decides from what actually happens on these calls, not generic sales advice."""
from vani.domain.seller import SellerContext
from vani.evidence.book import EvidenceBook


def _h(h: int) -> str:
    return f"{(h - 1) % 12 + 1} {'AM' if h < 12 else 'PM'}"


def render_global(book: EvidenceBook) -> str:
    g = book.raw.get("global") or {}
    b = book.baseline or {}
    lines = []
    if b.get("n"):
        lines.append(f"- {b['n']:,} past VANI seller calls; {b['meeting_rate']:.0%} ended in a meeting.")
    f = book.get("OUT-early_drop_share")
    if f:
        lines.append(f"- {f['rate']:.0%} of sellers hang up within 20 seconds: say who you are and why in the first line.")
    for fid, txt in (("OUT-confused", "were confused"), ("OUT-busy", "were busy"), ("OUT-bot_question", "asked if it's a bot"),
                     ("OUT-not_interested", "said not interested")):
        x = book.get(fid)
        if x and x["n"]:
            lines.append(f"- When sellers {txt}, only {x['rate']:.0%} fixed a meeting (vs {x['base_rate']:.0%}): handle it, don't push past it.")
    for fid, txt in (("OUT-visit", "the visit/location"), ("OUT-price", "price")):
        x = book.get(fid)
        if x and x["n"]:
            lines.append(f"- Calls that discussed {txt} fixed {x['rate']:.0%} meetings: answer such questions directly.")
    if g.get("agreed_meeting_hours"):
        hrs = ", ".join(_h(x["hour"]) for x in g["agreed_meeting_hours"][:3])
        lines.append(f"- Sellers most often agree to meetings at {hrs}; most agree to 'tomorrow' or Monday; Sunday is rare.")
    if g.get("worst_call_hours"):
        w = ", ".join(_h(x["hour"]) for x in g["worst_call_hours"])
        lines.append(f"- Around {w} sellers are busiest (lowest meeting rate): be extra brief then.")
    mix = book.get("TRN-language_mix")
    if mix:
        lines.append(f"- {mix['rate']:.0%} of sellers answer in Hinglish; switch only if the seller does.")
    lines.append("- Online meetings are an accepted fallback for sellers who can't host a visit.")
    return "\n".join(lines)


def render_seller_brief(ctx: SellerContext, max_calls: int = 2) -> str:
    p = ctx.profile
    out = []
    summaries = [c for c in ctx.calls if c.summary][:max_calls]
    for c in summaries:
        when = c.started_at.strftime("%d %b") if c.started_at else "earlier"
        out.append(f"- Past call ({when}, {c.disposition or 'unknown outcome'}): {c.summary[:240]}")
    h = p.bot_history
    if h.in_touch_with_executive:
        out.append("- Already in touch with an IndiaMART executive.")
    if h.do_not_call:
        out.append("- Has asked not to be called before.")
    return "\n".join(out) or "- No past call summaries."
