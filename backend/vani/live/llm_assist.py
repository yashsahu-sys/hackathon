"""Second opinion from the LLM on each seller turn (live mode only).

Rules are fast and explainable but miss phrasings they've never seen. The LLM
reads the turn in context and:
  * adds persona signals the rules missed (marked source=llm in the switch log)
  * vetoes a rule-detected "agreement" it doesn't believe: a meeting is only
    confirmed when the rules AND the LLM both say the seller agreed.
If the LLM is slow or fails, the rules decide alone.
"""
import asyncio
import logging
import re

from vani.domain.live import Signal, SignalType as T
from vani.integrations.sarvam.client import SarvamError, SpeechAI

log = logging.getLogger(__name__)

LABELS = {
    "frustration": T.frustration, "confusion": T.confusion, "rush": T.rush, "slow_down": T.slow_down,
    "interest": T.interest, "end_call": T.end_call, "do_not_call": T.do_not_call, "agreement": T.agreement,
    "refusal": T.refusal, "human_request": T.human_request, "bot_question": T.bot_question,
}
NEGATIVE = {T.frustration, T.refusal, T.end_call, T.do_not_call, T.rush, T.slow_down, T.confusion}

SYSTEM = """You label ONE seller utterance from an Indian B2B sales phone call (Hinglish, Hindi or English).
The agent is trying to fix a meeting. Pick every label that applies:
frustration (annoyed, angry, insulting), confusion (didn't understand), rush (busy, wants it quick),
slow_down (asks to speak slower / no hurry), interest (asks a genuine question, curious),
end_call (wants this call to end now), do_not_call (never call again), agreement (clearly accepts the meeting or time),
refusal (declines), human_request (wants a real person), bot_question (asks if this is a bot), none.
"theek hai" or "kar do" alone is NOT agreement when the rest of the sentence is negative.
Reply with ONLY the labels, comma-separated."""

FEW_SHOT = [
    ("Bot asked: kal 11 baje meeting? Seller: haan theek hai aa jaiye", "agreement"),
    ("Bot asked: kal 11 baje meeting? Seller: yaar dimaag kharab mat karo, call cut kar do", "frustration, end_call"),
    ("Bot asked: kal 11 baje meeting? Seller: aaram se bataiye, itni jaldi kya hai", "slow_down"),
    ("Bot asked: kal 11 baje meeting? Seller: abhi busy hoon, shaam ko baat karte hain", "rush"),
    ("Bot asked: kal 11 baje meeting? Seller: thik hai par dubara call mat karna", "do_not_call, refusal"),
]


class LLMSignalAssist:
    def __init__(self, speech: SpeechAI, timeout_s: float = 2.5):
        self.speech = speech
        self.timeout_s = timeout_s

    @property
    def enabled(self) -> bool:
        return bool(getattr(self.speech, "enabled", False))

    async def classify(self, text: str, last_bot: str) -> set[T] | None:
        if not self.enabled:
            return None
        messages = [{"role": "system", "content": SYSTEM}]
        for q, a in FEW_SHOT:
            messages += [{"role": "user", "content": q}, {"role": "assistant", "content": a}]
        messages.append({"role": "user", "content": f"Bot asked: {last_bot[-200:]} Seller: {text}"})
        try:
            out = await asyncio.wait_for(self.speech.chat(messages, max_tokens=40), self.timeout_s)
        except (SarvamError, asyncio.TimeoutError) as exc:
            log.warning("LLM signal assist unavailable: %s", exc)
            return None
        found = {LABELS[w] for w in re.findall(r"[a-z_]+", out.lower()) if w in LABELS}
        return found


def merge(rule_signals: list[Signal], llm: set[T] | None, text: str) -> tuple[list[Signal], list[str]]:
    """Combine rule and LLM views. Returns (signals, notes for the log)."""
    if llm is None:
        return rule_signals, []
    notes = []
    have = {s.type for s in rule_signals}
    out = list(rule_signals)
    if T.agreement in have and (T.agreement not in llm or llm & NEGATIVE):
        out = [s for s in out if s.type != T.agreement]
        notes.append(f"LLM vetoed 'agreement' (LLM read: {', '.join(sorted(x.value for x in llm)) or 'none'})")
    for t in sorted(llm - have - {T.agreement}, key=lambda x: x.value):   # LLM alone never confirms a meeting
        out.append(Signal(type=t, confidence=0.7, trigger=text[:60], detail={"source": "llm"}))
        notes.append(f"LLM added '{t.value}'")
    if llm & NEGATIVE:
        out = [s for s in out if s.type != T.agreement]
    return out, notes
