"""Persona spec: what VANI sounds like for one seller, and why."""
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Confidence(str, Enum):
    strong = "strong"         # significant on real data
    moderate = "moderate"     # directional on real data
    weak = "weak"             # small sample / suggestive
    guess = "informed_guess"  # rule of thumb, no data behind it
    default = "default"       # field missing, sensible default (FAQ Q6)
    live = "live"             # set mid-call from a detected signal


class Source(str, Enum):
    seller_data = "seller_data"
    evidence = "evidence"
    rule = "rule"
    default = "default"
    live_signal = "live_signal"


class Decision(BaseModel):
    value: Any
    reason: str
    source: Source
    confidence: Confidence
    evidence_ids: list[str] = Field(default_factory=list)


class VoiceSpec(BaseModel):
    gender: str                    # female / male
    speaker: str                   # Bulbul voice id
    pace: float                    # 0.5 – 2.0 (bulbul v3)
    pitch: float | None = None     # only bulbul v2 supports pitch
    temperature: float = 0.6       # bulbul v3/v4 expressiveness: low = calm/steady, high = lively
    accent: str                    # e.g. "Hindi (North Indian)"
    model: str = "bulbul:v3"


class LanguageSpec(BaseModel):
    code: str                      # BCP-47, e.g. hi-IN
    style: str                     # hinglish / hindi / english / regional
    english_mix: float             # share of English words, 0 – 1
    formality: str                 # casual / neutral / formal
    address_as: str
    seller_gender: str = "unknown"  # male / female / unknown: from the seller's own words, never guessed


class ToneSpec(BaseModel):
    warmth: str                    # low / medium / high
    empathy: str
    energy: str
    max_words_per_turn: int
    strategy: str = "standard"     # standard / direct / clarify / rush / close / handoff / reassure


class ConversationPlan(BaseModel):
    opening: str
    personalisation: list[str]
    objection_playbook: dict[str, str]
    escalation_rules: list[str]
    guardrails: list[str]
    benefit_facts: dict = {}       # real numbers VANI may quote (own enquiries, category top-10%), see evidence/demand.py


class PersonaSpec(BaseModel):
    persona_id: str
    version: int = 1
    seller_glid: str
    label: str
    voice: VoiceSpec
    language: LanguageSpec
    tone: ToneSpec
    plan: ConversationPlan
    decisions: dict[str, Decision]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
