"""Voice cues, per-seller line variants, history openings from the last call."""
import io
import math
import struct
import wave
from datetime import datetime

from vani.persona.lines import LINES, VARIANTS, HISTORY_OPENINGS, variant
from vani.speech.voice_cues import analyze, raised


def _wav(speech_s, amp=8000, silence_s=0.5, rate=16000):
    frames = [int(amp * math.sin(i / 5)) for i in range(int(rate * speech_s))] + [0] * int(rate * silence_s)
    b = io.BytesIO()
    with wave.open(b, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
        w.writeframes(struct.pack(f"<{len(frames)}h", *frames))
    return b.getvalue()


def test_voice_cues_rate_bands():
    fast = analyze(_wav(1.5), "abhi busy hoon jaldi bolo kya kaam hai")          # 8 words in 1.5 s
    slow = analyze(_wav(4.0), "haan ji main sun raha hoon")                         # 6 words in 4 s
    assert fast.band == "fast" and slow.band == "slow"
    assert analyze(_wav(1.0), "haan ji").band == "unknown"                          # too few words to judge
    assert analyze(b"not a wav", "x") is None


def test_raised_voice_is_relative_to_the_seller():
    assert raised(-14.0, [-24.0, -23.0]) and not raised(-20.0, [-24.0]) and not raised(-10.0, [])


def test_variants_differ_across_sellers_and_rotate_within_a_call():
    base = LINES["hinglish"]["pitch"]
    picks = {variant("hinglish", "pitch", base, str(g)) for g in range(50)}
    assert len(picks) == 3
    first = variant("hinglish", "pitch", base, "42", 0)
    assert variant("hinglish", "pitch", base, "42", 1) != first
    assert variant("hinglish", "pitch", base, "42", 0) == first                     # stable per seller


def test_variant_slots_and_history_keys_match():
    for style, keys in VARIANTS.items():
        for k, vs in keys.items():
            base = LINES[style]["playbook"].get(k) or LINES[style][k]
            for v in vs:
                for ph in ("{slot1}", "{slot2}"):
                    assert (ph in v) <= (ph in base or ph == "{slot2}" and "{slot1}" in base), (style, k, v)
    assert all(set(v) == set(HISTORY_OPENINGS["hinglish"]) for v in HISTORY_OPENINGS.values())


def test_history_opening_picks_up_last_call(repo):
    from vani.domain.seller import BotCall
    from vani.evidence.book import EvidenceBook
    from vani.persona.generator import PersonaGenerator
    ctx = repo.get_context("1001")
    ctx.calls = [BotCall(attempt_id="a", glid="1001", started_at=datetime(2026, 9, 1), duration_s=40,
                         disposition="Call Later / Busy")]
    ctx.profile.bot_history.answered = max(1, ctx.profile.bot_history.answered)
    p = PersonaGenerator(EvidenceBook.empty()).generate(ctx)
    assert p.decisions["plan.opening"].value == "history"
    assert "बाद में बात करेंगे" in p.plan.opening or "call back later" in p.plan.opening
