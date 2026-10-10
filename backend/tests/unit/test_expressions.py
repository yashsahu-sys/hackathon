from vani.domain.live import SignalType as T
from vani.persona.expressions import EXPRESSIONS, with_expression
from vani.text.slots import parse_slot, Slot


def test_every_style_has_every_situation():
    keys = set(EXPRESSIONS["hinglish"])
    assert all(set(b) == keys for b in EXPRESSIONS.values())


def test_frustration_gets_an_apology_and_variants_never_repeat():
    used = []
    t1, a1 = with_expression("जी, सीधी बात: free meeting.", "hinglish", [T.frustration], "direct", used)
    used.append(a1)
    t2, a2 = with_expression("जी, सीधी बात: free meeting.", "hinglish", [T.frustration], "direct", used)
    assert t1.startswith("माफ़ी") and "सीधी बात" in t1 and a2 != a1


def test_strongest_feeling_wins_and_own_feeling_lines_untouched():
    t, a = with_expression("Let me put it simply. Our executive visits you.", "english",
                           [T.confusion, T.language_switch], "clarify", [])
    assert t == "Sure, I'll speak in English. Our executive visits you."
    assert with_expression("माफ़ी चाहती हूँ जी, call ख़त्म करती हूँ।", "hinglish", [T.frustration], "end_close", [])[1] is None


def test_first_pitch_says_thanks_and_gujarati():
    assert with_expression("હમારા", "gujarati", [], "pitch", [], first_pitch=True)[0].startswith("આભાર")
    assert with_expression("pitch", "hinglish", [], "pitch", [], first_pitch=False)[1] is None


def test_refused_time_is_never_the_slot():
    assert parse_slot("11 baje nahi, 5 baje karte hai") == Slot(None, 17)
    assert parse_slot("kal 11 baje nahi") == Slot("tomorrow", None)
