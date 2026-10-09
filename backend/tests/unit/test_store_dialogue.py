import pytest

from vani.domain.live import (CallSession, CallStatus, Channel, FieldChange, Outcome, Role, SignalType as T,
                              SwitchEvent, TurnRecord)
from vani.evidence.book import EvidenceBook
from vani.persona.generator import PersonaGenerator
from vani.runtime.dialogue import next_move
from vani.runtime.store import MemorySessionStore, SQLiteSessionStore
from tests.unit.test_persona_generator import ctx


def make_session(sid="s1", glid="1", **kw):
    p = PersonaGenerator(EvidenceBook.empty()).generate(ctx(glid, **kw))
    return CallSession(session_id=sid, seller_glid=glid, channel=Channel.web, persona=p, initial_persona=p)


def event(sid, turn=1):
    return SwitchEvent(session_id=sid, turn=turn, at_ms=10, signal=T.rush, confidence=0.8, trigger="busy",
                       changes=[FieldChange(field="voice.pace", old=1.0, new=1.1)], reason="r", from_version=1, to_version=2)


@pytest.fixture(params=["memory", "sqlite"])
def store(request, tmp_path):
    if request.param == "memory":
        yield MemorySessionStore()
    else:
        s = SQLiteSessionStore(tmp_path / "s.sqlite")
        yield s
        s.close()


def test_store_roundtrip(store):
    s = make_session()
    s.transcript.append(TurnRecord(role=Role.seller, text="haan", at_ms=5, persona_version=1))
    store.save(s)
    got = store.get("s1")
    assert got.model_dump() == s.model_dump()
    assert store.get("nope") is None


def test_store_upsert_and_events(store):
    s = make_session()
    store.save(s, [event("s1")])
    s.status, s.outcome = CallStatus.ended, Outcome.meeting_fixed
    store.save(s, [event("s1", 2)])
    assert store.get("s1").outcome == Outcome.meeting_fixed
    assert [e.turn for e in store.switch_log()] == [2, 1]
    assert store.switch_log(seller_glid="other") == []
    store.save(make_session("s2", glid="2"), [event("s2")])
    assert len(store.switch_log(seller_glid="2")) == 1
    listed = store.list_sessions()
    assert {x["session_id"] for x in listed} == {"s1", "s2"} and all("persona" in x for x in listed)


def test_sqlite_persists_across_connections(tmp_path):
    a = SQLiteSessionStore(tmp_path / "p.sqlite")
    a.save(make_session(), [event("s1")])
    a.close()
    b = SQLiteSessionStore(tmp_path / "p.sqlite")
    assert b.get("s1") and len(b.switch_log()) == 1
    b.close()


# ---------------------------------------------------------------- dialogue
def mv(session, text, types=(), used=None, new_unavailable=None):
    return next_move(session, text, set(types), used, new_unavailable)


def Ctxless(session, key):
    from vani.runtime.dialogue import Ctx
    return Ctx(session).line(key)


def test_opening_then_pitch_then_ask():
    s = make_session()
    m = mv(s, "haan bolo")
    assert m.key == "pitch" and m.stage == "pitch"
    s.stage = "pitch"
    assert mv(s, "achha").key == "meeting_ask"


def test_agreement_with_agreed_slot_fixes_that_slot():
    s = make_session()
    s.stage, s.agreed_slot = "ask", {"day": "day_after", "hour": 17, "minute": 0}
    m = mv(s, "haan theek hai", [T.agreement])
    assert m.outcome == Outcome.meeting_fixed and m.end_call and "परसों शाम 5 बजे" in m.text


def test_agreement_without_slot_asks_for_time():
    s = make_session()
    s.stage = "ask"
    m = mv(s, "haan theek hai", [T.agreement])
    assert m.key == "ask_time" and m.outcome is None and len(m.offered) == 2


def test_ruled_out_day_triggers_reschedule_without_it():
    s = make_session()
    s.stage, s.unavailable_days = "ask", ["tomorrow"]
    m = mv(s, "kal free nahi hoon", [T.rush], new_unavailable={"tomorrow"})
    assert m.key == "reschedule" and "कल" not in m.text and all(o.day != "tomorrow" for o in m.offered)


def test_lines_never_contain_raw_placeholders():
    s = make_session()
    for key in ("pitch", "meeting_ask", "rush", "direct", "close", "handoff", "ask_time", "reschedule"):
        s.persona.tone.strategy = "standard"
        assert "{slot" not in Ctxless(s, key)


def test_plain_haan_in_opening_is_not_a_meeting():
    assert mv(make_session(), "haan ji", [T.agreement]).outcome is None


def test_first_refusal_gets_one_answer_second_ends():
    s = make_session()
    m = mv(s, "nahi chahiye", [T.refusal])
    assert m.key == "not_interested" and not m.end_call
    s.refusals = 1
    m = mv(s, "bola na nahi chahiye", [T.refusal])
    assert m.outcome == Outcome.declined and m.end_call


def test_refusal_with_other_platform_and_value():
    s = make_session()
    assert mv(s, "nahi, tradeindia pe hoon", [T.refusal]).key == "other_platform"
    assert mv(s, "koi fayda nahi", [T.refusal]).key == "value"


def test_do_not_call_ends_immediately():
    m = mv(make_session(), "call mat karo", [T.do_not_call])
    assert m.key == "dnc_close" and m.end_call and m.outcome == Outcome.declined


def test_identity_question():
    m = mv(make_session(), "kaun bol raha hai", [T.identity])
    assert m.key == "identity" and "IndiaMART" in m.text


def test_strategy_line_spoken_once():
    s = make_session()
    s.persona.tone.strategy = "rush"
    assert mv(s, "busy hoon", [T.rush]).key == "rush"
    assert mv(s, "haan", [], used="rush").key != "rush"


def test_objection_keywords():
    s = make_session()
    assert mv(s, "isme kitna paisa lagega").key == "price"
    assert mv(s, "details whatsapp kar do").key == "send_whatsapp"
    assert mv(s, "baad mein call karna").key == "call_later"


def test_repeated_ask_is_rephrased():
    s = make_session()
    s.stage = "ask"
    ask = mv(s, "hmm").text
    s.transcript.append(TurnRecord(role=Role.bot, text=ask, at_ms=0, persona_version=1))
    assert mv(s, "hmm").key == "direct"


def test_english_persona_speaks_english():
    s = make_session(seller_state="Tamil Nadu")
    assert mv(s, "yes").text.startswith("Our executive")
