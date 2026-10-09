import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def _load_dotenv() -> None:
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


_load_dotenv()

SARVAM_API_KEY = os.environ.get("SARVAM_API_KEY", "").strip()
SARVAM_BASE_URL = os.environ.get("SARVAM_BASE_URL", "https://api.sarvam.ai")
CHAT_MODEL = os.environ.get("SARVAM_CHAT_MODEL", "sarvam-105b")
STT_MODEL = os.environ.get("SARVAM_STT_MODEL", "saaras:v3")
TTS_MODEL = os.environ.get("SARVAM_TTS_MODEL", "bulbul:v3")

# Without a key the app still runs end to end: replies come from templates and
# the browser speaks them, so the persona/switch logic can be demoed anywhere.
LIVE = bool(SARVAM_API_KEY)
