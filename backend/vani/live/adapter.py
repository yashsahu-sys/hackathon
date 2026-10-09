"""Mid-call persona adaptation: signals in -> new persona version + switch log out.

Rules (PS04 §3.5): slow down and simplify when confused, shorten and get to the
point when rushed, follow the seller's language, de-escalate frustration,
move to the ask on interest. A confidence threshold and a per-signal cooldown
stop the bot from flip-flopping on one irritated sentence.
"""
from vani.domain.live import CallSession, FieldChange, Signal, SignalType, SwitchEvent
from vani.domain.persona import Confidence, Decision, PersonaSpec, Source
from vani.persona.generator import _gender_forms
from vani.persona.lines import REGIONAL_GREETING, lines_for
from vani.persona.voices import ACCENT, clamp_pace, speaker_for
from vani.text.slots import fill as fill_slots

T = SignalType
MIN_CONFIDENCE = 0.6
COOLDOWN_TURNS = 2
PACE_CAP, PACE_FLOOR = 1.4, 0.8
# Targets, not small nudges: a switch must be audible on the call.
RUSH_PACE, FRUSTRATION_PACE, SLOW_PACE = 1.2, 1.15, 0.85
TEMP = {"calm": 0.35, "clear": 0.45, "warm": 0.65, "lively": 0.75}   # bulbul v3/v4 expressiveness

# Highest wins when several land on one turn.
STRATEGY_PRIORITY = ["end", "handoff", "direct", "reassure", "rush", "clarify", "close", "standard"]

REASONS = {
    T.frustration: "Seller is irritated: acknowledge, cut the pitch, short sentences, go straight to the slot.",
    T.confusion: "Seller didn't follow: slow down, simpler words, fewer English terms, one idea per sentence.",
    T.rush: "Seller is short on time: skip the pitch, offer two concrete slots.",
    T.interest: "Seller is leaning in: answer briefly, then propose the meeting now.",
    T.human_request: "Seller wants a person: offer the executive callback, which is the call's goal anyway.",
    T.bot_question: "Seller asked if this is a bot: answer honestly, warmer and more human, then continue.",
    T.language_switch: "Seller changed language: follow them; the meeting matters more than our script.",
    T.do_not_call: "Seller asked not to be called: stop pitching, apologise, confirm, end the call.",
    T.slow_down: "Seller asked us to slow down: drop the pace, simple words, one idea per sentence.",
    T.end_call: "Seller wants to end the call: apologise briefly and hang up; never push for the meeting.",
    T.seller_gender: "Seller's own words show their gender: address them correctly from now on.",
}
ADDRESS = {("male", "hinglish"): "सर", ("female", "hinglish"): "मैडम", ("male", "english"): "Sir",
           ("female", "english"): "Ma'am", ("male", "regional"): "Sir", ("female", "regional"): "Ma'am",
           ("male", "gujarati"): "સર", ("female", "gujarati"): "મેડમ"}


class Mutation:
    def __init__(self, persona: PersonaSpec, turn_state: dict):
        self.p = persona.model_copy(deep=True)
        self.changes: list[FieldChange] = []
        self.turn = turn_state   # strategy chosen earlier in THIS turn

    def set(self, path: str, value) -> None:
        obj = self.p
        *parents, leaf = path.split(".")
        for name in parents:
            obj = getattr(obj, name)
        old = getattr(obj, leaf)
        if old != value:
            setattr(obj, leaf, value)
            self.changes.append(FieldChange(field=path, old=old, new=value))

    def strategy(self, s: str) -> None:
        """The seller's latest turn sets the strategy (a slow-down request replaces an
        earlier rush); priority only breaks ties between signals in the same turn.
        'end' is final."""
        if self.p.tone.strategy == "end":
            return
        chosen = self.turn.get("strategy")
        if chosen is None or STRATEGY_PRIORITY.index(s) <= STRATEGY_PRIORITY.index(chosen):
            self.turn["strategy"] = s
            self.set("tone.strategy", s)


