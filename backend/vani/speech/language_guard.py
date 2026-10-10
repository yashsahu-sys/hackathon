"""Make sure VANI answers in the language the persona is speaking NOW.

The LLM writes its reply in the same call that detects a language switch, so
it can still answer in the old language. Every reply is checked against the
persona's current language and, if it doesn't match, translated with Sarvam
Translate (Mayura, with the bot's gender so Hindi verbs agree). If translation
fails the caller falls back to the template line, which is already in the right
language.
"""
import re

from vani.domain.persona import PersonaSpec
from vani.integrations.sarvam.client import SarvamError, SpeechAI
from vani.text.language import SCRIPTS, WORD, detect

from .tts_text import is_roman_hindi

SCRIPT_CODES = {code for _, code in SCRIPTS} | {"hi-IN"}
DEVANAGARI = re.compile(r"[ऀ-ॿ]")
INDIC = re.compile(r"[ऀ-෿]")
NAMES = {"en-IN": "English", "hi-IN": "Hindi/Hinglish", "ta-IN": "Tamil", "te-IN": "Telugu", "kn-IN": "Kannada",
         "ml-IN": "Malayalam", "bn-IN": "Bengali", "gu-IN": "Gujarati", "mr-IN": "Marathi", "pa-IN": "Punjabi",
         "od-IN": "Odia"}


def language_of(text: str) -> str:
    for rx, code in SCRIPTS:
        if rx.search(text):
            return code
    if DEVANAGARI.search(text):
        return "hi-IN"
    if detect(text)[0] == "gu-IN":
        return "gu-IN"
    if is_roman_hindi(text):
        return "hi-IN"
    words = WORD.findall(text)
    return detect(text)[0] if len(words) < 3 else "en-IN"


def matches(text: str, persona: PersonaSpec) -> bool:
    target = persona.language.code
    got = language_of(text)
    if target == "en-IN":
        return got == "en-IN" and not INDIC.search(text)
    if target in ("hi-IN", "gu-IN"):
        short_filler = got not in SCRIPT_CODES and len(WORD.findall(text)) < 4     # "Okay sir." is fine
        return got == target or short_filler
    return got == target


async def ensure_language(text: str, persona: PersonaSpec, speech: SpeechAI, warnings: list[str]) -> str | None:
    """Text in the persona's current language, or None if it couldn't be fixed."""
    if not text or matches(text, persona):
        return text
    target = persona.language.code
    try:
        mode = "code-mixed" if target in ("hi-IN", "gu-IN") else "modern-colloquial"
        out = await speech.translate(text, target, "auto", persona.voice.gender, mode)
    except (SarvamError, AttributeError) as exc:
        warnings.append(f"reply was in {NAMES.get(language_of(text), language_of(text))}, persona speaks "
                        f"{NAMES.get(target, target)}; translation failed ({exc}); template used")
        return None
    if not out or not matches(out, persona):
        warnings.append(f"translation to {NAMES.get(target, target)} came back in the wrong language; template used")
        return None
    warnings.append(f"reply translated to {NAMES.get(target, target)} to follow the seller's language")
    return out
