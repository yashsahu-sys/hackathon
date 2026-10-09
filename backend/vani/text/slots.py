"""Meeting slots in Hinglish / Hindi / Gujarati / English: parse what the seller said, render
what VANI says, and suggest slots that respect what the seller ruled out.

"kal shaam paanch baje"  -> Slot(day="tomorrow", hour=17)
"kal free nahi hoon"     -> unavailable {"tomorrow"}
Used as a deterministic check on the LLM and as the offline fallback.
"""
import re
from dataclasses import asdict, dataclass

NUM = {"ek": 1, "do": 2, "teen": 3, "chaar": 4, "char": 4, "paanch": 5, "panch": 5, "chhe": 6, "che": 6, "chheh": 6,
       "saat": 7, "sat": 7, "aath": 8, "ath": 8, "nau": 9, "das": 10, "gyarah": 11, "gyara": 11, "barah": 12, "bara": 12,
       "एक": 1, "दो": 2, "तीन": 3, "चार": 4, "पांच": 5, "पाँच": 5, "छह": 6, "छः": 6, "सात": 7, "आठ": 8, "नौ": 9,
       "दस": 10, "ग्यारह": 11, "बारह": 12, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
       "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
       "agiyar": 11, "agyar": 11, "baar": 12, "એક": 1, "બે": 2, "ત્રણ": 3, "ચાર": 4, "પાંચ": 5, "છ": 6, "સાત": 7,
       "આઠ": 8, "નવ": 9, "દસ": 10, "અગિયાર": 11, "બાર": 12}
DAYS = {
    "today": ["aaj", "aj", "aaje", "today", "आज", "આજે", "આજ"], "tomorrow": ["kal", "kale", "kaale", "tomorrow", "कल", "કાલે", "કાલ"],
    "day_after": ["parso", "parson", "day after tomorrow", "परसों", "param divse", "parmdivse", "પરમ દિવસે", "પરમદિવસે"],
    "monday": ["monday", "somvar", "somwar", "somvare", "सोमवार", "સોમવાર", "સોમવારે"],
    "tuesday": ["tuesday", "mangalvar", "mangalwar", "mangalvare", "मंगलवार", "મંગળવાર", "મંગળવારે"],
    "wednesday": ["wednesday", "budhvar", "budhwar", "budhvare", "बुधवार", "બુધવાર", "બુધવારે"],
    "thursday": ["thursday", "guruvar", "guruwar", "veervar", "guruvare", "गुरुवार", "ગુરુવાર", "ગુરુવારે"],
    "friday": ["friday", "shukravar", "shukrawar", "shukravare", "शुक्रवार", "શુક્રવાર", "શુક્રવારે"],
    "saturday": ["saturday", "shanivar", "shaniwar", "shanivare", "शनिवार", "શનિવાર", "શનિવારે"],
    "sunday": ["sunday", "ravivar", "raviwar", "itwar", "itvaar", "ravivare", "रविवार", "इतवार", "રવિવાર", "રવિવારે"],
}
PARTS = {"morning": ["subah", "morning", "savare", "सुबह", "સવારે", "સવાર"],
         "noon": ["dopahar", "dopehar", "afternoon", "bapore", "दोपहर", "બપોરે", "બપોર"],
         "evening": ["shaam", "sham", "evening", "sanje", "saanje", "शाम", "સાંજે", "સાંજ"],
         "night": ["raat", "rat", "night", "ratre", "रात", "રાત્રે", "રાત"]}
LETTER = r"\wऀ-ॿ઀-૿"      # word characters incl. Devanagari and Gujarati vowel signs

_num = "|".join(sorted((re.escape(k) for k in NUM), key=len, reverse=True))
TIME = re.compile(rf"(?<![{LETTER}])(\d{{1,2}}|{_num})(?:[:.](\d{{2}}))?\s*"
                  rf"(baje|bje|बजे|vage|vaage|vagye|વાગ્યે|વાગે|o'?clock|am|pm|a\.m\.|p\.m\.)?",
                  re.I)
