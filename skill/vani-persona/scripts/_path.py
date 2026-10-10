"""Make backend/ importable, and fall back to the public demo dataset when the real one isn't here."""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))

if not (ROOT / "data" / "private" / "warehouse.duckdb").exists() and "WAREHOUSE_PATH" not in os.environ:
    demo = ROOT / "demo"
    os.environ.update(WAREHOUSE_PATH=str(demo / "warehouse.duckdb"), EVIDENCE_PATH=str(demo / "evidence.json"),
                      DEMAND_PATH=str(demo / "demand.json"))
    tmp = Path(tempfile.gettempdir())
    os.environ.setdefault("SESSIONS_DB_PATH", str(tmp / "vani_skill_sessions.sqlite"))
    os.environ.setdefault("ONBOARDED_DB_PATH", str(tmp / "vani_skill_onboarded.sqlite"))
