"""Seller-side data, normalised from the IndiaMART dataset."""
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class BusinessKind(str, Enum):
    manufacturer = "manufacturer"
    retailer = "retailer"            # 'Trader - Retailer', 'Retailer'
    wholesaler = "wholesaler"        # 'Trader - Wholesaler/Distributor', 'Wholesaler/Distributor'
    service = "service"              # 'Service Provider and Others'
    unknown = "unknown"


class TurnoverBand(str, Enum):
    micro = "micro"      # 0 - 40 L
    small = "small"      # 40 L - 1.5 Cr
    mid = "mid"          # 1.5 - 25 Cr
    large = "large"      # 25 Cr +
    unknown = "unknown"


class Engagement(BaseModel):
    activity_30d: float | None = None
    pickup_ratio_90d: float | None = None
    call_attempts_90d: float | None = None
    short_calls_90d: float | None = None
    long_calls_90d: float | None = None
    callbacks_90d: float | None = None
    meetings_1yr: float | None = None
    enquiries_90d: float | None = None
    enquiry_replies_90d: float | None = None
    buyer_calls_90d: float | None = None
    buyer_calls_answered_90d: float | None = None
    not_interested_1yr: float | None = None
    product_count: float | None = None
    catalog_quality: float | None = None


class BotHistory(BaseModel):
    attempts: int = 0
    answered: int = 0
    answer_rate: float | None = None
    meetings_fixed: int = 0
    not_interested: int = 0
    call_later: int = 0
    general: int = 0
    avg_answered_call_sec: float | None = None
    dispositions: dict[str, int] = Field(default_factory=dict)   # call_dropped: 2, meeting_fixed: 1 …
    objections: dict[str, int] = Field(default_factory=dict)
    questions: dict[str, int] = Field(default_factory=dict)
    asked_if_bot: bool = False
    showed_frustration: bool = False
    in_touch_with_executive: bool = False
    do_not_call: bool = False


class SellerProfile(BaseModel):
    glid: str
    company_name: str | None = None
    city: str | None = None
    state: str | None = None
    language_code: str = "hi-IN"           # primary language of the seller's state
    region: str = "unknown"                 # north / west / south / east / northeast
    business_kind: BusinessKind = BusinessKind.unknown
    legal_type: str | None = None           # Proprietorship / Partnership / Limited Company
    turnover_band: TurnoverBand = TurnoverBand.unknown
    turnover_raw: str | None = None
    business_age_years: int | None = None   # from GST registration year
    categories: list[str] = Field(default_factory=list)
    category_group: str | None = None
    customer_type: str | None = None
    is_paid: bool | None = None
    engagement: Engagement = Field(default_factory=Engagement)
    bot_history: BotHistory = Field(default_factory=BotHistory)
    missing_fields: list[str] = Field(default_factory=list)


class BotCall(BaseModel):
    attempt_id: str
    glid: str
    bot_version: str | None = None
    bucket: str | None = None
    started_at: datetime | None = None
    duration_s: float | None = None
    summary: str | None = None
    disposition: str | None = None
    meeting_fixed: bool = False
    has_transcript: bool = False


class CallTurn(BaseModel):
    attempt_id: str
    turn_no: int
    speaker: str          # bot / seller / unknown
    start_s: float | None = None
    end_s: float | None = None
    text: str = ""


class SellerContext(BaseModel):
    """Everything the persona generator gets about one seller."""
    profile: SellerProfile
    calls: list[BotCall] = Field(default_factory=list)
    turns: list[CallTurn] = Field(default_factory=list)
