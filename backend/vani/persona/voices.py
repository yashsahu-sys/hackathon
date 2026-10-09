"""Bulbul voice choices. Speaker names are bulbul:v3 voices (from Sarvam's SDK).

Which voice sounds best for which register is a judgement call made by ear;
tune VOICE_MAP after listening (scripts/voice_audition.py renders samples).
"""

ACCENT = {
    "hi-IN": "Hindi (North Indian)", "en-IN": "Indian English", "ta-IN": "Tamil", "te-IN": "Telugu",
    "kn-IN": "Kannada", "ml-IN": "Malayalam", "bn-IN": "Bengali", "gu-IN": "Gujarati", "mr-IN": "Marathi",
    "pa-IN": "Punjabi", "od-IN": "Odia", "as-IN": "Assamese",
}

# (gender, register) -> speaker. register: casual / neutral / formal
VOICE_MAP = {
    ("female", "casual"): "simran",
    ("female", "neutral"): "ritu",
    ("female", "formal"): "priya",
    ("male", "casual"): "rahul",
    ("male", "neutral"): "shubh",
    ("male", "formal"): "aditya",
}

# Language-specific voices where the catalogue has a better native fit.
LANGUAGE_VOICE = {
    ("female", "ta-IN"): "kavitha", ("female", "te-IN"): "kavitha", ("female", "bn-IN"): "roopa",
    ("female", "gu-IN"): "pooja", ("female", "mr-IN"): "rupali", ("male", "ta-IN"): "gokul",
    ("male", "te-IN"): "vijay", ("male", "pa-IN"): "anand",
}

BOT_NAME = {"female": "Payal", "male": "Arjun"}   # Payal = VANI's production name

PACE_MIN, PACE_MAX = 0.5, 2.0   # bulbul v3 range


def speaker_for(gender: str, register: str, language_code: str) -> str:
    if language_code not in ("hi-IN", "en-IN"):
        v = LANGUAGE_VOICE.get((gender, language_code))
        if v:
            return v
    return VOICE_MAP[(gender, register)]


def clamp_pace(p: float) -> float:
    return round(max(PACE_MIN, min(PACE_MAX, p)), 2)
