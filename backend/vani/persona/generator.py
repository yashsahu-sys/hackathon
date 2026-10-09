"""Persona generator: SellerContext + EvidenceBook -> PersonaSpec.

Precedence for every field: this seller's own history (most specific) >
segment evidence from past calls > rule of thumb > default. Each choice is a
Decision with reason, source, confidence and the evidence ids it rests on, so a
reviewer can audit it (PS04 §3.2, §3.4) and missing data degrades to
low-confidence defaults instead of failing (FAQ Q6).
"""
import hashlib
import re

from vani.domain.persona import (Confidence, ConversationPlan, Decision, LanguageSpec, PersonaSpec, Source,
                                 ToneSpec, VoiceSpec)
from vani.domain.seller import BusinessKind, SellerContext, TurnoverBand
from vani.evidence.book import EvidenceBook
from vani.evidence.miner import age_band
from vani.text.language import detect

from .lines import DISPOSITION_KEY, LINES, OBJECTION_KEY, QUESTION_KEY, REGIONAL_GREETING, lines_for
from .voices import ACCENT, BOT_NAME, clamp_pace, speaker_for

SOUTH_NON_HINDI = {"ta-IN", "te-IN", "kn-IN", "ml-IN"}
BASE_PACE = 1.0
GUARDRAILS = [
    "Personas change delivery only: never change facts, product claims, prices or compliance statements.",
    "Never claim to be human; if asked, say you are IndiaMART's virtual assistant and continue.",
    "The meeting is free; never imply payment is needed to meet.",
    "Use respectful fillers only; never 'यार', 'अरे', 'देखो'.",
    "If the seller asks not to be called, apologise, confirm, and end the call.",
]
ESCALATION = [
    "Seller asks for a person -> offer an executive callback at a fixed slot (that is the call's goal).",
    "Two frustration signals -> stop pitching, ask for one slot, close politely.",
    "Seller refuses twice -> thank and end; never push a third time.",
    "Seller says do-not-call -> confirm, apologise, end, mark do_not_call.",
]


def _evidence_reason(f: dict) -> str:
    return EvidenceBook.cite(f)


def _conf(strength: str) -> Confidence:
    return {"strong": Confidence.strong, "moderate": Confidence.moderate}.get(strength, Confidence.weak)


