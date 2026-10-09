"""Persona generator: seller data + past-call evidence -> persona spec.

Not a lookup over hand-written personas. Each field is decided from evidence
(what fixed meetings for similar sellers), then overridden by this seller's
own call history where that is more specific, and every decision carries the
reason and numbers behind it.
"""
import copy
import re
import uuid

from .evidence import EvidenceStore, Finding
from .templates import GENDER_FORMS, LANGUAGE_NAMES, fill, lines_for

STATE_LANGUAGE = {
    "Tamil Nadu": "ta", "Karnataka": "kn", "Kerala": "ml", "Telangana": "te", "Andhra Pradesh": "te",
    "West Bengal": "bn", "Gujarat": "gu", "Maharashtra": "mr", "Punjab": "pa", "Odisha": "od",
}
PACE_VALUE = {"slow": 0.85, "normal": 1.0, "fast": 1.2}
MAX_WORDS = {"slow": 16, "normal": 20, "fast": 12}
TEMPERATURE = {"casual": 0.7, "neutral": 0.6, "formal": 0.45}

# Bulbul v3 voices. Tune by ear once keys work (docs/TEAM_PLAN.md, task B3).
VOICE_MAP = {
    "female": {"casual": "neha", "neutral": "ritu", "formal": "priya"},
    "male": {"casual": "rahul", "neutral": "shubh", "formal": "aditya"},
}

ENGLISH_REQUEST = re.compile(r"\benglish\b|hindi\s+(i\s+am\s+)?not|hindi\s+nahi", re.I)


def seller_attributes(seller: dict) -> dict:
    age = seller.get("age") or 40
    age_band = "under_35" if age < 35 else ("over_50" if age > 50 else "35_50")
    return {
        "region": seller.get("region"),
        "business_type": seller.get("business_type"),
        "age_band": age_band,
        "turnover_band": _turnover_band(seller.get("annual_turnover", "")),
    }


def _turnover_band(text: str) -> str:
    m = re.match(r"\s*(\d+(?:\.\d+)?)\s*(L|Cr)", text or "", re.I)
    if not m:
        return "mid"
    crore = float(m.group(1)) / (100 if m.group(2).lower() == "l" else 1)
    return "small" if crore < 1 else ("large" if crore >= 25 else "mid")


def _first_name(name: str) -> str:
    parts = [p for p in name.replace(".", ". ").split() if not re.fullmatch(r"[A-Z]\.?", p)]
    return parts[0] if parts else name


def _last_name(name: str) -> str:
    return name.split()[-1]


def _address(seller: dict, style: str, formality: str, persona_gender: str) -> str:
    first, last = _first_name(seller["name"]), _last_name(seller["name"])
    honorific = "Ms." if seller.get("salutation") == "Ms" else "Mr."
    if style in ("english", "regional"):
        return f"{honorific} {first}" if formality != "casual" else first
    if formality == "formal":
        return f"{last} जी"
    if formality == "casual" and seller.get("salutation") == "Mr" and (seller.get("age") or 40) < 40:
        return f"{first} भाई"
    return f"{first} जी"


def _rationale(value, source: str, why: str, finding: Finding | None = None) -> dict:
    r = {"value": value, "source": source, "why": why}
    if finding is not None:
        r["evidence"] = finding.to_dict()
    return r


def _history_text(seller: dict) -> str:
    return " ".join(" ".join(c.get("seller_quotes", [])) + " " + c.get("summary", "")
                    for c in seller.get("past_calls", []))


def _past_objections(seller: dict) -> list[str]:
    seen = []
    for call in seller.get("past_calls", []):
        for o in call.get("objections", []):
            if o not in seen:
                seen.append(o)
    return seen


