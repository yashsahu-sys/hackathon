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