NEG = re.compile(r"(free nahi|nahi ho (paye|payega|sakta|sakti)|nahi (aa|mil) (sakta|sakti|paunga|paungi)|not (free|available)|"
                 r"busy (hoon|hu|hai|rahunga|rahungi)|nahi hoon|नहीं हूँ|फ्री नहीं|can'?t (do|make it|meet)|"
                 r"free nathi|ફ્રી નથી|(nahi|nai|nahin) fave|નહીં ફાવે|નહિ ફાવે|nathi favtu|નથી ફાવતું|busy (chu|chhu)|busy છું|બિઝી છું)",
                 re.I)


@dataclass
class Slot:
    day: str | None = None      # today / tomorrow / day_after / monday ...
    hour: int | None = None     # 24h
    minute: int = 0

    @property
    def complete(self) -> bool:
        return self.day is not None and self.hour is not None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict | None) -> "Slot | None":
        if not d:
            return None
        return cls(day=d.get("day"), hour=d.get("hour"), minute=d.get("minute") or 0)


def _find_day(text: str, skip: set[str] | frozenset = frozenset()) -> str | None:
    best = None
    for day, words in DAYS.items():
        if day in skip:
            continue
        for w in words:
            m = re.search(rf"(?<![{LETTER}]){re.escape(w)}(?![{LETTER}])", text, re.I)
            if m and (best is None or m.start() < best[0]):
                best = (m.start(), day)
    return best[1] if best else None


def _find_part(text: str) -> str | None:
    for part, words in PARTS.items():
        if any(re.search(rf"(?<![{LETTER}]){re.escape(w)}(?![{LETTER}])", text, re.I) for w in words):
            return part
    return None


def _to_24h(h: int, part: str | None, ampm: str | None) -> int:
    if ampm:
        a = ampm.lower()
        if a.startswith("p") and h < 12:
            return h + 12
        if a.startswith("a") and h == 12:
            return 0
        return h
    if part == "morning":
        return h if h < 12 else 12
    if part == "noon":
        return h + 12 if h < 6 else (12 if h == 12 else h)
    if part in ("evening", "night"):
        return h + 12 if h < 12 else h
    # Business hours default: 1-7 means afternoon/evening, 8-11 morning, 12 noon
    return h + 12 if 1 <= h <= 7 else h


def parse_slot(text: str) -> Slot | None:
    """Day and/or time the text mentions (None if neither)."""
    text = text or ""
    day = _find_day(text, unavailable_days(text)) or _find_day(text)   # "kal nahi, somvar rakho" -> Monday
    hour = minute = None
    for m in TIME.finditer(text):
        raw, mins, unit = m.group(1), m.group(2), m.group(3)
        if not unit and not raw.isdigit():
            continue          # bare number words ("do", "ek") are too ambiguous without "baje"
        if not unit and raw.isdigit():
            after = text[m.end():m.end() + 14].lower()
            if re.match(r"\s*(minute|min\b|mins|buyer|enquir|inquir|%|rupe|rs|lakh|lac|hazaar|hazar|crore|cr\b|din|days?|ghante|hours?|saal|year|log|calls?)", after):
                continue      # counts, not times: "20 minute", "5 buyers"
            context = _find_day(text) or re.search(r"\b(at|around|by|works|chalega|chalse|theek|thik|ok|okay|fine|karte|rakh|rakhte|rakho)\b", text, re.I)
            if not context or not 1 <= int(raw) <= 12:
                continue
        h = int(raw) if raw.isdigit() else NUM.get(raw.lower(), NUM.get(raw))     # int() also reads ૧૧ / ११
        if h is None or h > 23:
            continue
        ampm = unit if unit and unit.lower()[0] in "ap" else None
        hour = _to_24h(h, _find_part(text), ampm) if h <= 12 else h
        minute = int(mins) if mins else 0
        break
    if day is None and hour is None:
        return None
    return Slot(day=day, hour=hour, minute=minute or 0)


