"""Live call: signals, switches, sessions."""
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from .persona import PersonaSpec


class SignalType(str, Enum):
    frustration = "frustration"
    confusion = "confusion"
    interest = "interest"
    language_switch = "language_switch"
    rush = "rush"
    human_request = "human_request"
    bot_question = "bot_question"       # "aap AI ho?"
    identity = "identity"               # "kaun bol raha hai?"
    do_not_call = "do_not_call"         # "dubara call mat kijiye"
    slow_down = "slow_down"             # "thoda dheere boliye"
    end_call = "end_call"               # "call cut kar do", "phone rakho"
    seller_gender = "seller_gender"     # learned from the seller's own verb forms ("bol raha hoon")
    seller_pace = "seller_pace"         # how fast the seller actually speaks (words per voiced second, from audio)
    agreement = "agreement"
    refusal = "refusal"


# Signals that change the persona (the rest drive dialogue flow only)
PERSONA_SIGNALS = {
    SignalType.frustration, SignalType.confusion, SignalType.interest, SignalType.language_switch,
    SignalType.rush, SignalType.human_request, SignalType.bot_question, SignalType.slow_down,
    SignalType.seller_gender, SignalType.end_call, SignalType.seller_pace,
}


class Signal(BaseModel):
    type: SignalType
    confidence: float
    trigger: str                        # the seller's words that fired it
    detail: dict[str, Any] = Field(default_factory=dict)


class FieldChange(BaseModel):
    field: str
    old: Any
    new: Any


class SwitchEvent(BaseModel):
    session_id: str
    turn: int
    at_ms: int
    signal: SignalType
    confidence: float
    trigger: str
    changes: list[FieldChange]
    reason: str
    from_version: int
    to_version: int


class Role(str, Enum):
    bot = "bot"
    seller = "seller"


class TurnRecord(BaseModel):
    role: Role
    text: str
    language: str | None = None
    at_ms: int
    persona_version: int
    signals: list[Signal] = Field(default_factory=list)


class Channel(str, Enum):
    web = "web"                   # our browser runtime (Saaras + LLM + Bulbul)
    sarvam_agent = "sarvam_agent"  # Sarvam Samvaad agent calling our tools


class CallStatus(str, Enum):
    active = "active"
    ended = "ended"


class Outcome(str, Enum):
    meeting_fixed = "meeting_fixed"
    callback = "callback"
    declined = "declined"
    dropped = "dropped"
    unknown = "unknown"


class CallSession(BaseModel):
    session_id: str
    seller_glid: str
    channel: Channel
    status: CallStatus = CallStatus.active
    persona: PersonaSpec
    initial_persona: PersonaSpec
    transcript: list[TurnRecord] = Field(default_factory=list)
    switch_log: list[SwitchEvent] = Field(default_factory=list)
    cooldowns: dict[str, int] = Field(default_factory=dict)   # signal -> last seller turn it fired
    stage: str = "opening"
    strategy_used: str | None = None     # each switch's strategy line is spoken once
    refusals: int = 0
    outcome: Outcome = Outcome.unknown
    meeting_slot: str | None = None           # human-readable agreed slot
    agreed_slot: dict | None = None           # Slot as dict {day, hour, minute}
    offered_slots: list[dict] = Field(default_factory=list)   # what VANI has proposed, in order
    unavailable_days: list[str] = Field(default_factory=list)  # days the seller ruled out
    expressions_used: list[str] = Field(default_factory=list)  # acknowledgements already spoken (never twice)
    escalation: str | None = None             # "manager" / "executive" once the seller asked for a person
    info_turns: int = 0                       # seller questions answered without pushing the meeting
    line_uses: dict[str, int] = Field(default_factory=dict)    # how often each line key was spoken (rotates variants)
    voice_baseline: list[float] = Field(default_factory=list)  # seller's loudness on their first turns (dBFS)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def seller_turns(self) -> int:
        return sum(1 for t in self.transcript if t.role == Role.seller)
