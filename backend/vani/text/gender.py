"""Infer the SELLER's grammatical gender from their own first-person Hindi verbs.

Hindi marks the speaker's gender on first-person verbs: "main bol raha hoon"
(man) vs "bol rahi hoon" (woman), "karunga" vs "karungi". We only ever use what
the seller said about themselves. No names, no voice pitch, no guessing; with
no evidence the answer is "unknown" and the bot stays neutral ("ji", "aap").
"""
import re

_M = r"(?:raha|sakta|chahta|karta|deta|leta|jaata|jata|aata|baitha|gaya|aaya)"
_F = r"(?:rahi|sakti|chahti|karti|deti|leti|jaati|jati|aati|baithi|gayi|gai|aayi)"
_AUX = r"(?:hoon|hu|hun|hoon\b|tha|thi)"

PATTERNS = {
    "male": [re.compile(p, re.I) for p in (
        rf"\b{_M}\s+{_AUX}\b",
        r"\b(?:karunga|aaunga|aunga|jaunga|dunga|lunga|bataunga|milunga|bolunga|sochunga|dekhunga|bhejunga)\b",
        r"(?:रहा|सकता|चाहता|करता|देता|लेता|गया|आया)\s+(?:हूँ|हूं|था)",
        r"(?:करूँगा|करूंगा|आऊँगा|आऊंगा|दूँगा|दूंगा|लूँगा|लूंगा|बताऊँगा|बताऊंगा|मिलूँगा|मिलूंगा)",
    )],
    "female": [re.compile(p, re.I) for p in (
        rf"\b{_F}\s+{_AUX}\b",
        r"\b(?:karungi|aaungi|aungi|jaungi|dungi|lungi|bataungi|milungi|bolungi|sochungi|dekhungi|bhejungi)\b",
        r"(?:रही|सकती|चाहती|करती|देती|लेती|गई|गयी|आई)\s+(?:हूँ|हूं|थी)",
        r"(?:करूँगी|करूंगी|आऊँगी|आऊंगी|दूँगी|दूंगी|लूँगी|लूंगी|बताऊँगी|बताऊंगी|मिलूँगी|मिलूंगी)",
    )],
}
# "rahi hai" / "ho rahi hai" describe a thing ("meeting ho rahi hai"), not the speaker.
NOT_FIRST_PERSON = re.compile(r"\b(?:ho|hota|hoti)\s+(?:raha|rahi)\s+(?:hai|hain)\b|(?:हो)\s+(?:रहा|रही)\s+(?:है|हैं)", re.I)

MIN_MARGIN = 1


def gender_markers(text: str) -> dict[str, list[str]]:
    text = NOT_FIRST_PERSON.sub(" ", text or "")
    return {g: [m.group(0) for p in pats for m in p.finditer(text)] for g, pats in PATTERNS.items()}


def detect_seller_gender(texts: list[str]) -> tuple[str, float, str]:
    """-> (male|female|unknown, confidence 0-1, the words that decided it)."""
    male, female = [], []
    for t in texts:
        m = gender_markers(t)
        male += m["male"]
        female += m["female"]
    if len(male) - len(female) >= MIN_MARGIN and not female:
        return "male", round(min(0.95, 0.7 + 0.1 * (len(male) - 1)), 2), male[0]
    if len(female) - len(male) >= MIN_MARGIN and not male:
        return "female", round(min(0.95, 0.7 + 0.1 * (len(female) - 1)), 2), female[0]
    return "unknown", 0.0, ""
