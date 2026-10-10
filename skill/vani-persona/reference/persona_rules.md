# Persona rules: every field, its inputs and thresholds

Source of truth: `backend/vani/persona/generator.py`. Each decision is stored with
`value · reason · source · confidence · evidence_ids`.

| Field | Inputs | Rule |
|---|---|---|
| `language.style` / `code` | past transcripts, past summaries, state | Seller spoke English on a past call, or a summary says they wanted English → English. Spoke Gujarati → Gujarati. Another regional language → regional. Tamil Nadu / Telangana / AP / Karnataka / Kerala with no transcript → simple English. State unknown → Hinglish (default). Else Hinglish (evidence: 99% of 419 transcribed calls answered in Hinglish). |
| `language.formality` | turnover band, legal type, business age, kind | Mid/large turnover, Limited company or 15+ years → formal. New micro retailer → casual. Else neutral. |
| `language.english_mix` | style, size, confusion segment | English 1.0; Hinglish 0.3, 0.45 for large firms, 0.15 if the seller's segment is confusion-prone. |
| `language.address_as` | seller gender (from their own verbs), style, formality | Known gender → सर / मैडम (Sir / Ma'am). Unknown → "जी" / "you" / "Sir/Madam" (formal English). Never guesses gender from a name. |
| `voice.gender` / `speaker` | operator choice, register, language, TTS model | Payal (female) by default, Arjun on request; speaker chosen per register and language (native voices for Gujarati, Tamil, etc.). |
| `voice.pace` | rush history, segment evidence, state, age, past speech rate | Base 1.0. Rush history (≥2 callbacks, past "busy" objection, ≥60% dropped, avg answered call <15 s) +0.12; rush-elevated segment +0.08; past speech ≥3.4 words/s +0.06; non-Hindi state, confusion-prone segment, veteran business or past speech ≤1.8 words/s −0.1. Clamped 0.8–1.4. |
| `voice.temperature` | formality, empathy | casual 0.7 · neutral 0.6 · formal 0.5; ≤0.55 when empathy is high (friction history). |
| `tone.warmth / empathy / energy` | past frustration, not-interested, rush | Friction history → empathy high; rush → energy high, fewer words. |
| `tone.max_words_per_turn` | rush, pace | 16 for rush-prone, 25 default, shorter when slower. |
| `plan.opening` | new seller, rush, talked before, last call, enquiries | New seller → welcome. Rush-prone & never talked → one breath. Talked before → picks up the last call: asked for callback / call cut short (<15 s) / said not interested / met → matching line; else generic follow-up. Enquiries in 90 days → their number. Else "buyers in {city} search {category}". Openings always state the purpose (evidence TRN-opening_length). |
| `plan.objection_playbook` | past objections, dispositions, questions | Answers for the seller's own past objections first (busy, price, trust, already in touch...). |
| `plan.benefit_facts` | seller's enquiries, category group benchmarks | Top-10% enquiries and buyer calls in the seller's category group (≥30 sellers, else all sellers) vs the seller's own number. The only numbers VANI may quote. |
| Line phrasing | seller glid | 2–3 phrasings per key line; picked per seller, rotated if a move repeats in a call. |
