import json

import pytest

from vani.domain.live import CallStatus, Channel, Outcome, SignalType as T
from vani.evidence.book import EvidenceBook
from vani.integrations.sarvam.client import OfflineSpeechAI, SarvamError
from vani.persona.generator import PersonaGenerator
from vani.runtime.service import CallClosed, CallService, NotFound
from vani.runtime.store import MemorySessionStore


class FakeSpeech:
    enabled = True

    def __init__(self, reply="जी, कल 11 बजे ठीक रहेगा?", fail_chat=False, transcript="Abhi busy hoon, baad mein",
                 labels="none", agreed_slot=None, seller_slot=None, cannot=(), question=None,
                 language="hi-IN", translation="Sure, shall we meet tomorrow at 11 AM?", fail_translate=False):
        self.reply, self.fail_chat, self.transcript, self.labels = reply, fail_chat, transcript, labels
        self.agreed_slot, self.seller_slot, self.cannot, self.question = agreed_slot, seller_slot, list(cannot), question
        self.language, self.translation, self.fail_translate = language, translation, fail_translate
        self.tts_calls, self.chat_calls, self.classify_calls, self.translate_calls = [], [], [], []

    async def stt(self, audio, filename="turn.wav"):
        return {"transcript": self.transcript, "language_code": "hi-IN"}

    async def tts(self, text, language_code, speaker, pace, pitch=None, temperature=None):
        self.tts_calls.append({"text": text, "lang": language_code, "speaker": speaker, "pace": pace,
                               "temperature": temperature})
        return "QUFB"

    async def chat(self, messages, max_tokens=200, model=None, response_format=None):
        if self.fail_chat:
            raise SarvamError("llm down")
        if response_format is not None:                     # LLM brain: understanding + reply, as JSON
            self.classify_calls.append(messages)
            labels = [x.strip() for x in self.labels.split(",") if x.strip() and x.strip() != "none"]
            intent = ("agree" if "agreement" in labels else "end_call" if "end_call" in labels else
                      "do_not_call" if "do_not_call" in labels else "refuse" if "refusal" in labels else
                      "question" if self.question else "answer")
            moods = [x for x in labels if x not in ("agreement", "refusal", "end_call", "do_not_call")]
            return json.dumps({"intent": intent, "mood": moods, "seller_question": self.question, "objection": "none",
                               "seller_slot": self.seller_slot, "seller_cannot_days": self.cannot,
                               "agreed_to_meeting": "agreement" in labels, "agreed_slot": self.agreed_slot,
                               "language": self.language, "reply": self.reply, "slot_offered_in_reply": None})
        if messages[0]["content"].startswith("You label"):  # legacy signal assist
            self.classify_calls.append(messages)
            return self.labels
        self.chat_calls.append(messages)
        return self.reply

    async def translate(self, text, target, source="auto", speaker_gender=None, mode="modern-colloquial"):
        self.translate_calls.append({"text": text, "target": target, "gender": speaker_gender, "mode": mode})
        if self.fail_translate:
            raise SarvamError("translate down")
        return self.translation

    async def transliterate(self, text, source, target, spoken_form=False):
        self.translit_calls = getattr(self, "translit_calls", []) + [text]
        return "देवनागरी " + text


@pytest.fixture
def svc(repo):
    return CallService(repo, PersonaGenerator(EvidenceBook.empty()), MemorySessionStore(), OfflineSpeechAI())


async def test_offline_call_with_switch_then_meeting(svc):
    s, opening = await svc.start("1001")
    assert opening.text == s.persona.plan.opening and opening.audio_b64 is None
    r = await svc.seller_turn(s.session_id, "Haan bolo")
    assert r.move == "pitch"
    r = await svc.seller_turn(s.session_id, "Abhi busy hoon, baad mein baat karo")
    assert [e.signal for e in r.switches] == [T.rush] and r.move in ("rush", "call_later")
    r = await svc.seller_turn(s.session_id, "Theek hai, kal 11 baje aa jaiye")
    assert r.session.outcome == Outcome.meeting_fixed and r.session.status == CallStatus.ended
    stored = svc.store.get(s.session_id)
    assert len(stored.switch_log) == 1 and len(stored.transcript) == 7
    assert len(svc.store.switch_log(seller_glid="1001")) == 1


