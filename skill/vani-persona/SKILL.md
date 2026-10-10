---
name: vani-persona
description: Build a per-seller VANI persona (voice, language, tone, conversation plan, each with a reason and past-call evidence) for an IndiaMART seller, and adapt it live during a call when the seller is busy, irritated, confused, curious, asks for a person or switches language, with a switch log. Use for PS04 Persona Design: generating personas, explaining a persona choice, simulating a call, or exporting a switch log.
---

# VANI Persona Engine

One VANI per seller: built from that seller's profile and past calls, then changed turn by turn as the
seller reacts. Every decision carries `value`, `reason`, `source` (evidence / seller_data / rule /
default / live_signal), `confidence` and `evidence_ids`.

## When to use

- "Make a persona for seller X" / "why is this seller's pace 1.12x?"
- "Simulate a call with seller X where they say ... " / "show the switch log"
- "Which past-call findings back this persona?"
- "Add a new seller who is not in the dataset"

## Setup (once)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# real data (private, never committed): put the gc_*.csv files in data/private/raw/gc/, then
python -m vani.data.warehouse && python -m vani.evidence.miner
```
Without the real data the scripts use the public demo dataset in `demo/` automatically (8 fictional
sellers, glids 90000001-90000008, plus aggregate evidence). Live link: https://hackathon-eosin-chi.vercel.app

Optional: `SARVAM_API_KEY` in `backend/.env` turns on Saaras (STT), the Sarvam LLM and Bulbul (TTS).
Without it everything still works on rules and template lines (offline mode).

## Workflows

### 1. Persona for a seller
```bash
python ../skill/vani-persona/scripts/persona.py 90000001          # summary + every decision with its reason
python ../skill/vani-persona/scripts/persona.py 90000001 --json   # full PersonaSpec
```
Read the output top-down: label, opening, then decisions. Quote the `reason` and `evidence_ids` when
explaining a choice; never invent a reason the decision does not carry.

### 2. Simulate a call and get the switch log
```bash
python ../skill/vani-persona/scripts/simulate_call.py 90000002 \
  "Yes, tell me" "Abhi busy hoon, baad mein call karna" "Matlab? Samjha nahi" "Theek hai, kal 11 baje aa jaiye"
```
Prints each seller turn, the signals detected, VANI's reply, every persona switch (signal → field
old → new → reason) and the outcome. `--json` dumps the session with the full switch log.

### 3. Live demo (voice)
```bash
python -m uvicorn vani.api.app:app --port 8001     # open http://127.0.0.1:8001
```
Live call tab: load a glid, Start call, speak (hold the mic) or type. Compare tab: openings of the three
most contrasting sellers. Evidence tab: the 140 findings.

### 4. New seller (not in the dataset)
`POST /api/v1/sellers` with state, city, categories (and optional business type, turnover, GST year,
enquiries) or the "+ New seller" form. The persona falls back to data-based defaults and a welcome opening.

## How decisions are made

See `reference/persona_rules.md` for the full table. In short:
- **Language:** what the seller spoke on past calls > a past request for English > home state
  (Tamil/Telugu/Kannada/Malayalam → simple English; Gujarat/Bengal/Punjab → native greeting + Hinglish)
  > Hinglish default (99% of transcribed sellers answered in Hinglish).
- **Pace:** rush history (callbacks, dropped calls, very short calls) → brisker; non-Hindi state,
  confusion-prone segment, veteran business, slow past speech → calmer. Never above 1.1x when busy.
- **Opening:** joined recently → welcome; rush-prone → one breath; talked before → picks up how the last
  call ended (callback asked, call cut, not interested, met); enquiries → their own numbers; else category demand.
- **Live switches:** `reference/live_adaptation.md` (signal → what changes → why).

## Guardrails (never break)

1. "Don't call me again" / "cut the call" → apologise and end. Always.
2. Book a meeting only on a clear yes with a day and a time; never book an irritated seller.
3. The seller's own time wins ("11 nahi, 5 baje" → 5 PM); never re-offer a day they ruled out.
4. Reply in the seller's current language; an explicit language request is final.
5. "Who is this?" → name + IndiaMART + reason. "Are you a bot?" → honest: IndiaMART's AI assistant.
   Never claim to be human; never pose as a manager. "Get me a manager" → formal, slower, real senior callback.
6. Quote only real numbers (the seller's enquiries, category top-10% benchmarks); never invent buyer counts.
7. No customer data in outputs that leave the machine: use glids, not names or phones, when sharing.

## Validate

```bash
cd backend && python -m pytest -q                          # 358 tests
node ../tests_e2e/ui_scenarios.js http://127.0.0.1:8001    # 17 browser scenarios (needs the real dataset)
```

## Files

- `scripts/persona.py`: persona + reasons for a glid.
- `scripts/simulate_call.py`: text call simulation with switch log.
- `reference/persona_rules.md`: every persona field, its inputs and thresholds.
- `reference/live_adaptation.md`: live signals, what they change, and why.
- `reference/evidence.md`: the headline numbers from 9,657 real calls.
- Code: `backend/vani/` (data, evidence, persona, live, runtime, speech, api). Web UI: `web/`.
