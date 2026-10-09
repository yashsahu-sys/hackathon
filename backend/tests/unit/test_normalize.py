import math

import pytest

from vani.data.normalize import (business_kind, is_missing, parse_counts, profile_from_row, state_info, to_bool,
                                 to_float, turnover_band)
from vani.domain.seller import BusinessKind, TurnoverBand
from tests.conftest import seller_row


@pytest.mark.parametrize("raw,band", [
    ("0 - 40 L", TurnoverBand.micro), ("40 L - 1.5 Cr", TurnoverBand.small), ("1.5 - 5 Cr", TurnoverBand.mid),
    ("5 - 25 Cr", TurnoverBand.mid), ("25 - 100 Cr", TurnoverBand.large), ("100 - 500 Cr", TurnoverBand.large),
    ("> 500 Cr", TurnoverBand.large), (None, TurnoverBand.unknown), ("", TurnoverBand.unknown),
    ("weird", TurnoverBand.unknown),
])
def test_turnover_band(raw, band):
    assert turnover_band(raw) == band


@pytest.mark.parametrize("raw,kind", [
    ("Manufacturer", BusinessKind.manufacturer), ("Trader - Retailer", BusinessKind.retailer),
    ("Retailer", BusinessKind.retailer), ("Trader - Wholesaler/Distributor", BusinessKind.wholesaler),
    ("Wholesaler/Distributor", BusinessKind.wholesaler), ("Service Provider and Others", BusinessKind.service),
    ("Unknown", BusinessKind.unknown), (None, BusinessKind.unknown), ("  manufacturer ", BusinessKind.manufacturer),
])
def test_business_kind(raw, kind):
    assert business_kind(raw) == kind


@pytest.mark.parametrize("state,expected", [
    ("Tamil Nadu", ("ta-IN", "south")), ("gujarat", ("gu-IN", "west")), ("Delhi", ("hi-IN", "north")),
    ("West Bengal", ("bn-IN", "east")), ("Punjab", ("pa-IN", "north")), (None, ("hi-IN", "unknown")),
    ("Atlantis", ("hi-IN", "unknown")),
])
def test_state_info(state, expected):
    assert state_info(state) == expected


def test_parse_counts_handles_nested_parentheses():
    assert parse_counts("Seller Unavailability & Scheduling Constraints (1); Callback / Deferred Engagement (Neutral) (2)") == {
        "Seller Unavailability & Scheduling Constraints": 1, "Callback / Deferred Engagement (Neutral)": 2}
    assert parse_counts("call_dropped (2); call_dropped (1)") == {"call_dropped": 3}
    assert parse_counts(None) == {} and parse_counts("") == {}
    assert parse_counts("no count here") == {"no count here": 1}


def test_scalar_helpers():
    assert is_missing(None) and is_missing(float("nan")) and is_missing("  ") and is_missing("NaN")
    assert to_float("1.5") == 1.5 and to_float("x") is None and to_float(None) is None
    assert to_bool("1.0") and not to_bool("0") and not to_bool(None)
    assert not math.isnan(to_float("0") or 0)


def test_profile_full_row():
    p = profile_from_row(seller_row("1002", seller_state="Tamil Nadu", annual_turnover="5 - 25 Cr",
                                    gst_registration_year="1998", showed_frustration="1",
                                    past_dispositions_detailed="call_dropped (2); meeting_fixed (1)"))
    assert p.glid == "1002" and p.language_code == "ta-IN" and p.region == "south"
    assert p.turnover_band == TurnoverBand.mid and p.business_age_years == 28
    assert p.bot_history.showed_frustration and p.bot_history.dispositions == {"call_dropped": 2, "meeting_fixed": 1}
    assert p.missing_fields == []


def test_profile_missing_fields_are_flagged_not_fatal():
    p = profile_from_row(seller_row("1003", seller_state="", annual_turnover="", nature_of_business="",
                                    gst_registration_year="", top_category_1="", bot_answered="0"))
    assert set(p.missing_fields) >= {"state", "annual_turnover", "nature_of_business", "gst_registration_year",
                                     "categories", "bot_history"}
    assert p.language_code == "hi-IN"   # sensible default


def test_glid_float_string_normalised():
    assert profile_from_row(seller_row("110434458.0")).glid == "110434458"


def test_future_gst_year_rejected():
    p = profile_from_row(seller_row("9", gst_registration_year="2031"))
    assert p.business_age_years is None and "gst_registration_year" in p.missing_fields
