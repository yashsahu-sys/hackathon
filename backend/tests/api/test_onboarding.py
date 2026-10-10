from fastapi.testclient import TestClient

from vani.api.app import create_app
from vani.api.deps import Container
from vani.config import Settings
from vani.data.onboarded import OnboardedSellerStore, OnboardingRepository
from vani.evidence.book import EvidenceBook
from vani.evidence.global_context import render_seller_brief
from vani.integrations.sarvam.client import OfflineSpeechAI
from vani.persona.generator import PersonaGenerator
from vani.runtime.service import CallService
from vani.runtime.store import MemorySessionStore

V = "/api/v1"
NEW = {"company_name": "Shree Ganesh Traders", "state": "Gujarat", "city": "Surat",
       "categories": ["Cotton Sarees", "Dress Material"], "nature_of_business": "Trader - Wholesaler/Distributor",
       "annual_turnover": "0 - 40 L", "business_type": "Proprietorship", "gst_registration_year": 2025}


def client(repo, tmp_path):
    rep = OnboardingRepository(repo, OnboardedSellerStore(tmp_path / "onb.sqlite"))
    gen, store, speech = PersonaGenerator(EvidenceBook.empty()), MemorySessionStore(), OfflineSpeechAI()
    c = Container(Settings(), rep, EvidenceBook.empty(), gen, store, speech, CallService(rep, gen, store, speech))
    return TestClient(create_app(container=c)), rep


def test_onboard_new_seller_gets_persona_and_a_call(repo, tmp_path):
    api, rep = client(repo, tmp_path)
    with api:
        opts = api.get(f"{V}/onboarding/options").json()
        assert "Gujarat" in opts["states"] and "0 - 40 L" in opts["annual_turnover"]
        r = api.post(f"{V}/sellers", json=NEW)
        assert r.status_code == 201
        glid, persona = r.json()["seller"]["glid"], r.json()["persona"]
        assert persona["decisions"]["plan.opening"]["value"] == "welcome"
        assert "स्वागत" in persona["plan"]["opening"] and "Cotton Sarees" in persona["plan"]["opening"]
        assert "Kem cho" in persona["plan"]["opening"]                       # Gujarat greeting from state
        assert api.get(f"{V}/sellers/{glid}").json()["profile"]["city"] == "Surat"
        assert [s["glid"] for s in api.get(f"{V}/sellers/onboarded").json()] == [glid]
        sid = api.post(f"{V}/calls", json={"seller_glid": glid}).json()["session_id"]
        t = api.post(f"{V}/calls/{sid}/turns", data={"text": "Abhi busy hoon"}).json()
        assert t["switches"] and t["switches"][0]["signal"] == "rush"
        assert "NEW SELLER" in render_seller_brief(rep.get_context(glid))


def test_onboarding_validation_and_conflict(repo, tmp_path):
    api, _ = client(repo, tmp_path)
    with api:
        assert api.post(f"{V}/sellers", json={**NEW, "categories": []}).status_code == 422
        assert api.post(f"{V}/sellers", json={**NEW, "glid": "1001"}).status_code == 409   # already in the dataset
        assert api.post(f"{V}/sellers", json={**NEW, "glid": "n-77"}).json()["seller"]["glid"] == "n-77"
