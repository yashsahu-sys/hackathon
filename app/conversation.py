"""One call: persona + transcript + switch log, and the bot's next turn."""
import re
import time
import uuid

from . import config
from .adapter import adapt
from .evidence import EvidenceStore
from .persona import generate_persona, system_prompt
from .sarvam import SarvamClient, SarvamError
from .signals import detect
from .templates import fill, lines_for

OBJECTION_PATTERNS = {
    "already_other_platform": r"tradeindia|justdial|alibaba|already (on|listed)|पहले से|pehle se|dusre portal|दूसरे portal",
    "cost": r"paisa|paise|पैसे|charge|cost|fees?|kitna (lagega|padega)|कितना (लगेगा|पड़ेगा)|kharcha|खर्चा|price",
    "roi": r"\broi\b|return|fayda|फ़ायदा|फायदा|kya milega|क्या मिलेगा|benefit",
    "send_whatsapp": r"whatsapp|व्हाट्सऐप|व्हाट्सएप|message kar|bhej do details|details bhej",
    "think_later": r"soch(ke| ke| kar)|सोच(के| के| कर)|think about|let me think|baad me batata|बाद में बताता",
}


class Session:
    def __init__(self, seller: dict, evidence: EvidenceStore, client: SarvamClient | None):
        self.id = uuid.uuid4().hex[:10]
        self.seller = seller
        self.client = client
        self.started_at = time.time()
        self.persona = generate_persona(seller, evidence)
        self.persona_history = [self._snapshot()]
        self.transcript: list[dict] = []
        self.switch_log: list[dict] = []
        self.last_fired: dict = {}
        self.stage = "opening"       # opening -> pitch -> ask -> done
        self.refusals = 0
        self.meeting = None
        self.strategy_used = None    # each switch's strategy line is spoken once, not every turn
        self.warnings: list[str] = []

    @property
    def live(self) -> bool:
        return bool(self.client and self.client.enabled)

    def _snapshot(self) -> dict:
        return {k: v for k, v in self.persona.items() if not k.startswith("_")}

    def _say(self, text: str) -> dict:
        entry = {"role": "bot", "text": text, "lang": self.persona["language"]["code"],
                 "at_s": round(time.time() - self.started_at, 1), "persona_version": self.persona["version"]}
        self.transcript.append(entry)
        audio = self._tts(text)
        return {"text": text, "audio_b64": audio, "voice": dict(self.persona["voice"]),
                "language_code": self.persona["language"]["code"]}

    def _tts(self, text: str) -> str | None:
        if not self.live:
            return None
        v = self.persona["voice"]
        try:
            return self.client.tts(text, self.persona["language"]["code"], v["speaker"], v["pace"], v["temperature"])
        except SarvamError as exc:
            self.warnings.append(f"TTS failed, browser voice used: {exc}")
            return None

    def open(self) -> dict:
        text = self.persona["plan"]["opening"]
        if self.live and self.persona["language"]["style"] == "regional":
            text = self._llm_turn("Open the call now with a one-sentence greeting and the reason for calling.") or text
        return self._say(text)

    def transcribe(self, audio: bytes) -> dict:
        return self.client.stt(audio)

    def seller_turn(self, text: str, stt_language: str | None = None) -> dict:
        turn = sum(1 for t in self.transcript if t["role"] == "seller")
        signals = detect(text, self.persona["language"]["code"], stt_language, self.transcript)
        self.transcript.append({"role": "seller", "text": text, "lang": stt_language,
                                "at_s": round(time.time() - self.started_at, 1),
                                "signals": [s.to_dict() for s in signals]})
        self.persona, events = adapt(self.persona, self.seller, signals, turn, self.last_fired, self.started_at)
        if events:
            self.switch_log.extend(events)
            self.persona_history.append(self._snapshot())
            self.strategy_used = None

        reply = self._next_line(text, {s.type for s in signals if s.confidence >= 0.6})
        bot = self._say(reply)
        return {
            "seller_text": text,
            "signals": [s.to_dict() for s in signals],
            "switches": events,
            "persona": self._snapshot(),
            "bot": bot,
            "stage": self.stage,
            "meeting": self.meeting,
            "warnings": self.warnings[-3:],
        }

    # --- dialogue policy ---------------------------------------------------
    def _next_line(self, text: str, types: set) -> str:
        lines = lines_for(self.persona["language"]["style"])
        ctx = self.persona["_ctx"]
        plan = self.persona["plan"]
        strategy = self.persona["tone"]["strategy"]
        asked = self.stage == "ask"

        if self.stage == "done":
            return fill(lines["close_no"], ctx) if not self.meeting else fill(lines["meeting_confirm"], ctx)
        if "agreement" in types and (asked or re.search(r"\b\d{1,2}\s*(baje|bje|am|pm|बजे)", text, re.I)):
            self.meeting = {"slot": "tomorrow 11:00", "fixed_at_s": round(time.time() - self.started_at, 1)}
            self.stage = "done"
            return self._phrase(fill(lines["meeting_confirm"], ctx),
                                "The seller agreed. Confirm the meeting for tomorrow 11 AM in one sentence and thank them.")
        if "refusal" in types:
            self.refusals += 1
            if self.refusals >= 2:
                self.stage = "done"
                return self._phrase(fill(lines["close_no"], ctx), "Seller refused twice. Thank them and end the call.")
            return self._phrase(plan["objection_playbook"].get("not_interested", plan["meeting_ask"]),
                                "Seller said not interested once. Use the not_interested answer, then ask for the meeting.")

        objection = next((k for k, p in OBJECTION_PATTERNS.items() if re.search(p, text, re.I)), None)
        if objection and objection in plan["objection_playbook"]:
            self.stage = "ask"
            line = plan["objection_playbook"][objection] + " " + plan["meeting_ask"]
            return self._phrase(line, f"Seller raised '{objection}'. Answer with the playbook, then ask for the meeting.")

        hint_by_strategy = {
            "handoff": ("human_handoff", "Seller wants a person. Offer an executive callback tomorrow 11 AM."),
            "direct": ("direct", "Seller is irritated. One short apology-free line: free 20-min visit, ask for tomorrow 11 AM."),
            "rush": ("rush_ask", "Seller is busy. Ask them to pick: tomorrow 11 AM or 5 PM. One sentence."),
            "clarify": ("clarify", "Seller is confused. Explain in very simple words with a concrete example."),
            "close": ("interest_close", "Seller is interested. Answer briefly and propose tomorrow 11 AM."),
        }
        last_bot = next((t["text"] for t in reversed(self.transcript) if t["role"] == "bot"), "")
        if strategy in hint_by_strategy and strategy != self.strategy_used:
            key, hint = hint_by_strategy[strategy]
            self.strategy_used = strategy
            self.stage = "pitch" if strategy == "clarify" else "ask"
            return self._phrase(fill(lines[key], ctx), hint)

        if self.stage == "opening":
            self.stage = "pitch"
            return self._phrase(plan["pitch"], "Give the value pitch in one or two sentences.")
        self.stage = "ask"
        line = plan["meeting_ask"] if plan["meeting_ask"] != last_bot else fill(lines["direct"], ctx)
        return self._phrase(line, "Ask for the meeting: tomorrow 11 AM, 20 minutes, free.")

    def _phrase(self, template_line: str, hint: str) -> str:
        """Live: let the LLM say it in the persona's voice. Offline / on error: the template line."""
        if not self.live:
            return template_line
        return self._llm_turn(f"{hint} Reference line you may adapt: {template_line}") or template_line

    def _llm_turn(self, instruction: str) -> str | None:
        messages = [{"role": "system", "content": system_prompt(self.persona, self.seller)}]
        for t in self.transcript[-8:]:
            messages.append({"role": "assistant" if t["role"] == "bot" else "user", "content": t["text"]})
        if messages[-1]["role"] != "user":
            messages.append({"role": "user", "content": "(seller is listening)"})
        messages[-1]["content"] += f"\n\n[Instruction for your next turn, do not read aloud: {instruction}]"
        try:
            out = self.client.chat(messages)
            return out or None
        except SarvamError as exc:
            self.warnings.append(f"LLM failed, template used: {exc}")
            return None

    def summary(self) -> dict:
        return {
            "session_id": self.id,
            "seller_id": self.seller["seller_id"],
            "mode": "live" if self.live else "offline",
            "outcome": "meeting_fixed" if self.meeting else ("declined" if self.stage == "done" else "in_progress"),
            "meeting": self.meeting,
            "initial_persona": self.persona_history[0],
            "final_persona": self._snapshot(),
            "switch_log": self.switch_log,
            "transcript": self.transcript,
        }
