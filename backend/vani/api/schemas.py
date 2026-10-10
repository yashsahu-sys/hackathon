from typing import Literal

from pydantic import BaseModel, Field

from vani.domain.live import Channel, Outcome


VoiceGender = Literal["male", "female"] | None


class StartCall(BaseModel):
    seller_glid: str
    channel: Channel = Channel.web
    voice_gender: VoiceGender = None


class EndCall(BaseModel):
    outcome: Outcome | None = None


class BatchPersonas(BaseModel):
    seller_glids: list[str] = Field(min_length=1, max_length=50)


class AgentStart(BaseModel):
    seller_glid: str
    voice_gender: VoiceGender = None


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
    temperature: float | None = Field(None, ge=0.01, le=1.0)


TURNOVER_BANDS = ["0 - 40 L", "40 L - 1.5 Cr", "1.5 - 5 Cr", "5 - 25 Cr", "25 - 100 Cr", "100 - 500 Cr", "> 500 Cr"]
NATURES = ["Manufacturer", "Trader - Wholesaler/Distributor", "Trader - Retailer", "Retailer", "Wholesaler/Distributor",
           "Service Provider and Others"]
LEGAL_TYPES = ["Proprietorship", "Partnership", "Limited Company", "Others"]


class NewSeller(BaseModel):
    """A seller who joined after the dataset snapshot. Same fields the seller profile table has."""
    glid: str | None = Field(None, pattern=r"^[A-Za-z0-9_-]{1,32}$")
    company_name: str | None = Field(None, max_length=120)
    state: str = Field(min_length=2, max_length=60)
    city: str | None = Field(None, max_length=60)
    categories: list[str] = Field(min_length=1, max_length=3)
    nature_of_business: str | None = None
    annual_turnover: str | None = None
    business_type: str | None = None
    gst_registration_year: int | None = Field(None, ge=1950, le=2100)
    enquiries_90d: int | None = Field(None, ge=0, le=100000)
    product_count: int | None = Field(None, ge=0, le=100000)

    def to_row(self) -> dict:
        cats = [c.strip() for c in self.categories if c.strip()][:3]
        row = {"fk_glusr_usr_id": self.glid, "company_name": self.company_name, "seller_state": self.state.strip(),
               "seller_city": self.city, "nature_of_business": self.nature_of_business,
               "annual_turnover": self.annual_turnover, "business_type": self.business_type,
               "gst_registration_year": self.gst_registration_year, "eng_enq_received_90d": self.enquiries_90d,
               "eng_product_count": self.product_count}
        row.update({f"top_category_{i + 1}": c for i, c in enumerate(cats)})
        return row
