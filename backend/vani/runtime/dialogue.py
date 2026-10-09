"""Dialogue policy: what VANI says next. Deterministic, so the call flow is the
same whether the words come from templates (offline) or the LLM (live): the
policy picks the move, the LLM only phrases it in the persona's voice."""
import re
from dataclasses import dataclass

from vani.domain.live import CallSession, Outcome, Role, SignalType as T
from vani.persona.generator import _gender_forms
from vani.persona.lines import lines_for

SLOT = re.compile(r"\b\d{1,2}\s*(baje|bje|am|pm|o'?clock)\b|बजे|\b(kal|tomorrow|subah|shaam|morning|evening)\b", re.I)

OBJECTION_TEXT = {k: re.compile(p, re.I) for k, p in {
    "price": r"paisa|paise|पैसे|charge|kitne ka|\bcost|\bfees?\b|kharcha|खर्चा|\bpaid\b|price",
    "send_whatsapp": r"whatsapp|व्हाट्सऐप|व्हाट्सएप",
    "other_platform": r"tradeindia|justdial|alibaba|(doosri|dusri|dusre|doosre) jagah|other (platform|portal)",
    "already_in_touch": r"already (baat|mil|spoke|talked|in touch)|pehle (se|bhi) (baat|mil)|executive (aaya|aa chuka|aaye the)",
    "trust": r"fraud|fake|bharosa|भरोसा|\btrust\b|privacy|mera data",
    "visit_details": r"\bkahan\b|\bkidhar\b|kitne der|kitna time|\bonline\b|address|kaise aayeng|कहाँ|कितनी देर",
    "call_later": r"(baad|bad) (me|mein) (call|phone|baat)|call (me )?later|शाम को|kal (call|phone|baat)",
}.items()}


@dataclass
class Move:
    key: str                 # which line/playbook entry
    text: str                # template rendering (offline reply, and LLM reference)
    hint: str                # instruction for the LLM
    stage: str
    outcome: Outcome | None = None
    end_call: bool = False


def _line(session: CallSession, key: str) -> str:
    p = session.persona
    return _gender_forms(lines_for(p.language.style)[key], p.voice.gender)


def _play(session: CallSession, key: str) -> str:
    return session.persona.plan.objection_playbook.get(key) or _gender_forms(
        lines_for(session.persona.language.style)["playbook"][key], session.persona.voice.gender)


def next_move(session: CallSession, text: str, types: set[T], strategy_used: str | None) -> Move:
    p = session.persona
    stage = session.stage
    ask = _line(session, "meeting_ask")

    if stage == "done":
        key = "meeting_confirm" if session.outcome == Outcome.meeting_fixed else "close_no"
        return Move(key, _line(session, key), "The call is over; say a one-line goodbye.", "done", end_call=True)
    if T.end_call in types:
        return Move("end_close", _line(session, "end_close"),
                    "Seller wants to end the call. Apologise in one short sentence and say goodbye. Do not pitch.",
                    "done", Outcome.declined, True)
    if T.do_not_call in types:
        return Move("dnc_close", _line(session, "dnc_close"),
                    "Seller asked not to be called. Apologise, confirm they won't be called about this, end.",
                    "done", Outcome.declined, True)
    blocked = types & {T.frustration, T.refusal, T.rush, T.confusion, T.slow_down, T.end_call, T.do_not_call}
    if T.agreement in types and not blocked and (stage == "ask" or SLOT.search(text)):
        return Move("meeting_confirm", _line(session, "meeting_confirm"),
                    "Seller agreed. Confirm the meeting slot in one sentence and thank them.",
                    "done", Outcome.meeting_fixed, True)
    if T.refusal in types:
        if session.refusals + 1 >= 2:
            return Move("close_no", _line(session, "close_no"), "Seller refused twice. Thank them and end politely.",
                        "done", Outcome.declined, True)
        key = next((k for k in ("other_platform", "already_in_touch", "price") if OBJECTION_TEXT[k].search(text)),
                   "value" if "fayda" in text.lower() or "फ़ायदा" in text else "not_interested")
        return Move(key, f"{_play(session, key)} {ask}",
                    f"Seller declined once ({key}). Give the matching playbook answer in one line, then ask for the meeting.",
                    "ask")
    if T.identity in types:
        nxt = "pitch" if stage == "opening" else stage
        return Move("identity", f"{_play(session, 'identity')} {_line(session, 'pitch') if stage == 'opening' else ask}",
                    "Seller asked who is calling. Say who you are and why in one sentence, then continue.", nxt)

    strategy = p.tone.strategy
    if strategy != strategy_used and strategy in ("end", "handoff", "direct", "reassure", "rush", "clarify", "close"):
        if strategy == "end":
            return Move("end_close", _line(session, "end_close"), "End the call politely.", "done", Outcome.declined, True)
        key, hint, nxt = {
            "handoff": ("handoff", "Seller wants a person. Offer an executive callback at a fixed slot.", "ask"),
            "direct": ("direct", "Seller is irritated. Acknowledge in three words, then one line: free 20-minute meeting, ask for a slot.", "ask"),
            "reassure": ("reassure", "Seller asked if you are a bot. Say honestly you are IndiaMART's virtual assistant booking a real executive, then continue.", stage if stage != "opening" else "pitch"),
            "rush": ("rush", "Seller is busy. Offer two concrete slots in one sentence.", "ask"),
            "clarify": ("clarify", "Seller is confused. Explain in very simple words with one concrete example.", "pitch"),
            "close": ("close", "Seller is interested. Answer briefly and propose the slot.", "ask"),
        }[strategy]
        return Move(key, _line(session, key), hint, nxt)

    objection = next((k for k, rx in OBJECTION_TEXT.items() if rx.search(text)), None)
    if objection == "call_later":
        return Move("call_later", _play(session, "call_later"),
                    "Seller wants a later call. Offer two concrete callback times.", "ask")
    if objection:
        return Move(objection, f"{_play(session, objection)} {ask}",
                    f"Seller raised '{objection}'. Answer from the playbook, then ask for the meeting.", "ask")
    if stage == "opening":
        return Move("pitch", _line(session, "pitch"), "Give the value of the free meeting in one or two sentences.", "pitch")
    last_bot = next((t.text for t in reversed(session.transcript) if t.role == Role.bot), "")
    if stage == "ask" and last_bot.endswith(ask):
        return Move("direct", _line(session, "direct"), "Re-ask for the slot briefly, in different words.", "ask")
    return Move("meeting_ask", ask, "Ask for the meeting: tomorrow 11 AM, 20 minutes, free, online also possible.", "ask")
