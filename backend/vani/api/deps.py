"""Application container: built once at startup, injectable in tests."""
import logging
from dataclasses import dataclass

from vani.config import Settings
from vani.evidence.demand import CategoryDemand
from vani.data.onboarded import OnboardedSellerStore, OnboardingRepository
from vani.data.repository import DuckDBSellerRepository, SellerRepository
from vani.evidence.book import EvidenceBook
from vani.evidence.global_context import render_global
from vani.integrations.sarvam.client import OfflineSpeechAI, SarvamClient, SpeechAI
from vani.persona.generator import PersonaGenerator
from vani.runtime.service import CallService
from vani.runtime.store import SessionStore, SQLiteSessionStore

log = logging.getLogger(__name__)


@dataclass
class Container:
    settings: Settings
    repo: SellerRepository
    evidence: EvidenceBook
    generator: PersonaGenerator
    store: SessionStore
    speech: SpeechAI
    calls: CallService

    @classmethod
    def build(cls, settings: Settings) -> "Container":
        repo = OnboardingRepository(
            DuckDBSellerRepository(settings.resolve(settings.warehouse_path), settings.reference_year),
            OnboardedSellerStore(settings.resolve(settings.onboarded_db_path)), settings.reference_year)
        ev_path = settings.resolve(settings.evidence_path)
        if ev_path.exists():
            evidence = EvidenceBook.load(ev_path)
        else:
            log.warning("evidence book %s missing: run `python -m vani.evidence.miner`; using empty book", ev_path)
            evidence = EvidenceBook.empty()
        demand_file = settings.resolve(settings.demand_path) if settings.demand_path else None
        demand = (CategoryDemand.load(demand_file) if demand_file and demand_file.exists()
                  else CategoryDemand.build(repo.iter_profiles()))
        generator = PersonaGenerator(evidence, settings.sarvam_tts_model, demand)
        store = SQLiteSessionStore(settings.resolve(settings.sessions_db_path))
        speech: SpeechAI = SarvamClient(settings) if settings.sarvam_enabled else OfflineSpeechAI()
        return cls(settings, repo, evidence, generator, store, speech,
                   CallService(repo, generator, store, speech, llm_brain=settings.llm_brain,
                               tts_transliterate=settings.tts_transliterate, global_context=render_global(evidence)))
