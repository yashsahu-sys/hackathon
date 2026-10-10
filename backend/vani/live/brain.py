"""The LLM brain: ONE structured Sarvam LLM call per seller turn that reads the
WHOLE conversation (not keywords) and returns what the seller means plus the
reply in the persona's voice.

Given: persona, global context mined from 9,657 real VANI calls, this seller's
brief (past call summaries), the call state (slots offered, days ruled out),
the full conversation, and what the fast rule detector heard (as a hint).

Returns: intent, mood, the seller's question, the slot they said, days they
can't do, whether and to WHICH slot they agreed, and the reply.

The LLM's contextual reading drives mood and agreement. Rules keep only
high-precision safety signals (do-not-call, end-call, explicit slow-down /
language requests, seller gender) and run alone when the LLM is unavailable.
Outcome lines (booked / goodbye) stay templates filled with the agreed slot.
"""
import asyncio
import json
import logging
import re
from dataclasses import dataclass, field

from vani.domain.live import CallSession, Role, Signal, SignalType as T
from vani.domain.seller import SellerContext
from vani.integrations.sarvam.client import SarvamError, SpeechAI
from vani.persona.prompt import system_prompt
from vani.text.slots import DAYS, Slot, render, suggest

log = logging.getLogger(__name__)

MOODS = ["frustration", "confusion", "rush", "slow_down", "interest", "bot_question", "human_request", "language_switch"]
INTENTS = ["agree", "propose_time", "reject_time", "question", "objection", "refuse", "end_call", "do_not_call",
           "answer", "small_talk", "unclear"]
OBJECTIONS = ["busy", "call_later", "not_interested", "price", "other_platform", "already_in_touch", "trust",
              "visit_details", "send_whatsapp", "not_ready", "value", "none"]
DAY_ENUM = list(DAYS)

_SLOT = {"type": ["object", "null"], "additionalProperties": False, "required": ["day", "hour"],
         "properties": {"day": {"type": ["string", "null"], "enum": DAY_ENUM + [None]},
                        "hour": {"type": ["integer", "null"], "description": "24h, e.g. 17 for 5 baje shaam"}}}
SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "seller_turn",
        "description": "What the seller meant in context, and the agent's next spoken reply.",
        "strict": True,
        "schema": {
            "type": "object", "additionalProperties": False,
            "required": ["intent", "mood", "seller_question", "objection", "seller_slot", "seller_cannot_days",
                         "agreed_to_meeting", "agreed_slot", "language", "reply", "slot_offered_in_reply"],
            "properties": {
                "intent": {"type": "string", "enum": INTENTS},
                "mood": {"type": "array", "items": {"type": "string", "enum": MOODS}},
                "seller_question": {"type": ["string", "null"]},
                "objection": {"type": "string", "enum": OBJECTIONS},
                "seller_slot": _SLOT,
                "seller_cannot_days": {"type": "array", "items": {"type": "string", "enum": DAY_ENUM}},
                "agreed_to_meeting": {"type": "boolean"},
                "agreed_slot": _SLOT,
                "language": {"type": "string"},
                "reply": {"type": "string"},
                "slot_offered_in_reply": _SLOT,
            },
        },
    },
}

