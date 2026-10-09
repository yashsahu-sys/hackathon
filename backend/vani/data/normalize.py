"""Raw dataset rows -> typed SellerProfile. Pure functions, no I/O."""
import math
import re
from typing import Any

from vani.domain.seller import BotHistory, BusinessKind, Engagement, SellerProfile, TurnoverBand

# Primary language + broad region per state. Hindi-belt states default to Hindi.
STATE_INFO: dict[str, tuple[str, str]] = {
    "delhi": ("hi-IN", "north"), "uttar pradesh": ("hi-IN", "north"), "haryana": ("hi-IN", "north"),
    "rajasthan": ("hi-IN", "north"), "madhya pradesh": ("hi-IN", "north"), "bihar": ("hi-IN", "east"),
    "jharkhand": ("hi-IN", "east"), "chhattisgarh": ("hi-IN", "north"), "uttarakhand": ("hi-IN", "north"),
    "himachal pradesh": ("hi-IN", "north"), "chandigarh": ("hi-IN", "north"), "jammu and kashmir": ("hi-IN", "north"),
    "jammu & kashmir": ("hi-IN", "north"), "punjab": ("pa-IN", "north"),
    "gujarat": ("gu-IN", "west"), "maharashtra": ("mr-IN", "west"), "goa": ("en-IN", "west"),
    "dadra and nagar haveli": ("gu-IN", "west"), "daman and diu": ("gu-IN", "west"),
    "dadra and nagar haveli and daman and diu": ("gu-IN", "west"),
    "tamil nadu": ("ta-IN", "south"), "puducherry": ("ta-IN", "south"), "pondicherry": ("ta-IN", "south"),
    "karnataka": ("kn-IN", "south"), "kerala": ("ml-IN", "south"), "telangana": ("te-IN", "south"),
    "andhra pradesh": ("te-IN", "south"),
    "west bengal": ("bn-IN", "east"), "odisha": ("od-IN", "east"), "orissa": ("od-IN", "east"),
    "assam": ("as-IN", "northeast"), "tripura": ("bn-IN", "northeast"), "meghalaya": ("en-IN", "northeast"),
    "manipur": ("en-IN", "northeast"), "mizoram": ("en-IN", "northeast"), "nagaland": ("en-IN", "northeast"),
    "arunachal pradesh": ("hi-IN", "northeast"), "sikkim": ("hi-IN", "northeast"),
}

TURNOVER_BANDS = [
    (re.compile(r"^0\s*-\s*40\s*L", re.I), TurnoverBand.micro),
    (re.compile(r"^40\s*L\s*-\s*1\.5\s*Cr", re.I), TurnoverBand.small),
    (re.compile(r"^(1\.5\s*-\s*5|5\s*-\s*25)\s*Cr", re.I), TurnoverBand.mid),
    (re.compile(r"^(25\s*-\s*100|100\s*-\s*500)\s*Cr|^>\s*500", re.I), TurnoverBand.large),
]

NATURE = {
    "manufacturer": BusinessKind.manufacturer,
    "trader - retailer": BusinessKind.retailer,
    "retailer": BusinessKind.retailer,
    "trader - wholesaler/distributor": BusinessKind.wholesaler,
    "wholesaler/distributor": BusinessKind.wholesaler,
    "service provider and others": BusinessKind.service,
}

_COUNT_ITEM = re.compile(r"^(.*?)\s*\((\d+)\)\s*$")


def is_missing(v: Any) -> bool:
    if v is None:
        return True
    if isinstance(v, float) and math.isnan(v):
        return True
    return isinstance(v, str) and v.strip().lower() in ("", "nan", "none", "null", "unknown")


def to_float(v: Any) -> float | None:
    if is_missing(v):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def to_int(v: Any, default: int = 0) -> int:
    f = to_float(v)
    return int(f) if f is not None else default


def to_bool(v: Any) -> bool:
    f = to_float(v)
    return bool(f) and f > 0


def state_info(state: str | None) -> tuple[str, str]:
    if is_missing(state):
        return "hi-IN", "unknown"
    return STATE_INFO.get(state.strip().lower(), ("hi-IN", "unknown"))


def turnover_band(raw: str | None) -> TurnoverBand:
    if is_missing(raw):
        return TurnoverBand.unknown
    for pattern, band in TURNOVER_BANDS:
        if pattern.search(raw.strip()):
            return band
    return TurnoverBand.unknown


def business_kind(nature: str | None) -> BusinessKind:
    if is_missing(nature):
        return BusinessKind.unknown
    return NATURE.get(nature.strip().lower(), BusinessKind.unknown)


