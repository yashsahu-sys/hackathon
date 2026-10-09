from pydantic import BaseModel, Field

from vani.domain.live import Channel, Outcome


class StartCall(BaseModel):
    seller_glid: str
    channel: Channel = Channel.web


class EndCall(BaseModel):
    outcome: Outcome | None = None


class BatchPersonas(BaseModel):
    seller_glids: list[str] = Field(min_length=1, max_length=50)


class AgentStart(BaseModel):
    seller_glid: str


class AgentTurn(BaseModel):
    session_id: str
    seller_utterance: str = Field(min_length=1, max_length=2000)


class AgentEnd(BaseModel):
    session_id: str
    outcome: Outcome | None = None


class TTSRequest(BaseModel):
    text: str = Field(min_length=1, max_length=1500)
    language_code: str = "hi-IN"
    speaker: str = "ritu"
    pace: float = Field(1.0, ge=0.5, le=2.0)
    pitch: float | None = None
