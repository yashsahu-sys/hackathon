# VANI Persona Engine (Voice AI Hackathon 2.0, PS04: Persona Design)

> We don't write personas. We built the system that writes one per seller from their data, backs every choice with evidence from 9,657 real VANI calls, and rewrites it mid-call when the seller's behaviour changes.

## Architecture

```
                 ┌──────────────── offline (batch) ────────────────┐
 IndiaMART CSVs ─┤ data/warehouse.py  →  DuckDB warehouse           │
 (data/private)  │ evidence/miner.py  →  evidence.json (140 findings)│
                 └──────────────────────────────────────────────────┘
                                     │
 seller glid ──> persona/generator.py ──> PersonaSpec (voice, language, tone, plan; reason + confidence per field)
                                     │
        ┌────────────────────────────┴───────────────────────────┐
  web runtime (our UI)                                Sarvam Samvaad agent (phone/web)
  Saaras STT → signals → adapter → policy → LLM → Bulbul    agent → tool analyze_turn → signals → adapter → policy
        └──────────────── runtime/service.py (one CallService) ─┘
                                     │
                     SQLite: sessions + switch log  →  /api/v1/switch-log
```

| Layer | Code | Notes |
|---|---|---|
| Domain | `vani/domain/` | Typed models: SellerProfile, PersonaSpec + Decision, Signal, SwitchEvent, CallSession |
| Data | `vani/data/` | Normaliser (state→language, turnover bands, disposition parsing, missing-field flags), DuckDB warehouse, repository interface |
| Evidence | `vani/evidence/` | Call features from AI summaries + transcripts; outcome drivers, segment risks (Bonferroni, Wilson CI), bot-version variants; EvidenceBook query API |
| Persona | `vani/persona/` | Generator (seller history > evidence > rule > default), voices, bilingual lines, LLM/agent prompt rendering, distinctness metric |
| Live | `vani/live/` | Signal detector calibrated on real seller turns, adapter (threshold, cooldown, priorities), offline evaluation |
| Runtime | `vani/runtime/` | Dialogue policy, CallService, session stores (SQLite/memory) |
| Sarvam | `vani/integrations/sarvam/` | Async client (Saaras, Bulbul, sarvam-105b), agent prompt template |
| API | `vani/api/` | FastAPI `/api/v1/*` incl. agent tools |

Scaling: the API is stateless (state lives in the session store); repository, store and speech client sit behind interfaces, so DuckDB→Postgres, SQLite→Redis or a second STT/TTS vendor are drop-in. Evidence mining is a batch job; persona generation is pure and fast (~5k sellers/40 s including DB reads).

## Run

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env                    # add SARVAM_API_KEY
# put the dataset CSVs in data/private/raw/gc/ (gitignored)
python -m vani.data.warehouse           # CSV -> DuckDB
python -m vani.evidence.miner           # -> data/private/evidence.json
python -m vani.tools.smoke              # check Sarvam STT/TTS/LLM with your key
python -m uvicorn vani.api.app:app --port 8000   # API docs: http://localhost:8000/docs
```

Other tools:
```bash
python -m vani.live.evaluate            # detector precision/recall on real transcripts
python -m vani.tools.export --sample 50 # persona specs + 3 contrasting demo sellers -> data/private/out
python -m vani.tools.voice_audition     # every Bulbul voice x pace, to pick voices by ear
python -m pytest -q                     # 220 tests (real-data tests auto-skip without the dataset)
```

Sarvam agent setup: [docs/SARVAM_AGENT_SETUP.md](docs/SARVAM_AGENT_SETUP.md).

## What the evidence says (real data: 9,657 answered VANI calls, 11.2% meeting rate)

- 46% of answered calls end within 20 s, and only 2 of those 4,486 fixed a meeting. **The opening decides the call.**
- The bot version that references the seller's last interaction loses **39.5%** of calls in the first 20 s vs **47.3%** for the main bot (side-by-side variant, strong). → history-led openings.
- Bare openings ("Hello?", identity check only) drop more than openings that state the purpose (18.2% vs 11.6%, moderate).
- Calls where the seller got **confused** fixed 2.6% meetings; **busy** 5.0%; asked **"are you a bot?"** 2.7%; vs 11.3% otherwise. → these are the live switch triggers.
- Talking **price** (19.6%) and **visit/location** (62.6%) go with meetings. → pivot to the visit.
- 99% of transcribed sellers answer in Hinglish. → Hinglish default, switch only when the seller does.

## Honesty about evidence (PS04 §3.4)

Every persona field carries `source` (seller_data / evidence / rule / default / live_signal) and `confidence` (strong / moderate / weak / informed_guess / default / live).

- VANI used one persona for everyone, so "pace X beats pace Y" can't be measured directly. We measure behaviours that kill meetings, which segments show them, and real script variants; the generator marks everything else as an informed guess.
- Signal detector precision/recall is scored against keyword tags on AI summaries (noisy, call-level), and the lexicon was tuned on the same calls, so treat those numbers as optimistic.
- Voice gender: no evidence either way (one voice in production), kept VANI's female voice and said so.
- Pitch: only `bulbul:v2` supports it; the spec carries a target that v3 ignores.

## Data privacy

Raw data, the warehouse, evidence, sessions and exports live in `data/private/` (gitignored). Test fixtures use the real column headers with invented rows; test phrases are paraphrased.