def parse_counts(text: str | None) -> dict[str, int]:
    """'call_dropped (2); Callback / Deferred Engagement (Neutral) (1)' -> {label: count}."""
    out: dict[str, int] = {}
    if is_missing(text):
        return out
    for part in str(text).split(";"):
        part = part.strip()
        if not part:
            continue
        m = _COUNT_ITEM.match(part)
        label, n = (m.group(1).strip(), int(m.group(2))) if m else (part, 1)
        out[label] = out.get(label, 0) + n
    return out


def profile_from_row(row: dict[str, Any], reference_year: int = 2026) -> SellerProfile:
    missing: list[str] = []
    state = None if is_missing(row.get("seller_state")) else str(row["seller_state"]).strip()
    lang, region = state_info(state)
    if state is None:
        missing.append("state")
    kind = business_kind(row.get("nature_of_business"))
    if kind == BusinessKind.unknown:
        missing.append("nature_of_business")
    band = turnover_band(row.get("annual_turnover"))
    if band == TurnoverBand.unknown:
        missing.append("annual_turnover")
    gst_year = to_float(row.get("gst_registration_year"))
    age = None
    if gst_year and 1950 < gst_year <= reference_year:
        age = int(reference_year - gst_year)
    else:
        missing.append("gst_registration_year")
    categories = [str(row[c]).strip() for c in ("top_category_1", "top_category_2", "top_category_3")
                  if not is_missing(row.get(c))]
    if not categories:
        missing.append("categories")

    eng = Engagement(
        activity_30d=to_float(row.get("eng_activity_30d")),
        pickup_ratio_90d=to_float(row.get("eng_pickup_ratio_90d")),
        call_attempts_90d=to_float(row.get("eng_call_attempts_90d")),
        short_calls_90d=to_float(row.get("eng_short_calls_90d")),
        long_calls_90d=to_float(row.get("eng_long_calls_90d")),
        callbacks_90d=to_float(row.get("eng_callback_90d")),
        meetings_1yr=to_float(row.get("eng_meetings_1yr")),
        enquiries_90d=to_float(row.get("eng_enq_received_90d")),
        enquiry_replies_90d=to_float(row.get("eng_enq_replies_90d")),
        buyer_calls_90d=to_float(row.get("eng_pns_received_90d")),
        buyer_calls_answered_90d=to_float(row.get("eng_pns_answered_90d")),
        not_interested_1yr=to_float(row.get("eng_ni_count_1yr")),
        product_count=to_float(row.get("eng_product_count")),
        catalog_quality=to_float(row.get("eng_cqs")),
    )
    hist = BotHistory(
        attempts=to_int(row.get("bot_attempts")),
        answered=to_int(row.get("bot_answered")),
        answer_rate=to_float(row.get("bot_answer_rate")),
        meetings_fixed=to_int(row.get("calls_meeting_fixed")),
        not_interested=to_int(row.get("calls_not_interested")),
        call_later=to_int(row.get("calls_call_later")),
        general=to_int(row.get("calls_general")),
        avg_answered_call_sec=to_float(row.get("avg_answered_call_sec")),
        dispositions=parse_counts(row.get("past_dispositions_detailed")),
        objections=parse_counts(row.get("past_objections")),
        questions=parse_counts(row.get("past_questions_asked")),
        asked_if_bot=to_bool(row.get("asked_if_talking_to_bot")),
        showed_frustration=to_bool(row.get("showed_frustration")),
        in_touch_with_executive=to_bool(row.get("already_in_touch_with_executive")),
        do_not_call=to_bool(row.get("do_not_call_requested")),
    )
    if hist.answered == 0:
        missing.append("bot_history")
    paid = to_float(row.get("is_paid"))
    return SellerProfile(
        glid=str(to_int(row.get("fk_glusr_usr_id"))) if to_float(row.get("fk_glusr_usr_id")) is not None
        else str(row.get("fk_glusr_usr_id")),
        company_name=None if is_missing(row.get("company_name")) else str(row["company_name"]).strip(),
        city=None if is_missing(row.get("seller_city")) else str(row["seller_city"]).strip(),
        state=state, language_code=lang, region=region,
        business_kind=kind,
        legal_type=None if is_missing(row.get("business_type")) else str(row["business_type"]).strip(),
        turnover_band=band,
        turnover_raw=None if is_missing(row.get("annual_turnover")) else str(row["annual_turnover"]).strip(),
        business_age_years=age,
        categories=categories,
        category_group=None if is_missing(row.get("top_category_group")) else str(row["top_category_group"]).strip(),
        customer_type=None if is_missing(row.get("customer_type")) else str(row["customer_type"]).strip(),
        is_paid=None if paid is None else paid > 0,
        engagement=eng,
        bot_history=hist,
        missing_fields=missing,
    )
