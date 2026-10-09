# skills.md: build journey

**Team:** _<team name>_ · _<member 1>_, _<member 2>_, _<member 3 (non-tech)>_
**Problem:** 4, Persona Design

## Tools used
- **Sarvam AI**: Saaras v3 STT (`codemix` mode), Bulbul v3 TTS (speaker + pace per persona), Sarvam LLM `sarvam-105b`, Sarvam Agents.
- **Claude Code**: pair-programmed the backend, evidence engine, tests and UI; read Sarvam's Python SDK to get exact API contracts when docs weren't reachable from the build machine.
- Python, FastAPI, vanilla HTML/JS, pytest.

## Key decisions

1. **Generator, not a menu of personas.** The organisers said "persona generator, not a persona". Every field is computed from data for *this* seller, and each comes with a reason, so a seller we've never seen still gets a sensible, explainable persona.
2. **Evidence first, then the seller's own history.** Segment statistics pick the defaults; a seller's own past calls override them when they are more specific (Senthil asked for English, so he gets English even though South India favours the regional language).
3. **Compare against today's bot, not against the runner-up.** The business question is "does this beat what we do now?". Comparing with the runner-up hid big wins when two good options were close.
4. **Rule-based live signals.** About 1 ms per turn, no added latency, and each switch quotes the seller's exact words. An LLM classifier would add a second or more per turn on a phone call.
5. **Cooldown on switches.** Without it the bot oscillates on every irritated sentence.
6. **Offline fallback.** Same logic with browser speech, so a network failure on stage doesn't kill the demo.

## Mistakes we caught (and fixed)
- **P-hacking.** The first evidence engine searched every narrow segment and reported a "strong" voice-gender effect that does not exist in the data. Fixed by learning the driver attribute once across all sellers. A test guards it.
- **Wrong cause for a short call.** Senthil's 52-second call was a language failure, not impatience, but we first gave him a rushed opening. Short calls now count as "impatient" only when nothing else explains them.
- **Guardrail violated by our own script.** The pitch promised to "double" enquiries while the guardrail says never promise lead numbers. Rewritten, and a test checks it.
- **Missed "yes".** "Alright, tomorrow 11 AM is fine" wasn't detected as agreement. Lexicon extended, regression test added.

## What we'd do next
- Train signal detection on real call transcripts and measure precision/recall against human labels.
- Run a live A/B test of generated personas vs today's bot (pairs with Problem 5).
- Stream STT/TTS over WebSocket to cut turn latency.

## Day log
_<fill in as you go: what you tried, what broke, what you changed>_
