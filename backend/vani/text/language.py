"""Language identification for short, noisy, code-mixed call turns.

Real VANI transcripts are mostly Roman-script Hinglish ("Haan ji bol rahe hain"),
so script alone isn't enough: we count Roman Hindi function words vs English
function words. Shared by evidence mining and live signal detection.
"""
import re

SCRIPTS = [
    (re.compile(r"[஀-௿]"), "ta-IN"), (re.compile(r"[ఀ-౿]"), "te-IN"),
    (re.compile(r"[ಀ-೿]"), "kn-IN"), (re.compile(r"[ഀ-ൿ]"), "ml-IN"),
    (re.compile(r"[਀-੿]"), "pa-IN"), (re.compile(r"[઀-૿]"), "gu-IN"),
    (re.compile(r"[ঀ-৿]"), "bn-IN"), (re.compile(r"[଀-୿]"), "od-IN"),
]
DEVANAGARI = re.compile(r"[ऀ-ॿ]")
WORD = re.compile(r"[a-zA-Z']+")

HINDI_WORDS = set("""
hai hain ho hoon hu tha thi the nahi nahin na haan han ha haanji ji kya kyun kaise kaun kab kahan
mein main mai mujhe mera meri mere hum hamara humara aap aapka aapki tum tumhara woh wo yeh ye
ka ki ke ko se par pe aur bhi toh to abhi kal aaj baad pehle phir bas sirf accha achha acha theek thik
bolo boliye bol rahe raha rahi karo kariye karna karenge kar diya dijiye lena dena chahiye chalega
bhai bhaiya sahab saheb yaar matlab samjha samajh pata maloom kitna kitne kitni wala wali vale
dhanyavad shukriya namaste namaskar haanji bilkul zaroor jaroor sahi galat kaam baat
""".split())
ENGLISH_WORDS = set("""
the a an is are was were am be been i you we they he she it my your our their this that these those
what why how who when where which yes no not please sorry thank thanks okay ok can could would should
will shall do does did have has had to of in on for with from at by about just only also very
speak talk understand english call later busy meeting interested sure fine right good morning sir madam
""".split())
SHARED = {"ok", "okay", "sir", "madam", "hello", "hi", "yes", "no"}   # used in both, weak evidence


def detect(text: str, hint: str | None = None) -> tuple[str, float]:
    """Return (BCP-47 code, confidence). `hint` = language reported by STT, if any."""
    text = text or ""
    for pattern, code in SCRIPTS:
        if pattern.search(text):
            return code, 0.95
    if DEVANAGARI.search(text):
        return "hi-IN", 0.9
    words = [w.lower() for w in WORD.findall(text)]
    if not words:
        return (hint or "unknown"), 0.3 if hint else 0.0
    hi = sum(w in HINDI_WORDS for w in words)
    en = sum(w in ENGLISH_WORDS and w not in SHARED for w in words)
    if hi == 0 and en == 0:
        if hint and hint not in ("hi-IN", "en-IN"):
            return hint, 0.6
        return (hint or "unknown"), 0.3
    if hi >= en:
        return "hi-IN", min(0.95, 0.55 + 0.1 * (hi - en))
    return "en-IN", min(0.95, 0.55 + 0.1 * (en - hi))


def english_share(text: str) -> float:
    """Share of English function words among recognised words (0 = pure Hindi, 1 = pure English)."""
    words = [w.lower() for w in WORD.findall(text or "")]
    hi = sum(w in HINDI_WORDS for w in words)
    en = sum(w in ENGLISH_WORDS and w not in SHARED for w in words)
    return en / (hi + en) if hi + en else 0.0
