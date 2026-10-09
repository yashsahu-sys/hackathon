import pytest

from vani.domain.live import SignalType as T
from vani.live.signals import SignalDetector

det = SignalDetector()


def types(text, lang="hi-IN", history=None):
    return {s.type for s in det.detect(text, lang, recent_seller_turns=history)}


# Paraphrased from real VANI seller turns (no verbatim customer speech in the repo)
@pytest.mark.parametrize("text,expected", [
    ("Abhi hum busy hain, baad mein call karna", T.rush),
    ("Main abhi bahar hoon", T.rush),
    ("Madam main free nahi hoon abhi", T.rush),
    ("Thodi der mein call karta hoon, meeting mein hoon", T.rush),
    ("अभी बिज़ी हूँ, बाद में बात करते हैं", T.rush),
    ("I'm driving, call me later", T.rush),
    ("Matlab? Samjha nahi", T.confusion),
    ("Ye call kis liye kiya?", T.confusion),
    ("समझ नहीं आया", T.confusion),
    ("Sorry, I did not understand", T.confusion),
    ("Aap baar baar phone kyun karte ho?", T.frustration),
    ("Kitni baar bataun, pareshan mat karo", T.frustration),
    ("Aap zabardasti karoge kya?", T.frustration),
    ("बार-बार कॉल क्यों करते हो", T.frustration),
    ("Aap AI ho?", T.bot_question),
    ("Is this a recording? Are you a bot?", T.bot_question),
    ("Kaun bol raha hai?", T.identity),
    ("Who is this?", T.identity),
    ("Kisi insaan se baat karao", T.human_request),
    ("I want to talk to a human", T.human_request),
    ("Kitne der ki meeting hogi?", T.interest),
    ("Executive kab aayenge? Kaise hoga?", T.interest),
    ("Haan theek hai, kal 11 baje aa jaiye", T.agreement),
    ("Alright, tomorrow 11 works", T.agreement),
    ("Nahi chahiye madam", T.refusal),
    ("Main interested nahi hoon", T.refusal),
    ("Humein karwana nahi hai", T.refusal),
    ("Already doosri jagah pe membership hai", T.refusal),
    ("Dubara call mat kijiye", T.do_not_call),
    ("Mera number block kar do", T.do_not_call),
    ("Please don't call me again", T.do_not_call),
])
def test_detects(text, expected):
    assert expected in types(text)


@pytest.mark.parametrize("text,absent", [
    ("Theek hai, abhi toh busy hain", T.agreement),          # busy overrides "theek hai"
    ("Thik hai, dubara call mat kijiyega", T.agreement),       # do-not-call overrides "thik hai"
    ("Uska koi fayda nahi hota", T.interest),                  # negated value = scepticism
    ("Kaun bol raha hai?", T.confusion),                       # identity, not confusion
    ("Abhi nahi, call mat karo", T.rush),                      # do-not-call is not scheduling
    ("Haan ji boliye", T.refusal),
    ("This is a business enquiry", T.rush),                    # 'business' is not 'busy'
])
def test_precedence(text, absent):
    assert absent not in types(text)


def test_negated_value_becomes_value_objection():
    sigs = {s.type: s for s in det.detect("Pehle karke dekha, koi fayda nahi hua", "hi-IN")}
    assert sigs[T.refusal].detail.get("objection") == "value"


@pytest.mark.parametrize("text,target", [
    ("Can you speak in English please", "en-IN"),
    ("Tamil la pesunga, Tamil only", "ta-IN"),
    ("எனக்கு தமிழ் தான் தெரியும்", "ta-IN"),
    ("I am not able to follow what you are saying, sorry", "en-IN"),
])
def test_language_switch(text, target):
    sig = [s for s in det.detect(text, "hi-IN") if s.type == T.language_switch]
    assert sig and sig[0].detail["to"] == target


def test_hindi_request_during_english_call():
    sig = [s for s in det.detect("Hindi mein baat kariye", "en-IN") if s.type == T.language_switch]
    assert sig and sig[0].detail["to"] == "hi-IN"


def test_no_language_switch_on_short_or_same_language():
    assert T.language_switch not in types("Yes")                 # too short to be sure
    assert T.language_switch not in types("Haan ji bol raha hoon main")   # already Hindi
    assert T.language_switch not in types("Please continue in English", lang="en-IN")


def test_three_tiny_replies_mean_rush():
    assert T.rush in types("Hmm", history=["Achha", "Hmm"])
    assert T.rush not in types("Hmm", history=["Achha bataiye aap kya keh rahe the"])
    assert T.rush not in types("Haan", history=["Hmm", "Achha"])     # "haan" is agreement, not rush


def test_double_exclamation_is_frustration():
    assert T.frustration in types("Hello!! Hello!!")


def test_triggers_quote_seller_words_and_confidence_bounds():
    for s in det.detect("Abhi busy hoon, baad mein, jaldi bolo", "hi-IN"):
        assert 0.6 <= s.confidence <= 0.95 and s.trigger
    assert det.detect("", "hi-IN") == [] and det.detect("   ", "hi-IN") == []


def test_more_matches_raise_confidence():
    one = {s.type: s for s in det.detect("busy hoon", "hi-IN")}[T.rush].confidence
    three = {s.type: s for s in det.detect("busy hoon, baad mein, jaldi", "hi-IN")}[T.rush].confidence
    assert three > one
