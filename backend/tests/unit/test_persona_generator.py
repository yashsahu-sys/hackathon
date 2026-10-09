import re

import pytest

from vani.data.normalize import profile_from_row
from vani.domain.persona import Confidence, Source
from vani.domain.seller import BotCall, CallTurn, SellerContext
from vani.evidence.book import EvidenceBook
from vani.persona.generator import PersonaGenerator, _gender_forms, line
from tests.conftest import seller_row


def F(fid, rate, base, strength, k=50, n=100, bk=40, bn=400, statement=None):
    return {"id": fid, "rate": rate, "base_rate": base, "strength": strength, "k": k, "n": n, "base_k": bk,
            "base_n": bn, "statement": statement or fid}


BOOK = EvidenceBook({"baseline": {"meeting_rate": 0.11}, "findings": [
    F("TRN-language_mix", 0.99, 0.99, "strong", statement="99% answered in Hinglish"),
    F("VAR-last_met_d-early_drop", 0.395, 0.473, "strong", statement="last-interaction opening drops less"),
    F("TRN-opening_length", 0.18, 0.12, "moderate", statement="bare openings drop more"),
    F("OUT-busy", 0.05, 0.118, "strong"), F("OUT-not_interested", 0.04, 0.12, "strong"),
    F("OUT-price", 0.19, 0.10, "strong"), F("OUT-bot_question", 0.03, 0.11, "moderate"),
    F("SEG-region=east-confused", 0.08, 0.01, "strong", k=8, n=100, bk=4, bn=400, statement="east sellers get confused more"),
]})


def ctx(glid, calls=(), turns=(), **kw):
    return SellerContext(profile=profile_from_row(seller_row(glid, **kw)), calls=list(calls), turns=list(turns))


@pytest.fixture
def gen():
    return PersonaGenerator(BOOK)


def test_every_decision_is_explained(gen):
    p = gen.generate(ctx("1", calls=[BotCall(attempt_id="a", glid="1", duration_s=60)]))
    for key, dec in p.decisions.items():
        assert dec.reason.strip(), key
        assert isinstance(dec.source, Source) and isinstance(dec.confidence, Confidence)
        for fid in dec.evidence_ids:
            assert BOOK.get(fid), f"{key} cites unknown evidence {fid}"
    for key in ("language.style", "language.formality", "voice.pace", "voice.gender", "voice.speaker",
                "voice.pitch", "tone.empathy", "tone.warmth", "plan.opening", "plan.objection_playbook"):
        assert key in p.decisions


def test_missing_fields_fall_back_to_low_confidence_defaults(gen):
    p = gen.generate(ctx("3", seller_state="", annual_turnover="", nature_of_business="", gst_registration_year="",
                         top_category_1="", bot_answered="0", bot_attempts="0"))
    assert p.language.style == "hinglish"
    assert p.decisions["language.style"].confidence == Confidence.default
    assert p.decisions["language.formality"].confidence == Confidence.default
    assert p.plan.opening   # still produces a usable opening


def test_seller_who_asked_for_english_gets_english(gen):
    c = ctx("2", seller_state="Rajasthan", calls=[BotCall(attempt_id="a", glid="2", duration_s=40,
            summary="The lead did not understand Hindi and asked to speak in English.")])
    p = gen.generate(c)
    assert p.language.code == "en-IN" and p.decisions["language.style"].source == Source.seller_data


def test_seller_who_spoke_english_on_transcript_gets_english(gen):
    turns = [CallTurn(attempt_id="a", turn_no=2, speaker="seller", text="Sorry I don't understand, please speak in English")]
    p = gen.generate(ctx("2", turns=turns))
    assert p.language.style == "english"


def test_south_seller_without_history_opens_in_english_as_informed_guess(gen):
    p = gen.generate(ctx("5", seller_state="Tamil Nadu"))
    assert p.language.code == "en-IN"
    assert p.decisions["language.style"].confidence == Confidence.guess
    assert p.voice.pace < 1.0   # slower for non-Hindi home state
    assert p.voice.accent == "Indian English"


def test_regional_greeting_for_gujarat_hinglish(gen):
    p = gen.generate(ctx("6", seller_state="Gujarat"))
    assert p.language.style == "hinglish" and p.plan.opening.startswith("Kem cho")


def test_rush_prone_seller_gets_quick_brief_persona(gen):
    p = gen.generate(ctx("7", calls_call_later="2", past_dispositions_detailed="callback_requested (1); call_dropped (3)",
                         bot_answered="4", avg_answered_call_sec="10"))
    assert p.voice.pace > 1.0 and p.tone.max_words_per_turn <= 16
    assert p.decisions["plan.opening"].value == "brief"
    assert "callback" in p.decisions["voice.pace"].reason


def test_history_opening_cites_variant_evidence(gen):
    p = gen.generate(ctx("8", calls=[BotCall(attempt_id="a", glid="8", duration_s=95)]))
    d = p.decisions["plan.opening"]
    assert d.value == "history" and "VAR-last_met_d-early_drop" in d.evidence_ids and d.confidence == Confidence.strong


def test_enquiry_opening_uses_sellers_own_number(gen):
    p = gen.generate(ctx("9", eng_enq_received_90d="23", bot_answered="0"))
    assert p.decisions["plan.opening"].value == "enquiries" and "23" in p.plan.opening


