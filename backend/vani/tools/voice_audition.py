"""Render the same line in every candidate Bulbul voice and pace, to pick voices by ear.

    python -m vani.tools.voice_audition          -> data/private/out/voices/*.wav
"""
import asyncio
import base64

from vani.config import get_settings
from vani.integrations.sarvam.client import SarvamClient, SarvamError
from vani.persona.voices import LANGUAGE_VOICE, VOICE_MAP

LINES = {
    "hi-IN": "नमस्ते जी, मैं IndiaMART से Payal बोल रही हूँ। क्या कल सुबह 11 बजे executive आपसे मिल सकते हैं?",
    "en-IN": "Hello, this is Payal from IndiaMART. Could our executive meet you tomorrow at 11 AM?",
}
EXTRA = ["neha", "kavya", "shreya", "ishita", "pooja", "tanya", "shruti"]


async def main():
    s = get_settings()
    c = SarvamClient(s)
    out = s.resolve(s.evidence_path).parent / "out" / "voices"
    out.mkdir(parents=True, exist_ok=True)
    speakers = sorted(set(VOICE_MAP.values()) | set(LANGUAGE_VOICE.values()) | set(EXTRA))
    for lang, text in LINES.items():
        for sp in speakers:
            for pace in (0.9, 1.0, 1.15):
                try:
                    wav = base64.b64decode(await c.tts(text, lang, sp, pace))
                    (out / f"{lang}_{sp}_{pace}.wav").write_bytes(wav)
                    print("ok  ", lang, sp, pace)
                except SarvamError as e:
                    print("skip", lang, sp, pace, e)
    await c.aclose()


if __name__ == "__main__":
    asyncio.run(main())
