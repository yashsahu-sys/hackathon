"""Live Sarvam smoke test: is the key good and does each API answer?

    python -m vani.tools.smoke            (needs SARVAM_API_KEY in backend/.env)

Writes data/private/out/smoke_tts.wav and round-trips it through STT.
"""
import asyncio
import base64
import sys
import time

from vani.config import get_settings
from vani.integrations.sarvam.client import SarvamClient, SarvamError


def hint(e: SarvamError, model_env: str) -> str:
    if e.status is None:
        return "     -> network: this machine can't reach api.sarvam.ai (proxy/firewall/VPN?)"
    if e.status in (401, 403):
        return "     -> key rejected: check SARVAM_API_KEY in backend/.env"
    if e.status in (400, 404, 422):
        return f"     -> request/model rejected: try another {model_env} in backend/.env"
    if e.status == 429:
        return "     -> rate limited / out of credits"
    return "     -> Sarvam server error, retry in a minute"


async def main() -> int:
    s = get_settings()
    if not s.sarvam_enabled:
        print("SARVAM_API_KEY is empty: put it in backend/.env")
        return 1
    c = SarvamClient(s)
    out = s.resolve(s.evidence_path).parent / "out"
    out.mkdir(parents=True, exist_ok=True)
    ok = True
    text = "नमस्ते जी, मैं IndiaMART से Payal बोल रही हूँ। क्या कल सुबह 11 बजे meeting हो सकती है?"
    try:
        t = time.perf_counter()
        audio = await c.tts(text, "hi-IN", "ritu", 1.0)
        wav = base64.b64decode(audio)
        (out / "smoke_tts.wav").write_bytes(wav)
        print(f"TTS  ok  {s.sarvam_tts_model}  {len(wav) // 1024} KB  {time.perf_counter() - t:.2f}s")
    except SarvamError as e:
        ok = False
        wav = None
        print("TTS  FAIL", e)
        print(hint(e, "SARVAM_TTS_MODEL (bulbul:v2 / bulbul:v3)"))
    if wav:
        try:
            t = time.perf_counter()
            r = await c.stt(wav)
            print(f"STT  ok  {s.sarvam_stt_model}  {time.perf_counter() - t:.2f}s  -> {r['transcript']!r} ({r['language_code']})")
        except SarvamError as e:
            ok = False
            print("STT  FAIL", e)
            print(hint(e, "SARVAM_STT_MODEL (saaras:v3 / saaras:v4)"))
    try:
        t = time.perf_counter()
        r = await c.chat([{"role": "system", "content": "Reply in one short Hinglish sentence."},
                          {"role": "user", "content": "Seller says: abhi busy hoon"}])
        print(f"LLM  ok  {s.sarvam_chat_model}  {time.perf_counter() - t:.2f}s  -> {r!r}")
    except SarvamError as e:
        ok = False
        print("LLM  FAIL", e)
        print(hint(e, "SARVAM_CHAT_MODEL (sarvam-105b / sarvam-105b-conversations / sarvam-m)"))
    await c.aclose()
    return 0 if ok else 2


if __name__ == "__main__":
    from vani.tools.console import utf8_console
    utf8_console()
    sys.exit(asyncio.run(main()))
