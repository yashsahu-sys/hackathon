"""Live signal detection on each seller turn.

Rule-based on purpose: it runs in ~1 ms, so it never adds latency to the call,
it's explainable (every signal quotes the words that triggered it), and it
handles Hinglish in both Devanagari and Roman script, which is how Saaras
codemix transcripts actually look.
"""
import re
from dataclasses import dataclass, asdict

SIGNALS = ("frustration", "confusion", "rush", "interest", "language_switch", "human_request", "agreement", "refusal")


@dataclass
class Signal:
    type: str
    confidence: float
    trigger: str           # the words that fired it
    detail: dict

    def to_dict(self) -> dict:
        return asdict(self)


LEXICON = {
    "frustration": [
        r"point (pe|par) aa?o", r"kitni der", r"बस करो", r"bas karo", r"pak(a|aa) (diya|rahe)", r"pareshan",
        r"परेशान", r"dimag", r"दिमाग", r"faltu", r"फ़ालतू|फालतू", r"yaar\b.*(bolo|batao)", r"यार", r"seedha bolo",
        r"सीधा बोलो|सीधी बात", r"kitni baar", r"कितनी बार", r"irritat", r"annoy", r"stop (calling|it)", r"get to the point",
        r"waste of time", r"time waste", r"टाइम waste|time बर्बाद", r"phir se\b", r"फिर से", r"कितनी देर",
        r"पॉइंट पे आओ|point पे आओ|point पर आओ",
    ],
    "confusion": [
        r"samjh?a nahi", r"समझा नहीं|समझ नहीं", r"\bmatlab\b", r"मतलब", r"kya bol rah", r"क्या बोल रह", r"\bkya\?",
        r"क्या\?", r"\bwhat\?", r"(didn'?t|did not|don'?t|do not|could not|couldn'?t) (get|understand|follow)", r"not (following|clear|understood)",
        r"what is (this|it) about", r"what do you mean", r"confus",
        r"pardon", r"repeat", r"dobara", r"दोबारा", r"kaun sa", r"कौन सा", r"kaise\??$",
    ],
    "rush": [
        r"busy", r"बिज़ी|बिजी", r"jaldi", r"जल्दी", r"meeting me(in)? hoon", r"मीटिंग में", r"driving", r"gaadi chala",
        r"abhi (time|samay) nahi", r"अभी (time|टाइम|समय) नहीं", r"later", r"baad me(in)?", r"बाद में", r"in a hurry",
        r"customer (aaya|hai)", r"ग्राहक", r"दुकान पर", r"shop pe",
    ],
    "interest": [
        r"kitn(a|e) (ka|ki|lag)", r"कितन(ा|े) (का|की|लग)", r"kaise (milega|hoga|kaam)", r"कैसे (मिलेगा|होगा|काम)",
        r"aur batao", r"और बताओ|और बताइए", r"interesting", r"tell me more", r"how (does|much)", r"accha\b.*\?",
        r"अच्छा.*\?", r"leads?\s+(kaise|kitn)", r"leads? (कैसे|कितने)", r"roi", r"फ़ायदा|फायदा|fayda", r"benefit",
    ],
    "human_request": [
        r"insaan", r"इंसान", r"real person", r"human", r"executive se baat", r"executive से बात", r"manager",
        r"kisi (aadmi|bande) se", r"किसी (आदमी|बंदे) से", r"bot (ho|hai)", r"robot",
    ],
    "agreement": [
        r"^(haan|ha|haanji|ji haan|ok|okay|theek hai|thik hai|done|sure|yes|chalo|chalega)\b", r"^(हाँ|हां|जी हाँ|ठीक है|चलेगा|चलो)",
        r"(theek|thik) hai\b", r"ठीक है", r"chalega", r"चलेगा", r"\b11 (baje|bje)\b.*(theek|ok|chalega)",
        r"fix kar (do|dijiye)", r"fix कर (दो|दीजिए)", r"bhej do executive", r"sounds good", r"that works", r"\bconfirm",
        r"aa jao", r"आ जाओ|आ जाइए", r"मिल लेते हैं|mil lete", r"\b(is|are|sounds|that'?s) (fine|ok|okay|good)\b",
        r"^(alright|all right|fine|sure|great)\b", r"works for me", r"\bbook it\b",
    ],
    "refusal": [
        r"interest(ed)? nahi", r"interest नहीं", r"nahi chahiye", r"नहीं चाहिए", r"not interested", r"don'?t call",
        r"mat karo call", r"call मत", r"no thanks", r"zaroorat nahi", r"ज़रूरत नहीं|जरूरत नहीं",
    ],
}
COMPILED = {k: [re.compile(p, re.I) for p in v] for k, v in LEXICON.items()}

