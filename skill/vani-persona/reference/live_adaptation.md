# Live adaptation: signal → what changes → why

Source: `backend/vani/live/` (signals.py rules, brain.py Sarvam LLM, adapter.py changes) and
`backend/vani/runtime/` (dialogue policy, guardrails). Each change becomes a new persona version and a
switch-log entry. Confidence ≥ 0.6; most signals have a 2-turn cooldown (language, gender, slow-down,
end-call do not).

| Seller | VANI changes | Why |
|---|---|---|
| is busy ("abhi busy hoon", "jaldi batao") | pace 1.05–1.1x (never racing), ≤22 words, strategy rush: one real benefit + two slots | Busy sellers book 5% today; short = fewer words, not faster words |
| is irritated ("kitni baar call karoge") | pace 1.0x, calm voice (temp 0.35), sincere apology, strategy direct; never books | Booking an annoyed seller loses them |
| is confused / asks to slow down | pace 0.85x, clear voice, fewer English words, one idea per sentence | Confused sellers book 2.6% |
| switches language | language, voice accent and speaker follow from that turn; replies checked and translated if needed | The seller's language beats the script; an explicit request is final |
| asks for a manager / a person | formal, ≤0.95x, calm, stops pitching, books a real senior callback (outcome: callback) | It is a trust request; never argue, never pose as the manager |
| asks if VANI is a bot | honest one-line disclosure ("IndiaMART's AI assistant"), then continues | Never claim to be human |
| is curious (buyers, results, cost, process) | answers first, "anything else?"; meeting ask from the 3rd answer; fuller replies (30 words) | Sellers who ask about the visit book 62.6% |
| speaks fast / slow (measured from audio) | follows their speed (fast ≤1.1x, slow 0.9x) | Real median 2.6 words/s; fast ≥3.4, slow ≤1.8 |
| reveals gender ("bol raha hoon") | address as सर / मैडम | From their own words only |
| says "don't call" / "cut the call" | apologise and end; outcome declined | Hard rule, overrides the LLM |
| proposes a time / rules out a day | takes their time, reads it back; never re-offers a ruled-out day | Their time beats ours |

Human touches: a short acknowledgement fitting the moment (apology, "achha sawaal", "sure, in English",
thanks on the first pitch), each used once per call, varied per seller. Dead-end LLM replies
("mere paas nahi hai") are replaced by a positive line with a real benefit.