async def test_language_switch_mid_call_changes_reply_language(svc):
    s, _ = await svc.start("1001")
    r = await svc.seller_turn(s.session_id, "Sorry, can you speak in English please")
    assert r.session.persona.language.code == "en-IN" and r.bot.language_code == "en-IN"
    assert r.bot.text.isascii()


async def test_two_refusals_end_politely(svc):
    s, _ = await svc.start("1001")
    await svc.seller_turn(s.session_id, "Nahi chahiye")
    r = await svc.seller_turn(s.session_id, "Bola na, interest nahi hai")
    assert r.session.outcome == Outcome.declined and r.session.status == CallStatus.ended


async def test_ended_call_rejects_turns(svc):
    s, _ = await svc.start("1001")
    await svc.seller_turn(s.session_id, "Dubara call mat kijiye")
    with pytest.raises(CallClosed):
        await svc.seller_turn(s.session_id, "hello")


async def test_errors(svc):
    with pytest.raises(NotFound):
        await svc.start("nope")
    with pytest.raises(NotFound):
        await svc.seller_turn("nope", "hi")
    s, _ = await svc.start("1001")
    with pytest.raises(ValueError):
        await svc.seller_turn(s.session_id, "   ")


async def test_end_marks_dropped(svc):
    s, _ = await svc.start("1001")
    assert svc.end(s.session_id).outcome == Outcome.dropped
    assert svc.end(s.session_id, Outcome.callback).outcome == Outcome.callback


async def test_live_path_uses_llm_and_switched_voice(repo):
    fake = FakeSpeech(labels="rush")
    svc = CallService(repo, PersonaGenerator(EvidenceBook.empty()), MemorySessionStore(), fake)
    s, opening = await svc.start("1001")
    assert opening.audio_b64 == "QUFB"
    r = await svc.seller_turn(s.session_id, audio=b"RIFF")
    assert r.seller_text == "Abhi busy hoon, baad mein" and r.bot.source == "llm" and r.bot.audio_b64 == "QUFB"
    assert fake.tts_calls[-1]["pace"] > fake.tts_calls[0]["pace"]          # faster after the rush switch
    brain = fake.classify_calls[-1]
    assert "YOUR JOB THIS TURN" in brain[0]["content"] and "rush" in brain[0]["content"]   # rule hints passed
    assert brain[-1]["content"] == "Abhi busy hoon, baad mein" and fake.chat_calls == []    # one call per turn


async def test_llm_failure_falls_back_to_template(repo):
    svc = CallService(repo, PersonaGenerator(EvidenceBook.empty()), MemorySessionStore(), FakeSpeech(fail_chat=True))
    s, _ = await svc.start("1001")
    r = await svc.seller_turn(s.session_id, "Haan bolo")
    assert r.bot.source == "template" and any("LLM brain unavailable" in w for w in r.warnings)


async def test_llm_output_with_banned_filler_is_rejected(repo):
    svc = CallService(repo, PersonaGenerator(EvidenceBook.empty()), MemorySessionStore(), FakeSpeech(reply="अरे यार सुनो"))
    s, _ = await svc.start("1001")
    r = await svc.seller_turn(s.session_id, "Haan bolo")
    assert r.bot.source == "template" and any("guardrail" in w for w in r.warnings)


async def test_meeting_confirmation_never_paraphrased(repo):
    fake = FakeSpeech(reply="something else", labels="agreement")
    svc = CallService(repo, PersonaGenerator(EvidenceBook.empty()), MemorySessionStore(), fake)
    s, _ = await svc.start("1001")
    r = await svc.seller_turn(s.session_id, "Haan theek hai kal 11 baje aa jaiye")
    assert r.move == "meeting_confirm" and r.bot.source == "template"


