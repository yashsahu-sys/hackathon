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


def test_frustration_speeds_up_shortens_and_goes_direct(session):
    pace0 = session.persona.voice.pace
    seller_says(session)
    ev = A.adapt(session, [sig(T.frustration)], 1000)
    p = session.persona
    assert len(ev) == 1 and p.voice.pace > pace0 and p.tone.max_words_per_turn <= 12
    assert p.tone.strategy == "direct" and p.tone.empathy == "high" and p.version == 2
    e = ev[0]
    assert e.signal == T.frustration and e.trigger == "<frustration>" and e.from_version == 1 and e.to_version == 2
    assert {c.field for c in e.changes} >= {"voice.pace", "tone.strategy"} and e.reason


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
