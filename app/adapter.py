"""Mid-call persona adaptation: signals in, new persona version + switch log out."""
import time

from .persona import _address, clone
from .signals import Signal
from .templates import LANGUAGE_NAMES, fill, lines_for

MIN_CONFIDENCE = 0.6
COOLDOWN_TURNS = 2   # same signal can't re-trigger within this many seller turns (stops flip-flopping)

# Highest wins when several signals land on the same turn.
STRATEGY_PRIORITY = ["handoff", "direct", "rush", "clarify", "close", "standard"]

REASONS = {
    "frustration": "Seller is irritated: cut the pitch, speed up, short sentences, go straight to the slot.",
    "confusion": "Seller didn't follow: slow down, simpler words, one idea per sentence, give an example.",
    "rush": "Seller is short on time: skip the pitch, offer two slot options and let them pick.",
    "interest": "Seller is leaning in: answer briefly, then propose the meeting now.",
    "human_request": "Seller wants a person: offer the executive callback, which is the call's goal anyway.",
    "language_switch": "Seller changed language: follow them, the meeting matters more than our script.",
}


def _set(persona: dict, path: str, value, changes: list):
    node = persona
    keys = path.split(".")
    for k in keys[:-1]:
        node = node[k]
    old = node.get(keys[-1])
    if old != value:
        node[keys[-1]] = value
        changes.append({"field": path, "from": old, "to": value})


def _relocalise(persona: dict, seller: dict, style: str, code: str, changes: list):
    _set(persona, "language.style", style, changes)
    _set(persona, "language.code", code, changes)
    _set(persona, "language.name", LANGUAGE_NAMES.get(code, style), changes)
    ctx = persona["_ctx"]
    ctx["addr"] = _address(seller, style, persona["language"]["formality"], persona["voice"]["gender"])
    _set(persona, "language.address_as", ctx["addr"], changes)
    lines = lines_for(style)
    persona["plan"]["pitch"] = fill(lines["pitch"] if ctx["enq"] else lines["pitch_new"], ctx)
    persona["plan"]["meeting_ask"] = fill(lines["meeting_ask"], ctx)
    persona["plan"]["objection_playbook"] = {k: fill(lines["objections"][k], ctx)
                                             for k in persona["plan"]["objection_playbook"] if k in lines["objections"]}


def adapt(persona: dict, seller: dict, signals: list[Signal], turn: int, last_fired: dict, started_at: float):
    """Returns (persona, events). `last_fired` maps signal type -> turn, mutated in place."""
    new = clone(persona)
    events = []
    for sig in signals:
        if sig.confidence < MIN_CONFIDENCE or sig.type not in REASONS:
            continue
        if sig.type != "language_switch" and turn - last_fired.get(sig.type, -99) < COOLDOWN_TURNS:
            continue
        changes: list = []
        tone, voice = new["tone"], new["voice"]
        if sig.type == "frustration":
            _set(new, "voice.pace", round(min(1.4, voice["pace"] + 0.15), 2), changes)
            _set(new, "tone.max_sentence_words", min(tone["max_sentence_words"], 10), changes)
            _set(new, "tone.energy", "calm-direct", changes)
            _set(new, "voice.temperature", 0.4, changes)
            _strategy(new, "direct", changes)
        elif sig.type == "confusion":
            _set(new, "voice.pace", round(max(0.8, voice["pace"] - 0.2), 2), changes)
            _set(new, "tone.max_sentence_words", min(tone["max_sentence_words"], 10), changes)
            _set(new, "tone.warmth", "high", changes)
            _strategy(new, "clarify", changes)
        elif sig.type == "rush":
            _set(new, "voice.pace", round(min(1.4, voice["pace"] + 0.1), 2), changes)
            _set(new, "tone.max_sentence_words", min(tone["max_sentence_words"], 10), changes)
            _strategy(new, "rush", changes)
        elif sig.type == "interest":
            _set(new, "tone.energy", "high", changes)
            _strategy(new, "close", changes)
        elif sig.type == "human_request":
            _strategy(new, "handoff", changes)
        elif sig.type == "language_switch":
            target = sig.detail["to"]
            if target == new["language"]["code"]:
                continue
            style = {"en-IN": "english", "hi-IN": "hinglish"}.get(target, "regional")
            _relocalise(new, seller, style, target, changes)
        if not changes:
            continue
        why = f"Switched mid-call (turn {turn}): seller said “{sig.trigger}”. {REASONS[sig.type]}"
        if sig.type == "language_switch":
            new["rationale"]["language"] = {"value": new["language"]["style"], "source": "live_signal", "why": why}
        elif any(c["field"] == "voice.pace" for c in changes):
            new["rationale"]["pace"] = {"value": new["voice"]["pace"], "source": "live_signal", "why": why}
        last_fired[sig.type] = turn
        new["version"] += 1
        events.append({
            "turn": turn,
            "at_s": round(time.time() - started_at, 1),
            "signal": sig.type,
            "confidence": sig.confidence,
            "trigger": sig.trigger,
            "changes": changes,
            "reason": REASONS[sig.type],
            "persona_version": new["version"],
        })
    if events:
        new["label"] = " → ".join([new["label"]] + [e["signal"].replace("_", " ") for e in events])
    return new, events


def _strategy(persona: dict, strategy: str, changes: list):
    current = persona["tone"]["strategy"]
    if STRATEGY_PRIORITY.index(strategy) <= STRATEGY_PRIORITY.index(current):
        _set(persona, "tone.strategy", strategy, changes)