def generate_persona(seller: dict, evidence: EvidenceStore) -> dict:
    attrs = seller_attributes(seller)
    f = {dim: evidence.best(dim, attrs) for dim in ("language_style", "pace", "formality", "opening", "voice_gender")}
    rationale = {}
    history = _history_text(seller)
    objections = _past_objections(seller)
    known = set(seller.get("languages_known") or ["hi", "en"])
    regional = STATE_LANGUAGE.get(seller.get("state", ""))

    # --- language ---------------------------------------------------------
    style = f["language_style"].choice
    if ENGLISH_REQUEST.search(history):
        style = "english"
        rationale["language"] = _rationale(
            "english", "seller_history",
            "Seller asked for English on a past call (\"" + _quote(seller, ENGLISH_REQUEST) + "\"). "
            "Their own history beats the segment average (" + f["language_style"].summary() + ").",
            f["language_style"])
    elif style == "regional" and not (regional and regional in known):
        style = "english" if "en" in known else "hindi"
        rationale["language"] = _rationale(
            style, "rule", f"Evidence favours the regional language for this region, but the seller isn't "
            f"listed as speaking it; falling back to {style}.", f["language_style"])
    elif style in ("hindi", "hinglish") and "hi" not in known:
        style = "english"
        rationale["language"] = _rationale("english", "rule", "Seller doesn't list Hindi; using English.",
                                           f["language_style"])
    else:
        rationale["language"] = _rationale(style, "segment_evidence", f["language_style"].summary(),
                                           f["language_style"])
    language_code = {"hinglish": "hi-IN", "hindi": "hi-IN", "english": "en-IN"}.get(style, f"{regional}-IN")

    # --- pace, formality, opening -----------------------------------------
    pace = f["pace"].choice
    rationale["pace"] = _rationale(pace, "segment_evidence", f["pace"].summary(), f["pace"])

    formality = f["formality"].choice
    rationale["formality"] = _rationale(formality, "segment_evidence", f["formality"].summary(), f["formality"])

    opening = f["opening"].choice
    # A short call only means "impatient" if nothing else explains it (e.g. a language mismatch).
    short_calls = [c for c in seller.get("past_calls", [])
                   if c.get("duration_s", 999) < 60 and "language" not in c.get("objections", [])]
    if "busy" in objections or short_calls:
        why = (f"Seller cut the last call at {short_calls[0]['duration_s']}s" if short_calls else "Seller said they were busy")
        why += f"; lead with a 1-line opening. Segment evidence: {f['opening'].summary()}"
        source = "seller_history+segment_evidence" if opening == "short" else "seller_history"
        opening = "short"
        rationale["opening"] = _rationale(opening, source, why, f["opening"])
    else:
        rationale["opening"] = _rationale(opening, "segment_evidence", f["opening"].summary(), f["opening"])

    # --- voice --------------------------------------------------------------
    gender = f["voice_gender"].choice
    speaker = VOICE_MAP[gender][formality]
    rationale["voice"] = _rationale(
        {"gender": gender, "speaker": speaker, "pace": PACE_VALUE[pace]}, "segment_evidence",
        f"Gender: {f['voice_gender'].summary()}. Speaker '{speaker}' matches {formality} register; "
        f"pace {PACE_VALUE[pace]}x from the pace decision.", f["voice_gender"])

    # --- plan -----------------------------------------------------------------
    forms = GENDER_FORMS[gender]
    ctx = {
        **forms,
        "addr": _address(seller, style, formality, gender),
        "city": seller.get("city", ""),
        "category": (seller.get("categories") or ["products"])[0],
        "enq": seller.get("engagement", {}).get("enquiries_received_30d", 0),
    }
    lines = lines_for(style)
    playbook_order = objections + [k for k in lines["objections"] if k not in objections]
    playbook = {k: fill(lines["objections"][k], ctx) for k in playbook_order if k in lines["objections"]}
    rationale["objection_playbook"] = _rationale(
        list(playbook), "seller_history" if objections else "rule",
        (f"Seller raised {', '.join(objections)} before; those answers come first." if objections
         else "No call history (cold start); default objection order."))

    if not seller.get("past_calls"):
        rationale["cold_start"] = _rationale(True, "rule", "No past calls: persona built from segment evidence only.")

    persona = {
        "persona_id": f"P-{seller['seller_id']}-{uuid.uuid4().hex[:6]}",
        "version": 1,
        "seller_id": seller["seller_id"],
        "label": _label(style, pace, formality, opening),
        "voice": {"gender": gender, "speaker": speaker, "pace": PACE_VALUE[pace],
                  "temperature": TEMPERATURE[formality]},
        "language": {"code": language_code, "style": style, "name": LANGUAGE_NAMES.get(language_code, style),
                     "formality": formality, "address_as": ctx["addr"]},
        "tone": {"pace_label": pace, "max_sentence_words": MAX_WORDS[pace],
                 "warmth": "high" if formality == "formal" else "medium",
                 "energy": "high" if pace == "fast" else ("low" if pace == "slow" else "medium"),
                 "strategy": "standard"},
        "plan": {
            "opening_style": opening,
            "opening": fill(lines[f"opening_{opening}"], ctx),
            "pitch": fill(lines["pitch"] if ctx["enq"] else lines["pitch_new"], ctx),
            "meeting_ask": fill(lines["meeting_ask"], ctx),
            "objection_playbook": playbook,
            "escalation_rules": [
                "Seller asks for a human -> offer executive callback at a fixed slot (that is the goal anyway).",
                "Two frustration signals -> stop pitching, ask for one slot, close politely.",
                "Seller says no twice -> thank and end; never push a third time.",
            ],
            "guardrails": [
                "Never quote prices or promise lead numbers; say the executive will show their own data.",
                "Never claim to be human if asked.",
                "Meeting is free; never imply a payment is needed to meet.",
            ],
        },
        "rationale": rationale,
        "_ctx": ctx,
    }
    return persona