class PersonaAdapter:
    def adapt(self, session: CallSession, signals: list[Signal], now_ms: int) -> list[SwitchEvent]:
        turn = session.seller_turns
        events: list[SwitchEvent] = []
        turn_state: dict = {}
        for sig in signals:
            if sig.confidence < MIN_CONFIDENCE or sig.type not in REASONS:
                continue
            last = session.cooldowns.get(sig.type.value, -99)
            if sig.type not in (T.language_switch, T.seller_gender, T.slow_down, T.end_call) and turn - last < COOLDOWN_TURNS:
                continue
            m = Mutation(session.persona, turn_state)
            self._apply(m, sig, session)
            if not m.changes:
                continue
            m.p.version = session.persona.version + 1
            m.p.decisions = dict(m.p.decisions)
            why = f"Switched mid-call (seller turn {turn}): seller said “{sig.trigger}”. {REASONS[sig.type]}"
            for ch in m.changes:
                m.p.decisions[ch.field] = Decision(value=ch.new, reason=why, source=Source.live_signal,
                                                   confidence=Confidence.live)
            events.append(SwitchEvent(
                session_id=session.session_id, turn=turn, at_ms=now_ms, signal=sig.type, confidence=sig.confidence,
                trigger=sig.trigger, changes=m.changes, reason=REASONS[sig.type],
                from_version=session.persona.version, to_version=m.p.version))
            session.persona = m.p
            session.cooldowns[sig.type.value] = turn
        if events:
            base = session.initial_persona.label
            trail = [e.signal.value.replace("_", " ") for e in session.switch_log + events]
            session.persona.label = " → ".join([base] + trail)
        return events

    @staticmethod
    def _apply(m: Mutation, sig: Signal, session: CallSession) -> None:
        p = m.p
        if sig.type == T.frustration:
            m.set("voice.pace", clamp_pace(min(PACE_CAP, max(p.voice.pace + 0.1, FRUSTRATION_PACE))))
            m.set("voice.temperature", TEMP["calm"])
            m.set("tone.max_words_per_turn", min(p.tone.max_words_per_turn, 12))
            m.set("tone.energy", "calm")
            m.set("tone.empathy", "high")
            m.strategy("direct")
        elif sig.type in (T.confusion, T.slow_down):
            m.set("voice.pace", clamp_pace(max(PACE_FLOOR, min(p.voice.pace - 0.1, SLOW_PACE))))
            m.set("voice.temperature", TEMP["clear"])
            m.set("tone.max_words_per_turn", min(p.tone.max_words_per_turn, 12))
            m.set("tone.warmth", "high")
            if p.language.style in ("hinglish", "gujarati"):
                m.set("language.english_mix", min(p.language.english_mix, 0.1))
            m.strategy("clarify")
        elif sig.type == T.rush:
            m.set("voice.pace", clamp_pace(min(PACE_CAP, max(p.voice.pace + 0.1, RUSH_PACE))))
            m.set("tone.max_words_per_turn", min(p.tone.max_words_per_turn, 12))
            m.strategy("rush")
        elif sig.type == T.interest:
            m.set("tone.energy", "high")
            m.set("voice.temperature", TEMP["lively"])
            m.strategy("close")
        elif sig.type == T.human_request:
            m.strategy("handoff")
        elif sig.type == T.bot_question:
            m.set("tone.warmth", "high")
            m.set("voice.temperature", TEMP["warm"])
            m.strategy("reassure")
        elif sig.type in (T.do_not_call, T.end_call):
            m.set("voice.temperature", TEMP["calm"])
            m.strategy("end")
        elif sig.type == T.seller_gender:
            gender = sig.detail.get("gender")
            if gender not in ("male", "female") or gender == p.language.seller_gender:
                return
            m.set("language.seller_gender", gender)
            m.set("language.address_as", ADDRESS[(gender, p.language.style)])
        elif sig.type == T.language_switch:
            target = sig.detail.get("to")
            if not target or target == p.language.code:
                return
            style = {"en-IN": "english", "hi-IN": "hinglish", "gu-IN": "gujarati"}.get(target, "regional")
            m.set("language.code", target)
            m.set("language.style", style)
            m.set("language.english_mix", {"english": 1.0, "hinglish": 0.3}.get(style, 0.3))
            known = p.language.seller_gender in ("male", "female")
            m.set("language.address_as", ADDRESS[(p.language.seller_gender, style)] if known else
                  ("जी" if style == "hinglish" else "જી" if style == "gujarati" else ("Sir/Madam" if p.language.formality == "formal" else "you")))
            m.set("voice.accent", ACCENT.get(target, target))
            m.set("voice.speaker", speaker_for(p.voice.gender, p.language.formality, target, p.voice.model))
            L = lines_for(style)
            m.p.plan.objection_playbook = {k: fill_slots(_gender_forms(L["playbook"][k], p.voice.gender), style)
                                           for k in p.plan.objection_playbook if k in L["playbook"]}
            if style == "regional" and target in REGIONAL_GREETING:
                m.set("plan.opening", f"{REGIONAL_GREETING[target]}! " + p.plan.opening)
