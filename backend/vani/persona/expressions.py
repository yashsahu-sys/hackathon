"""Human touches: a short, situation-fitting acknowledgement before VANI's line.

Bulbul has no SSML or emotion tags; it infers prosody from the words and the
punctuation (and from pace/temperature, which the adapter already changes).
So the expression lives in the text: a sincere "माफ़ी चाहती हूँ" when the seller
is annoyed, "अच्छा जी, बहुत बढ़िया!" when they're interested, an explicit "sure,
in English" when they switch language. Each variant is used once per call, so
VANI never sounds like a loop. No fillers like "यार"/"अरे", no fake laughs.
"""
import re
import zlib

from vani.domain.live import SignalType as T

EXPRESSIONS = {
    "hinglish": {
        "frustration": ["माफ़ी चाहती हूँ जी, मैं आपका ज़्यादा समय नहीं लूँगी।",
                        "समझ सकती हूँ जी, बार-बार call आना परेशान करता है।", "जी, माफ़ कीजिए।"],
        "confusion": ["माफ़ कीजिए, शायद मैं जल्दी बोल गई।", "ओह, मैं ठीक से समझा नहीं पाई।", "जी, एक बार फिर से बताती हूँ।"],
        "slow_down": ["जी ज़रूर, आराम से बताती हूँ।", "जी बिल्कुल, धीरे-धीरे बताती हूँ।"],
        "interest": ["अच्छा जी, बहुत बढ़िया!", "वाह, यह सुनकर अच्छा लगा!"],
        "language_switch": ["जी ज़रूर, हिंदी में बात करते हैं।", "जी बिल्कुल, हिंदी में ही बताती हूँ।"],
        "thanks": ["जी, शुक्रिया।", "जी धन्यवाद।"],
        "question": ["बहुत अच्छा सवाल है जी।", "जी, ज़रूर बताती हूँ।"],
    },
    "english": {
        "frustration": ["I'm really sorry, I won't take much of your time.", "I understand, repeated calls are annoying.",
                        "Sorry about that."],
        "confusion": ["Sorry, I think I went too fast.", "Oh, let me put that better.", "Let me say it once more."],
        "slow_down": ["Of course, I'll go slowly.", "Sure, no rush at all."],
        "interest": ["Oh, that's great to hear!", "Wonderful!"],
        "language_switch": ["Sure, I'll speak in English.", "Of course, let's continue in English."],
        "thanks": ["Thank you.", "Thanks for your time."],
        "question": ["That's a good question.", "Sure, let me explain."],
    },
    "gujarati": {
        "frustration": ["માફ કરજો, હું તમારો વધારે સમય નહીં લઉં.", "સમજી શકું છું, વારંવાર call આવે તો હેરાનગતિ થાય.", "માફ કરજો."],
        "confusion": ["માફ કરજો, હું સરળ રીતે સમજાવું.", "ઓહ, ચાલો ફરીથી કહું."],
        "slow_down": ["ચોક્કસ, આરામથી કહું છું.", "હા, ધીમે ધીમે કહું છું."],
        "interest": ["વાહ, ખૂબ સરસ!", "સરસ, સાંભળીને આનંદ થયો!"],
        "language_switch": ["ચોક્કસ, ગુજરાતીમાં વાત કરીએ.", "હા, ગુજરાતીમાં જ વાત કરીએ."],
        "thanks": ["આભાર.", "તમારો આભાર."],
        "question": ["સરસ સવાલ છે.", "ચોક્કસ, સમજાવું."],
    },
}
# Strongest feeling first: one acknowledgement per turn.
PRIORITY = [T.language_switch, T.frustration, T.confusion, T.slow_down, T.interest]
# Lines that already carry their own feeling (apology, goodbye, thanks) or open with "I understand".
OWN_FEELING = {"end_close", "dnc_close", "close_no", "meeting_confirm", "callback_confirm", "reassure", "handoff",
               "rush", "reschedule", "ask_time", "confirm_proposed"}
LEADING_ACK = re.compile(r"^(जी( बिल्कुल| ज़रूर)?,\s*|Certainly,\s*|Of course,\s*|Sure,\s*|ચોક્કસ,\s*)?"
                         r"(मैं आसान शब्दों में बताती हूँ।\s*|Let me put it simply\.\s*|હું સરળ શબ્દોમાં કહું\.\s*)?")


def situation(switched: list[T], move_key: str, first_pitch: bool, question: bool = False) -> str | None:
    for sig in PRIORITY:
        if sig in switched:
            # "kya fayda hoga?" is a question (often a sceptical one), not delight: no "wah, sunkar achha laga"
            return "question" if sig == T.interest and question else sig.value
    if move_key == "pitch" and first_pitch:
        return "thanks"
    return None


def with_expression(text: str, style: str, switched: list[T], move_key: str, used: list[str],
                    first_pitch: bool = False, seed: str = "", question: bool = False) -> tuple[str, str | None]:
    """(text with an acknowledgement in front, the acknowledgement used) or the text unchanged."""
    bank = EXPRESSIONS.get(style)
    if bank is None or move_key in OWN_FEELING and T.language_switch not in switched:
        return text, None
    sit = situation(switched, move_key, first_pitch, question)
    if sit is None:
        return text, None
    fresh = [e for e in bank[sit] if e not in used]
    if not fresh:
        return text, None
    ack = fresh[zlib.crc32(f"{seed}:{sit}".encode()) % len(fresh)] if seed else fresh[0]   # differs per seller
    return f"{ack} {LEADING_ACK.sub('', text, count=1)}", ack   # drop our own "let me put it simply" too