async def test_agent_channel_returns_directives_without_speech(repo):
    fake = FakeSpeech(labels="frustration")
    svc = CallService(repo, PersonaGenerator(EvidenceBook.empty()), MemorySessionStore(), fake)
    s, _ = await svc.start("1001", channel=Channel.sarvam_agent)
    r = await svc.seller_turn(s.session_id, "Aap baar baar call kyun karte ho")
    assert fake.tts_calls == [] and fake.chat_calls == []       # no speech, no reply phrasing
    assert len(fake.classify_calls) == 1                         # but the LLM second opinion still runs
    d = svc.agent_directives(r.session, r.move)
    assert d["persona_mode"] == "direct" and d["persona_version"] == "2" and float(d["pace"]) == 1.0   # calm, not racing


async def test_live_call_learns_seller_gender_and_tone_reaches_tts(repo):
    fake = FakeSpeech()
    svc = CallService(repo, PersonaGenerator(EvidenceBook.empty()), MemorySessionStore(), fake)
    s, _ = await svc.start("1001")
    r = await svc.seller_turn(s.session_id, "Haan ji, main bol raha hoon")
    assert [e.signal for e in r.switches] == [T.seller_gender]
    assert r.session.persona.language.address_as == "सर"
    temp0 = fake.tts_calls[-1]["temperature"]
    fake.labels = "frustration"                     # the LLM reads frustration on the next turn
    r = await svc.seller_turn(s.session_id, "Aap baar baar call kyun karte ho")
    assert "The seller is a man" in fake.classify_calls[-1][0]["content"]   # next turn's brain knows
    assert fake.tts_calls[-1]["temperature"] < temp0 and fake.tts_calls[-1]["pace"] == 1.0


async def test_start_with_male_voice(repo):
    svc = CallService(repo, PersonaGenerator(EvidenceBook.empty()), MemorySessionStore(), OfflineSpeechAI())
    s, bot = await svc.start("1001", voice_gender="male")
    assert s.persona.voice.gender == "male" and "रहा हूँ" in bot.text



# ----------------------------------------------- regression: the laptop call
SCREENSHOT_CALL = [
    "Arjun jo bhi baat hai kya tum jaldi bata sakte ho ek minute ke andar",
    "Aaram se batao Arjun itni bhi jaldaabazi nahi hai",
    "Arjun main bol raha hoon ki aaraam se batao dheere dheere batao itni koi jaldbaazi nahin hai",
    "Are yaar tum mood kharab kar rahe ho be faaltu ka yaar mera bahut dimaag kharab ho raha hai call cut kar do",
]


async def test_regression_frustrated_seller_is_never_booked_offline(repo):
    """Real failure from the laptop demo: the bot fixed a meeting after 'call cut kar do'."""
    svc = CallService(repo, PersonaGenerator(EvidenceBook.empty()), MemorySessionStore(), OfflineSpeechAI())
    s, _ = await svc.start("1001", voice_gender="male")
    moves, strategies = [], []
    for text in SCREENSHOT_CALL:
        r = await svc.seller_turn(s.session_id, text)
        moves.append(r.move)
        strategies.append(r.session.persona.tone.strategy)
    assert strategies[0] == "rush"
    assert strategies[1] == "clarify" and moves[1] != "rush"           # slow-down replaces rush
    assert r.move == "end_close" and r.session.outcome == Outcome.declined
    assert r.session.outcome != Outcome.meeting_fixed
    assert r.session.persona.voice.pace <= 0.9 or r.session.persona.tone.strategy == "end"
    signals = {e.signal for e in r.session.switch_log}
    assert {T.rush, T.slow_down, T.frustration, T.end_call, T.seller_gender} <= signals


async def test_llm_vetoes_a_rule_agreement(repo):
    fake = FakeSpeech(labels="refusal")
    svc = CallService(repo, PersonaGenerator(EvidenceBook.empty()), MemorySessionStore(), fake)
    s, _ = await svc.start("1001")
    s.stage = "ask"
    svc.store.save(s)
    r = await svc.seller_turn(s.session_id, "theek hai theek hai, kal 11 baje")
    assert r.session.outcome != Outcome.meeting_fixed
    assert any("context overrode keyword match" in w for w in r.warnings)


