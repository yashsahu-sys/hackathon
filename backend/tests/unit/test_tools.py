import io
import sys

from vani.tools import doctor
from vani.tools.console import utf8_console


def test_doctor_reports_every_check(monkeypatch):
    rows = doctor.check()
    names = " ".join(r[1] for r in rows)
    for must in ("Python", "package duckdb", ".env", "SARVAM_API_KEY", "gc_seller_profile.csv", "warehouse", "evidence"):
        assert must in names
    assert all(r[0] in (doctor.OK, doctor.BAD, doctor.WARN) for r in rows)
    assert all(r[2] for r in rows if r[0] == doctor.BAD)        # every failure says how to fix it


def test_doctor_flags_missing_key(monkeypatch):
    from vani import config
    config.get_settings.cache_clear()
    monkeypatch.setenv("SARVAM_API_KEY", "")
    monkeypatch.setattr(config.Settings, "model_config", {**config.Settings.model_config, "env_file": None})
    try:
        rows = {r[1]: r for r in doctor.check()}
        assert rows["SARVAM_API_KEY set"][0] == doctor.BAD
    finally:
        config.get_settings.cache_clear()


def test_utf8_console_survives_cp1252(monkeypatch):
    raw = io.BytesIO()
    stream = io.TextIOWrapper(raw, encoding="cp1252")
    monkeypatch.setattr(sys, "stdout", stream)
    utf8_console()
    print("नमस्ते जी")
    sys.stdout.flush()
    assert "नमस्ते".encode() in raw.getvalue()


def test_smoke_hints():
    from vani.integrations.sarvam.client import SarvamError
    from vani.tools.smoke import hint
    assert "network" in hint(SarvamError("x"), "M")
    assert "key" in hint(SarvamError("x", 401), "M")
    assert "M" in hint(SarvamError("x", 404), "M")
    assert "credits" in hint(SarvamError("x", 429), "M")
