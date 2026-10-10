"""Make reply text right for Bulbul.

Rules from Sarvam's TTS docs and VANI's production prompt:
  * plain spoken sentences: no markdown, emojis, lists, brackets, variable names
  * numbers over 4 digits need commas ('10,000') to be read as one number
  * Hindi in Devanagari reads best; optionally transliterate Roman Hinglish
"""
import re

from vani.domain.persona import PersonaSpec
from vani.integrations.sarvam.client import SarvamError, SpeechAI
from vani.text.language import ENGLISH_WORDS, HINDI_WORDS, WORD

EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿️]")
NOTES = re.compile(r"\[[^\]]*\]|\([^)]*\)|\{[^}]*\}")      # stage directions / asides: drop whole
MARKUP = re.compile(r"[*_#`>|~]")
LONG_NUMBER = re.compile(r"(?<![\d,.])(\d{5,})(?![\d,.])")


def _indian_commas(n: str) -> str:
    head, tail = n[:-3], n[-3:]
    head = re.sub(r"(\d)(?=(\d{2})+$)", r"\1,", head)
    return f"{head},{tail}" if head else tail


def clean(text: str, max_words: int) -> str:
    text = EMOJI.sub("", text or "")
    text = NOTES.sub("", text)
    text = MARKUP.sub("", text)
    text = re.sub(r"\s+", " ", text.replace("\n", " ")).strip().strip('"').strip()
    text = LONG_NUMBER.sub(lambda m: _indian_commas(m.group(1)), text)
    words = text.split()
    limit = max_words * 2   # persona limit is per sentence-ish; hard stop well above it
    if len(words) > limit:
        cut = " ".join(words[:limit])
        last = max(cut.rfind("।"), cut.rfind("."), cut.rfind("?"))
        text = cut[: last + 1] if last > len(cut) // 2 else cut
    return text


def is_roman_hindi(text: str) -> bool:
    words = [w.lower() for w in WORD.findall(text)]
    if len(words) < 3 or re.search(r"[ऀ-ॿ]", text):
        return False
    hi = sum(w in HINDI_WORDS for w in words)
    en = sum(w in ENGLISH_WORDS for w in words)
    return hi >= 2 and hi >= en


async def for_bulbul(text: str, persona: PersonaSpec, speech: SpeechAI, transliterate: bool,
                     warnings: list[str] | None = None) -> str:
    text = clean(text, persona.tone.max_words_per_turn)
    if transliterate and persona.language.code == "hi-IN" and is_roman_hindi(text):
        try:
            text = await speech.transliterate(text, "en-IN", "hi-IN")
        except SarvamError as exc:
            if warnings is not None:
                warnings.append(f"transliteration skipped: {exc}")
    return text