class PersonaGenerator:
    def __init__(self, evidence: EvidenceBook, tts_model: str = "bulbul:v3"):
        self.ev = evidence
        self.tts_model = tts_model

    # ------------------------------------------------------------------ public
    def generate(self, ctx: SellerContext) -> PersonaSpec:
        p = ctx.profile
        d: dict[str, Decision] = {}
        heard = self._seller_language_heard(ctx)

        style, code = self._language(ctx, heard, d)
        formality = self._formality(ctx, d)
        english_mix = self._english_mix(ctx, style, d)
        pace = self._pace(ctx, d)
        gender = self._voice_gender(d)
        speaker = speaker_for(gender, formality, code, self.tts_model)
        d["voice.speaker"] = Decision(
            value=speaker, source=Source.rule, confidence=Confidence.guess,
            reason=f"{self.tts_model} voice matched to {formality} register and {ACCENT.get(code, code)} accent; "
                   "chosen by ear (python -m vani.tools.voice_audition).")
        pitch = self._pitch(ctx, formality, d)
        tone = self._tone(ctx, pace, d)
        plan = self._plan(ctx, style, code, formality, gender, tone, d)

        address = "Sir/Madam" if style in ("english", "regional") and formality == "formal" else "जी"
        if style in ("english", "regional") and formality != "formal":
            address = "you"
        label = " · ".join([
            {True: "Quick", False: "Patient" if pace < BASE_PACE else "Steady"}[pace > BASE_PACE],
            {"hinglish": "Hinglish", "english": "English", "regional": f"{ACCENT.get(code, code)}-first"}[style],
            formality.capitalize(),
            {"history": "Follow-up", "enquiries": "Enquiry-led", "cold": "Category-led", "brief": "One-breath"}[
                d["plan.opening"].value],
        ])
        return PersonaSpec(
            persona_id=f"P-{p.glid}-{hashlib.sha1(label.encode()).hexdigest()[:6]}",
            seller_glid=p.glid, label=label,
            voice=VoiceSpec(gender=gender, speaker=speaker, pace=pace, pitch=pitch, accent=ACCENT.get(code, code),
                            model=self.tts_model),
            language=LanguageSpec(code=code, style=style, english_mix=english_mix, formality=formality, address_as=address),
            tone=tone, plan=plan, decisions=d,
        )

    # ------------------------------------------------------------- decisions
    def _seller_language_heard(self, ctx: SellerContext) -> str | None:
        """Language the seller actually spoke on past calls (transcripts), if clear."""
        votes: dict[str, int] = {}
        for t in ctx.turns:
            if t.speaker != "seller":
                continue
            code, conf = detect(t.text)
            if conf >= 0.6:
                votes[code] = votes.get(code, 0) + len(t.text.split())
        if not votes or sum(votes.values()) < 4:
            return None
        return max(votes, key=votes.get)

    def _language(self, ctx, heard, d) -> tuple[str, str]:
        p = ctx.profile
        summaries = " ".join(c.summary or "" for c in ctx.calls).lower()
        asked_english = bool(re.search(r"(understand|speak|prefer)\w*\s+(in\s+)?english|english (please|only)|not .*understand.* hindi", summaries))
        mix = self.ev.usable("TRN-language_mix", "moderate")
        if heard == "en-IN" or asked_english:
            why = ("Seller answered in English on a past call" if heard == "en-IN"
                   else "A past call summary says the seller wanted English")
            d["language.style"] = Decision(value="english", source=Source.seller_data, confidence=Confidence.strong,
                                           reason=f"{why}; their own history beats the regional default.")
            return "english", "en-IN"
        if heard and heard not in ("hi-IN", "en-IN"):
            d["language.style"] = Decision(value="regional", source=Source.seller_data, confidence=Confidence.strong,
                                           reason=f"Seller spoke {ACCENT.get(heard, heard)} on a past call.")
            return "regional", heard
        if p.language_code in SOUTH_NON_HINDI:
            d["language.style"] = Decision(
                value="english", source=Source.rule, confidence=Confidence.guess,
                reason=f"{p.state} is not Hindi-speaking and the seller has no transcript yet; open in simple English, "
                       f"offer {ACCENT[p.language_code]}, and let the live language switch take over.",
                evidence_ids=[mix["id"]] if mix else [])
            return "english", "en-IN"
        if "state" in p.missing_fields:
            d["language.style"] = Decision(value="hinglish", source=Source.default, confidence=Confidence.default,
                                           reason="State unknown; Hinglish is the safe default. Live switch will correct it.")
            return "hinglish", "hi-IN"
        reason = (EvidenceBook.cite(mix) if mix else "Most VANI sellers answer in Hinglish.")
        if heard == "hi-IN":
            reason = "Seller answered in Hinglish on a past call. " + reason
        d["language.style"] = Decision(value="hinglish", source=Source.evidence if mix else Source.rule,
                                       confidence=_conf(mix["strength"]) if mix else Confidence.guess,
                                       reason=reason, evidence_ids=[mix["id"]] if mix else [])
        return "hinglish", "hi-IN"

    def _formality(self, ctx, d) -> str:
        p = ctx.profile
        big = p.turnover_band in (TurnoverBand.mid, TurnoverBand.large) or (p.legal_type or "").lower().startswith("limited")
        veteran = age_band(p.business_age_years) == "veteran"
        small_retail = p.business_kind == BusinessKind.retailer and p.turnover_band == TurnoverBand.micro
        if big or veteran:
            why = []
            if big:
                why.append(f"turnover {p.turnover_raw or p.legal_type}")
            if veteran:
                why.append(f"{p.business_age_years} years in business")
            d["language.formality"] = Decision(value="formal", source=Source.rule, confidence=Confidence.guess,
                                               reason=f"Established business ({', '.join(why)}): formal register, 'aap', no slang.")
            return "formal"
        if small_retail and age_band(p.business_age_years) == "new":
            d["language.formality"] = Decision(value="casual", source=Source.rule, confidence=Confidence.guess,
                                               reason="New, small retail business: warm, everyday Hinglish (still respectful).")
            return "casual"
        missing = {"annual_turnover", "nature_of_business"} & set(p.missing_fields)
        d["language.formality"] = Decision(
            value="neutral", source=Source.default if missing else Source.rule,
            confidence=Confidence.default if missing else Confidence.guess,
            reason=("Turnover/business type missing; neutral register by default." if missing
                    else "Mid-sized or mixed signals: neutral, polite register."))
        return "neutral"

    def _english_mix(self, ctx, style, d) -> float:
        p = ctx.profile
        if style in ("english", "regional"):
            d["language.english_mix"] = Decision(value=1.0 if style == "english" else 0.3, source=Source.rule,
                                                 confidence=Confidence.guess, reason=f"Follows the {style} style.")
            return 1.0 if style == "english" else 0.3
        confused = self.ev.elevated(p, "confused")
        mix = 0.3
        reason = "Default Hinglish: Hindi sentences with common English business words (listing, buyer, meeting)."
        ids: list[str] = []
        conf = Confidence.guess
        if p.turnover_band == TurnoverBand.large or (p.legal_type or "").lower().startswith("limited"):
            mix, reason = 0.45, "Larger company: more English business vocabulary is natural."
        if confused:
            mix, reason, ids, conf = 0.15, "Fewer English words: " + _evidence_reason(confused), [confused["id"]], _conf(confused["strength"])
        d["language.english_mix"] = Decision(value=mix, source=Source.evidence if ids else Source.rule,
                                             confidence=conf, reason=reason, evidence_ids=ids)
        return mix

    def _pace(self, ctx, d) -> float:
        p, h = ctx.profile, ctx.profile.bot_history
        pace, reasons, ids, conf, source = BASE_PACE, [], [], Confidence.default, Source.default
        rush_why = self._rush_reasons(ctx)
        if rush_why:
            pace += 0.12
            reasons += rush_why
            source, conf = Source.seller_data, Confidence.moderate
            out = self.ev.usable("OUT-busy")
            if out:
                ids.append(out["id"])
        else:
            rush = self.ev.elevated(p, "busy") or self.ev.elevated(p, "early_drop")
            if rush:
                pace += 0.08
                reasons.append(_evidence_reason(rush))
                ids.append(rush["id"])
                source, conf = Source.evidence, _conf(rush["strength"])
        slow_reasons = []
        if p.language_code in SOUTH_NON_HINDI:
            slow_reasons.append("non-Hindi home state: slower, clearer delivery")
        confused = self.ev.elevated(p, "confused")
        if confused:
            slow_reasons.append(_evidence_reason(confused))
            ids.append(confused["id"])
        if age_band(p.business_age_years) == "veteran":
            slow_reasons.append(f"{p.business_age_years}-year-old business: unhurried delivery")
        if slow_reasons:
            pace -= 0.1
            reasons += slow_reasons
            if source == Source.default:
                source, conf = Source.rule, Confidence.guess
        pace = clamp_pace(pace)
        d["voice.pace"] = Decision(
            value=pace, source=source, confidence=conf, evidence_ids=ids,
            reason=("; ".join(reasons) if reasons else "No rush or confusion signals for this seller; normal pace.") +
                   f" -> {pace}x.")
        return pace

    @staticmethod
    def _rush_reasons(ctx) -> list[str]:
        """Seller-level rush evidence, thresholds set from the real distributions
        (avg answered call: quartiles 15/30/55s; 25% of sellers asked for a callback once)."""
        h = ctx.profile.bot_history
        why = []
        callbacks = h.call_later + h.dispositions.get("callback_requested", 0)
        if callbacks >= 2:
            why.append(f"asked for a callback {callbacks}x")
        if any(OBJECTION_KEY.get(k) == "busy" for k in h.objections):
            why.append("past objection: unavailable / scheduling constraints")
        drops = h.dispositions.get("call_dropped", 0)
        if drops >= 2 and h.answered and drops / h.answered >= 0.6:
            why.append(f"{drops} of {h.answered} answered calls dropped")
        if h.avg_answered_call_sec is not None and h.avg_answered_call_sec < 15 and h.answered >= 2:
            why.append(f"answered calls average {h.avg_answered_call_sec:.0f}s (shortest 25% of sellers)")
        return why

    def _voice_gender(self, d) -> str:
        f = self.ev.get("VAR-gender")   # no such evidence in VANI data: one voice was used for everyone
        d["voice.gender"] = Decision(
            value="female", source=Source.default, confidence=Confidence.default,
            reason="VANI's production voice is female ('Payal'); past calls used no other voice, so the data "
                   "can't say a different gender works better. Kept for brand continuity." if not f else EvidenceBook.cite(f))
        return "female"

    def _pitch(self, ctx, formality, d) -> float | None:
        # Pitch is only honoured by bulbul:v2; bulbul:v3 ignores it (see Sarvam SDK).
        value = {"formal": -0.1, "neutral": 0.0, "casual": 0.1}[formality]
        d["voice.pitch"] = Decision(
            value=value, source=Source.rule, confidence=Confidence.guess,
            reason=f"{'Slightly lower' if value < 0 else 'Slightly brighter' if value > 0 else 'Neutral'} pitch for a "
                   f"{formality} register. Applied only when TTS model is bulbul:v2 (v3 has no pitch control).")
        return value

    def _tone(self, ctx, pace, d) -> ToneSpec:
        p, h = ctx.profile, ctx.profile.bot_history
        empathy_why, ids = [], []
        if h.showed_frustration:
            empathy_why.append("seller showed frustration on a past call")
        if h.not_interested or h.dispositions.get("not_interested"):
            empathy_why.append("seller said not interested before")
        if h.objections.get("Call Handling / Executive Gaps"):
            empathy_why.append("seller complained about executive follow-up")
        frus = self.ev.elevated(p, "frustrated")
        if frus:
            empathy_why.append(_evidence_reason(frus))
            ids.append(frus["id"])
        empathy = "high" if empathy_why else "medium"
        d["tone.empathy"] = Decision(
            value=empathy, source=Source.seller_data if empathy_why and not ids else (Source.evidence if ids else Source.default),
            confidence=Confidence.moderate if empathy_why else Confidence.default, evidence_ids=ids,
            reason="; ".join(empathy_why) if empathy_why else "No frustration history; standard empathy.")
        warmth = "high" if (empathy == "high" or h.asked_if_bot or self.ev.elevated(p, "bot_question")) else "medium"
        d["tone.warmth"] = Decision(
            value=warmth, source=Source.rule, confidence=Confidence.guess,
            reason=("Seller asked if they were talking to a bot / needs reassurance: warmer, more human delivery."
                    if h.asked_if_bot else "Warmth follows empathy." if warmth == "high" else "Standard warmth."))
        rushy = pace > BASE_PACE
        max_words = 16 if rushy else (18 if pace < BASE_PACE else 25)
        d["tone.max_words_per_turn"] = Decision(
            value=max_words, source=Source.rule, confidence=Confidence.guess,
            reason=("Rush-prone seller: very short turns." if rushy else
                    "Slower delivery: short, simple sentences." if pace < BASE_PACE else
                    "VANI default: under 25 words per turn, one question at a time."))
        energy = "high" if rushy else ("calm" if pace < BASE_PACE else "medium")
        return ToneSpec(warmth=warmth, empathy=empathy, energy=energy, max_words_per_turn=max_words)

    def _plan(self, ctx, style, code, formality, gender, tone, d) -> ConversationPlan:
        p, h = ctx.profile, ctx.profile.bot_history
        L = lines_for(style)
        talked_before = h.answered > 0 and any((c.duration_s or 0) >= 20 for c in ctx.calls)
        enq = int(p.engagement.enquiries_90d or 0)
        rushy = bool(self._rush_reasons(ctx))
        last_met = self.ev.usable("VAR-last_met_d-early_drop", "moderate")
        bare = self.ev.usable("TRN-opening_length", "moderate")
        ids = [f["id"] for f in (last_met, bare) if f]
        if rushy and not talked_before:
            kind, why = "brief", "Rush-prone seller: one-breath opening that still says who and why."
        elif talked_before:
            kind = "history"
            why = "Seller has spoken to VANI before: reference the last conversation."
            if last_met:
                why += " " + EvidenceBook.cite(last_met)
        elif enq > 0:
            kind, why = "enquiries", f"Seller received {enq} enquiries in 90 days: lead with their own numbers."
        else:
            kind, why = "cold", "No call history or enquiries: open with demand for their category in their city."
        if bare and kind != "brief":
            why += " Openings must state purpose, not just confirm identity: " + EvidenceBook.cite(bare)
        d["plan.opening"] = Decision(value=kind, source=Source.evidence if ids and kind == "history" else Source.seller_data,
                                     confidence=_conf(last_met["strength"]) if kind == "history" and last_met else Confidence.moderate,
                                     reason=why, evidence_ids=ids)
        greet = L["greet"][formality]
        if style == "regional" or (style in ("english", "hinglish") and code in REGIONAL_GREETING):
            greet = f"{REGIONAL_GREETING.get(code, greet)}" if code in REGIONAL_GREETING else greet
        if style == "hinglish" and p.language_code in REGIONAL_GREETING:
            greet = f"{REGIONAL_GREETING[p.language_code]}, {L['greet'][formality]}"
        ctx_vars = {
            "greet": greet, "bot": BOT_NAME[gender], "city": p.city or "आपके शहर" if style == "hinglish" else (p.city or "your city"),
            "category": (p.categories[0] if p.categories else ("products" if style != "hinglish" else "products")),
            "enq": enq,
            "enq_phrase": (("1 buyer enquiry आई है" if enq == 1 else f"{enq} buyer enquiries आई हैं") if style == "hinglish"
                           else ("1 buyer enquiry" if enq == 1 else f"{enq} buyer enquiries")),
        }
        opening = L[f"opening_{kind}"].format(**ctx_vars)
        if style == "hinglish" and p.language_code in REGIONAL_GREETING:
            d["plan.greeting"] = Decision(value=greet, source=Source.seller_data, confidence=Confidence.guess,
                                          reason=f"Native greeting for a seller in {p.state} before switching to Hinglish.")

        hooks = []
        if p.categories:
            hooks.append(f"Category: {', '.join(p.categories[:2])}")
        if enq:
            hooks.append(f"{enq} enquiries in the last 90 days")
        bc, bca = p.engagement.buyer_calls_90d, p.engagement.buyer_calls_answered_90d
        if bc and bca is not None and bca < bc:
            hooks.append(f"Missed {int(bc - bca)} of {int(bc)} buyer calls in 90 days")
        if p.engagement.catalog_quality is not None and p.engagement.catalog_quality < 50:
            hooks.append(f"Catalog quality score {p.engagement.catalog_quality:.0f}: listing can improve")
        if h.in_touch_with_executive:
            hooks.append("Already in touch with an executive: position meeting as a listing review")
        if p.city:
            hooks.append(f"City: {p.city}")

        # Objection playbook: this seller's own objections first, then what most often hurts VANI calls.
        seen: list[str] = []
        sources: list[str] = []
        for label, n in sorted(h.objections.items(), key=lambda x: -x[1]):
            k = OBJECTION_KEY.get(label)
            if k and k not in seen:
                seen.append(k)
                sources.append(f"objection '{label}' x{n}")
        for disp, n in sorted(h.dispositions.items(), key=lambda x: -x[1]):
            k = DISPOSITION_KEY.get(disp)
            if k and k not in seen:
                seen.append(k)
                sources.append(f"past disposition '{disp}' x{n}")
        for q, n in sorted(h.questions.items(), key=lambda x: -x[1]):
            k = QUESTION_KEY.get(q)
            if k and k not in seen:
                seen.append(k)
                sources.append(f"asked '{q}' x{n}")
        if h.asked_if_bot and "bot_question" not in seen:
            seen.insert(0, "bot_question")
            sources.insert(0, "asked if talking to a bot")
        global_order = ["busy", "not_interested", "price", "bot_question", "call_later", "already_in_touch",
                        "other_platform", "purpose", "visit_details", "send_whatsapp", "trust", "not_ready",
                        "identity", "value", "engagement_drop", "audio_issue", "executive_gap", "wrong_contact", "mismatch"]
        order = seen + [k for k in global_order if k not in seen]
        playbook = {k: _gender_forms(L["playbook"][k], gender) for k in order if k in L["playbook"]}
        out_ids = [f["id"] for f in (self.ev.usable(x) for x in ("OUT-busy", "OUT-not_interested", "OUT-price", "OUT-bot_question")) if f]
        d["plan.objection_playbook"] = Decision(
            value=list(playbook)[:6],
            source=Source.seller_data if seen else Source.evidence,
            confidence=Confidence.strong if seen else (Confidence.moderate if out_ids else Confidence.guess),
            reason=(("This seller's own history first: " + "; ".join(sources[:4]) + ". ") if seen else
                    "No objection history (cold start). ") +
                   "Then the behaviours that most often cost VANI meetings (busy, not interested, price, bot question).",
            evidence_ids=out_ids)
        escalation = list(ESCALATION)
        if h.do_not_call:
            escalation.insert(0, "Seller previously asked not to be called: do NOT pitch; apologise and confirm removal.")
        if h.in_touch_with_executive:
            escalation.append("Seller is in touch with an executive: offer to loop in the same executive.")
        return ConversationPlan(
            opening=_gender_forms(opening, gender),
            personalisation=hooks,
            objection_playbook=playbook,
            escalation_rules=escalation,
            guardrails=GUARDRAILS,
        )


_MALE = [("रही हूँ", "रहा हूँ"), ("बताती हूँ", "बताता हूँ"), ("सकती हूँ", "सकता हूँ"), ("देती हूँ", "देता हूँ"),
         ("करवाती हूँ", "करवाता हूँ"), ("चाहती हूँ", "चाहता हूँ"), ("लूँगी", "लूँगा"), ("करवाऊँगी", "करवाऊँगा"),
         ("कर दूँ", "कर दूँ"), ("assistant हूँ", "assistant हूँ"), ("समझ सकती", "समझ सकता")]


def _gender_forms(text: str, gender: str) -> str:
    if gender != "male":
        return text
    for f, m in _MALE:
        text = text.replace(f, m)
    return text


def line(style: str, key: str, gender: str = "female", **kw) -> str:
    """A strategy line (direct/clarify/rush/...) rendered for a persona."""
    return _gender_forms(lines_for(style)[key].format(**kw) if kw else lines_for(style)[key], gender)
