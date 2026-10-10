# Sarvam agent setup (Hybrid mode)

Our backend is the brain (persona generator, live signal detection, switch log).
A Sarvam **Samvaad** voice agent (indus.sarvam.ai → Voice Agents) handles the
phone or web call and asks our backend what to do after every seller turn.

```
seller ──voice──> Sarvam agent (Saaras STT, LLM, Bulbul TTS)
                      │  every turn: tool analyze_turn(session_id, seller words)
                      v
              our backend /api/v1/agent-tools/*  ──> signals → persona switch → switch log
                      │  returns persona_mode, language_code, pace, suggested_reply
                      v
              agent follows the {%if persona_mode == ...%} block for its next reply
```

## 1. Make the backend reachable from Sarvam

Sarvam's cloud must be able to call your laptop:

```bash
cd backend && python -m uvicorn vani.api.app:app --port 8000
cloudflared tunnel --url http://localhost:8000      # or: ngrok http 8000
```

Note the public `https://….trycloudflare.com` URL. Set `AGENT_TOOL_SECRET` in `backend/.env`.

## 2. Create the agent

1. Voice Agents → **Create agent** → blank.
2. **Instructions**: paste `backend/vani/integrations/sarvam/agent_prompt.md`.
3. **Variables → input**: add every `{{…}}` name used in the prompt: `session_id, bot_name, seller_company,
   seller_city, persona_label, language_style, language_code, formality, english_mix, warmth, empathy,
   max_words, personalisation, objection_playbook, opening_line, persona_mode, voice_gender, address_as`.
4. **Variables → output**: `persona_mode`, `language_code`, `address_as`, `call_outcome`, `meeting_slot`.
5. **Tools → add HTTP tool** `analyze_turn`:
   - `POST {PUBLIC_URL}/api/v1/agent-tools/analyze_turn`
   - Header `X-Tool-Secret: <your secret>`
   - Body: `{"session_id": "{{session_id}}", "seller_utterance": "<seller's exact words>"}`
   - Description: "Call after every seller turn, before replying. Returns persona_mode and language_code to follow."
6. **Settings**: voice = the persona's `speaker` (for a male persona call `start_call` with `"voice_gender": "male"`
   and pick a male Bulbul voice: rahul / shubh / aditya) (from `/api/v1/sellers/{glid}/persona`), pace = persona `pace`,
   turn on **Switch language during call**, allow Hindi + English (+ the seller's regional language).

## 3. Start a call for a seller

```bash
curl -X POST {PUBLIC_URL}/api/v1/agent-tools/start_call -H "X-Tool-Secret: …" \
     -H "Content-Type: application/json" -d '{"seller_glid": "<glid>"}'
```

The response has `session_id` plus every variable above. Put them into the agent's input variables
(Test agent → variables, or the outbound campaign / API call that starts the agent).

## 4. What switches where

| Change | Sarvam agent | Our web runtime |
|---|---|---|
| Strategy (direct / clarify / rush / close / reassure / handoff / end) | yes, via `persona_mode` blocks | yes |
| Language switch | yes (native toggle + `language_code`) | yes |
| Pace / speaker mid-call | only if Sarvam lets a tool change voice settings mid-call (ask the Sarvam mentors) | **yes, per turn** |
| Switch log | yes (our backend logs every analyze_turn) | yes |

If the agent can't change pace mid-call, show the pace switch in the web runtime (`/` UI) and the
strategy + language switch on the Sarvam agent. Both write to the same switch log.

## Questions to ask the Sarvam team on the floor
1. Can a tool response update agent variables directly (so `@persona_mode` is set automatically)?
2. Can voice pace/speaker change mid-call (tool or API)?
3. How do we pass input variables when starting a call (API / outbound campaign / test console)?
4. Exact HTTP tool config fields (auth header support, timeout).
