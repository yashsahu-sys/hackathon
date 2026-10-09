"""The LLM brain: one structured Sarvam LLM call per seller turn that both
UNDERSTANDS the turn and WRITES the reply in the persona's voice.

    seller words + persona + conversation  ->  {signals, agreed, objection, language, reply}

Why one call: on a phone call every extra round trip is silence. Why structured
(json_schema): the understanding must be machine-checkable. Rules still run
first (1 ms) as a guardrail and offline fallback; the policy, not the LLM,
decides outcomes (a meeting is booked only when rules AND LLM see a yes).
"""
import asyncio
import json
import logging
import re
from dataclasses import dataclass, field

from vani.domain.live import CallSession, Role, Signal, SignalType as T
from vani.domain.seller import SellerProfile
from vani.integrations.sarvam.client import SarvamError, SpeechAI
from vani.persona.prompt import system_prompt

log = logging.getLogger(__name__)

LABELS = ["frustration", "confusion", "rush", "slow_down", "interest", "end_call", "do_not_call",
          "agreement", "refusal", "human_request", "bot_question", "language_switch", "none"]
OBJECTIONS = ["busy", "call_later", "not_interested", "price", "other_platform", "already_in_touch", "trust",
              "visit_details", "send_whatsapp", "not_ready", "value", "none"]

SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "turn",
        "description": "Understanding of the seller's last turn and the agent's next spoken reply.",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["signals", "agreed_to_meeting", "objection", "language", "reply"],
            "properties": {
                "signals": {"type": "array", "items": {"type": "string", "enum": LABELS}},
                "agreed_to_meeting": {"type": "boolean"},
                "objection": {"type": "string", "enum": OBJECTIONS},
                "language": {"type": "string", "description": "BCP-47 code the seller spoke, e.g. hi-IN, en-IN, ta-IN"},
                "reply": {"type": "string", "description": "Exactly what the agent says next. Spoken words only."},
            },
        },
    },
}

UNDERSTAND = """
TASK FOR THIS TURN
1. Understand the seller's LAST message in context. Labels:
   frustration (annoyed/angry/insulting), confusion (didn't understand), rush (busy, wants it quick),
   slow_down (asks to speak slower / says there's no hurry), interest (genuine question, curious),
   end_call (wants this call to end now), do_not_call (never call again), agreement (clearly accepts the
   meeting or a time), refusal (declines), human_request, bot_question, language_switch (seller changed language), none.
   "theek hai" or "kar do" is NOT agreement when the rest of the message is negative ("theek hai, call cut kar do").
   agreed_to_meeting = true ONLY if the seller clearly accepted the meeting or proposed slot.
2. Write the reply as the persona would say it NOW, adapting to what you understood:
   frustration -> acknowledge in 3-4 words, no pitch, one short line;  rush -> offer two concrete slots in one sentence;
   confusion or slow_down -> very simple words, one idea;  end_call / do_not_call -> apologise and say goodbye, no pitch;
   interest -> answer briefly then propose the slot.
   Never say the meeting is fixed unless agreed_to_meeting is true.
Rule-based detector heard: {hints}
Return ONLY the JSON object."""


@dataclass
class BrainResult:
    signals: set[T] = field(default_factory=set)
    agreed: bool = False
    objection: str | None = None
    language: str | None = None
    reply: str = ""


class LLMBrain:
    def __init__(self, speech: SpeechAI, timeout_s: float = 4.0):
        self.speech = speech
        self.timeout_s = timeout_s
        self._format: dict | None = SCHEMA   # downgraded to json_object if the API rejects json_schema

    @property
    def enabled(self) -> bool:
        return bool(getattr(self.speech, "enabled", False))

    def messages(self, session: CallSession, profile: SellerProfile, text: str, rule_hints: list[str]) -> list[dict]:
        sys = system_prompt(session.persona, profile).replace(
            "Output only the words to speak: plain sentences, standard punctuation, no lists, no markdown, no notes.", "")
        sys += UNDERSTAND.replace("{hints}", ", ".join(rule_hints) or "nothing")
        msgs = [{"role": "system", "content": sys}]
        for t in session.transcript[-8:]:
            msgs.append({"role": "assistant" if t.role == Role.bot else "user", "content": t.text})
        if not msgs[-1]["content"] == text:
            msgs.append({"role": "user", "content": text})
        return msgs

    async def think(self, session: CallSession, profile: SellerProfile, text: str, rule_hints: list[str]) -> BrainResult | None:
        if not self.enabled:
            return None
        msgs = self.messages(session, profile, text, rule_hints)
        for fmt in ([self._format, {"type": "json_object"}] if self._format is SCHEMA else [self._format]):
            try:
                raw = await asyncio.wait_for(self.speech.chat(msgs, max_tokens=400, response_format=fmt), self.timeout_s)
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


def parse(raw: str) -> BrainResult | None:
    m = re.search(r"\{.*\}", raw or "", re.S)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    labels = {T(x) for x in d.get("signals", []) if x in LABELS and x not in ("none",)}
    agreed = bool(d.get("agreed_to_meeting"))
    if agreed:
        labels.add(T.agreement)
    else:
        labels.discard(T.agreement)
    obj = d.get("objection")
    return BrainResult(signals=labels, agreed=agreed, objection=None if obj in (None, "none") else obj,
                       language=d.get("language") or None, reply=str(d.get("reply") or "").strip())