async def test_llm_adds_a_signal_the_rules_missed(repo):
    fake = FakeSpeech(labels="frustration")
    svc = CallService(repo, PersonaGenerator(EvidenceBook.empty()), MemorySessionStore(), fake)
    s, _ = await svc.start("1001")
    r = await svc.seller_turn(s.session_id, "aap log bhi na, hadd hai")
    sig = [x for x in r.signals if x.type == T.frustration]
    assert sig and sig[0].detail["source"] == "llm" and any(e.signal == T.frustration for e in r.switches)


async def test_llm_alone_never_confirms_a_meeting(repo):
    fake = FakeSpeech(labels="agreement")
    svc = CallService(repo, PersonaGenerator(EvidenceBook.empty()), MemorySessionStore(), fake)
    s, _ = await svc.start("1001")
    r = await svc.seller_turn(s.session_id, "hmm dekhte hain")
    assert r.session.outcome != Outcome.meeting_fixed


async def test_llm_failure_leaves_rules_in_charge(repo):
    svc = CallService(repo, PersonaGenerator(EvidenceBook.empty()), MemorySessionStore(), FakeSpeech(fail_chat=True))
    s, _ = await svc.start("1001")
    r = await svc.seller_turn(s.session_id, "Haan theek hai, kal 11 baje aa jaiye")
    assert r.session.outcome == Outcome.meeting_fixed



async def test_brain_reply_used_and_formatted_for_bulbul(repo):
    fake = FakeSpeech(reply="**Ji**, aapke 123456 buyers 😊 hain")
    svc = CallService(repo, PersonaGenerator(EvidenceBook.empty()), MemorySessionStore(), fake)
    s, _ = await svc.start("1001")
    r = await svc.seller_turn(s.session_id, "Haan bolo")
    assert r.bot.source == "llm" and r.bot.text == "Ji, aapke 1,23,456 buyers hain"   # markdown/emoji gone, commas


async def test_brain_cannot_claim_a_booking(repo):
    fake = FakeSpeech(reply="बढ़िया, आपकी meeting fix हो गई है", labels="interest")
    svc = CallService(repo, PersonaGenerator(EvidenceBook.empty()), MemorySessionStore(), fake)
    s, _ = await svc.start("1001")
    r = await svc.seller_turn(s.session_id, "achha kaise hoga")
    assert r.bot.source == "template" and any("claimed a booked meeting" in w for w in r.warnings)


async def test_transliteration_toggle(repo):
    fake = FakeSpeech(reply="Theek hai ji, main aapko kal call karti hoon")
    svc = CallService(repo, PersonaGenerator(EvidenceBook.empty()), MemorySessionStore(), fake, tts_transliterate=True)
    s, _ = await svc.start("1001")
    r = await svc.seller_turn(s.session_id, "Haan bolo")
    assert r.bot.text.startswith("देवनागरी ") and fake.tts_calls[-1]["text"] == r.bot.text


async def test_regression_with_brain_never_books_frustrated_seller(repo):
    fake = FakeSpeech(labels="agreement")   # even a wrong LLM 'yes' can't book: rules see frustration/end_call
    svc = CallService(repo, PersonaGenerator(EvidenceBook.empty()), MemorySessionStore(), fake)
    s, _ = await svc.start("1001", voice_gender="male")
    for text in SCREENSHOT_CALL:
        r = await svc.seller_turn(s.session_id, text)
    assert r.session.outcome != Outcome.meeting_fixed and r.move == "end_close"



# ------------------------------------- regression: laptop call #2 (slots)
SLOT_CALL = [
    "Haan bataiye",
    "Actually kal main free nahi hoon toh aap kisi doosre time par kar sakte hain matlab meetings",
    "Nahi bhai toh us hisab se rahe toh matlab hours bolne type. Sab change karenge. Okay toh paanch baje karte hain waiting.",
]


