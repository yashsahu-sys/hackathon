import math

import pytest

from vani.domain.seller import BotCall, CallTurn
from vani.evidence.features import call_features, summary_tags
from vani.evidence.stats import strength, two_proportion_p, wilson
from vani.text.language import detect, english_share


@pytest.mark.parametrize("summary,expected", [
    ("The lead mentioned being busy and asked the agent to call back after the 5th.", {"busy"}),
    ("The lead initially seemed confused about the demo booking.", {"confused"}),
    ("The lead expressed frustration over too many calls from IndiaMART.", {"frustrated"}),
    ("Seller asked whether he was talking to a bot.", {"bot_question"}),
    ("The lead asked about the price of the paid plan.", {"price", "interest"}),
    ("Agreed to a visit at the shop location tomorrow.", {"interest", "visit"}),
    ("Lead said he is already on TradeIndia and not interested.", {"other_platform", "not_interested"}),
    ("The lead could not understand Hindi and asked for English.", {"language_issue"}),
    ("Agent will share details on WhatsApp.", {"whatsapp"}),
    ("", set()), (None, set()),
])
def test_summary_tags(summary, expected):
    assert summary_tags(summary) == expected


def test_not_interested_is_not_interest():
    assert summary_tags("The lead was not interested.") == {"not_interested"}
    assert summary_tags("Seller is uninterested") == set()
    assert "interest" in summary_tags("Seller was interested in the visit")


def test_summary_tags_do_not_fire_on_substrings():
    assert "busy" not in summary_tags("This is a business call about busybox units")



@pytest.mark.parametrize("text,code", [
    ("Haan ji, bol raha hoon", "hi-IN"), ("Abhi time nahi hai, baad mein call karo", "hi-IN"),
    ("Sorry, I don't understand, please speak in English", "en-IN"), ("हाँ बोलिए", "hi-IN"),
    ("வணக்கம்", "ta-IN"), ("నమస్తే", "te-IN"), ("ਸਤ ਸ੍ਰੀ ਅਕਾਲ", "pa-IN"), ("કેમ છો", "gu-IN"),
])
def test_language_detect(text, code):
    assert detect(text)[0] == code


def test_language_detect_short_or_empty_is_unsure():
    assert detect("Hmm.")[1] < 0.55 and detect("")[1] == 0.0
    assert detect("Hello", hint="ta-IN") == ("ta-IN", 0.6)


def test_english_share():
    assert english_share("haan ji bolo") == 0.0
    assert english_share("please speak english") == 1.0
    assert 0 < english_share("haan please bolo") < 1


def test_call_features_from_transcript():
    call = BotCall(attempt_id="1", glid="9", duration_s=12, summary="Lead was busy.", meeting_fixed=False, has_transcript=True)
    turns = [CallTurn(attempt_id="1", turn_no=1, speaker="bot", text="Hello, kya aap Test Co se bol rahe hain?"),
             CallTurn(attempt_id="1", turn_no=2, speaker="seller", text="Haan bolo, abhi busy hoon")]
    f = call_features(call, turns)
    assert f.early_drop and f.tags == {"busy"} and f.has_transcript
    assert f.seller_language == "hi-IN" and f.bot_words_first_turn == 9 and f.seller_words_per_turn == 5


def test_call_features_without_transcript():
    f = call_features(BotCall(attempt_id="1", glid="9", duration_s=None, summary=None), [])
    assert not f.early_drop and f.seller_language is None and not f.has_transcript


def test_wilson_bounds():
    lo, hi = wilson(10, 100)
    assert 0.05 < lo < 0.1 < hi < 0.18
    assert wilson(0, 0) == (0.0, 1.0)
    assert wilson(0, 50)[0] == 0.0 and wilson(50, 50)[1] == pytest.approx(1.0)


def test_two_proportion_p():
    assert two_proportion_p(50, 100, 50, 100) == pytest.approx(1.0)
    assert two_proportion_p(80, 100, 20, 100) < 1e-10
    assert two_proportion_p(1, 0, 1, 10) == 1.0
    assert two_proportion_p(0, 10, 0, 10) == 1.0
    assert math.isclose(two_proportion_p(30, 100, 20, 100), two_proportion_p(20, 100, 30, 100))


def test_strength_rules():
    assert strength(1e-6, 500) == "strong"
    assert strength(1e-6, 20) == "weak"          # sample-size floor
    assert strength(0.03, 500) == "moderate"
    assert strength(0.03, 500, n_tests=10) == "weak"  # Bonferroni