def unavailable_days(text: str) -> set[str]:
    """'kal free nahi hoon' -> {'tomorrow'}. Only days mentioned together with a negation."""
    out = set()
    for clause in re.split(r"[,.;।?!]| lekin | par | but ", text or "", flags=re.I):
        if NEG.search(clause) and (d := _find_day(clause)):
            out.add(d)
    return out


HI_DAY = {"today": "आज", "tomorrow": "कल", "day_after": "परसों", "monday": "सोमवार", "tuesday": "मंगलवार",
          "wednesday": "बुधवार", "thursday": "गुरुवार", "friday": "शुक्रवार", "saturday": "शनिवार", "sunday": "रविवार"}
GU_DAY = {"today": "આજે", "tomorrow": "કાલે", "day_after": "પરમ દિવસે", "monday": "સોમવારે", "tuesday": "મંગળવારે",
          "wednesday": "બુધવારે", "thursday": "ગુરુવારે", "friday": "શુક્રવારે", "saturday": "શનિવારે", "sunday": "રવિવારે"}
EN_DAY = {"today": "today", "tomorrow": "tomorrow", "day_after": "day after tomorrow"}


def render(slot: Slot, style: str = "hinglish") -> str:
    h = slot.hour
    if style == "hinglish":
        part = "" if h is None else ("सुबह " if h < 12 else "दोपहर " if h < 16 else "शाम " if h < 20 else "रात ")
        hh = "" if h is None else f"{(h - 1) % 12 + 1}{':%02d' % slot.minute if slot.minute else ''} बजे"
        return " ".join(x for x in (HI_DAY.get(slot.day, ""), part + hh) if x).strip()
    if style == "gujarati":
        part = "" if h is None else ("સવારે " if h < 12 else "બપોરે " if h < 16 else "સાંજે " if h < 20 else "રાત્રે ")
        hh = "" if h is None else f"{(h - 1) % 12 + 1}{':%02d' % slot.minute if slot.minute else ''} વાગ્યે"
        return " ".join(x for x in (GU_DAY.get(slot.day, ""), part + hh) if x).strip()
    day = EN_DAY.get(slot.day, slot.day.capitalize() if slot.day else "")
    tm = "" if h is None else f"{(h - 1) % 12 + 1}{':%02d' % slot.minute if slot.minute else ''} {'AM' if h < 12 else 'PM'}"
    return f"{day} at {tm}".strip() if day and tm else (day or tm)


# What real sellers accepted most (mined from 1,078 meeting-fixed VANI summaries): 11-12 AM, then 2-5 PM.
PREFERRED_HOURS = (11, 17, 15, 12)
DAY_ORDER = ["tomorrow", "day_after", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]


def suggest(unavailable: set[str], already_offered: list[Slot] | None = None, n: int = 2) -> list[Slot]:
    offered = {(s.day, s.hour) for s in already_offered or []}
    out = []
    for day in DAY_ORDER:
        if day in unavailable:
            continue
        for h in PREFERRED_HOURS:
            if (day, h) not in offered:
                out.append(Slot(day, h))
                if len(out) == n:
                    return out
    return out


def fill(text: str, style: str, offer: list[Slot] | None = None, agreed: Slot | None = None) -> str:
    """Put real slots into a line's {slot1}/{slot2}/{slot} placeholders."""
    offer = offer or suggest(set())
    st = style if style in ("hinglish", "gujarati") else "english"
    vals = {"slot1": render(offer[0], st), "slot2": render(offer[1 if len(offer) > 1 else 0], st),
            "slot": render(agreed, st) if agreed else render(offer[0], st)}
    for k, v in vals.items():
        text = text.replace("{" + k + "}", v)
    return text
