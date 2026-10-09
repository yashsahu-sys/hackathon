"""Seller gender from their own words, male bot voice, audible tone/pace switches."""
import pytest

from vani.domain.live import CallSession, Channel, Role, Signal, SignalType as T, TurnRecord
from vani.domain.seller import CallTurn
from vani.evidence.book import EvidenceBook
from vani.live.adapter import FRUSTRATION_PACE, RUSH_PACE, SLOW_PACE, TEMP, PersonaAdapter
from vani.live.signals import SignalDetector
from vani.persona.generator import PersonaGenerator
from vani.persona.prompt import agent_variables, system_prompt
from vani.persona.voices import VOICE_MAP
from vani.text.gender import detect_seller_gender
from tests.unit.test_persona_generator import ctx

GEN = PersonaGenerator(EvidenceBook.empty())


# ----------------------------------------------------------- seller gender
@pytest.mark.parametrize("texts,expected", [
    (["Haan ji, main bol raha hoon"], "male"),
    (["Main kal bataunga"], "male"),
    (["Main dekh leta hoon, phir karunga"], "male"),
    (["मैं बोल रहा हूँ"], "male"),
    (["Main bol rahi hoon"], "female"),
    (["Theek hai, main call karungi"], "female"),
    (["मैं आऊँगी"], "female"),
    (["Abhi busy hoon"], "unknown"),                     # no gendered verb
    (["Meeting ho rahi hai kya?"], "unknown"),           # describes the meeting, not the speaker
    (["Main bol raha hoon", "main aaungi"], "unknown"),  # contradictory: don't guess
    ([], "unknown"),
])
def test_detect_seller_gender(texts, expected):
    assert detect_seller_gender(texts)[0] == expected


def test_gender_confidence_grows_with_evidence():
    one = detect_seller_gender(["main bol raha hoon"])[1]
    three = detect_seller_gender(["main bol raha hoon", "main karunga", "main aaunga"])[1]
    assert 0.7 == one < three <= 0.95


def test_generator_learns_seller_gender_from_past_transcript():
    turns = [CallTurn(attempt_id="a", turn_no=2, speaker="seller", text="Haan ji main bol raha hoon")]
    p = GEN.generate(ctx("60", turns=turns))
    assert p.language.seller_gender == "male" and p.language.address_as == "सर"
    assert p.decisions["language.seller_gender"].source.value == "seller_data"
    assert "raha hoon" in p.decisions["language.seller_gender"].reason


def test_generator_stays_neutral_without_evidence():
    p = GEN.generate(ctx("61"))
    assert p.language.seller_gender == "unknown" and p.language.address_as == "जी"


def test_prompt_rules_follow_seller_gender():
    c = ctx("62")
    p = GEN.generate(c)
    assert 'never "sir"' in system_prompt(p, c.profile)
    p.language.seller_gender, p.language.address_as = "female", "मैडम"
    sp = system_prompt(p, c.profile)
    assert "The seller is a woman" in sp and "मैडम" in sp
    v = agent_variables(p, c.profile)
    assert v["seller_gender"] == "female" and v["address_as"] == "मैडम" and v["voice_gender"] == "female"


# --------------------------------------------------------------- male voice
def test_male_voice_override():
    p = GEN.generate(ctx("63"), voice_gender="male")
    assert p.voice.gender == "male" and p.voice.speaker in {v for (g, _), v in VOICE_MAP.items() if g == "male"}
    assert "Arjun" in p.plan.opening and "रहा हूँ" in p.plan.opening and "रही" not in p.plan.opening
    assert all("रही हूँ" not in t for t in p.plan.objection_playbook.values())
    assert "operator" in p.decisions["voice.gender"].reason
    assert "masculine Hindi verb forms" in system_prompt(p, ctx("63").profile)


def test_default_voice_is_female_and_says_so():
    p = GEN.generate(ctx("64"))
    assert p.voice.gender == "female" and "male is available" in p.decisions["voice.gender"].reason


def test_voice_override_ignores_junk():
    assert GEN.generate(ctx("65"), voice_gender="robot").voice.gender == "female"


# ------------------------------------------------------ audible tone & pace
def session(**kw):
    p = GEN.generate(ctx("70", **kw))
    s = CallSession(session_id="s", seller_glid="70", channel=Channel.web, persona=p, initial_persona=p)
    s.transcript.append(TurnRecord(role=Role.seller, text="x", at_ms=0, persona_version=1))
    return s


def fire(s, t, **detail):
    return PersonaAdapter().adapt(s, [Signal(type=t, confidence=0.9, trigger="<x>", detail=detail)], 0)


def test_initial_temperature_by_register():
    assert GEN.generate(ctx("71", annual_turnover="25 - 100 Cr")).voice.temperature == 0.5   # formal: steady
    casual = dict(nature_of_business="Trader - Retailer", gst_registration_year="2024")
    assert GEN.generate(ctx("72", past_dispositions_detailed="", calls_not_interested="0", **casual)).voice.temperature == 0.7
    # same seller with a past "not interested": empathy high -> steadier, softer voice
    assert GEN.generate(ctx("73", **casual)).voice.temperature == 0.55


def test_frustration_is_audibly_calmer_and_quicker():
    s = session()
    fire(s, T.frustration)
    assert s.persona.voice.pace >= FRUSTRATION_PACE and s.persona.voice.temperature == TEMP["calm"]


def test_rush_jumps_to_rush_pace():
    s = session()
    fire(s, T.rush)
    assert s.persona.voice.pace >= RUSH_PACE


def test_confusion_and_slow_down_drop_pace_and_steady_voice():
    for t in (T.confusion, T.slow_down):
        s = session()
        fire(s, t)
        assert s.persona.voice.pace <= SLOW_PACE and s.persona.voice.temperature == TEMP["clear"]
        assert s.persona.tone.strategy == "clarify"


def test_interest_makes_voice_livelier():
    s = session()
    fire(s, T.interest)
    assert s.persona.voice.temperature == TEMP["lively"]


def test_seller_gender_switch_changes_address_once():
    s = session()
    ev = fire(s, T.seller_gender, gender="female")
    assert s.persona.language.address_as == "मैडम" and ev[0].signal == T.seller_gender
    assert fire(s, T.seller_gender, gender="female") == []            # already known: no duplicate event


def test_language_switch_keeps_known_seller_gender():
    s = session()
    fire(s, T.seller_gender, gender="male")
    fire(s, T.language_switch, to="en-IN")
    assert s.persona.language.address_as == "Sir"


# ------------------------------------------------------------- detection
DET = SignalDetector()


@pytest.mark.parametrize("text", ["Thoda dheere boliye", "Itna fast mat bolo", "Please speak slowly", "धीरे बोलिए"])
def test_slow_down_requests(text):
    types = {s.type for s in DET.detect(text, "hi-IN")}
    assert T.slow_down in types and T.rush not in types


def test_jaldi_bataiye_is_rush():
    assert T.rush in {s.type for s in DET.detect("Jaldi bataiye kya kaam hai", "hi-IN")}
