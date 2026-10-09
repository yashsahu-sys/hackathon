"""Gujarati: third language with native lines, slots, signals and detection."""
from vani.live.signals import SignalDetector
from vani.domain.live import SignalType as T
from vani.persona.lines import LINES, lines_for
from vani.text.language import detect
from vani.text.slots import Slot, fill, parse_slot, render, unavailable_days


def test_gujarati_lines_cover_every_key():
    en, gu = LINES["english"], LINES["gujarati"]
    assert set(en) == set(gu) and set(en["playbook"]) == set(gu["playbook"])
    assert lines_for("gujarati") is gu and lines_for("regional") is en


def test_gujarati_slots_render_and_parse():
    assert render(Slot("tomorrow", 11), "gujarati") == "કાલે સવારે 11 વાગ્યે"
    assert render(Slot("monday", 17), "gujarati") == "સોમવારે સાંજે 5 વાગ્યે"
    assert "કાલે" in fill("{slot1} કે {slot2}", "gujarati")
    assert parse_slot("kale savare 11 vage chalse") == Slot("tomorrow", 11)
    assert parse_slot("કાલે સાંજે ૫ વાગ્યે રાખો") == Slot("tomorrow", 17)
    assert unavailable_days("kale free nathi") == {"tomorrow"}


def test_seller_slot_skips_the_day_they_ruled_out():
    assert parse_slot("kale free nathi, somvare savare 11 vage rakho") == Slot("monday", 11)
    assert parse_slot("kal free nahi hoon, somvar subah 11 baje rakho") == Slot("monday", 11)


def test_roman_gujarati_detection():
    assert detect("tame kem cho, maru business saru chale che")[0] == "gu-IN"
    assert detect("ગુજરાતીમાં વાત કરો")[0] == "gu-IN"
    assert detect("haan ji bolo kya baat hai")[0] == "hi-IN"
    assert detect("kal chhe baje aa jaiye")[0] == "hi-IN"           # "chhe" = six in Hindi
    assert detect("ha bolo, kem cho tame", hint="gu-IN")[0] == "gu-IN"


def test_gujarati_signals():
    d = SignalDetector()
    types = lambda t: {s.type for s in d.detect(t, "gu-IN")}
    assert T.agreement in types("haa saru che")
    assert T.agreement not in types("kale nahi chalse")
    assert T.refusal in types("nathi joitu bhai")
    assert T.rush in types("atyare busy chu, pachi vaat karo")
    assert T.confusion in types("samjatu nathi, farithi bolo")
    assert T.do_not_call in types("farithi call na karta")
    sw = [s for s in d.detect("Gujarati ma vaat karo ne", "hi-IN") if s.type == T.language_switch]
    assert sw and sw[0].detail["to"] == "gu-IN"
