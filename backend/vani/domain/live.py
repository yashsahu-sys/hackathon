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
    agreement = "agreement"
    refusal = "refusal"


# Signals that change the persona (the rest drive dialogue flow only)
PERSONA_SIGNALS = {
    SignalType.frustration, SignalType.confusion, SignalType.interest, SignalType.language_switch,
    SignalType.rush, SignalType.human_request, SignalType.bot_question,
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
    refusals: int = 0
    outcome: Outcome = Outcome.unknown
    meeting_slot: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def seller_turns(self) -> int:
        return sum(1 for t in self.transcript if t.role == Role.seller)
