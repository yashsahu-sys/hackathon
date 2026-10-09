"""Live signal detection on each seller turn.

Lexicons come from the real VANI seller turns (Roman-script Hinglish, which is
how Saaras transcribes these calls), plus Devanagari and English variants.
Rule-based on purpose: ~1 ms per turn so it adds no latency, deterministic,
and every signal quotes the words that fired it, which feeds the switch log.

Precedence fixes seen in real calls:
  "thik hai ... dubara call mat kijiyega"  -> do_not_call, not agreement
  "theek hai, abhi busy hain"              -> rush, not agreement
  "fayda nahi hota"                         -> scepticism (objection), not interest
  "kaun bol raha hai?"                      -> identity, not confusion
"""
import re

from vani.domain.live import Signal, SignalType
from vani.text.language import detect as detect_language

T = SignalType


_VOWEL_RUNS = [(re.compile(r"a{2,}"), "a"), (re.compile(r"e{2,}"), "i"), (re.compile(r"o{2,}"), "u"),
               (re.compile(r"i{2,}"), "i"), (re.compile(r"u{2,}"), "u"), (re.compile(r"z"), "j"), (re.compile(r"ph"), "f")]


def norm(text: str) -> str:
    """Fold Roman-Hindi spelling variants: faaltu/faltu, dimaag/dimag, dheere/dhire,
    jaldbaazi/jaldbaji, phone/fone. Applied to the lexicon AND to the seller's text,
    so patterns are written once. Devanagari is untouched."""
    text = text.lower()
    for rx, rep in _VOWEL_RUNS:
        text = rx.sub(rep, text)
    return text


def _rx(*patterns: str) -> list[re.Pattern]:
    return [re.compile(norm(p), re.I) for p in patterns]


