"""Exercise the live (Sarvam) code path with a fake client, no network."""
import json
from pathlib import Path

from fastapi.testclient import TestClient

from app import main
from app.conversation import Session
from app.evidence import EvidenceStore
from app.sarvam import SarvamError, strip_reasoning

ROOT = Path(__file__).resolve().parent.parent


class FakeClient:
    enabled = True

    def __init__(self, fail_chat=False):
        self.fail_chat = fail_chat
        self.tts_calls, self.chat_calls = [], []

    def chat(self, messages, **kw):
        self.chat_calls.append(messages)
        if self.fail_chat:
            raise SarvamError("boom")
        return "ठीक है, कल 11 बजे मिलते हैं?"

    def tts(self, text, language_code, speaker, pace, temperature=0.6):
        self.tts_calls.append((language_code, speaker, pace))
        return "UklGRg=="

    def stt(self, audio, filename="turn.wav"):
        return {"transcript": "Yaar point pe aao!", "language_code": "hi-IN"}


def seller(sid):
    return json.loads((ROOT / "data" / "sellers" / f"{sid}.json").read_text())


def test_live_turn_uses_llm_and_new_voice_after_switch():
    fake = FakeClient()
    s = Session(seller("S103"), EvidenceStore.load(), fake)
    s.open()
    r = s.seller_turn("Yaar point pe aao, kitni der se bol rahe ho!")
    assert r["bot"]["audio_b64"] == "UklGRg=="
    assert r["bot"]["text"].startswith("ठीक है")
    # TTS after the switch is faster than the opening
    assert fake.tts_calls[-1][2] > fake.tts_calls[0][2]
    # The LLM saw the updated persona in its system prompt
    assert "Current strategy: direct" in fake.chat_calls[-1][0]["content"]


def test_llm_failure_falls_back_to_template():
    s = Session(seller("S101"), EvidenceStore.load(), FakeClient(fail_chat=True))
    s.open()
    r = s.seller_turn("Haan bolo")
    assert r["bot"]["text"]
    assert any("LLM failed" in w for w in r["warnings"])


def test_strip_reasoning():
    assert strip_reasoning("<think>hmm</think> Namaste") == "Namaste"


def test_api_offline_flow():
    api = TestClient(main.app)
    assert api.get("/api/health").json()["evidence_calls"] > 0
    start = api.post("/api/session", json={"seller_id": "S101"}).json()
    r = api.post(f"/api/session/{start['session_id']}/turn", data={"text": "Yaar point pe aao!"}).json()
    assert r["switches"][0]["signal"] == "frustration"
    assert api.post("/api/persona", json={"seller": {"name": "x"}}).status_code == 400
    custom = {"seller_id": "X1", "name": "Anil Verma", "city": "Jaipur", "state": "Rajasthan", "region": "north",
              "business_type": "trader", "age": 31, "annual_turnover": "50L-1Cr", "categories": ["Marble"],
              "languages_known": ["hi"], "engagement": {"enquiries_received_30d": 3}, "past_calls": []}
    p = api.post("/api/persona", json={"seller": custom}).json()["persona"]
    assert p["rationale"]["cold_start"]


def test_api_live_audio_turn(monkeypatch):
    fake = FakeClient()
    monkeypatch.setattr(main, "client", fake)
    api = TestClient(main.app)
    start = api.post("/api/session", json={"seller_id": "S101"}).json()
    r = api.post(f"/api/session/{start['session_id']}/turn",
                 files={"audio": ("turn.wav", b"RIFF....", "audio/wav")}).json()
    assert r["seller_text"] == "Yaar point pe aao!"
    assert r["switches"]
