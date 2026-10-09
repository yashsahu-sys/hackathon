"""Dialogue policy: what VANI does next, from the call STATE (slots offered,
days ruled out, agreed slot) and the turn's signals. Deterministic, so outcomes
are auditable: the policy books meetings, the LLM only phrases replies.
Every line's {slot1}/{slot2}/{slot} is filled with real, constraint-respecting slots."""
import re
from dataclasses import dataclass, field

from vani.domain.live import CallSession, Outcome, Role, SignalType as T
from vani.persona.generator import _gender_forms
from vani.persona.lines import lines_for
from vani.text.slots import Slot, fill, render, suggest

OBJECTION_TEXT = {k: re.compile(p, re.I) for k, p in {
    "price": r"paisa|paise|पैसे|charge|kitne ka|\bcost|\bfees?\b|kharcha|खर्चा|\bpaid\b|price",
    "send_whatsapp": r"whatsapp|व्हाट्सऐप|व्हाट्सएप",
    "other_platform": r"tradeindia|justdial|alibaba|(doosri|dusri|dusre|doosre) jagah|other (platform|portal)",
    "already_in_touch": r"already (baat|mil|spoke|talked|in touch)|pehle (se|bhi) (baat|mil)|executive (aaya|aa chuka|aaye the)",
    "trust": r"fraud|fake|bharosa|भरोसा|\btrust\b|privacy|mera data",
    "visit_details": r"\bkahan\b|\bkidhar\b|kitne der|kitna time|\bonline\b|address|kaise aayeng|कहाँ|कितनी देर",
    "call_later": r"(baad|bad) (me|mein) (call|phone|baat)|call (me )?later|शाम को|kal (call|phone|baat)",
}.items()}
NEGATIVE = {T.frustration, T.refusal, T.rush, T.confusion, T.slow_down, T.end_call, T.do_not_call}


@dataclass
class Move:
    key: str
    text: str
    hint: str
    stage: str
    outcome: Outcome | None = None
    end_call: bool = False
    offered: list[Slot] = field(default_factory=list)


class Ctx:
    def __init__(self, s: CallSession):
        self.s = s
        self.style = s.persona.language.style
        self.gender = s.persona.voice.gender
        self.offer = suggest(set(s.unavailable_days), [Slot.from_dict(d) for d in s.offered_slots])
        self.agreed = Slot.from_dict(s.agreed_slot)

    def raw(self, key: str) -> str:
        L = lines_for(self.style)
        return L["playbook"][key] if key in L["playbook"] else L[key]

    def line(self, key: str) -> str:
        return fill(_gender_forms(self.raw(key), self.gender), self.style, self.offer, self.agreed)

    def offers_in(self, key: str) -> list[Slot]:
        raw = self.raw(key)
        return self.offer[:2] if "{slot2}" in raw else (self.offer[:1] if "{slot1}" in raw else [])

    def move(self, key: str, hint: str, stage: str, **kw) -> Move:
        return Move(key, self.line(key), hint, stage, offered=self.offers_in(key), **kw)

    def combo(self, key: str, hint: str) -> Move:
        ask = self.line("meeting_ask")
        return Move(key, f"{self.line(key)} {ask}", hint, "ask", offered=self.offers_in("meeting_ask"))


def next_move(session: CallSession, text: str, types: set[T], strategy_used: str | None,
              new_unavailable: set[str] | None = None) -> Move:
    c = Ctx(session)
    stage = session.stage
    if stage == "done":
        key = "meeting_confirm" if session.outcome == Outcome.meeting_fixed else "close_no"
        return c.move(key, "The call is over; one-line goodbye.", "done", end_call=True)
    if T.end_call in types:
        return c.move("end_close", "Seller wants to end the call. Apologise in one sentence and say goodbye.", "done",
                      outcome=Outcome.declined, end_call=True)
    if T.do_not_call in types:
        return c.move("dnc_close", "Seller asked not to be called. Apologise, confirm, end.", "done",
                      outcome=Outcome.declined, end_call=True)

    blocked = types & (NEGATIVE - {T.slow_down, T.rush})   # a rushed "haan 5 baje theek hai" is still a yes
    if T.agreement in types and not blocked:
        if c.agreed and c.agreed.complete:
            return c.move("meeting_confirm", f"Seller agreed to {render(c.agreed, 'english')}. Confirm it.", "done",
                          outcome=Outcome.meeting_fixed, end_call=True)
        return c.move("ask_time", "Seller agreed but no full day/time yet. Ask which day and time suit them.", "ask")

    if new_unavailable:
        return c.move("reschedule", f"Seller can't do {', '.join(sorted(new_unavailable))}. Offer the other slots.", "ask")

    if T.refusal in types:
        if session.refusals + 1 >= 2:
            return c.move("close_no", "Seller refused twice. Thank them and end politely.", "done",
                          outcome=Outcome.declined, end_call=True)
        key = next((k for k in ("other_platform", "already_in_touch", "price") if OBJECTION_TEXT[k].search(text)),
                   "value" if re.search(r"fayda|फ़ायदा|फायदा", text, re.I) else "not_interested")
        return c.combo(key, f"Seller declined once ({key}). One playbook line, then ask for the meeting.")
    if T.identity in types:
        nxt = "pitch" if stage == "opening" else stage
        follow = c.line("pitch") if stage == "opening" else c.line("meeting_ask")
        return Move("identity", f"{c.line('identity')} {follow}", "Say who you are and why, then continue.", nxt,
                    offered=[] if stage == "opening" else c.offers_in("meeting_ask"))

    strategy = session.persona.tone.strategy
    if strategy != strategy_used and strategy in ("end", "handoff", "direct", "reassure", "rush", "clarify", "close"):
        if strategy == "end":
            return c.move("end_close", "End the call politely.", "done", outcome=Outcome.declined, end_call=True)
        hint, nxt = {
            "handoff": ("Seller wants a person. Offer an executive callback at a fixed slot.", "ask"),
            "direct": ("Seller is irritated. Acknowledge briefly, then one line: free 20-minute meeting, one slot.", "ask"),
            "reassure": ("Seller asked if you are a bot. Say honestly you are IndiaMART's virtual assistant, then continue.",
                         stage if stage != "opening" else "pitch"),
            "rush": ("Seller is busy. Offer two concrete slots in one sentence.", "ask"),
            "clarify": ("Seller is confused or wants it slower. Very simple words, one concrete example.", "pitch"),
            "close": ("Seller is interested. Answer briefly and propose the slot.", "ask"),
        }[strategy]
        return c.move(strategy, hint, nxt)

    objection = next((k for k, rx in OBJECTION_TEXT.items() if rx.search(text)), None)
    if objection == "call_later":
        return c.move("call_later", "Seller wants a later call. Offer two concrete callback times.", "ask")
    if objection:
        return c.combo(objection, f"Seller raised '{objection}'. Answer from the playbook, then ask for the meeting.")
    if stage == "opening":
        return c.move("pitch", "Give the value of the free meeting in one or two sentences.", "pitch")
    last_bot = next((t.text for t in reversed(session.transcript) if t.role == Role.bot), "")
    ask = c.move("meeting_ask", "Ask for the meeting with the suggested slots.", "ask")
    if stage == "ask" and last_bot.endswith(ask.text):
        return c.move("direct", "Re-ask briefly, in different words.", "ask")
    return ask