def test_formal_for_established_large_business(gen):
    p = gen.generate(ctx("10", annual_turnover="25 - 100 Cr", gst_registration_year="2000"))
    assert p.language.formality == "formal" and p.voice.speaker == "priya" and p.voice.pitch < 0


def test_casual_for_new_small_retailer(gen):
    p = gen.generate(ctx("11", nature_of_business="Trader - Retailer", annual_turnover="0 - 40 L", gst_registration_year="2024"))
    assert p.language.formality == "casual"


def test_confusion_prone_segment_lowers_english_and_pace(gen):
    p = gen.generate(ctx("12", seller_state="West Bengal"))
    assert p.language.english_mix == 0.15 and "SEG-region=east-confused" in p.decisions["language.english_mix"].evidence_ids
    assert p.voice.pace < 1.0


def test_playbook_puts_sellers_own_objections_first(gen):
    p = gen.generate(ctx("13", past_objections="Information / Trust / Privacy Concerns (2); Explicit Disinterest / Refusal (1)",
                         past_dispositions_detailed="already_in_touch_with_im (1)"))
    assert list(p.plan.objection_playbook)[:3] == ["trust", "not_interested", "already_in_touch"]
    assert p.decisions["plan.objection_playbook"].source == Source.seller_data


def test_bot_question_history(gen):
    p = gen.generate(ctx("14", asked_if_talking_to_bot="1"))
    assert list(p.plan.objection_playbook)[0] == "bot_question" and p.tone.warmth == "high"


def test_do_not_call_seller_is_flagged_in_escalation(gen):
    p = gen.generate(ctx("15", do_not_call_requested="1"))
    assert "do NOT pitch" in p.plan.escalation_rules[0]


def test_guardrails_and_no_banned_fillers(gen):
    for kw in ({}, {"seller_state": "Tamil Nadu"}, {"asked_if_talking_to_bot": "1"}):
        p = gen.generate(ctx("16", **kw))
        text = p.plan.opening + " ".join(p.plan.objection_playbook.values())
        # whole words only: "तैयारी" (preparation) contains "यार" and is fine
        assert not re.search(r"(?<![\u0900-\u097F])(यार|अरे|देखो)(?![\u0900-\u097F])", text)
        assert any("never change facts" in g for g in p.plan.guardrails)
        assert not re.search(r"₹|\brs\.?\s*\d|\d+\s*rupees", text, re.I)   # no prices


def test_banned_filler_check_is_word_bounded():
    pat = r"(?<![\u0900-\u097F])(यार|अरे|देखो)(?![\u0900-\u097F])"
    assert re.search(pat, "बोलो यार") and not re.search(pat, "कोई तैयारी नहीं")


def test_deterministic(gen):
    a, b = gen.generate(ctx("17")), gen.generate(ctx("17"))
    assert a.model_dump(exclude={"created_at"}) == b.model_dump(exclude={"created_at"})


def test_contrasting_sellers_get_distinct_personas(gen):
    a = gen.generate(ctx("20", calls_call_later="2", nature_of_business="Trader - Retailer", gst_registration_year="2024"))
    b = gen.generate(ctx("21", seller_state="Tamil Nadu", annual_turnover="25 - 100 Cr", gst_registration_year="1995"))
    c = gen.generate(ctx("22", seller_state="Gujarat", calls=[BotCall(attempt_id="x", glid="22", duration_s=90)]))
    assert len({a.label, b.label, c.label}) == 3
    assert len({a.voice.pace, b.voice.pace, c.voice.pace}) >= 2
    assert len({a.language.code, b.language.code}) == 2


def test_empty_evidence_still_works():
    p = PersonaGenerator(EvidenceBook.empty()).generate(ctx("30"))
    assert p.decisions["language.style"].confidence == Confidence.guess


def test_male_forms():
    assert _gender_forms("मैं Payal बोल रही हूँ, बताती हूँ", "male") == "मैं Payal बोल रहा हूँ, बताता हूँ"
    assert _gender_forms("बोल रही हूँ", "female") == "बोल रही हूँ"
    assert "रहा" not in line("hinglish", "rush") and line("english", "direct").startswith("To be brief")


def test_v4_voices_when_model_is_v4():
    from vani.persona.voices import VOICE_MAP_V4, LANGUAGE_VOICE_V4, speaker_for
    g = PersonaGenerator(BOOK, tts_model="bulbul:v4-flash")
    p = g.generate(ctx("40"))
    assert p.voice.model == "bulbul:v4-flash" and p.voice.speaker in set(VOICE_MAP_V4.values())
    assert speaker_for("female", "neutral", "gu-IN", "bulbul:v4-flash") == "pooja_gu_customer"
    assert speaker_for("female", "neutral", "ml-IN", "bulbul:v4-flash") == "simran_enhi_customer"   # no ml voice: fallback
    assert speaker_for("female", "neutral", "hi-IN") == "ritu"                                      # v3 unchanged
    sdk_voices = set(VOICE_MAP_V4.values()) | set(LANGUAGE_VOICE_V4.values())
    assert all("_" in v for v in sdk_voices)