DEVANAGARI = re.compile(r"[ऀ-ॿ]")
TAMIL = re.compile(r"[஀-௿]")
TELUGU = re.compile(r"[ఀ-౿]")
KANNADA = re.compile(r"[ಀ-೿]")
GURMUKHI = re.compile(r"[਀-੿]")
GUJARATI = re.compile(r"[઀-૿]")
BENGALI = re.compile(r"[ঀ-৿]")
ROMAN_HINDI = re.compile(
    r"\b(hai|hain|nahi|kya|haan|bhai|yaar|mujhe|aap|hum|karo|kar|bolo|batao|abhi|kal|theek|accha|achha|kaise|kitna|"
    r"mein|par|pe|se|ko|ka|ki|ke|wala|chahiye|samjha)\b", re.I)
ENGLISH_REQUEST = re.compile(r"\b(speak|talk) (in )?english\b|english (please|me|mein|में)|इंग्लिश|अंग्रेज़ी|अंग्रेजी", re.I)
HINDI_REQUEST = re.compile(r"hindi (me|mein|में) (bolo|baat)|हिंदी में|हिन्दी में", re.I)


def detect_language(text: str, stt_code: str | None = None) -> str:
    """Returns a BCP-47 code. Trusts Saaras when it's confident about a non-Hindi/English language."""
    for pattern, code in ((TAMIL, "ta-IN"), (TELUGU, "te-IN"), (KANNADA, "kn-IN"), (GURMUKHI, "pa-IN"),
                          (GUJARATI, "gu-IN"), (BENGALI, "bn-IN")):
        if pattern.search(text):
            return code
    if stt_code and stt_code not in ("hi-IN", "en-IN"):
        return stt_code
    if DEVANAGARI.search(text):
        return "hi-IN"
    words = re.findall(r"[A-Za-z']+", text)
    if words and len(ROMAN_HINDI.findall(text)) / len(words) >= 0.2:
        return "hi-IN"
    return "en-IN" if words else (stt_code or "hi-IN")


def detect(text: str, current_language: str, stt_language: str | None = None, history: list[dict] | None = None) -> list[Signal]:
    text = (text or "").strip()
    if not text:
        return []
    found: list[Signal] = []
    for kind in ("frustration", "confusion", "rush", "interest", "human_request", "agreement", "refusal"):
        hits = [m.group(0) for p in COMPILED[kind] if (m := p.search(text))]
        if hits:
            conf = round(min(0.95, 0.6 + 0.15 * (len(hits) - 1)), 2)
            found.append(Signal(kind, conf, hits[0], {"matches": hits}))

    # Punctuation / shape cues
    if text.count("!") >= 2 and not any(s.type == "frustration" for s in found):
        found.append(Signal("frustration", 0.55, "!!", {"cue": "exclamations"}))
    if history:
        seller_turns = [t["text"] for t in history if t["role"] == "seller"][-2:]
        if len(seller_turns) == 2 and all(len(t.split()) <= 3 for t in seller_turns) and len(text.split()) <= 3 \
                and not any(s.type in ("agreement", "interest") for s in found):
            found.append(Signal("rush", 0.55, text, {"cue": "three very short replies in a row"}))

    # Language switch: explicit request beats detected language
    lang = detect_language(text, stt_language)
    if ENGLISH_REQUEST.search(text):
        target, conf, trig = "en-IN", 0.95, ENGLISH_REQUEST.search(text).group(0)
    elif HINDI_REQUEST.search(text):
        target, conf, trig = "hi-IN", 0.95, HINDI_REQUEST.search(text).group(0)
    else:
        target, conf, trig = lang, 0.7, text[:40]
    if target != current_language and (conf > 0.9 or len(text.split()) >= 3):
        found.append(Signal("language_switch", conf, trig, {"from": current_language, "to": target}))

    # A clear yes shouldn't also count as a refusal etc.
    types = {s.type for s in found}
    if "agreement" in types and ("refusal" in types or "rush" in types):
        found = [s for s in found if s.type not in ("refusal", "rush")] if "theek" in text.lower() or "ठीक" in text \
            else found
    return sorted(found, key=lambda s: -s.confidence)
