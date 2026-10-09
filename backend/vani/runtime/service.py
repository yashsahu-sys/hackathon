"""CallService: one place that runs a call turn, for every channel.

  web channel:          audio/text in -> STT -> signals -> adapt -> policy -> LLM -> TTS -> audio out
  sarvam_agent channel: text in (from the agent's tool call) -> signals -> adapt -> policy -> directives out
                        (the Sarvam agent does its own STT/LLM/TTS; we are its brain for persona switching)
"""
import logging
import re
import time
import uuid
from dataclasses import dataclass, field

from vani.data.repository import SellerRepository
from vani.domain.live import (CallSession, CallStatus, Channel, Outcome, Role, Signal, SignalType, SwitchEvent,
                              TurnRecord)
from vani.domain.persona import PersonaSpec
from vani.integrations.sarvam.client import SarvamError, SpeechAI
from vani.live.adapter import MIN_CONFIDENCE, PersonaAdapter
from vani.evidence.global_context import render_seller_brief
from vani.live.brain import BrainResult, LLMBrain, contextual_merge
from vani.live.llm_assist import LLMSignalAssist, merge
from vani.live.signals import SignalDetector
from vani.persona.generator import PersonaGenerator
from vani.persona.prompt import agent_variables, system_prompt
from vani.speech.language_guard import ensure_language
from vani.speech.tts_text import for_bulbul
from vani.text.gender import detect_seller_gender
from vani.text.slots import Slot, parse_slot, render, suggest, unavailable_days

from .dialogue import Move, next_move
from .store import SessionStore

log = logging.getLogger(__name__)
BANNED = re.compile(r"(?<![ऀ-ॿ])(यार|अरे|देखो)(?![ऀ-ॿ])")
CLAIMS_BOOKED = re.compile(r"fix (है|हो गई|हो गयी|kar di|ho gayi|ho gai)|meeting (fix|pakki|confirm)\w* (है|ho|hai)|"
                           r"confirmed|पक्की|पक्का|booked|book (kar|ho) (di|diya|gayi)", re.I)
TEMPLATE_ONLY = {"meeting_confirm", "end_close", "dnc_close", "close_no"}   # outcome lines are never improvised


class NotFound(LookupError):
    pass


class CallClosed(RuntimeError):
    pass


@dataclass
class BotUtterance:
    text: str
    language_code: str
    speaker: str
    pace: float
    temperature: float = 0.6
    audio_b64: str | None = None
    source: str = "template"     # template | llm


@dataclass
class TurnResult:
    session: CallSession
    seller_text: str
    signals: list[Signal]
    switches: list[SwitchEvent]
    bot: BotUtterance
    move: str
    warnings: list[str] = field(default_factory=list)


