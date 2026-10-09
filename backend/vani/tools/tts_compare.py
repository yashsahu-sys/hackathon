"""Which text form does Bulbul pronounce best? Listen and decide.

    python -m vani.tools.tts_compare      -> data/private/out/compare/*.wav

Renders the same Hinglish line as (a) Roman script, (b) Devanagari + English
words, (c) Roman transliterated by Sarvam to Devanagari, at the persona voice.
If (b)/(c) sound clearly better than (a), set TTS_TRANSLITERATE=true in .env.
"""
import asyncio
import base64

from vani.config import get_settings
from vani.integrations.sarvam.client import SarvamClient, SarvamError
from vani.tools.console import utf8_console

LINES = {
    "roman": "Theek hai ji, main samajh sakti hoon aap busy hain. Kal subah 11 baje ya shaam 5 baje, kaunsa time theek rahega?",
    "devanagari": "ठीक है जी, मैं समझ सकती हूँ आप busy हैं। कल सुबह 11 बजे या शाम 5 बजे, कौन सा time ठीक रहेगा?",
}


async def main():
    utf8_console()
    s = get_settings()
    c = SarvamClient(s)
    out = s.resolve(s.evidence_path).parent / "out" / "compare"
    out.mkdir(parents=True, exist_ok=True)
    lines = dict(LINES)
    try:
        lines["transliterated"] = await c.transliterate(LINES["roman"], "en-IN", "hi-IN")
        print("transliterated ->", lines["transliterated"])
    except SarvamError as e:
        print("transliterate FAIL", e)
    for speaker in ("ritu", "shubh"):
        for name, text in lines.items():
            try:
                wav = base64.b64decode(await c.tts(text, "hi-IN", speaker, 1.0, temperature=0.6))
                path = out / f"{speaker}_{name}.wav"
                path.write_bytes(wav)
                print("ok  ", path.name)
            except SarvamError as e:
                print("FAIL", speaker, name, e)
    await c.aclose()
    print(f"\nListen: aplay {out}/ritu_roman.wav  (then _devanagari, _transliterated)")


if __name__ == "__main__":
    asyncio.run(main())
