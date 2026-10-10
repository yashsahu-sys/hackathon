import json

import httpx
import pytest

from vani.config import Settings
from vani.domain.live import SignalType as T
from vani.domain.persona import PersonaSpec
from vani.evidence.book import EvidenceBook
from vani.integrations.sarvam.client import SarvamClient, SarvamError
from vani.live.brain import SCHEMA, LLMBrain, parse
from vani.persona.generator import PersonaGenerator
from vani.speech.tts_text import clean, for_bulbul, is_roman_hindi
from tests.unit.test_persona_generator import ctx


def test_parse_valid():
    r = parse('{"signals":["frustration","end_call"],"agreed_to_meeting":false,"objection":"none",'
              '"language":"hi-IN","reply":"माफ़ी चाहती हूँ"}')
    assert r.signals == {T.frustration, T.end_call} and not r.agreed and r.objection is None and r.reply


def test_parse_agreement_follows_flag():
    assert T.agreement in parse('{"signals":[],"agreed_to_meeting":true,"reply":"x"}').signals
    assert T.agreement not in parse('{"signals":["agreement"],"agreed_to_meeting":false,"reply":"x"}').signals


def test_parse_tolerates_wrapping_and_junk_labels():
    r = parse('Sure! ```json {"signals":["rush","dancing"],"agreed_to_meeting":false,"reply":"ok"} ```')
    assert r.signals == {T.rush}


@pytest.mark.parametrize("raw", ["", "no json here", "{broken", None])
def test_parse_garbage(raw):
    assert parse(raw) is None


def test_schema_is_strict_and_complete():
    sch = SCHEMA["json_schema"]["schema"]
    assert SCHEMA["json_schema"]["strict"] and sch["additionalProperties"] is False
    assert set(sch["required"]) == set(sch["properties"])


async def test_brain_falls_back_to_json_object_when_schema_rejected():
    formats = []

    def h(req):
        body = json.loads(req.content)
        formats.append(body["response_format"]["type"])
        if body["response_format"]["type"] == "json_schema":
            return httpx.Response(422, text="response_format json_schema not supported")
        return httpx.Response(200, json={"choices": [{"message": {"content":
            '{"signals":["rush"],"agreed_to_meeting":false,"objection":"busy","language":"hi-IN","reply":"ji"}'}}]})
    client = SarvamClient(Settings(sarvam_api_key="k"), transport=httpx.MockTransport(h))
    brain = LLMBrain(client)
    from vani.domain.live import CallSession, Channel
    c = ctx("1")
    p = PersonaGenerator(EvidenceBook.empty()).generate(c)
    s = CallSession(session_id="s", seller_glid="1", channel=Channel.web, persona=p, initial_persona=p)
    r = await brain.think(s, c, "busy hoon", ["rush"])
    assert r.signals == {T.rush} and r.objection == "busy" and formats == ["json_schema", "json_object"]
    await brain.think(s, c, "busy hoon", [])
    assert formats[-1] == "json_object"          # remembers the downgrade


async def test_transliterate_client():
    def h(req):
        body = json.loads(req.content)
        assert req.url.path == "/transliterate" and body["source_language_code"] == "en-IN"
        return httpx.Response(200, json={"transliterated_text": "नमस्ते"})
    client = SarvamClient(Settings(sarvam_api_key="k"), transport=httpx.MockTransport(h))
    assert await client.transliterate("namaste", "en-IN", "hi-IN") == "नमस्ते"


def test_clean_for_tts():
    assert clean("**Hello** 😊 [note] (aside) world", 25) == "Hello world"
    assert clean("कुल 1500000 buyers", 25) == "कुल 15,00,000 buyers"
    assert clean("pin 1234 aur 12345", 25) == "pin 1234 aur 12,345"
    long = " ".join(["शब्द"] * 80) + "।"
    assert len(clean(long, 10).split()) <= 20


def test_roman_hindi_detection():
    assert is_roman_hindi("Theek hai ji, main aapko kal call karti hoon")
    assert not is_roman_hindi("Sure, I will call you tomorrow")
    assert not is_roman_hindi("ठीक है जी")