class CallService:
    def __init__(self, repo: SellerRepository, generator: PersonaGenerator, store: SessionStore, speech: SpeechAI,
                 detector: SignalDetector | None = None, adapter: PersonaAdapter | None = None,
                 llm_brain: bool = True, tts_transliterate: bool = False, global_context: str = ""):
        self.repo, self.gen, self.store, self.speech = repo, generator, store, speech
        self.brain = LLMBrain(speech, global_context) if llm_brain else None
        self._ctx_cache: dict = {}
        self.assist = None if llm_brain else LLMSignalAssist(speech)
        self.tts_transliterate = tts_transliterate
        self.detector = detector or SignalDetector()
        self.adapter = adapter or PersonaAdapter()
        self._t0: dict[str, float] = {}

    # ------------------------------------------------------------ personas
    def persona_for(self, glid: str, voice_gender: str | None = None) -> tuple[PersonaSpec, object]:
        ctx = self.repo.get_context(glid)
        if ctx is None:
            raise NotFound(f"seller {glid} not found")
        return self.gen.generate(ctx, voice_gender), ctx.profile

    # --------------------------------------------------------------- calls
    async def start(self, glid: str, channel: Channel = Channel.web, speak: bool = True,
                    voice_gender: str | None = None) -> tuple[CallSession, BotUtterance]:
        persona, _ = self.persona_for(glid, voice_gender)
        sid = uuid.uuid4().hex[:12]
        session = CallSession(session_id=sid, seller_glid=glid, channel=channel, persona=persona, initial_persona=persona)
        self._t0[sid] = time.monotonic()
        bot = BotUtterance(text=persona.plan.opening, language_code=persona.language.code,
                           speaker=persona.voice.speaker, pace=persona.voice.pace, temperature=persona.voice.temperature)
        warnings: list[str] = []
        if speak and channel == Channel.web:
            await self._speak(session, bot, warnings)
        self._record_bot(session, bot.text)
        self.store.save(session)
        return session, bot

    async def seller_turn(self, session_id: str, text: str | None = None, audio: bytes | None = None,
                          speak: bool = True) -> TurnResult:
        session = self._load(session_id)
        warnings: list[str] = []
        stt_lang = None
        if audio is not None:
            stt = await self.speech.stt(audio)          # errors propagate: the caller should ask to repeat
            text, stt_lang = stt["transcript"], stt.get("language_code")
        text = (text or "").strip()
        if not text:
            raise ValueError("empty seller turn")

        seller_texts = [t.text for t in session.transcript if t.role == Role.seller]
        signals = self.detector.detect(text, session.persona.language.code, stt_lang, seller_texts[-3:])
        rule_agreed = any(x.type == SignalType.agreement for x in signals)
        brain: BrainResult | None = None
        if self.brain is not None and self.brain.enabled:
            ctx = self._context(session.seller_glid)
            switch_to = next((x.detail.get("to") for x in signals
                              if x.type == SignalType.language_switch and x.confidence >= 0.75), None)
            brain = await self.brain.think(session, ctx, text, [x.type.value for x in signals], render_seller_brief(ctx),
                                           switch_to)
            if brain is None:
                warnings.append("LLM brain unavailable: rules only this turn")
            else:
                signals, notes = contextual_merge(signals, brain, text, session.persona.language.code)
                warnings += notes
        elif self.assist is not None and self.assist.enabled:
            last_bot = next((t.text for t in reversed(session.transcript) if t.role == Role.bot), "")
            signals, notes = merge(signals, await self.assist.classify(text, last_bot), text)
            warnings += notes
        gender, gconf, words = detect_seller_gender(seller_texts + [text])
        if gender != "unknown" and gender != session.persona.language.seller_gender:
            signals.append(Signal(type=SignalType.seller_gender, confidence=gconf, trigger=words, detail={"gender": gender}))

        new_unavailable = self._update_slots(session, text, signals, brain, rule_agreed)
        session.transcript.append(TurnRecord(role=Role.seller, text=text, language=stt_lang, at_ms=self._now(session),
                                             persona_version=session.persona.version, signals=signals))
        switches = self.adapter.adapt(session, signals, self._now(session))
        if switches:
            session.switch_log.extend(switches)
            session.strategy_used = None

        types = {s.type for s in signals if s.confidence >= MIN_CONFIDENCE}
        move = next_move(session, text, types, session.strategy_used, new_unavailable)
        self._apply_move(session, move, types)

        bot = BotUtterance(text=move.text, language_code=session.persona.language.code,
                           speaker=session.persona.voice.speaker, pace=session.persona.voice.pace,
                           temperature=session.persona.voice.temperature)
        offered = move.offered
        if move.key not in TEMPLATE_ONLY and self.speech.enabled:
            reply = None
            if brain is not None:
                reply = self._accept(brain.reply, session, warnings)
                if reply:
                    said = brain.offered or parse_slot(reply)
                    offered = [said] if said and said.complete else []
            elif session.channel == Channel.web and self.brain is None:
                reply = await self._llm_phrase(session, move, warnings)
            if reply:
                bot.text, bot.source = reply, "llm"
        if self.speech.enabled:
            # The reply must be in the language the persona speaks NOW (after this turn's switch).
            fixed = await ensure_language(bot.text, session.persona, self.speech, warnings)
            if fixed is None:
                bot.text, bot.source, offered = move.text, "template", move.offered
                bot.text = await ensure_language(bot.text, session.persona, self.speech, warnings) or bot.text
            else:
                bot.text = fixed
        session.offered_slots += [o.to_dict() for o in offered if o.to_dict() not in session.offered_slots]
        if session.channel == Channel.web and self.speech.enabled:
            bot.text = await for_bulbul(bot.text, session.persona, self.speech, self.tts_transliterate, warnings)
        if speak and session.channel == Channel.web:
            await self._speak(session, bot, warnings)
        self._record_bot(session, bot.text)
        if move.end_call:
            session.status = CallStatus.ended
        self.store.save(session, switches)
        return TurnResult(session, text, signals, switches, bot, move.key, warnings)

    # -------------------------------------------------------- call state
    def _context(self, glid: str):
        if glid not in self._ctx_cache:
            ctx = self.repo.get_context(glid)
            if ctx is None:
                raise NotFound(f"seller {glid} not found")
            self._ctx_cache[glid] = ctx
        return self._ctx_cache[glid]

    @staticmethod
    def _update_slots(session: CallSession, text: str, signals: list[Signal], brain: BrainResult | None,
                      rule_agreed: bool = False) -> set[str]:
        """Track days ruled out and resolve the slot the seller agreed to (their time beats ours)."""
        cannot = unavailable_days(text) | (brain.cannot if brain else set())
        new = cannot - set(session.unavailable_days)
        session.unavailable_days += sorted(new)
        unavailable = set(session.unavailable_days)
        offered = [Slot.from_dict(d) for d in session.offered_slots]
        said = (brain.seller_slot if brain and brain.seller_slot else None) or parse_slot(text)

        types = {s.type for s in signals}
        if SignalType.agreement in types and brain is None and not offered and not said:
            # rules only: "haan ji" before any slot was offered is not agreeing to a meeting
            signals[:] = [s for s in signals if s.type != SignalType.agreement]
            return new
        if SignalType.agreement not in {s.type for s in signals}:
            return new
        cand = (brain.agreed_slot if brain and brain.agreed_slot else None) or said
        last = offered[-1] if offered else None
        if cand is None and last is not None and (brain is None or rule_agreed):
            # "haan theek hai" right after an offer = that offer. With the LLM on, only when the
            # rules ALSO heard a yes: an LLM-only "agree" with no slot never books by itself.
            cand = Slot(last.day, last.hour)
        if cand is not None:
            if cand.day is None:
                match = next((o for o in reversed(offered) if o.hour == cand.hour), None)
                ref = match or last
                cand.day = ref.day if ref else suggest(unavailable)[0].day   # first day they haven't ruled out
            if cand.hour is None:
                match = next((o for o in reversed(offered) if o.day == cand.day), None)
                cand.hour = match.hour if match else None
            if cand.day in unavailable:
                cand = None
        session.agreed_slot = cand.to_dict() if cand and cand.complete else None
        return new

    def end(self, session_id: str, outcome: Outcome | None = None) -> CallSession:
        session = self._load(session_id, allow_ended=True)
        session.status = CallStatus.ended
        if outcome:
            session.outcome = outcome
        elif session.outcome == Outcome.unknown:
            session.outcome = Outcome.dropped
        self.store.save(session)
        return session

    def agent_directives(self, session: CallSession, move: str | None = None) -> dict:
        """What a Sarvam agent needs after each tool call: the (possibly switched) persona as variables."""
        profile = self.repo.get_profile(session.seller_glid)
        v = agent_variables(session.persona, profile)
        v["persona_version"] = str(session.persona.version)
        v["next_move"] = move or ""
        v["call_status"] = session.status.value
        v["agreed_slot"] = render(Slot.from_dict(session.agreed_slot), "english") if session.agreed_slot else ""
        v["seller_unavailable"] = ", ".join(session.unavailable_days)
        return v

    # ------------------------------------------------------------ internals
    def _load(self, session_id: str, allow_ended: bool = False) -> CallSession:
        s = self.store.get(session_id)
        if s is None:
            raise NotFound(f"session {session_id} not found")
        if s.status == CallStatus.ended and not allow_ended:
            raise CallClosed(f"session {session_id} has ended")
        self._t0.setdefault(session_id, time.monotonic() - (s.transcript[-1].at_ms / 1000 if s.transcript else 0))
        return s

    def _now(self, s: CallSession) -> int:
        return int((time.monotonic() - self._t0.get(s.session_id, time.monotonic())) * 1000)

    @staticmethod
    def _apply_move(session: CallSession, move: Move, types: set) -> None:
        if move.key in ("handoff", "direct", "reassure", "rush", "clarify", "close"):
            session.strategy_used = session.persona.tone.strategy
        if SignalType.refusal in types and move.key not in ("meeting_confirm",):
            session.refusals += 1
        session.stage = move.stage
        if move.outcome:
            session.outcome = move.outcome
        if move.key == "call_later" and session.outcome == Outcome.unknown:
            session.outcome = Outcome.callback
        if move.outcome == Outcome.meeting_fixed and session.agreed_slot:
            session.meeting_slot = render(Slot.from_dict(session.agreed_slot), "english")

    def _record_bot(self, session: CallSession, text: str) -> None:
        session.transcript.append(TurnRecord(role=Role.bot, text=text, language=session.persona.language.code,
                                             at_ms=self._now(session), persona_version=session.persona.version))

    @staticmethod
    def _accept(reply: str, session: CallSession, warnings: list[str]) -> str | None:
        """Guardrails on an LLM-written reply; None -> use the policy's template line."""
        if not reply or not reply.strip():
            return None
        if BANNED.search(reply):
            warnings.append("LLM reply rejected by guardrail filter (banned filler); template used")
            return None
        if CLAIMS_BOOKED.search(reply) and session.outcome != Outcome.meeting_fixed:
            warnings.append("LLM reply claimed a booked meeting that the policy did not confirm; template used")
            return None
        said = parse_slot(reply)
        if said and said.day and said.day in session.unavailable_days:
            warnings.append(f"LLM reply offered {said.day}, which the seller ruled out; template used")
            return None
        return reply

    async def _speak(self, session: CallSession, bot: BotUtterance, warnings: list[str]) -> None:
        if not self.speech.enabled:
            return
        p = session.persona
        try:
            bot.audio_b64 = await self.speech.tts(bot.text, p.language.code, p.voice.speaker, p.voice.pace, p.voice.pitch,
                                                  p.voice.temperature)
        except SarvamError as exc:
            warnings.append(f"TTS failed, browser voice fallback: {exc}")

    async def _llm_phrase(self, session: CallSession, move: Move, warnings: list[str]) -> str | None:
        profile = self.repo.get_profile(session.seller_glid)
        messages = [{"role": "system", "content": system_prompt(session.persona, profile)}]
        for t in session.transcript[-8:]:
            messages.append({"role": "assistant" if t.role == Role.bot else "user", "content": t.text})
        messages[-1]["content"] += f"\n\n[Next move, do not read aloud: {move.hint} Reference line: {move.text}]"
        try:
            out = await self.speech.chat(messages)
        except SarvamError as exc:
            warnings.append(f"LLM failed, template used: {exc}")
            return None
        out = re.sub(r"[*_#`>\[\]]", "", out).replace("\n", " ").strip()
        if not out or BANNED.search(out):
            warnings.append("LLM reply rejected by guardrail filter; template used")
            return None
        limit = session.persona.tone.max_words_per_turn * 2
        words = out.split()
        return " ".join(words[:limit]) if len(words) > limit else out
