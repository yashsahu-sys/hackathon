import pytest
from fastapi.testclient import TestClient

from vani.api.app import create_app
from vani.api.deps import Container
from vani.config import Settings
from vani.evidence.book import EvidenceBook
from vani.evidence.miner import EvidenceMiner
from vani.integrations.sarvam.client import OfflineSpeechAI
from vani.persona.generator import PersonaGenerator
from vani.runtime.service import CallService
from vani.runtime.store import MemorySessionStore
from tests.integration.test_call_service import FakeSpeech

SECRET = {"X-Tool-Secret": "s3cret"}


def make_client(repo, speech=None):
    settings = Settings(agent_tool_secret="s3cret")
    book = EvidenceBook(EvidenceMiner(repo).mine())
    gen = PersonaGenerator(book)
    store = MemorySessionStore()
    speech = speech or OfflineSpeechAI()
    c = Container(settings, repo, book, gen, store, speech, CallService(repo, gen, store, speech))
    return TestClient(create_app(container=c))


@pytest.fixture
def api(repo):
    with make_client(repo) as client:
        yield client


V = "/api/v1"


def test_health(api):
    h = api.get(f"{V}/health").json()
    assert h["status"] == "ok" and h["mode"] == "offline" and h["evidence_findings"] > 0


def test_sellers_list_filter_and_detail(api):
    assert len(api.get(f"{V}/sellers").json()) == 4
    assert [s["glid"] for s in api.get(f"{V}/sellers", params={"state": "Tamil Nadu"}).json()] == ["1002"]
    assert api.get(f"{V}/sellers", params={"limit": 0}).status_code == 422
    d = api.get(f"{V}/sellers/1001").json()
    assert d["profile"]["glid"] == "1001" and len(d["calls"]) == 2
    assert api.get(f"{V}/sellers/xyz").status_code == 404


def test_persona_endpoint(api):
    r = api.get(f"{V}/sellers/1002/persona").json()
    assert r["persona"]["decisions"]["language.style"]["reason"]
    assert "IndiaMART" in r["system_prompt"] and r["agent_variables"]["persona_mode"] == "standard"
    assert api.get(f"{V}/sellers/xyz/persona").status_code == 404


def test_batch_personas(api):
    r = api.post(f"{V}/personas/batch", json={"seller_glids": ["1001", "1002", "nope"]}).json()
    assert r[0]["seller_glid"] == "1001" and r[2]["error"] == "not found"
    assert api.post(f"{V}/personas/batch", json={"seller_glids": []}).status_code == 422


def test_evidence_endpoints(api):
    r = api.get(f"{V}/evidence", params={"min_strength": "weak"}).json()
    assert r["findings"] and r["caveats"]
    fid = r["findings"][0]["id"]
    assert api.get(f"{V}/evidence/{fid}").json()["id"] == fid
    assert api.get(f"{V}/evidence/nope").status_code == 404
    assert api.get(f"{V}/evidence", params={"min_strength": "bogus"}).status_code == 422


def test_full_web_call(api):
    r = api.post(f"{V}/calls", json={"seller_glid": "1001"})
    assert r.status_code == 201
    sid = r.json()["session_id"]
    t = api.post(f"{V}/calls/{sid}/turns", data={"text": "Yaar baar baar call kyun karte ho"}).json()
    assert t["switches"][0]["signal"] == "frustration" and t["persona"]["version"] == 2
    t = api.post(f"{V}/calls/{sid}/turns", data={"text": "Theek hai, kal 11 baje aa jaiye"}).json()
    assert t["outcome"] == "meeting_fixed" and t["status"] == "ended"
    assert api.post(f"{V}/calls/{sid}/turns", data={"text": "hello"}).status_code == 409
    full = api.get(f"{V}/calls/{sid}").json()
    assert full["initial_persona"]["version"] == 1 and len(full["switch_log"]) == 1
    assert api.get(f"{V}/switch-log", params={"seller_glid": "1001"}).json()[0]["signal"] == "frustration"
    assert api.get(f"{V}/calls").json()[0]["session_id"] == sid