async def test_regression_slot_negotiation_rules_only(repo):
    """Laptop bug: seller ruled out tomorrow, agreed to 5 baje; bot confirmed 'kal 11 baje'."""
    svc = CallService(repo, PersonaGenerator(EvidenceBook.empty()), MemorySessionStore(), OfflineSpeechAI())
    s, _ = await svc.start("1001", voice_gender="male")
    await svc.seller_turn(s.session_id, SLOT_CALL[0])
    r = await svc.seller_turn(s.session_id, SLOT_CALL[1])
    assert r.session.unavailable_days == ["tomorrow"]
    assert r.move == "reschedule" and "कल" not in r.bot.text           # never re-offers tomorrow
    r = await svc.seller_turn(s.session_id, SLOT_CALL[2])
    assert r.session.outcome == Outcome.meeting_fixed
    assert r.session.agreed_slot["hour"] == 17 and r.session.agreed_slot["day"] != "tomorrow"
    assert "शाम 5 बजे" in r.bot.text and "11 बजे" not in r.bot.text     # confirms THEIR time
    assert r.session.meeting_slot.endswith("5 PM")


async def test_regression_slot_negotiation_with_brain(repo):
    fake = FakeSpeech(reply="ठीक है जी, तो परसों कैसा रहेगा?", cannot=["tomorrow"])
    svc = CallService(repo, PersonaGenerator(EvidenceBook.empty()), MemorySessionStore(), fake)
    s, _ = await svc.start("1001", voice_gender="male")
    await svc.seller_turn(s.session_id, SLOT_CALL[0])
    r = await svc.seller_turn(s.session_id, SLOT_CALL[1])
    assert "tomorrow" in r.session.unavailable_days
    fake.labels, fake.agreed_slot, fake.cannot = "agreement", {"day": None, "hour": 17}, []
    r = await svc.seller_turn(s.session_id, SLOT_CALL[2])
    assert r.session.outcome == Outcome.meeting_fixed and r.session.agreed_slot["hour"] == 17
    assert r.session.agreed_slot["day"] != "tomorrow" and "शाम 5 बजे" in r.bot.text


async def test_brain_reply_offering_a_ruled_out_day_is_rejected(repo):
    fake = FakeSpeech(reply="तो कल सुबह 11 बजे मिलते हैं?", cannot=["tomorrow"])
    svc = CallService(repo, PersonaGenerator(EvidenceBook.empty()), MemorySessionStore(), fake)
    s, _ = await svc.start("1001")
    r = await svc.seller_turn(s.session_id, "kal free nahi hoon")
    assert r.bot.source == "template" and "कल" not in r.bot.text
    assert any("ruled out" in w for w in r.warnings)


async def test_brain_gets_global_context_seller_brief_and_state(repo):
    fake = FakeSpeech(cannot=["tomorrow"])
    svc = CallService(repo, PersonaGenerator(EvidenceBook.empty()), MemorySessionStore(), fake,
                      global_context="- 46% of sellers hang up within 20 seconds")
    s, _ = await svc.start("1001")
    await svc.seller_turn(s.session_id, "kal free nahi hoon")
    await svc.seller_turn(s.session_id, "achha")
    sys = fake.classify_calls[-1][0]["content"]
    assert "46% of sellers hang up" in sys                       # global context
    assert "Past call" in sys                                     # this seller's call summaries
    assert "Seller ruled out: tomorrow" in sys                    # call state
    assert "answer it first" in sys                               # answer the question first


async def test_llm_only_yes_without_slot_never_books(repo):
    fake = FakeSpeech(labels="agreement")                         # LLM wrongly says yes, no slot, rules hear no yes
    svc = CallService(repo, PersonaGenerator(EvidenceBook.empty()), MemorySessionStore(), fake)
    s, _ = await svc.start("1001")
    for text in ("Haan bataiye", "aaram se batao", "hmm"):
        r = await svc.seller_turn(s.session_id, text)
    assert r.session.outcome != Outcome.meeting_fixed