INSTRUCTIONS = """
YOUR JOB THIS TURN
Read the WHOLE conversation, not single words. Work out what the seller means, then reply to THAT.
1 intent: agree (accepts a meeting), propose_time (suggests a day/time), reject_time (rules out a day/time we offered),
  question, objection, refuse, end_call (wants to hang up now), do_not_call (never call again), answer, small_talk, unclear.
2 mood (may be empty): frustration, confusion, rush, slow_down (asks for slower / says no hurry), interest,
  bot_question, human_request, language_switch.
3 seller_question: the seller's question in their words, or null. If not null, your reply MUST answer it first, in one sentence.
4 seller_slot: the day + hour (24h) the seller mentioned. "paanch baje" in business hours = 17. If they gave only a time,
  take the day that was being discussed.
5 seller_cannot_days: days the seller ruled out ("kal free nahi hoon" -> tomorrow). Never offer those again.
6 agreed_to_meeting: true only if the seller clearly accepts a specific meeting. agreed_slot = that exact day and hour.
  If the seller counter-proposes ("5 baje karte hain"), THEIR time is the agreed slot, not ours.
7 reply: respond to what the seller actually said, in the persona's voice. Never repeat a line you already said.
  If they ruled out a day, offer a different day. If they propose a time, accept their time. Never confirm a time
  they didn't agree to and never say a meeting is fixed unless agreed_to_meeting is true.
  frustration -> acknowledge in 3-4 words, no pitch | rush -> one sentence with concrete times |
  confusion / slow_down -> very simple words, one idea | end_call / do_not_call -> apologise and say goodbye.
8 slot_offered_in_reply: the day + hour you propose in your reply, or null.
Sound like a warm human caller, not a script: start the reply with ONE short natural acknowledgement that fits the
moment (annoyed -> a sincere one-line apology; confused -> "sorry, let me put it simply"; asked to slow down -> "sure,
slowly"; interested -> "achha ji, bahut badhiya!"; switched language -> say you'll continue in it). Never reuse an
acknowledgement already said in this call. No fillers (yaar, arre), no fake laughs or sound words.
CURIOUS SELLER: if they ask about buyers, results, cost, the process or the meeting, answer properly (2-3 short
sentences, concrete, using SELLER BRIEF facts like their category, city or enquiries) and do NOT push a slot in that
reply; end by checking if they want to know more. Propose the meeting once they seem satisfied, say "theek hai" /
"samajh gaya", or after about {info_left} more answers. Never invent numbers or promise results.
Mood calibration: a question, even a blunt one ("no no, just tell me the purpose"), is NOT frustration or rush.
Label frustration only for complaints, insults or anger; rush only when they say they're busy or want it quick.
LANGUAGE: {language_rule}
Fast keyword detector heard: {hints} (it is often wrong; trust the context). voice_fast / voice_slow / voice_raised
are measured from the seller's audio: match a fast talker with a shorter, quicker reply and a slow one with a calmer
reply; a raised voice means irritation only when the words agree.
HOW A GOOD INDIAMART CALLER SOUNDS (follow this, don't quote it):
- Talk, don't read: short spoken sentences, one thought each, contractions, natural Hinglish markers like
  "देखिए", "असल में", "बस", "अच्छा", "हाँ जी" (vary them; never two in one reply).
- Pick up the seller's own words: if they said "orders kam aa rahe hain", answer about their orders, not the script.
- Mirror their register: they speak English-heavy -> more English; pure Hindi -> fewer English words; formal -> "aap", respectful.
- Use their business or city when it helps ("आपके plywood business के लिए"), never their phone number or personal details.
- One question per reply, at the end. No lists, no "Firstly", no brackets, no emojis.
- Good: "अच्छा जी, समझ गई। देखिए, बस 20 मिनट की free meeting है, executive खुद आएँगे। कल शाम 5 बजे ठीक रहेगा?"
- Bad: "हमारी सेवा के निम्नलिखित लाभ हैं: 1) ... कृपया बताएं।" (written, robotic, a list)."""


@dataclass
class BrainResult:
    intent: str = "unclear"
    signals: set[T] = field(default_factory=set)
    question: str | None = None
    objection: str | None = None
    seller_slot: Slot | None = None
    cannot: set[str] = field(default_factory=set)
    agreed: bool = False
    agreed_slot: Slot | None = None
    language: str | None = None
    reply: str = ""
    offered: Slot | None = None


LANG_NAMES = {"en-IN": "English", "hi-IN": "Hinglish (Hindi in Devanagari with English business words)",
              "ta-IN": "Tamil", "te-IN": "Telugu", "kn-IN": "Kannada", "ml-IN": "Malayalam", "bn-IN": "Bengali",
              "gu-IN": "Gujarati (Gujarati script with English business words in Latin)", "mr-IN": "Marathi", "pa-IN": "Punjabi", "od-IN": "Odia"}


def language_rule(current: str, switch_to: str | None) -> str:
    if switch_to and switch_to != current:
        name = LANG_NAMES.get(switch_to, switch_to)
        return f"The seller just switched to {name}. Write the reply ONLY in {name}, from this turn on."
    return ("Reply in the language of the seller's LAST message. If they switch language, switch with them; "
            f"otherwise use {LANG_NAMES.get(current, current)}.")


def call_state_text(session: CallSession) -> tuple[str, list[Slot]]:
    offered = [Slot.from_dict(d) for d in session.offered_slots]
    unavailable = set(session.unavailable_days)
    nxt = suggest(unavailable, offered)
    lines = [
        "- Slots already offered: " + (", ".join(render(s, "english") for s in offered) or "none"),
        "- Seller ruled out: " + (", ".join(sorted(unavailable)) or "nothing"),
        "- If you propose times, use: " + " or ".join(render(s, "english") for s in nxt)
        + " (they respect the seller's constraints and match when sellers usually agree)",
    ]
    if session.agreed_slot:
        lines.append(f"- Agreed slot so far: {render(Slot.from_dict(session.agreed_slot), 'english')}")
    return "\n".join(lines), nxt