LEXICON: dict[SignalType, list[re.Pattern]] = {
    T.slow_down: _rx(
        r"\bdheere\b|\bdhire\b|aaram se (bol|bata|samjha)", r"\bslow(ly)?\b", r"itna fast|bahut fast|bahut tez|jaldi jaldi (mat|na) bol",
        r"(koi|itni|itna|ki|bhi) (jaldi|jaldbaazi|jaldbazi|hadbadi)( bhi)? (nahi|nahin|na)", r"(jaldi|jaldbaazi) (kyu|kyun|kya) (hai|kar)",
        r"ruk ruk ke", r"thoda ruk(o|iye) ke",
        r"धीरे", r"आराम से बोल", r"(speak|talk) slower|too fast",
    ),
    T.rush: _rx(
        r"\bbusy\b", r"abhi (nahi|nahin)\b", r"baad (me|mein|main)\b", r"\bbahar (hoon|hu|hun|hai)\b",
        r"free nahi", r"meeting (me|mein|main) (hoon|hu|hun)", r"thodi der (me|mein)", r"kal baat kar",
        r"gaadi chala|driving", r"time nahi", r"\bjaldi\b", r"in a (meeting|hurry)", r"call (me )?later",
        r"बिज़ी|बिजी", r"बाद में", r"अभी (नहीं|टाइम नहीं|समय नहीं)", r"बाहर (हूँ|हूं)", r"जल्दी",
        r"customer (aaya|hai)|grahak", r"rehne dijiye abhi", r"jaldi (bolo|boliye|bataiye|batao)", r"(speak|talk) faster",
    ),
    T.confusion: _rx(
        r"samjh?a nahi|samajh (nahi|nahin) (aa|aaya)", r"\bmatlab\b\s*\??$", r"matlab kya", r"kya bol rah",
        r"kis (baare|cheez|baat) (me|mein|ke)", r"kya hai (ye|yeh)\??", r"phir se bol", r"dobara bol",
        r"समझ(ा)? नहीं|समझ नहीं आया", r"मतलब\s*\??$", r"क्या बोल रह",
        r"(didn'?t|did not|don'?t|do not|could not|couldn'?t) (get|understand|follow)", r"not (clear|following)",
        r"what do you mean", r"\bpardon\b", r"come again",
        # purpose confusion, from real VANI calls
        r"kis liye\b", r"kyun (call|phone) kiya", r"kya karna hai\??$", r"kahan (pe|par) (check|dekhna|karna)",
        r"किस लिए", r"क्यों (कॉल|फ़ोन|फोन) किया",
    ),
    T.frustration: _rx(
        r"baar baar", r"kitni baar", r"\bdas(vi|wi)?\s*baar", r"pareshan", r"\bband karo\b", r"\bbas karo\b",
        r"zabardasti", r"\bfaltu\b", r"bakwas", r"dimag", r"time pass kar", r"jhoot", r"complain",
        r"बार बार|बार-बार", r"कितनी बार", r"परेशान", r"बस करो", r"बंद करो", r"ज़बरदस्ती|जबरदस्ती",
        r"irritat", r"annoy", r"stop calling", r"waste (of|my) time", r"too many calls",
        r"mood kharab", r"dimaag kharab|dimaag mat", r"sar dard|sir dard|sir kha", r"pakao|pakaa rahe|paka rahe",
        r"\bpagal\b", r"\btang\b (kar|aa)", r"\bbe faaltu|\bfaaltu", r"bewakoof|bekar ki baat",
        r"दिमाग ख़राब|दिमाग खराब|मूड ख़राब|मूड खराब|फ़ालतू|फालतू|बकवास", r"(why|what) the hell|nonsense|useless",
    ),
    T.bot_question: _rx(
        r"\b(ai|a\.i\.)\s*(ho|hai|hain)\b", r"\bbot\b", r"robot", r"recording (hai|chal)", r"machine (hai|ho)",
        r"computer (hai|se)", r"real (person|insaan)", r"are you (a )?(bot|human|real|robot|ai)",
        r"रोबोट", r"मशीन", r"असली इंसान",
    ),
    T.identity: _rx(
        r"\bk(a|au)u?n bol rah", r"\bkaun\??$", r"\bkon\b.*\?", r"kahan se bol", r"kis company se",
        r"कौन बोल रह", r"कहाँ से बोल", r"who('?s| is) (this|calling|speaking)",
    ),
    T.human_request: _rx(
        r"insaan se", r"kisi (aadmi|bande|insaan) se", r"executive se baat", r"manager se baat", r"senior se baat",
        r"इंसान से", r"executive से बात", r"(talk|speak) to (a )?(human|person|executive|manager)",
    ),
    T.interest: _rx(
        r"kitn(a|e|i) (ka|ki|ke|der|time|lag|charge|paisa)", r"kaise (hoga|milega|aayeng|kaam|karenge)",
        r"kab aa(yenge|oge|ayenge)", r"kya milega", r"aur batao|aur bataiye", r"details? (do|dijiye|bhejo)",
        r"कितन(ा|े|ी)", r"कैसे (होगा|मिलेगा)", r"और बताइए", r"how (much|does|long)", r"tell me more",
        r"\bfayda\b(?!.*\bnahi)", r"फ़ायदा|फायदा",
    ),
    T.agreement: _rx(
        r"^(haan|ha|haanji|han ji|ji haan|ji|ok|okay|theek|thik|chalo|done|sure|yes|alright|fine)\b",
        r"(theek|thik) hai", r"chalega", r"aa (jao|jaiye|jaana)", r"(fix|book|confirm|pakka) kar (do|dijiye|lo)",
        r"meeting (fix|rakh|rakho|kar)", r"(haan|ha|ji) (aa|bhej) (jaiye|do|dijiye)",
        r"baje (karte|rakh|rakhte|kar lete|kar lenge|kar lo|chalega|theek|thik|ok|fix)", r"बजे (करते|रख|चलेगा|ठीक)",
        r"\b(11|gyarah|5|paanch) baje", r"mil lete", r"ठीक है", r"चलेगा", r"आ जाइए|आ जाओ", r"हाँ|हां",
        r"(that|it) works", r"sounds good", r"\bconfirm",
    ),
    T.refusal: _rx(
        r"nahi chahiye|nahin chahiye", r"interest nahi|koi interest", r"not interested", r"(zaroorat|jarurat|zarurat) nahi",
        r"nahi karna", r"mana kiya", r"kaam nahi karna", r"नहीं चाहिए", r"ज़रूरत नहीं|जरूरत नहीं",
        r"no thanks", r"\bnot (needed|required)\b",
        # from real VANI misses
        r"interested nahi", r"nahi (chahte|chahta|chahti)\b", r"nahi (karwani|karwana|karana|chalana)\b",
        r"(karana|karwana|chalana) nahi", r"koi plan nahi", r"(already|pehle se).{0,40}(doosri|dusri|dusre|doosre) jagah",
        r"apne aap contact", r"rehne (do|dijiye)\b(?!.*abhi)",
    ),
    T.end_call: _rx(
        r"call (cut|kaat|kat|band|rakh|khatam)\w* (kar|karo|kardo|do|dijiye|de)", r"(phone|call) (rakh|rakho|rakhiye|rakhta|rakhti)",
        r"(cut|disconnect) (the )?call", r"(cut|kaat) (do|dijiye|kar do)", r"band karo (ye|yeh)? ?(call|phone)",
        r"baat (khatam|band) kar", r"kal baat karna,? abhi (rakh|band)", r"hang up", r"bye bye",
        r"कॉल (काट|कट|बंद) (कर|करो|दो)", r"फ़ोन (रख|रखो)|फोन (रख|रखो)",
    ),
    T.do_not_call: _rx(
        r"(call|phone) mat (karo|kariye|kijiye|kijiyega)", r"dubara (call|phone)", r"number (block|delete|hata)",
        r"block (me|mein|kar)", r"profile (delete|hata)", r"कॉल मत", r"फ़ोन मत|फोन मत",
        r"(don'?t|do not|never) call", r"remove my number",
    ),
}