def _quote(seller: dict, pattern: re.Pattern) -> str:
    for call in seller.get("past_calls", []):
        for q in call.get("seller_quotes", []):
            if pattern.search(q):
                return q
    return ""


def _label(style: str, pace: str, formality: str, opening: str) -> str:
    return " · ".join([
        {"slow": "Patient", "normal": "Steady", "fast": "Quick"}[pace],
        style.capitalize(),
        formality.capitalize(),
        {"short": "Straight-to-the-point", "value": "Value-led", "detailed": "Explainer"}[opening],
    ])


def system_prompt(persona: dict, seller: dict) -> str:
    """Prompt for the LLM turn, also pasteable into a Sarvam Agent."""
    lang = persona["language"]
    tone = persona["tone"]
    plan = persona["plan"]
    script_rule = {
        "hinglish": "Speak natural Hinglish: Hindi words in Devanagari, English business words in Latin script.",
        "hindi": "Speak simple, respectful Hindi in Devanagari.",
        "english": "Speak clear Indian English.",
    }.get(lang["style"], f"Speak {lang['name']} in its native script; keep English business words as they are.")
    objections = "\n".join(f"- {k}: {v}" for k, v in plan["objection_playbook"].items())
    return f"""You are {persona['_ctx']['bot']}, an IndiaMART voice agent calling a seller. Your ONLY goal is to fix a free 20-minute meeting between the seller and an IndiaMART field executive (default slot: tomorrow 11 AM).

SELLER: {seller['name']} ({seller.get('company', '')}), {seller.get('business_type')} of {', '.join(seller.get('categories', []))} in {seller.get('city')}. Enquiries last 30 days: {seller.get('engagement', {}).get('enquiries_received_30d', 0)}.
Address them as: {lang['address_as']}

PERSONA ({persona['label']}):
- {script_rule}
- Formality: {lang['formality']}. Warmth: {tone['warmth']}. Energy: {tone['energy']}.
- Max {tone['max_sentence_words']} words per sentence, max 2 sentences per turn. This is a phone call.
- Current strategy: {tone['strategy']}.

OBJECTION PLAYBOOK (use the matching answer, in your own words):
{objections}

RULES:
- {chr(10).join('- ' + g for g in plan['guardrails'])[2:]}
- {chr(10).join('- ' + r for r in plan['escalation_rules'])[2:]}
- Output only the words to speak. No stage directions, no quotes, no lists."""


def clone(persona: dict) -> dict:
    return copy.deepcopy(persona)