def test_turn_validation(api):
    sid = api.post(f"{V}/calls", json={"seller_glid": "1001"}).json()["session_id"]
    assert api.post(f"{V}/calls/{sid}/turns", data={"text": "  "}).status_code == 400
    assert api.post(f"{V}/calls/{sid}/turns", files={"audio": ("a.wav", b"RIFF", "audio/wav")}).status_code == 400
    assert api.post(f"{V}/calls/nope/turns", data={"text": "hi"}).status_code == 404
    assert api.post(f"{V}/calls", json={"seller_glid": "nope"}).status_code == 404
    assert api.post(f"{V}/calls", json={"seller_glid": "1001", "channel": "fax"}).status_code == 422


def test_end_call(api):
    sid = api.post(f"{V}/calls", json={"seller_glid": "1001"}).json()["session_id"]
    assert api.post(f"{V}/calls/{sid}/end", json={"outcome": "callback"}).json()["outcome"] == "callback"


def test_audio_turn_live(repo):
    with make_client(repo, FakeSpeech()) as api:
        sid = api.post(f"{V}/calls", json={"seller_glid": "1001"}).json()["session_id"]
        t = api.post(f"{V}/calls/{sid}/turns", files={"audio": ("a.wav", b"RIFFdata", "audio/wav")}).json()
        assert t["seller_text"] == "Abhi busy hoon, baad mein" and t["bot"]["audio_b64"] == "QUFB"
        big = b"0" * (5 * 1024 * 1024 + 1)
        assert api.post(f"{V}/calls/{sid}/turns", files={"audio": ("a.wav", big, "audio/wav")}).status_code == 413


def test_agent_tools_require_secret(api):
    assert api.post(f"{V}/agent-tools/start_call", json={"seller_glid": "1001"}).status_code == 401
    assert api.post(f"{V}/agent-tools/start_call", json={"seller_glid": "1001"},
                    headers={"X-Tool-Secret": "wrong"}).status_code == 401


def test_agent_tool_flow(api):
    s = api.post(f"{V}/agent-tools/start_call", json={"seller_glid": "1001"}, headers=SECRET).json()
    assert s["session_id"] and s["persona_mode"] == "standard" and s["opening_line"]
    assert all(isinstance(v, str) for v in s.values())          # Sarvam variables are strings
    r = api.post(f"{V}/agent-tools/analyze_turn", headers=SECRET,
                 json={"session_id": s["session_id"], "seller_utterance": "Sorry, can you speak in English please"}).json()
    assert r["switched"] and r["switch_signal"] == "language_switch" and r["language_code"] == "en-IN"
    r = api.post(f"{V}/agent-tools/analyze_turn", headers=SECRET,
                 json={"session_id": s["session_id"], "seller_utterance": "Okay, tomorrow 11 works, confirm it"}).json()
    assert r["end_call"] and r["outcome"] == "meeting_fixed"
    e = api.post(f"{V}/agent-tools/end_call", headers=SECRET, json={"session_id": s["session_id"]}).json()
    assert e["outcome"] == "meeting_fixed" and e["switches"] == 1
    assert api.post(f"{V}/agent-tools/analyze_turn", headers=SECRET,
                    json={"session_id": s["session_id"], "seller_utterance": ""}).status_code == 422


@pytest.mark.realdata
def test_real_app_boots(real_repo, tmp_path):
    with make_client(real_repo) as api:
        glid = api.get(f"{V}/sellers", params={"with_transcripts": True, "limit": 1}).json()[0]["glid"]
        p = api.get(f"{V}/sellers/{glid}/persona").json()["persona"]
        assert p["decisions"]
        sid = api.post(f"{V}/calls", json={"seller_glid": glid}).json()["session_id"]
        assert api.post(f"{V}/calls/{sid}/turns", data={"text": "Abhi busy hoon"}).json()["switches"]