ENGLISH_REQUEST = re.compile(r"\b(speak|talk|baat)\w* (in )?english\b|english (please|me|mein|main|only)|अंग्रेज़ी|इंग्लिश", re.I)
HINDI_REQUEST = re.compile(r"hindi (me|mein|main) (bolo|baat|boliye)|हिंदी में|हिन्दी में|speak (in )?hindi", re.I)
REGIONAL_REQUEST = {
    "ta-IN": re.compile(r"\btamil\b", re.I), "te-IN": re.compile(r"\btelugu\b", re.I),
    "gu-IN": re.compile(r"\bgujarati\b", re.I), "mr-IN": re.compile(r"\bmarathi\b", re.I),
    "bn-IN": re.compile(r"\bbengali|bangla\b", re.I), "kn-IN": re.compile(r"\bkannada\b", re.I),
    "pa-IN": re.compile(r"\bpunjabi\b", re.I), "ml-IN": re.compile(r"\bmalayalam\b", re.I),
}
NEGATED_VALUE = re.compile(r"(fayda|फ़ायदा|फायदा).{0,25}(nahi|nahin|नहीं)|(nahi|nahin).{0,15}fayda", re.I)

BASE_CONF = 0.65
STEP = 0.12


class SignalDetector:
    def detect(self, text: str, current_language: str, stt_language: str | None = None,
               recent_seller_turns: list[str] | None = None) -> list[Signal]:
        text = (text or "").strip()
        if not text:
            return []
        found: dict[SignalType, Signal] = {}
        folded = norm(text)
        for kind, patterns in LEXICON.items():
            hits = [m.group(0) for p in patterns if (m := p.search(text) or p.search(folded))]
            if hits:
                found[kind] = Signal(type=kind, confidence=round(min(0.95, BASE_CONF + STEP * (len(hits) - 1)), 2),
                                     trigger=hits[0], detail={"matches": hits})

        # Shape cues from the conversation so far
        if text.count("!") >= 2 and T.frustration not in found:
            found[T.frustration] = Signal(type=T.frustration, confidence=0.6, trigger="!!", detail={"cue": "exclamations"})
        if recent_seller_turns and len(recent_seller_turns) >= 2:
            short = all(len(t.split()) <= 2 for t in recent_seller_turns[-2:]) and len(text.split()) <= 2
            if short and not ({T.agreement, T.interest, T.identity} & set(found)) and T.rush not in found:
                found[T.rush] = Signal(type=T.rush, confidence=0.6, trigger=text,
                                       detail={"cue": "three one-or-two-word replies in a row"})
            repeated = sum(1 for t in recent_seller_turns[-3:] if LEXICON_CONFUSION_LIGHT.search(t))
            if repeated and T.confusion in found:
                found[T.confusion].confidence = min(0.95, found[T.confusion].confidence + 0.1)

        # Language switch: explicit request beats detected language
        lang_sig = self._language(text, current_language, stt_language)
        if lang_sig:
            found[T.language_switch] = lang_sig

        self._resolve(found, text)
        return sorted(found.values(), key=lambda s: -s.confidence)

    @staticmethod
    def _language(text, current, stt_language) -> Signal | None:
        if m := ENGLISH_REQUEST.search(text):
            target, conf, trig = "en-IN", 0.95, m.group(0)
        elif m := HINDI_REQUEST.search(text):
            target, conf, trig = "hi-IN", 0.95, m.group(0)
        else:
            req = next(((code, m) for code, rx in REGIONAL_REQUEST.items() if (m := rx.search(text))), None)
            if req:
                target, conf, trig = req[0], 0.9, req[1].group(0)
            else:
                target, lconf = detect_language(text, stt_language)
                conf, trig = round(lconf, 2), text[:60]
                # Only follow an unrequested switch when the turn is long enough to be sure.
                if lconf < 0.75 or len(text.split()) < 4:
                    return None
        if target == current or target == "unknown":
            return None
        return Signal(type=T.language_switch, confidence=conf, trigger=trig, detail={"from": current, "to": target})

    @staticmethod
    def _resolve(found: dict, text: str) -> None:
        """Precedence rules learned from real turns."""
        negative = {T.do_not_call, T.refusal, T.frustration, T.rush, T.end_call, T.slow_down, T.confusion}
        if T.agreement in found and negative & set(found):
            del found[T.agreement]                       # "thik hai, dubara call mat kijiye"
        if NEGATED_VALUE.search(text):
            found.pop(T.interest, None)                  # "fayda nahi hota" = scepticism, not interest
            found.setdefault(T.refusal, Signal(type=T.refusal, confidence=0.6, trigger="fayda nahi",
                                               detail={"objection": "value"}))
        if T.end_call in found:
            found.pop(T.rush, None)                       # "call cut kar do" is not a scheduling request
        if T.do_not_call in found:
            found.pop(T.rush, None)                       # "abhi nahi ... call mat karo" is not a scheduling issue
        if T.slow_down in found:
            found.pop(T.rush, None)                       # "itna fast mat bolo" is a pace request, not a rush
        if T.identity in found and T.confusion in found and not re.search(r"samjh|समझ|understand|matlab", text, re.I):
            del found[T.confusion]


LEXICON_CONFUSION_LIGHT = re.compile(r"samjh|matlab|समझ|मतलब|understand", re.I)
