"""Shared fixtures. Fixture data is INVENTED; only the column headers match the real dataset."""
import csv
import json
from pathlib import Path

import pytest

from vani.data.repository import DuckDBSellerRepository
from vani.data.warehouse import build

FIXTURES = Path(__file__).parent / "fixtures"
HEADERS = json.loads((FIXTURES / "headers.json").read_text())
REAL_RAW = Path(__file__).resolve().parents[2] / "data" / "private" / "raw" / "gc"


def seller_row(glid, **kw):
    base = {
        "fk_glusr_usr_id": glid, "seller_city": "Jaipur", "seller_state": "Rajasthan",
        "business_type": "Proprietorship", "annual_turnover": "0 - 40 L", "nature_of_business": "Manufacturer",
        "gst_registration_year": "2015", "top_category_1": "Marble Slabs", "top_category_group": "Building Material",
        "eng_activity_30d": "4", "eng_pickup_ratio_90d": "0.5", "eng_enq_received_90d": "12",
        "bot_attempts": "3", "bot_answered": "2", "calls_meeting_fixed": "0", "calls_not_interested": "1",
        "calls_general": "1", "calls_call_later": "0", "bot_answer_rate": "0.66", "avg_answered_call_sec": "35",
        "past_objections": "", "past_questions_asked": "", "past_dispositions_detailed": "not_interested (1)",
        "asked_if_talking_to_bot": "0", "showed_frustration": "0", "already_in_touch_with_executive": "0",
        "do_not_call_requested": "0", "company_name": f"Test Co {glid}", "customer_type": "CATALOG", "is_paid": "0",
    }
    base.update(kw)
    return base


SELLERS = [
    seller_row("1001"),
    seller_row("1002", seller_state="Tamil Nadu", seller_city="Coimbatore", annual_turnover="5 - 25 Cr",
               nature_of_business="Trader - Wholesaler/Distributor", gst_registration_year="1998",
               past_objections="Seller Unavailability & Scheduling Constraints (1); Callback / Deferred Engagement (Neutral) (2)",
               past_dispositions_detailed="call_dropped (2); meeting_fixed (1)", showed_frustration="1"),
    seller_row("1003", seller_state="", annual_turnover="", nature_of_business="", gst_registration_year="",
               top_category_1="", bot_answered="0", bot_attempts="0", avg_answered_call_sec=""),
    seller_row("1004", seller_state="Delhi", seller_city="Delhi", nature_of_business="Trader - Retailer",
               annual_turnover="40 L - 1.5 Cr", gst_registration_year="2022", asked_if_talking_to_bot="1"),
]

CALLS = [
    {"attempt_id": "5001", "fk_glusr_usr_id": "1001", "lead_bot_version": "main_vani", "redis_bucket": "PIM",
     "call_start_time": "2026-09-01 10:00:00", "lead_call_duration": "12", "lead_call_summary": "Lead was busy and asked to call later.",
     "disposition_label": "Call Later / Busy", "meeting_fixed": "0", "has_turn_transcript": "1"},
    {"attempt_id": "5002", "fk_glusr_usr_id": "1001", "lead_bot_version": "main_vani", "redis_bucket": "PIM",
     "call_start_time": "2026-09-05 11:00:00", "lead_call_duration": "95", "lead_call_summary": "Lead was interested and agreed to a visit.",
     "disposition_label": "Meeting Fixed", "meeting_fixed": "1", "has_turn_transcript": "0"},
    {"attempt_id": "5003", "fk_glusr_usr_id": "1002", "lead_bot_version": "arrowhead", "redis_bucket": "PUA",
     "call_start_time": "2026-09-03 12:00:00", "lead_call_duration": "40", "lead_call_summary": "The lead did not understand Hindi and asked for English.",
     "disposition_label": "Not Interested", "meeting_fixed": "0", "has_turn_transcript": "1"},
]

TURNS = [
    {"attempt_id": "5001", "fk_glusr_usr_id": "1001", "turn_no": "1", "speaker": "bot", "start_sec": "0", "end_sec": "3", "text": "Hello, kya aap Test Co se bol rahe hain?"},
    {"attempt_id": "5001", "fk_glusr_usr_id": "1001", "turn_no": "2", "speaker": "seller", "start_sec": "3", "end_sec": "5", "text": "Haan bolo, abhi busy hoon"},
    {"attempt_id": "5003", "fk_glusr_usr_id": "1002", "turn_no": "1", "speaker": "bot", "start_sec": "0", "end_sec": "3", "text": "Namaste ji, IndiaMART se bol rahi hoon"},
    {"attempt_id": "5003", "fk_glusr_usr_id": "1002", "turn_no": "2", "speaker": "seller", "start_sec": "3", "end_sec": "6", "text": "Sorry, I don't understand Hindi, please speak English"},
]


def write_csv(path: Path, header: list[str], rows: list[dict]):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=header, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({h: r.get(h, "") for h in header})


@pytest.fixture(scope="session")
def raw_dir(tmp_path_factory) -> Path:
    d = tmp_path_factory.mktemp("raw")
    write_csv(d / "gc_seller_profile.csv", HEADERS["gc_seller_profile"], SELLERS)
    write_csv(d / "gc_bot_calls.csv", HEADERS["gc_bot_calls"], CALLS)
    write_csv(d / "gc_bot_call_turns.csv", HEADERS["gc_bot_call_turns"], TURNS)
    return d


@pytest.fixture(scope="session")
def warehouse(raw_dir, tmp_path_factory) -> Path:
    path = tmp_path_factory.mktemp("wh") / "warehouse.duckdb"
    build(raw_dir, path)
    return path


@pytest.fixture(scope="session")
def repo(warehouse):
    r = DuckDBSellerRepository(warehouse)
    yield r
    r.close()


@pytest.fixture(scope="session")
def real_repo(tmp_path_factory):
    if not (REAL_RAW / "gc_seller_profile.csv").exists():
        pytest.skip("real dataset not present in data/private/raw/gc")
    path = tmp_path_factory.mktemp("realwh") / "warehouse.duckdb"
    build(REAL_RAW, path)
    r = DuckDBSellerRepository(path)
    yield r
    r.close()
