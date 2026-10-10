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

# bulbul:v4-flash uses persona voice ids (<name>_<lang>_<style>); v3 short names are rejected by v4.
# Ids from Sarvam's SDK speaker catalogue; "enhi" = English-Hindi code-mixed.
VOICE_MAP_V4 = {
    ("female", "casual", "hi-IN"): "ishita_enhi_customer_expressive",
    ("female", "neutral", "hi-IN"): "simran_enhi_customer",
    ("female", "formal", "hi-IN"): "ritu_hi_customer",
    ("male", "casual", "hi-IN"): "sunny_enhi_customer",
    ("male", "neutral", "hi-IN"): "shubh_hi_customer",
    ("male", "formal", "hi-IN"): "aditya_hi_sales",
    ("female", "casual", "en-IN"): "simran_en_conversation",
    ("female", "neutral", "en-IN"): "neha_en_customer",
    ("female", "formal", "en-IN"): "shalini_en_customer",
    ("male", "casual", "en-IN"): "dev_en_conversational",
    ("male", "neutral", "en-IN"): "deven_en_conversation",
    ("male", "formal", "en-IN"): "varun_en_ads",
}
LANGUAGE_VOICE_V4 = {
    ("female", "gu-IN"): "pooja_gu_customer", ("female", "mr-IN"): "ishita_mr_conversational",
    ("female", "bn-IN"): "roopa_bn_conversational", ("female", "te-IN"): "kavitha_te_conversation",
    ("female", "kn-IN"): "chaitra_kn_conversation", ("male", "ta-IN"): "vetri_ta_ads",
    ("male", "pa-IN"): "anand_pa_customer", ("male", "kn-IN"): "chetan_kn_conversation",
    ("male", "gu-IN"): "bhavik_gu_conversation", ("male", "mr-IN"): "nilesh_mr_conversation",
}

BOT_NAME = {"female": "Payal", "male": "Arjun"}   # Payal = VANI's production name

PACE_MIN, PACE_MAX = 0.5, 2.0   # bulbul v3 range


def speaker_for(gender: str, register: str, language_code: str, model: str = "bulbul:v3") -> str:
    if model.startswith("bulbul:v4"):
        if language_code not in ("hi-IN", "en-IN") and (gender, language_code) in LANGUAGE_VOICE_V4:
            return LANGUAGE_VOICE_V4[(gender, language_code)]
        base = "en-IN" if language_code == "en-IN" else "hi-IN"
        return VOICE_MAP_V4[(gender, register, base)]
    if language_code not in ("hi-IN", "en-IN"):
        v = LANGUAGE_VOICE.get((gender, language_code))
        if v:
            return v
    return VOICE_MAP[(gender, register)]


def clamp_pace(p: float) -> float:
    return round(max(PACE_MIN, min(PACE_MAX, p)), 2)
