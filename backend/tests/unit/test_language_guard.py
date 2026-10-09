import pytest

from vani.integrations.sarvam.client import SarvamError
from vani.speech.language_guard import ensure_language, language_of, matches


class _P:
    def __init__(self, code, gender="female"):
        self.language = type("L", (), {"code": code})()
        self.voice = type("V", (), {"gender": gender})()


class _Speech:
    def __init__(self, fail=False):
        self.fail, self.calls = fail, []

    async def translate(self, text, target, source="auto", speaker_gender=None, mode="modern-colloquial"):
        self.calls.append((target, speaker_gender, mode))
        if self.fail:
            raise SarvamError("down")
        return "translated"


def test_language_of():
    assert language_of("जी, कल मिलते हैं") == "hi-IN"
    assert language_of("Sure, shall we meet tomorrow at eleven?") == "en-IN"
    assert language_of("haan ji kal milte hain aap kab free ho") == "hi-IN"


def test_matches():
    assert matches("Sure, tomorrow at 11 works.", _P("en-IN"))
    assert not matches("जी, कल 11 बजे?", _P("en-IN"))
    assert matches("जी, कल 11 बजे?", _P("hi-IN"))
    assert matches("Okay sir.", _P("hi-IN"))                   # short filler is fine in Hinglish
    assert not matches("Sure, shall we meet tomorrow at eleven in the morning?", _P("hi-IN"))


async def test_ensure_language_translates_with_gender_and_mode():
    sp, w = _Speech(), []
    assert await ensure_language("जी, कल 11 बजे मिलते हैं?", _P("en-IN", "male"), sp, w) == "translated"
    assert sp.calls == [("en-IN", "male", "modern-colloquial")] and "translated" in w[0]
    await ensure_language("Sure, shall we meet tomorrow at eleven in the morning?", _P("hi-IN"), sp, [])
    assert sp.calls[-1][2] == "code-mixed"


async def test_ensure_language_noop_and_failure():
    sp = _Speech(fail=True)
    assert await ensure_language("Sure, tomorrow works.", _P("en-IN"), sp, []) == "Sure, tomorrow works." and not sp.calls
    w = []
    assert await ensure_language("जी, कल 11 बजे मिलते हैं?", _P("en-IN"), sp, w) is None
    assert "translation failed" in w[0]
