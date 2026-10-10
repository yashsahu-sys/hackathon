"""Vercel entry point: the FastAPI app on the public DEMO dataset (fictional sellers, aggregate evidence).

Real seller data never ships: data/private/ is gitignored, so it isn't in the deploy. The only
secret is SARVAM_API_KEY, set in Vercel > Project > Settings > Environment Variables.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

os.environ.setdefault("WAREHOUSE_PATH", str(ROOT / "demo" / "warehouse.duckdb"))
os.environ.setdefault("EVIDENCE_PATH", str(ROOT / "demo" / "evidence.json"))
os.environ.setdefault("DEMAND_PATH", str(ROOT / "demo" / "demand.json"))
os.environ.setdefault("SESSIONS_DB_PATH", "/tmp/vani_sessions.sqlite")      # the only writable place on Vercel
os.environ.setdefault("ONBOARDED_DB_PATH", "/tmp/vani_onboarded.sqlite")

from vani.api.app import app  # noqa: E402

__all__ = ["app"]
