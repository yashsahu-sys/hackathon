# Persona Generator for the IndiaMART Voice Bot

**Problem 4: Persona Design** · Voice AI Hackathon 2.0

> We did not write personas. We wrote the thing that writes personas, and it rewrites them mid-call.

Today the Voice Bot talks to every seller in one voice and one style for the whole call. This system:

1. **Generates a persona per seller before the call**: voice, pace, language, formality, opening and objection playbook, each decided from past-call evidence, with the reason and numbers attached.
2. **Adapts it live**: detects frustration, confusion, rush, interest, a language switch or a request for a human on every seller turn, and changes the persona mid-call.
3. **Logs every switch**: signal detected → what changed → why.

Built on Sarvam: **Saaras v3** (speech-to-text, `codemix` mode for Hinglish), **Sarvam LLM** (`sarvam-105b`) for the turns, **Bulbul v3** (text-to-speech, speaker + pace per persona).

## Run it

```bash
pip install -r requirements.txt
cp .env.example .env          # paste SARVAM_API_KEY (from dashboard.sarvam.ai)
python -m uvicorn app.main:app --port 8000
# open http://localhost:8000
```

Without a key it runs **offline**: same persona and switch logic, but the browser speaks the replies and does the speech recognition. Use it for development, and as a fallback if the network dies during the live demo.

```bash
python -m pytest -q            # 23 tests
python scripts/run_demo.py     # writes samples/personas/* and samples/calls/*
python scripts/backtest.py     # held-out lift vs today's bot -> samples/backtest.json
```

## How it works

```
seller.json ─┐
             ├─> Persona Generator ──> persona spec v1 (+ reason per field)
past calls ──┘   evidence.py + persona.py        │
                                                 v
 seller speaks ─> Saaras STT ─> Signal Detector ─> Adapter ─> persona v2, v3…  ──> switch log
                                 signals.py        adapter.py      │
                                                                   v
                                         Sarvam LLM (persona system prompt) ─> Bulbul TTS (speaker, pace)
```

| File | What it does |
|---|---|
| `app/evidence.py` | Learns from past calls which seller attribute drives each persona choice, then picks the option that beats today's bot for this seller's segment (two-proportion z-test). Keeps today's default when evidence is weak. |
| `app/persona.py` | Builds the persona spec. Seller's own call history overrides segment averages (e.g. a seller who asked for English gets English even though their region favours Tamil). Renders the system prompt. |
| `app/signals.py` | Rule-based detector for Hinglish in Devanagari and Roman script, English and regional scripts. About 1 ms per turn, so it adds no latency, and every signal quotes the words that fired it. |
| `app/adapter.py` | Maps signals to persona changes with a confidence threshold and a 2-turn cooldown so the bot doesn't flip-flop. |
| `app/conversation.py` | Call state, dialogue policy (pitch → ask → confirm), LLM turn with template fallback. |
| `app/sarvam.py` | REST client for Saaras, Bulbul and chat completions. |
| `web/index.html` | Demo UI: seller → persona card with reasons, live call with push-to-talk, switch log. |

## Persona spec (abridged, `samples/personas/S101.json`)

```json
{
  "label": "Quick · Hinglish · Neutral · Straight-to-the-point",
  "voice": {"gender": "female", "speaker": "ritu", "pace": 1.2, "temperature": 0.6},
  "language": {"code": "hi-IN", "style": "hinglish", "formality": "neutral", "address_as": "Rohit जी"},
  "tone": {"max_sentence_words": 12, "energy": "high", "strategy": "standard"},
  "plan": {"opening_style": "short", "opening": "Hello Rohit जी, IndiaMART से Anaya बोल रही हूँ…", "objection_playbook": {"busy": "…"}},
  "rationale": {
    "language": {"source": "segment_evidence", "why": "hinglish fixed 46% of meetings vs 31% for today's 'hindi' among [region=north] (n=365 vs 356, p=0.000)"},
    "opening": {"source": "seller_history+segment_evidence", "why": "Seller cut the last call at 38s; lead with a 1-line opening…"}
  }
}
```

## Validation

- **Held-out backtest** (`scripts/backtest.py`): train on 70% of calls, test on 30%. Compares meeting-fix rate of calls whose persona matched the generator's pick vs calls that matched today's default bot, with a bootstrap 95% CI.
- **We tested the statistics against our own mistakes.** The first version searched every narrow segment and "found" a voice-gender effect that isn't in the data. That is p-hacking. The fix: learn the driving attribute once over all sellers, and compare against today's bot rather than the runner-up. A test now guards against it (`test_evidence_does_not_invent_voice_gender_effect`).

> ⚠️ **The bundled `data/evidence/past_calls.json` is synthetic** with planted patterns (see `scripts/generate_evidence.py`). The backtest on it proves the method recovers real effects; it is **not** a business number. Drop the organisers' real call data into `data/private/past_calls.json` (same schema) and re-run `scripts/backtest.py` for the real lift.
>
> The backtest is unbiased only if past personas were assigned at random (A/B-style). On observational logs, treat it as directional and confirm with a live A/B test.

## Using real data

`data/private/` is gitignored: hackathon rules say customer data stays on premises.

- `data/private/past_calls.json`: `{"calls": [{"seller": {"region", "business_type", "age_band", "turnover_band"}, "persona": {"language_style", "pace", "formality", "opening", "voice_gender"}, "meeting_fixed": bool}]}`
- `data/private/sellers/*.json`: same shape as `data/sellers/S101.json`.

## Sarvam Agent

`POST /api/persona` (or `samples/personas/<id>_system_prompt.txt`) returns the generated system prompt. Paste it into a Sarvam Voice Agent with the persona's speaker and pace to get the Agent ID for submission.
