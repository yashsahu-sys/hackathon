import json

import httpx
import pytest

from vani.config import Settings
from vani.integrations.sarvam.client import OfflineSpeechAI, SarvamClient, SarvamError


def client(handler, **kw):
    s = Settings(sarvam_api_key="k-123", **kw)
    return SarvamClient(s, transport=httpx.MockTransport(handler))


async def test_stt_request_shape():
    seen = {}

    def h(req: httpx.Request):
        seen["path"], seen["key"], seen["body"] = req.url.path, req.headers["api-subscription-key"], req.content
        return httpx.Response(200, json={"transcript": "haan bolo", "language_code": "hi-IN", "language_probability": 0.9})
    out = await client(h).stt(b"RIFFxxxx")
    assert out == {"transcript": "haan bolo", "language_code": "hi-IN", "language_probability": 0.9}
    assert seen["path"] == "/speech-to-text" and seen["key"] == "k-123"
    body = seen["body"].decode(errors="ignore")
    for field in ('name="model"', "saaras:v3", 'name="mode"', "codemix", 'name="language_code"', "unknown", 'name="file"'):
        assert field in body


async def test_tts_v3_omits_pitch_and_clamps_pace():
    seen = {}

    def h(req):
        seen.update(json.loads(req.content))
        return httpx.Response(200, json={"audios": ["UklGRg=="]})
    audio = await client(h).tts("नमस्ते", "hi-IN", "ritu", pace=3.5, pitch=0.2)
    assert audio == "UklGRg==" and seen["pace"] == 2.0 and "pitch" not in seen and seen["model"] == "bulbul:v3"
    assert seen["speaker"] == "ritu" and seen["language_code"] == "hi-IN"


async def test_tts_v2_sends_pitch():
    seen = {}

    def h(req):
        seen.update(json.loads(req.content))
        return httpx.Response(200, json={"audios": ["x"]})
    await client(h, sarvam_tts_model="bulbul:v2").tts("hi", "en-IN", "anushka", pace=1.0, pitch=-2)
    assert seen["pitch"] == -0.75


async def test_tts_empty_audio_is_error():
    with pytest.raises(SarvamError):
        await client(lambda r: httpx.Response(200, json={"audios": []})).tts("hi", "hi-IN", "ritu", 1.0)


async def test_chat_strips_reasoning_and_quotes():
    def h(req):
        body = json.loads(req.content)
        assert body["model"] == "sarvam-105b" and body["reasoning_effort"] == "low"
        return httpx.Response(200, json={"choices": [{"message": {"content": '<think>plan</think> "जी, कल 11 बजे?"'}}]})
    assert await client(h).chat([{"role": "user", "content": "x"}]) == "जी, कल 11 बजे?"


async def test_chat_bad_shape():
    with pytest.raises(SarvamError):
        await client(lambda r: httpx.Response(200, json={"oops": 1})).chat([])


async def test_retries_5xx_then_succeeds():
    calls = {"n": 0}

    def h(req):
        calls["n"] += 1
        return httpx.Response(503, text="busy") if calls["n"] == 1 else httpx.Response(200, json={"audios": ["ok"]})
    assert await client(h).tts("a", "hi-IN", "ritu", 1.0) == "ok" and calls["n"] == 2


async def test_no_retry_on_4xx_and_status_kept():
    calls = {"n": 0}

    def h(req):
        calls["n"] += 1
        return httpx.Response(401, text="bad key")
    with pytest.raises(SarvamError) as e:
        await client(h).tts("a", "hi-IN", "ritu", 1.0)
    assert e.value.status == 401 and calls["n"] == 1


async def test_network_error_wrapped():
    def h(req):
        raise httpx.ConnectError("down")
    with pytest.raises(SarvamError, match="ConnectError"):
        await client(h).chat([])


def test_enabled_flag():
    assert SarvamClient(Settings(sarvam_api_key="")).enabled is False
    assert SarvamClient(Settings(sarvam_api_key="x")).enabled is True


async def test_offline_raises():
    o = OfflineSpeechAI()
    assert not o.enabled
    for coro in (o.stt(b""), o.tts("a"), o.chat([])):
        with pytest.raises(SarvamError):
            await coro


async def test_tts_falls_back_to_target_language_code():
    bodies = []

    def h(req):
        body = json.loads(req.content)
        bodies.append(body)
        if "language_code" in body:
            return httpx.Response(422, text='{"detail":"field target_language_code required"}')
        return httpx.Response(200, json={"audios": ["ok"]})
    assert await client(h).tts("hi", "hi-IN", "ritu", 1.0) == "ok"
    assert "target_language_code" in bodies[-1] and "language_code" not in bodies[-1]


async def test_tts_other_422_not_retried():
    calls = []

    def h(req):
        calls.append(1)
        return httpx.Response(422, text="speaker invalid")
    with pytest.raises(SarvamError):
        await client(h).tts("hi", "hi-IN", "nobody", 1.0)
    assert len(calls) == 1
