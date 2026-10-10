"""Check the laptop setup step by step and say exactly what to fix.

    python -m vani.tools.doctor          (run from the backend/ folder)
"""
import importlib
import importlib.util
import sys

from vani.tools.console import utf8_console

OK, BAD, WARN = "[ OK ]", "[FAIL]", "[WARN]"
REQUIRED_CSV = ["gc_seller_profile.csv", "gc_bot_calls.csv"]
OPTIONAL_CSV = ["gc_bot_call_turns.csv", "gc_executive_calls.csv"]


def check() -> list[tuple[str, str, str]]:
    out: list[tuple[str, str, str]] = []
    v = sys.version_info
    out.append((OK if v >= (3, 10) else BAD, f"Python {v.major}.{v.minor}",
                "" if v >= (3, 10) else "Install Python 3.10 or newer from python.org"))
    for mod in ("fastapi", "uvicorn", "pydantic_settings", "httpx", "duckdb", "python_multipart|multipart", "pytest"):
        names = mod.split("|")   # python-multipart renamed its import; accept either
        found = next((n for n in names if importlib.util.find_spec(n)), None)
        out.append((OK, f"package {names[0]}", "") if found else
                   (BAD, f"package {names[0]}", "Run: pip install -r requirements.txt"))
    try:
        from vani.config import REPO_ROOT, get_settings
    except Exception as exc:   # noqa: BLE001
        out.append((BAD, "import vani", f"Run this from the backend/ folder ({exc})"))
        return out
    s = get_settings()
    env = REPO_ROOT / "backend" / ".env"
    out.append((OK if env.exists() else BAD, f".env at {env}", "" if env.exists() else
                "Copy backend/.env.example to backend/.env and fill SARVAM_API_KEY"))
    key = s.sarvam_api_key
    out.append((OK if key.startswith("sk_") else (WARN if key else BAD), "SARVAM_API_KEY set",
                "" if key.startswith("sk_") else "Paste the key from dashboard.sarvam.ai into backend/.env"))
    out.append((OK if s.agent_tool_secret != "change-me" else WARN, "AGENT_TOOL_SECRET changed",
                "" if s.agent_tool_secret != "change-me" else "Set AGENT_TOOL_SECRET in .env (any random text)"))
    raw = s.resolve(s.raw_data_dir)
    for name in REQUIRED_CSV + OPTIONAL_CSV:
        f = raw / name
        status = OK if f.exists() else (BAD if name in REQUIRED_CSV else WARN)
        out.append((status, f"data file {name}", "" if f.exists() else
                    f"Unzip 'Global Context - Seller Dataset.zip' and put the CSVs directly in {raw}"))
    wh = s.resolve(s.warehouse_path)
    out.append((OK if wh.exists() else BAD, "warehouse built", "" if wh.exists() else "Run: python -m vani.data.warehouse"))
    ev = s.resolve(s.evidence_path)
    out.append((OK if ev.exists() else BAD, "evidence mined", "" if ev.exists() else "Run: python -m vani.evidence.miner"))
    return out


def main() -> int:
    utf8_console()
    rows = check()
    for status, what, fix in rows:
        print(f"{status} {what}" + (f"\n       -> {fix}" if fix else ""))
    bad = sum(r[0] == BAD for r in rows)
    print("\nAll good. Next: python -m vani.tools.smoke" if not bad else f"\n{bad} thing(s) to fix above.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