async def test_regression_brain_reply_follows_seller_language_switch(repo):
    # Screenshot: seller switched to English, LLM still answered in Hindi.
    fake = FakeSpeech(reply="जी, कल 11 बजे मिलते हैं?", language="en-IN")
    svc = CallService(repo, PersonaGenerator(EvidenceBook.empty()), MemorySessionStore(), fake)
    s, _ = await svc.start("1001")
    r = await svc.seller_turn(s.session_id, "Sorry, can you please speak in English, I don't understand Hindi")
    assert r.session.persona.language.code == "en-IN" and r.bot.language_code == "en-IN"
    assert "switched to English" in fake.classify_calls[-1][0]["content"]
    assert fake.translate_calls and fake.translate_calls[-1]["target"] == "en-IN"
    assert r.bot.text.isascii() and any("translated to English" in w for w in r.warnings)


async def test_translate_failure_falls_back_to_english_template(repo):
    fake = FakeSpeech(reply="जी, कल 11 बजे मिलते हैं?", language="en-IN", fail_translate=True)
    svc = CallService(repo, PersonaGenerator(EvidenceBook.empty()), MemorySessionStore(), fake)
    s, _ = await svc.start("1001")
    r = await svc.seller_turn(s.session_id, "Please speak in English")
    assert r.bot.language_code == "en-IN" and r.bot.source == "template" and r.bot.text.isascii()
    assert any("translation failed" in w for w in r.warnings)


async def test_llm_detected_language_switch_without_rule(repo):
    # Seller just starts talking English (no "speak English" phrase): the LLM's language field drives the switch.
    fake = FakeSpeech(reply="Sure sir, shall we meet tomorrow at 11 AM?", language="en-IN")
    svc = CallService(repo, PersonaGenerator(EvidenceBook.empty()), MemorySessionStore(), fake)
    s, _ = await svc.start("1001")
    r = await svc.seller_turn(s.session_id, "Okay, what exactly is this about, tell me the benefits")
    assert r.session.persona.language.code == "en-IN" and r.bot.text.isascii()
    assert any(e.signal == T.language_switch for e in r.switches)


async def test_hindi_reply_kept_when_persona_is_hindi(repo):
    fake = FakeSpeech(reply="जी, कल 11 बजे ठीक रहेगा?")
    svc = CallService(repo, PersonaGenerator(EvidenceBook.empty()), MemorySessionStore(), fake)
    s, _ = await svc.start("1001")
    await svc.seller_turn(s.session_id, "Haan bolo")
    assert fake.translate_calls == []


async def test_switch_to_gujarati_mid_call_offline(svc):
    s, _ = await svc.start("1001")
    r = await svc.seller_turn(s.session_id, "Gujarati ma vaat karo ne, Hindi nathi aavdtu")
    assert r.session.persona.language.code == "gu-IN" and r.session.persona.language.style == "gujarati"
    assert r.bot.language_code == "gu-IN" and any("઀" <= ch <= "૿" for ch in r.bot.text)
    r = await svc.seller_turn(s.session_id, "kale free nathi, somvare savare 11 vage rakho")
    assert r.move == "confirm_proposed" and "સોમવારે સવારે 11 વાગ્યે" in r.bot.text
    r = await svc.seller_turn(s.session_id, "haa saru che")
    assert r.session.outcome == Outcome.meeting_fixed and "સોમવારે" in r.bot.text


async def test_brain_told_to_write_gujarati_after_switch(repo):
    fake = FakeSpeech(reply="સારું, કાલે સવારે 11 વાગ્યે મળીએ?", language="gu-IN")
    svc = CallService(repo, PersonaGenerator(EvidenceBook.empty()), MemorySessionStore(), fake)
    s, _ = await svc.start("1001")
    r = await svc.seller_turn(s.session_id, "Gujarati ma vaat karo ne, Hindi nathi aavdtu")
    assert "switched to Gujarati" in fake.classify_calls[-1][0]["content"]
    assert r.bot.language_code == "gu-IN" and r.bot.source == "llm" and fake.translate_calls == []


