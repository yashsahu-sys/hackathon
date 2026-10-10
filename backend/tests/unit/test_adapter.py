import pytest

from vani.domain.live import CallSession, Channel, Role, Signal, SignalType as T, TurnRecord
from vani.domain.persona import Confidence, Source
from vani.evidence.book import EvidenceBook
from vani.live.adapter import COOLDOWN_TURNS, PersonaAdapter
from vani.persona.generator import PersonaGenerator
from tests.unit.test_persona_generator import ctx


@pytest.fixture
def session():
    p = PersonaGenerator(EvidenceBook.empty()).generate(ctx("1"))
    return CallSession(session_id="s1", seller_glid="1", channel=Channel.web, persona=p, initial_persona=p)


def seller_says(session, n=1):
    for _ in range(n):
        session.transcript.append(TurnRecord(role=Role.seller, text="x", at_ms=0, persona_version=session.persona.version))


def sig(t, conf=0.8, **detail):
    return Signal(type=t, confidence=conf, trigger=f"<{t.value}>", detail=detail)


A = PersonaAdapter()


def test_frustration_calms_down_and_goes_direct(session):
    seller_says(session)
    ev = A.adapt(session, [sig(T.frustration)], 1000)
    p = session.persona
    assert len(ev) == 1 and p.voice.pace == 1.0 and p.tone.max_words_per_turn <= 18
    assert p.tone.strategy == "direct" and p.tone.empathy == "high" and p.version == 2
    e = ev[0]
    assert e.signal == T.frustration and e.trigger == "<frustration>" and e.from_version == 1 and e.to_version == 2
    assert {c.field for c in e.changes} >= {"voice.temperature", "tone.strategy"} and e.reason


def test_confusion_slows_down_and_simplifies(session):
    pace0 = session.persona.voice.pace
    seller_says(session)
    A.adapt(session, [sig(T.confusion)], 0)
    p = session.persona
    assert p.voice.pace < pace0 and p.language.english_mix <= 0.1 and p.tone.strategy == "clarify"


def test_rush_offers_slots(session):
    seller_says(session)
    A.adapt(session, [sig(T.rush)], 0)
    assert session.persona.tone.strategy == "rush"


def test_language_switch_to_english_rerenders_playbook_and_voice(session):
    seller_says(session)
    ev = A.adapt(session, [sig(T.language_switch, 0.95, to="en-IN")], 0)
    p = session.persona
    assert p.language.code == "en-IN" and p.language.style == "english" and p.voice.accent == "Indian English"
    assert p.plan.objection_playbook["busy"].startswith("I understand")
    assert ev[0].changes and any(c.field == "language.code" for c in ev[0].changes)


def test_language_switch_to_regional_picks_native_voice(session):
    seller_says(session)
    A.adapt(session, [sig(T.language_switch, 0.95, to="ta-IN")], 0)
    assert session.persona.language.style == "regional" and session.persona.voice.speaker == "kavitha"


def test_decisions_record_the_live_switch(session):
    seller_says(session)
    A.adapt(session, [sig(T.rush)], 0)
    d = session.persona.decisions["tone.strategy"]
    assert d.source == Source.live_signal and d.confidence == Confidence.live and "<rush>" in d.reason


def test_low_confidence_ignored(session):
    seller_says(session)
    assert A.adapt(session, [sig(T.frustration, 0.5)], 0) == [] and session.persona.version == 1


def test_flow_only_signals_do_not_change_persona(session):
    seller_says(session)
    assert A.adapt(session, [sig(T.agreement), sig(T.refusal), sig(T.identity)], 0) == []


def test_cooldown_blocks_flip_flop_then_releases(session):
    seller_says(session)
    assert A.adapt(session, [sig(T.frustration)], 0)
    session.switch_log += []
    seller_says(session)
    assert A.adapt(session, [sig(T.frustration)], 0) == []            # next turn: cooled down
    seller_says(session, COOLDOWN_TURNS)
    session.persona = session.initial_persona.model_copy(deep=True)   # (calm again, so a new switch has changes)
    assert A.adapt(session, [sig(T.frustration)], 0)                   # later: allowed again


def test_language_switch_ignores_cooldown(session):
    seller_says(session)
    A.adapt(session, [sig(T.language_switch, 0.95, to="en-IN")], 0)
    seller_says(session)
    assert A.adapt(session, [sig(T.language_switch, 0.95, to="hi-IN")], 0)


def test_pace_is_capped(session):
    for _ in range(10):
        seller_says(session, COOLDOWN_TURNS)
        A.adapt(session, [sig(T.frustration)], 0)
    assert session.persona.voice.pace <= 1.4


def test_strategy_priority_handoff_beats_close(session):
    seller_says(session)
    A.adapt(session, [sig(T.interest, 0.9), sig(T.human_request, 0.8)], 0)
    assert session.persona.tone.strategy == "handoff"


def test_do_not_call_ends(session):
    seller_says(session)
    A.adapt(session, [sig(T.do_not_call)], 0)
    assert session.persona.tone.strategy == "end"


def test_label_keeps_switch_trail(session):
    seller_says(session)
    session.switch_log += A.adapt(session, [sig(T.rush)], 0)
    seller_says(session)
    A.adapt(session, [sig(T.language_switch, 0.95, to="en-IN")], 0)
    assert session.persona.label.endswith("→ rush → language switch")


def test_initial_persona_untouched(session):
    seller_says(session)
    A.adapt(session, [sig(T.frustration)], 0)
    assert session.initial_persona.version == 1 and session.initial_persona.tone.strategy == "standard"


def test_distinctness_metric():
    from vani.persona.distinct import distance, most_distinct
    gen = PersonaGenerator(EvidenceBook.empty())
    a = gen.generate(ctx("1"))
    b = gen.generate(ctx("2", seller_state="Tamil Nadu", annual_turnover="25 - 100 Cr", gst_registration_year="1990"))
    c = gen.generate(ctx("3", calls_call_later="3"))
    assert distance(a, a) == 0 and distance(a, b) > 0 and distance(a, b) == distance(b, a)
    chosen, min_d = most_distinct([a, a.model_copy(), b, c], 3)
    assert len(chosen) == 3 and min_d > 0


def test_latest_turn_sets_strategy_slow_down_replaces_rush(session):
    seller_says(session)
    A.adapt(session, [sig(T.rush)], 0)
    assert session.persona.tone.strategy == "rush"
    seller_says(session)
    A.adapt(session, [sig(T.slow_down)], 0)
    assert session.persona.tone.strategy == "clarify"


def test_end_is_final(session):
    seller_says(session)
    A.adapt(session, [sig(T.end_call)], 0)
    seller_says(session, 3)
    A.adapt(session, [sig(T.interest)], 0)
    assert session.persona.tone.strategy == "end"
