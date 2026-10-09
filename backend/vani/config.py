"""Settings from environment / .env. One place for every knob."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(REPO_ROOT / "backend" / ".env", REPO_ROOT / ".env"), extra="ignore")

    sarvam_api_key: str = ""
    sarvam_base_url: str = "https://api.sarvam.ai"
    sarvam_chat_model: str = "sarvam-105b"
    sarvam_stt_model: str = "saaras:v3"
    sarvam_tts_model: str = "bulbul:v3"
    sarvam_timeout_s: float = 20.0

    agent_tool_secret: str = "change-me"

    raw_data_dir: Path = Path("data/private/raw/gc")
    warehouse_path: Path = Path("data/private/warehouse.duckdb")
    sessions_db_path: Path = Path("data/private/sessions.sqlite")
    evidence_path: Path = Path("data/private/evidence.json")

    reference_year: int = 2026   # dataset window ends Oct 2026

    def resolve(self, p: Path) -> Path:
        return p if p.is_absolute() else REPO_ROOT / p

    @property
    def sarvam_enabled(self) -> bool:
        return bool(self.sarvam_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
