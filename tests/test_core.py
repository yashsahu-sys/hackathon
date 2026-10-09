import json
from pathlib import Path

import pytest

from app.conversation import Session
from app.evidence import CURRENT_DEFAULT, EvidenceStore
from app.persona import generate_persona
from app.signals import detect, detect_language

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def evidence():
    return EvidenceStore.load()


def seller(sid):
    return json.loads((ROOT / "data" / "sellers" / f"{sid}.json").read_text())


def test_evidence_learns_planted_drivers(evidence):
    assert evidence.driver("language_style")[0] == "region"
    assert evidence.driver("pace")[0] == "age_band"
    assert evidence.driver("opening")[0] == "business_type"


def test_evidence_does_not_invent_voice_gender_effect(evidence):
    # Synthetic data has no voice-gender effect; the generator must keep the default.
    assert evidence.driver("voice_gender")[0] is None
    for s in ("S101", "S102", "S103", "S104"):
        from app.persona import seller_attributes
        assert evidence.best("voice_gender", seller_attributes(seller(s))).choice == CURRENT_DEFAULT["voice_gender"]


def test_personas_are_distinct(evidence):
    labels = {generate_persona(seller(s), evidence)["label"] for s in ("S101", "S102", "S103")}
    assert len(labels) == 3


def test_seller_history_beats_segment(evidence):
    p = generate_persona(seller("S102"), evidence)
    assert p["language"]["code"] == "en-IN"
    assert p["rationale"]["language"]["source"] == "seller_history"


def test_busy_seller_gets_short_opening(evidence):
    p = generate_persona(seller("S101"), evidence)
    assert p["plan"]["opening_style"] == "short"
    assert p["voice"]["pace"] > 1.0


def test_language_mismatch_short_call_is_not_impatience(evidence):
    assert generate_persona(seller("S102"), evidence)["plan"]["opening_style"] != "short"


def test_every_decision_has_a_reason(evidence):
    p = generate_persona(seller("S104"), evidence)
    for key in ("language", "pace", "formality", "opening", "voice", "objection_playbook"):
        assert p["rationale"][key]["why"]


def test_no_lead_number_promises(evidence):
    for s in ("S101", "S102", "S103", "S104"):
        p = generate_persona(seller(s), evidence)
        text = json.dumps(p["plan"], ensure_ascii=False).lower()
        assert "double" not in text and "दुगन" not in text


@pytest.mark.parametrize("text,expected", [
    ("Yaar point pe aao, kitni der se bol rahe ho!", "frustration"),
    ("मतलब? समझा नहीं", "confusion"),
    ("Sorry, I did not understand", "confusion"),
    ("Abhi busy hoon, customer aaya hai", "rush"),
    ("Accha, leads kaise milenge?", "interest"),
    ("Mujhe kisi insaan se baat karni hai", "human_request"),
    ("Haan theek hai, kal 11 baje chalega", "agreement"),
    ("Alright, tomorrow 11 AM is fine", "agreement"),
    ("I am not interested", "refusal"),
])
def test_signals(text, expected):
    assert expected in {s.type for s in detect(text, "hi-IN")}


def test_language_detection():
    assert detect_language("Haan bhai bolo kya hai") == "hi-IN"
    assert detect_language("Yes please tell me about the meeting") == "en-IN"
    assert detect_language("வணக்கம் சொல்லுங்க") == "ta-IN"
    switch = [s for s in detect("Sorry, can you speak in English please", "hi-IN") if s.type == "language_switch"]
    assert switch and switch[0].detail["to"] == "en-IN"


def test_cooldown_prevents_flip_flop(evidence):
    s = Session(seller("S103"), evidence, client=None)
    s.open()
    s.seller_turn("Yaar point pe aao!")
    s.seller_turn("Yaar seedha bolo")
    assert [e["signal"] for e in s.switch_log].count("frustration") == 1


@pytest.mark.parametrize("sid,turns", [
    ("S101", ["Haan bolo", "Yaar point pe aao, kitni der se bol rahe ho!", "Haan theek hai, kal 11 baje chalega"]),
    ("S102", ["Yes", "Sorry, I did not understand", "Alright, tomorrow 11 AM is fine"]),
    ("S103", ["Haan bolo", "Sorry, can you speak in English please", "Yes okay, 11 AM tomorrow works"]),
])
def test_end_to_end_switch_then_meeting(evidence, sid, turns):
    s = Session(seller(sid), evidence, client=None)
    s.open()
    for t in turns:
        r = s.seller_turn(t)
    assert s.switch_log, "expected at least one mid-call switch"
    assert r["meeting"] is not None
    assert s.persona["version"] > 1


def test_two_refusals_end_politely(evidence):
    s = Session(seller("S101"), evidence, client=None)
    s.open()
    s.seller_turn("not interested")
    r = s.seller_turn("I am not interested, don't call")
    assert r["stage"] == "done" and r["meeting"] is None