async def test_human_acknowledgements_follow_the_situation(svc):
    s, _ = await svc.start("1001")
    from vani.persona.expressions import EXPRESSIONS
    starts = lambda text, style, sit: any(text.startswith(e) for e in EXPRESSIONS[style][sit])
    r = await svc.seller_turn(s.session_id, "Haan bolo")
    assert starts(r.bot.text, "hinglish", "thanks")
    r = await svc.seller_turn(s.session_id, "Kitni baar call karoge, pareshan kar diya")
    assert starts(r.bot.text, "hinglish", "frustration")
    r = await svc.seller_turn(s.session_id, "Please speak in English")
    assert starts(r.bot.text, "english", "language_switch")


async def test_regression_counter_proposed_time_books_their_time(svc):
    s, _ = await svc.start("1001")
    await svc.seller_turn(s.session_id, "Haan bolo")
    await svc.seller_turn(s.session_id, "Theek hai")
    r = await svc.seller_turn(s.session_id, "11 baje nahi, 5 baje karte hai")
    assert r.session.outcome != Outcome.meeting_fixed or "5 PM" in r.session.meeting_slot


async def test_seller_voice_speed_switches_persona(repo):
    import io, math, struct, wave
    frames = [int(8000 * math.sin(i / 5)) for i in range(16000)] + [0] * 8000     # 1 s of speech
    b = io.BytesIO()
    with wave.open(b, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
        w.writeframes(struct.pack(f"<{len(frames)}h", *frames))
    fake = FakeSpeech(transcript="haan ji bolo kya kaam hai aapko")                 # 7 words in 1 s = fast talker
    svc = CallService(repo, PersonaGenerator(EvidenceBook.empty()), MemorySessionStore(), fake)
    s, _ = await svc.start("1001")
    r = await svc.seller_turn(s.session_id, audio=b.getvalue())
    assert r.voice["band"] == "fast" and r.voice["words_per_s"] >= 3.4
    assert any(e.signal == T.seller_pace for e in r.switches) and 1.05 <= r.session.persona.voice.pace <= 1.1
    assert "voice_fast" in fake.classify_calls[-1][0]["content"]


async def test_curious_seller_gets_answers_before_the_meeting_ask(svc):
    s, _ = await svc.start("1001")
    await svc.seller_turn(s.session_id, "Haan bolo")
    r = await svc.seller_turn(s.session_id, "Accha, ye buyers kaise milte hain?")
    assert r.move == "explain" and "search" in r.bot.text and "बजे" not in r.bot.text       # answer, no slot push
    r = await svc.seller_turn(s.session_id, "Aur executive aakar kya karenge?")
    assert r.move == "explain" and "photos" in r.bot.text and "बजे" not in r.bot.text
    r = await svc.seller_turn(s.session_id, "Iska kuch paisa lagega kya?")
    assert r.move == "explain" and "free" in r.bot.text and "बजे" in r.bot.text          # third answer comes with the ask
    r = await svc.seller_turn(s.session_id, "Theek hai samajh gaya, kal 5 baje aa jaiye")
    assert r.session.outcome == Outcome.meeting_fixed and "5 PM" in r.session.meeting_slot


async def test_when_question_goes_straight_to_the_slot(svc):
    s, _ = await svc.start("1001")
    await svc.seller_turn(s.session_id, "Haan bolo")
    r = await svc.seller_turn(s.session_id, "Kab aa sakte ho?")
    assert r.move == "meeting_ask"


async def test_doubled_transcript_is_collapsed(repo):
    fake = FakeSpeech(transcript="Bahut bahut saari saari ke ke meeting meeting fix fix karo karo")
    svc = CallService(repo, PersonaGenerator(EvidenceBook.empty()), MemorySessionStore(), fake)
    s, _ = await svc.start("1001")
    r = await svc.seller_turn(s.session_id, audio=b"RIFF")
    assert r.seller_text == "Bahut saari ke meeting fix karo" and any("twice" in w for w in r.warnings)


async def test_busy_seller_gets_calm_benefit_led_reply(repo):
    from vani.evidence.demand import CategoryDemand
    gen = PersonaGenerator(EvidenceBook.empty(), demand=CategoryDemand.build(repo.iter_profiles()))
    svc = CallService(repo, gen, MemorySessionStore(), OfflineSpeechAI())
    s, _ = await svc.start("1001")
    await svc.seller_turn(s.session_id, "Haan bolo")
    r = await svc.seller_turn(s.session_id, "yaar mai busy hu jaldi btao")
    assert r.move == "rush" and r.session.persona.voice.pace <= 1.1
    assert "IndiaMART" in r.bot.text or "listing" in r.bot.text.lower()        # a benefit, not just "10 seconds"
    assert "बजे" in r.bot.text                                                    # and the slots


async def test_dead_end_llm_reply_is_replaced_by_positive_line(repo):
    fake = FakeSpeech(reply="जी, अभी exact competitors की list मेरे पास नहीं है।")
    svc = CallService(repo, PersonaGenerator(EvidenceBook.empty()), MemorySessionStore(), fake)
    s, _ = await svc.start("1001")
    r = await svc.seller_turn(s.session_id, "Haan bolo, kaun kaun competitor hai?")
    assert "मेरे पास नहीं" not in r.bot.text and any("dead end" in w for w in r.warnings)


async def test_manager_request_gets_real_escalation_not_more_pitch(repo):
    svc = CallService(repo, PersonaGenerator(EvidenceBook.empty()), MemorySessionStore(), OfflineSpeechAI())
    s, _ = await svc.start("1001", voice_gender="male")
    await svc.seller_turn(s.session_id, "Haan bolo")
    r = await svc.seller_turn(s.session_id, "Mujhe aapse baat nahi karni, aap apne manager ko bula ke lao")
    p = r.session.persona
    assert r.move == "handoff" and "senior manager" in r.bot.text and "meeting" not in r.bot.text.lower()
    assert p.language.formality == "formal" and p.voice.pace <= 0.95 and p.tone.strategy == "handoff"
    assert p.voice.speaker == s.persona.voice.speaker                       # same voice: no pretend new person
    r = await svc.seller_turn(s.session_id, "hmm")
    assert "meeting" not in r.bot.text.lower() and "senior manager" in r.bot.text
    r = await svc.seller_turn(s.session_id, "Theek hai kal 5 baje call karwa dijiye")
    assert r.session.outcome == Outcome.callback and "manager" in r.session.meeting_slot and "5 PM" in r.session.meeting_slot


async def test_who_are_you_gets_name_and_bot_question_gets_honest_answer(repo):
    svc = CallService(repo, PersonaGenerator(EvidenceBook.empty()), MemorySessionStore(), OfflineSpeechAI())
    s, _ = await svc.start("1001", voice_gender="male")
    r = await svc.seller_turn(s.session_id, "Aap kaun bol rahe ho?")
    assert "Arjun" in r.bot.text and "assistant" not in r.bot.text.lower()
    r = await svc.seller_turn(s.session_id, "Aap manager ho ya assistant?")
    assert "AI assistant Arjun" in r.bot.text and "का AI" in r.bot.text


async def test_regression_llm_cannot_veto_a_counted_language_switch(repo):
    # Screenshot: English persona, seller answered "Abhi busy hoon, baad mein call karna" and the bot stayed
    # in English because the LLM said language=en-IN (it echoed the persona) and the rule switch was dropped.
    fake = FakeSpeech(reply="Okay, I can understand. Would you prefer a call back at 11 AM tomorrow?", language="en-IN",
                      translation="जी, समझ सकती हूँ। कल सुबह 11 बजे call करूँ?")
    svc = CallService(repo, PersonaGenerator(EvidenceBook.empty()), MemorySessionStore(), fake)
    s, _ = await svc.start("1001")
    await svc.seller_turn(s.session_id, "Please speak in English")
    r = await svc.seller_turn(s.session_id, "Abhi busy hoon, baad mein call karna")
    assert r.session.persona.language.code == "hi-IN" and r.bot.language_code == "hi-IN"
    assert not r.bot.text.isascii()                                   # the English LLM reply was translated
