import pytest

from vani.domain.live import CallStatus, Channel, Outcome, SignalType as T
from vani.evidence.book import EvidenceBook
from vani.integrations.sarvam.client import OfflineSpeechAI, SarvamError
from vani.persona.generator import PersonaGenerator
from vani.runtime.service import CallClosed, CallService, NotFound
from vani.runtime.store import MemorySessionStore


class FakeSpeech:
    enabled = True

    def __init__(self, reply="जी, कल 11 बजे ठीक रहेगा?", fail_chat=False, transcript="Abhi busy hoon, baad mein"):
        self.reply, self.fail_chat, self.transcript = reply, fail_chat, transcript
        self.tts_calls, self.chat_calls = [], []

    async def stt(self, audio, filename="turn.wav"):
        return {"transcript": self.transcript, "language_code": "hi-IN"}

    async def tts(self, text, language_code, speaker, pace, pitch=None):
        self.tts_calls.append({"text": text, "lang": language_code, "speaker": speaker, "pace": pace})
        return "QUFB"

    async def chat(self, messages, max_tokens=200):
        self.chat_calls.append(messages)
        if self.fail_chat:
            raise SarvamError("llm down")
        return self.reply


@pytest.fixture
def svc(repo):
    return CallService(repo, PersonaGenerator(EvidenceBook.empty()), MemorySessionStore(), OfflineSpeechAI())


async def test_offline_call_with_switch_then_meeting(svc):
    s, opening = await svc.start("1001")
    assert opening.text == s.persona.plan.opening and opening.audio_b64 is None
    r = await svc.seller_turn(s.session_id, "Haan bolo")
    assert r.move == "pitch"
    r = await svc.seller_turn(s.session_id, "Abhi busy hoon, baad mein baat karo")
    assert [e.signal for e in r.switches] == [T.rush] and r.move in ("rush", "call_later")
    r = await svc.seller_turn(s.session_id, "Theek hai, kal 11 baje aa jaiye")
    assert r.session.outcome == Outcome.meeting_fixed and r.session.status == CallStatus.ended
    stored = svc.store.get(s.session_id)
    assert len(stored.switch_log) == 1 and len(stored.transcript) == 7
    assert len(svc.store.switch_log(seller_glid="1001")) == 1


async def test_language_switch_mid_call_changes_reply_language(svc):
    s, _ = await svc.start("1001")
    r = await svc.seller_turn(s.session_id, "Sorry, can you speak in English please")
    assert r.session.persona.language.code == "en-IN" and r.bot.language_code == "en-IN"
    assert r.bot.text.isascii()


async def test_two_refusals_end_politely(svc):
    s, _ = await svc.start("1001")
    await svc.seller_turn(s.session_id, "Nahi chahiye")
    r = await svc.seller_turn(s.session_id, "Bola na, interest nahi hai")
    assert r.session.outcome == Outcome.declined and r.session.status == CallStatus.ended


async def test_ended_call_rejects_turns(svc):
    s, _ = await svc.start("1001")
    await svc.seller_turn(s.session_id, "Dubara call mat kijiye")
    with pytest.raises(CallClosed):
        await svc.seller_turn(s.session_id, "hello")


async def test_errors(svc):
    with pytest.raises(NotFound):
        await svc.start("nope")
    with pytest.raises(NotFound):
        await svc.seller_turn("nope", "hi")
    s, _ = await svc.start("1001")
    with pytest.raises(ValueError):
        await svc.seller_turn(s.session_id, "   ")


async def test_end_marks_dropped(svc):
    s, _ = await svc.start("1001")
    assert svc.end(s.session_id).outcome == Outcome.dropped
    assert svc.end(s.session_id, Outcome.callback).outcome == Outcome.callback


async def test_live_path_uses_llm_and_switched_voice(repo):
    fake = FakeSpeech()
    svc = CallService(repo, PersonaGenerator(EvidenceBook.empty()), MemorySessionStore(), fake)
    s, opening = await svc.start("1001")
    assert opening.audio_b64 == "QUFB"
    r = await svc.seller_turn(s.session_id, audio=b"RIFF")
    assert r.seller_text == "Abhi busy hoon, baad mein" and r.bot.source == "llm" and r.bot.audio_b64 == "QUFB"
    assert fake.tts_calls[-1]["pace"] > fake.tts_calls[0]["pace"]          # faster after the rush switch
    assert "Current strategy: rush" in fake.chat_calls[-1][0]["content"]  # LLM saw the new persona
    assert "[Next move" in fake.chat_calls[-1][-1]["content"]


async def test_llm_failure_falls_back_to_template(repo):
    svc = CallService(repo, PersonaGenerator(EvidenceBook.empty()), MemorySessionStore(), FakeSpeech(fail_chat=True))
    s, _ = await svc.start("1001")
    r = await svc.seller_turn(s.session_id, "Haan bolo")
    assert r.bot.source == "template" and any("LLM failed" in w for w in r.warnings)


async def test_llm_output_with_banned_filler_is_rejected(repo):
    svc = CallService(repo, PersonaGenerator(EvidenceBook.empty()), MemorySessionStore(), FakeSpeech(reply="अरे यार सुनो"))
    s, _ = await svc.start("1001")
    r = await svc.seller_turn(s.session_id, "Haan bolo")
    assert r.bot.source == "template" and any("guardrail" in w for w in r.warnings)


async def test_meeting_confirmation_never_paraphrased(repo):
    fake = FakeSpeech(reply="something else")
    svc = CallService(repo, PersonaGenerator(EvidenceBook.empty()), MemorySessionStore(), fake)
    s, _ = await svc.start("1001")
    r = await svc.seller_turn(s.session_id, "Haan theek hai kal 11 baje aa jaiye")
    assert r.move == "meeting_confirm" and r.bot.source == "template"


async def test_agent_channel_returns_directives_without_speech(repo):
    fake = FakeSpeech()
    svc = CallService(repo, PersonaGenerator(EvidenceBook.empty()), MemorySessionStore(), fake)
    s, _ = await svc.start("1001", channel=Channel.sarvam_agent)
    r = await svc.seller_turn(s.session_id, "Aap baar baar call kyun karte ho")
    assert fake.tts_calls == [] and fake.chat_calls == []
    d = svc.agent_directives(r.session, r.move)
    assert d["persona_mode"] == "direct" and d["persona_version"] == "2" and float(d["pace"]) > 1.0