class LLMBrain:
    def __init__(self, speech: SpeechAI, global_context: str = "", timeout_s: float = 5.0):
        self.speech = speech
        self.global_context = global_context
        self.timeout_s = timeout_s
        self._format: dict = SCHEMA       # downgraded to json_object if the API rejects json_schema

    @property
    def enabled(self) -> bool:
        return bool(getattr(self.speech, "enabled", False))

    def messages(self, session: CallSession, ctx: SellerContext, text: str, hints: list[str], brief: str,
                 switch_to: str | None = None) -> list[dict]:
        sys = system_prompt(session.persona, ctx.profile)
        sys = sys.replace("Output only the words to speak: plain sentences, standard punctuation, no lists, no markdown, no notes.",
                          "The reply field holds only the words to speak: plain sentences, no lists, no markdown, no notes.")
        state, _ = call_state_text(session)
        sys += ("\n\nWHAT REAL VANI CALLS TELL US ABOUT SELLERS:\n" + (self.global_context or "- (no data loaded)")
                + "\n\nTHIS SELLER:\n" + brief + "\n\nCALL STATE:\n" + state
                + INSTRUCTIONS.replace("{hints}", ", ".join(hints) or "nothing").replace("{language_rule}", language_rule(
                    session.persona.language.code, switch_to)).replace(
                    "{info_left}", str(max(0, 2 - session.info_turns)))
                + "\nReturn ONLY the JSON object.")
        msgs = [{"role": "system", "content": sys}]
        for t in session.transcript[-14:]:
            msgs.append({"role": "assistant" if t.role == Role.bot else "user", "content": t.text})
        if msgs[-1]["role"] != "user" or msgs[-1]["content"] != text:
            msgs.append({"role": "user", "content": text})
        return msgs

    async def think(self, session: CallSession, ctx: SellerContext, text: str, hints: list[str],
                    brief: str = "", switch_to: str | None = None) -> BrainResult | None:
        if not self.enabled:
            return None
        msgs = self.messages(session, ctx, text, hints, brief, switch_to)
        attempts = [self._format] + ([{"type": "json_object"}] if self._format is SCHEMA else [])
        for fmt in attempts:
            try:
                raw = await asyncio.wait_for(self.speech.chat(msgs, max_tokens=500, response_format=fmt), self.timeout_s)
            except SarvamError as exc:
                if exc.status in (400, 422) and fmt is SCHEMA:
                    log.warning("json_schema rejected (%s); falling back to json_object", exc)
                    self._format = {"type": "json_object"}
                    continue
                log.warning("LLM brain unavailable: %s", exc)
                return None
            except asyncio.TimeoutError:
                log.warning("LLM brain timed out")
                return None
            return parse(raw)
        return None


def _slot(d) -> Slot | None:
    if not isinstance(d, dict):
        return None
    day = d.get("day") if d.get("day") in DAYS else None
    hour = d.get("hour") if isinstance(d.get("hour"), int) and 0 <= d.get("hour") <= 23 else None
    return Slot(day, hour) if day or hour is not None else None


def parse(raw: str) -> BrainResult | None:
    m = re.search(r"\{.*\}", raw or "", re.S)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    if not isinstance(d, dict):
        return None
    intent = d.get("intent") if d.get("intent") in INTENTS else "unclear"
    sig = {T(x) for x in d.get("mood") or d.get("signals") or [] if x in MOODS}
    sig |= {T(x) for x in d.get("signals") or [] if x in ("end_call", "do_not_call", "refusal", "agreement")}
    sig |= {"refuse": {T.refusal}, "end_call": {T.end_call}, "do_not_call": {T.do_not_call}}.get(intent, set())
    agreed = bool(d.get("agreed_to_meeting"))
    if agreed:
        sig.add(T.agreement)
    else:
        sig.discard(T.agreement)
    obj = d.get("objection")
    return BrainResult(
        intent=intent, signals=sig, question=d.get("seller_question") or None,
        objection=None if obj in (None, "none") else obj, seller_slot=_slot(d.get("seller_slot")),
        cannot={x for x in d.get("seller_cannot_days") or [] if x in DAYS}, agreed=agreed,
        agreed_slot=_slot(d.get("agreed_slot")), language=d.get("language") or None,
        reply=str(d.get("reply") or "").strip(), offered=_slot(d.get("slot_offered_in_reply")))


# Rule signals precise enough to keep even when the LLM reads the turn differently.
HARD_RULE_SIGNALS = {T.do_not_call, T.end_call, T.slow_down, T.seller_gender, T.seller_pace}   # seller_pace is measured from audio


def contextual_merge(rule_signals: list[Signal], brain: BrainResult | None, text: str,
                     current_language: str | None = None) -> tuple[list[Signal], list[str]]:
    """LLM context decides mood and agreement; rules keep only hard safety signals."""
    if brain is None:
        return rule_signals, []
    keep = [s for s in rule_signals if s.type in HARD_RULE_SIGNALS
            or (s.type == T.language_switch and s.confidence >= 0.9)]
    dropped = sorted({s.type.value for s in rule_signals} - {s.type.value for s in keep} - {x.value for x in brain.signals})
    have = {s.type for s in keep}
    out = list(keep)
    lang = brain.language if brain.language in LANG_NAMES else None
    if T.language_switch not in have and lang and (T.language_switch in brain.signals or current_language
                                                    and lang != current_language):
        if current_language is None or lang != current_language:
            out.append(Signal(type=T.language_switch, confidence=0.8, trigger=text[:80],
                              detail={"to": lang, "source": "llm"}))
            have.add(T.language_switch)
    for t in sorted(brain.signals - have - {T.language_switch}, key=lambda x: x.value):
        out.append(Signal(type=t, confidence=0.8, trigger=text[:80], detail={"source": "llm", "intent": brain.intent}))
    notes = []
    if dropped:
        notes.append(f"context overrode keyword match: rules heard {', '.join(dropped)}; LLM read intent={brain.intent}")
    if {T.do_not_call, T.end_call} & {s.type for s in out}:
        out = [s for s in out if s.type != T.agreement]
    return out, notes
