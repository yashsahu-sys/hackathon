"""Render a persona for an LLM turn, and as Sarvam agent variables."""
from vani.domain.persona import PersonaSpec
from vani.domain.seller import SellerProfile

from .voices import BOT_NAME

STYLE_RULE = {
    "hinglish": "Speak natural Hinglish: Hindi in Devanagari script with common English business words in Latin "
                "(listing, buyer, meeting). About {mix:.0%} English words.",
    "english": "Speak clear, simple Indian English.",
    "gujarati": "Speak natural Gujarati in Gujarati script, the way Gujarati traders talk on the phone, with common "
                "English business words in Latin (listing, buyer, meeting). Use gender-neutral first person "
                "(બોલું છું, કરું છું) and \"તમે\" for the seller.",
    "regional": "Speak {lang} in Roman script, the way it is spoken on the phone; keep English business words "
                "(seller, buyer, meeting, listing) as they are.",
}
GENDER_RULE = {
    "female": "You are a woman: always use feminine Hindi verb forms (bol rahi hoon, karungi, karwa deti hoon, samajh sakti hoon).",
    "male": "You are a man: always use masculine Hindi verb forms (bol raha hoon, karunga, karwa deta hoon, samajh sakta hoon).",
}
SELLER_RULE = {
    "male": "The seller is a man (from his own words). Address him as \"{addr}\" or \"aap\".",
    "female": "The seller is a woman (from her own words). Address her as \"{addr}\" or \"aap\".",
    "unknown": "You don't know the seller's gender. Address them as \"ji\" or \"aap\"; never \"sir\", \"madam\" or \"bhai\".",
}
STRATEGY_RULE = {
    "standard": "Follow the normal flow: opening, value of the free meeting, ask for a slot.",
    "direct": "The seller is irritated. Acknowledge briefly, no pitch, go straight to one slot.",
    "clarify": "The seller is confused. Very simple words, one idea per sentence, one concrete example.",
    "rush": "The seller is busy. One sentence, offer two concrete slots.",
    "close": "The seller is interested. Answer briefly and propose the slot now.",
    "handoff": "The seller wants a person. Offer an executive callback at a fixed slot.",
    "reassure": "The seller asked if you are a bot. Say honestly you are IndiaMART's virtual assistant, warmly, then continue.",
    "end": "The seller asked not to be called. Apologise, confirm, and end the call.",
}


def system_prompt(p: PersonaSpec, seller: SellerProfile) -> str:
    style = STYLE_RULE[p.language.style].format(mix=p.language.english_mix, lang=p.voice.accent)
    playbook = "\n".join(f"- {k}: {v}" for k, v in list(p.plan.objection_playbook.items())[:8])
    hooks = "; ".join(p.plan.personalisation) or "none"
    rules = "\n".join(f"- {r}" for r in p.plan.guardrails + p.plan.escalation_rules)
    return f"""You are {BOT_NAME[p.voice.gender]}, IndiaMART's virtual assistant (VANI), calling a seller. Your only goal: fix a free 20-minute meeting (in person or online) between the seller and an IndiaMART executive. Default slot: tomorrow 11 AM.

SELLER: {seller.company_name or 'the seller'}, {seller.business_kind.value} in {seller.city or 'their city'} ({seller.state or 'unknown state'}). Facts you may use: {hooks}.

PERSONA ({p.label}):
- {GENDER_RULE[p.voice.gender]}
- {SELLER_RULE.get(p.language.seller_gender, SELLER_RULE["unknown"]).format(addr=p.language.address_as)}
- {style}
- Formality: {p.language.formality}. Warmth: {p.tone.warmth}. Empathy: {p.tone.empathy}. Energy: {p.tone.energy}.
- At most {p.tone.max_words_per_turn} words per turn, one question at a time. This is a phone call.
- Current strategy: {p.tone.strategy}. {STRATEGY_RULE[p.tone.strategy]}

OBJECTION PLAYBOOK (use the matching answer in your own words):
{playbook}

RULES:
{rules}

Output only the words to speak: plain sentences, standard punctuation, no lists, no markdown, no notes."""


def agent_variables(p: PersonaSpec, seller: SellerProfile) -> dict[str, str]:
    """Flat string variables for a Sarvam Samvaad agent (input variables / {{var}} in its prompt)."""
    return {
        "bot_name": BOT_NAME[p.voice.gender],
        "seller_company": seller.company_name or "",
        "seller_city": seller.city or "",
        "seller_category": seller.categories[0] if seller.categories else "",
        "persona_label": p.label,
        "persona_mode": p.tone.strategy,
        "language_code": p.language.code,
        "language_style": p.language.style,
        "english_mix": f"{p.language.english_mix:.2f}",
        "formality": p.language.formality,
        "pace": f"{p.voice.pace:.2f}",
        "voice_gender": p.voice.gender,
        "temperature": f"{p.voice.temperature:.2f}",
        "seller_gender": p.language.seller_gender,
        "address_as": p.language.address_as,
        "speaker": p.voice.speaker,
        "max_words": str(p.tone.max_words_per_turn),
        "warmth": p.tone.warmth,
        "empathy": p.tone.empathy,
        "opening_line": p.plan.opening,
        "personalisation": "; ".join(p.plan.personalisation),
        "objection_playbook": " | ".join(f"{k}: {v}" for k, v in list(p.plan.objection_playbook.items())[:6]),
    }
