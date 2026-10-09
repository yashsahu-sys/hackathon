"""Mine past VANI calls into an evidence book the persona generator cites.

What the data can and can't tell us (and the book says so):
  * VANI used one persona for everyone, so we can't directly measure "pace X
    beats pace Y". We CAN measure (a) which in-call behaviours kill meetings
    (confusion, rush, frustration, early drop), (b) which seller segments show
    those behaviours more often, and (c) real script variants that ran side by
    side (bot versions), which is the closest thing to an A/B test.
  * Every finding is correlational unless it comes from a variant comparison.

    python -m vani.evidence.miner        # writes data/private/evidence.json
"""
import json
import logging
from collections import defaultdict
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path

from vani.config import get_settings
from vani.data.repository import DuckDBSellerRepository
from vani.domain.seller import SellerProfile

from .features import CallFeatures, call_features
from .stats import strength, two_proportion_p, wilson

log = logging.getLogger(__name__)

RISK_METRICS = ("early_drop", "busy", "confused", "frustrated", "bot_question", "not_interested")
MIN_SEGMENT_CALLS = 80
MIN_VARIANT_CALLS = 60


def age_band(years: int | None) -> str:
    if years is None:
        return "unknown"
    return "new" if years < 5 else ("established" if years <= 15 else "veteran")


def engagement_band(pickup: float | None) -> str:
    if pickup is None:
        return "unknown"
    return "low" if pickup < 0.3 else ("high" if pickup > 0.6 else "mid")


def segments_of(p: SellerProfile) -> dict[str, str]:
    return {
        "region": p.region,
        "business_kind": p.business_kind.value,
        "turnover_band": p.turnover_band.value,
        "business_age": age_band(p.business_age_years),
        "pickup": engagement_band(p.engagement.pickup_ratio_90d),
    }


def metric(f: CallFeatures, name: str) -> bool:
    if name == "meeting":
        return f.meeting_fixed
    if name == "early_drop":
        return f.early_drop
    return name in f.tags


@dataclass
class Finding:
    id: str
    kind: str                 # outcome_driver | segment_risk | segment_outcome | variant | transcript
    title: str
    statement: str
    metric: str
    segment: dict = field(default_factory=dict)
    rate: float = 0.0
    k: int = 0
    n: int = 0
    base_rate: float = 0.0
    base_k: int = 0
    base_n: int = 0
    ci95: tuple = (0.0, 0.0)
    p_value: float | None = 1.0   # None for descriptive findings (no comparison)
    strength: str = "weak"
    implication: str = ""
    causal: bool = False      # True only for variant comparisons

    @property
    def ratio(self) -> float:
        return self.rate / self.base_rate if self.base_rate else float("inf")


def _finding(fid, kind, title, metric_name, segment, k, n, bk, bn, n_tests, implication, statement_fmt, causal=False):
    rate, base = (k / n if n else 0.0), (bk / bn if bn else 0.0)
    p = two_proportion_p(k, n, bk, bn)
    return Finding(
        id=fid, kind=kind, title=title, metric=metric_name, segment=segment,
        rate=round(rate, 4), k=k, n=n, base_rate=round(base, 4), base_k=bk, base_n=bn,
        ci95=tuple(round(x, 4) for x in wilson(k, n)), p_value=round(min(1.0, p * n_tests), 6),
        strength=strength(p, min(n, bn), n_tests), implication=implication, causal=causal,
        statement=statement_fmt.format(rate=rate, base=base, n=n, bn=bn),
    )


class EvidenceMiner:
    def __init__(self, repo: DuckDBSellerRepository):
        self.repo = repo

    def load_features(self) -> tuple[list[CallFeatures], dict[str, SellerProfile]]:
        profiles = {p.glid: p for p in self.repo.iter_profiles()}
        calls = []
        rows = self.repo._rows("SELECT * FROM v_bot_calls")
        from vani.data.repository import _call
        bot_calls = [_call(r) for r in rows]
        turn_ids = [c.attempt_id for c in bot_calls if c.has_transcript]
        turns_by_call = defaultdict(list)
        for t in self.repo.get_turns(turn_ids):
            turns_by_call[t.attempt_id].append(t)
        for c in bot_calls:
            calls.append(call_features(c, turns_by_call.get(c.attempt_id, [])))
        return calls, profiles

    def mine(self) -> dict:
        calls, profiles = self.load_features()
        n_all = len(calls)
        k_meet = sum(c.meeting_fixed for c in calls)
        findings: list[Finding] = []

        # 1. Behaviours that kill (or carry) meetings ---------------------------------
        tags = ["early_drop", "busy", "confused", "frustrated", "bot_question", "price", "visit", "whatsapp",
                "not_interested", "already_in_touch", "language_issue"]
        implications = {
            "early_drop": "The first 20 seconds decide the call: personalise the opening and keep it short for drop-prone sellers.",
            "busy": "Detect rush live; skip the pitch and offer two concrete slots.",
            "confused": "Detect confusion live; slow down, simplify, one idea per sentence.",
            "frustrated": "Detect frustration live; acknowledge, cut length, go straight to the ask.",
            "bot_question": "Answer 'are you a bot?' honestly and warmly, then continue; reassure strategy.",
            "price": "Price questions signal engagement: answer that the visit is free, then ask for the slot.",
            "visit": "Talking about the visit/location goes with meetings: bring the visit up early.",
            "whatsapp": "Offering WhatsApp confirmation goes with fixed meetings.",
            "not_interested": "First 'not interested' needs one value line, not a repeat of the pitch.",
            "already_in_touch": "Sellers already in touch with an executive need a different hook (review, not intro).",
            "language_issue": "Language trouble is a live switch trigger: follow the seller's language.",
        }
        for t in tags:
            with_t = [c for c in calls if metric(c, t)]
            without = [c for c in calls if not metric(c, t)]
            k1 = sum(c.meeting_fixed for c in with_t)
            k0 = sum(c.meeting_fixed for c in without)
            findings.append(_finding(
                f"OUT-{t}", "outcome_driver", f"Meeting rate when '{t}' happens", "meeting", {"call_tag": t},
                k1, len(with_t), k0, len(without), len(tags), implications[t],
                f"Calls tagged '{t}' fixed {{rate:.1%}} meetings (n={{n}}) vs {{base:.1%}} without (n={{bn}})."))

        k_drop = sum(c.early_drop for c in calls)
        share_drop = k_drop / n_all
        drop_meet = sum(c.meeting_fixed for c in calls if c.early_drop)
        findings.append(Finding(
            id="OUT-early_drop_share", kind="descriptive", title="Share of answered calls over within 20s",
            metric="early_drop", rate=round(share_drop, 4), k=k_drop, n=n_all, base_rate=round(share_drop, 4),
            ci95=tuple(round(x, 4) for x in wilson(k_drop, n_all)), p_value=None,
            strength="strong" if n_all >= 1000 else "moderate",
            statement=f"{share_drop:.0%} of answered VANI calls end within 20 seconds; only {drop_meet} of those "
                      f"{k_drop} fixed a meeting.",
            implication=implications["early_drop"]))

        # 2. Which segments show each risk more (or less) than everyone else ------------
        seg_calls = defaultdict(list)
        for c in calls:
            p = profiles.get(c.glid)
            if p is None:
                continue
            for dim, level in segments_of(p).items():
                if level != "unknown":
                    seg_calls[(dim, level)].append(c)
        risk_tests = [(dim_level, m) for dim_level, cs in seg_calls.items() if len(cs) >= MIN_SEGMENT_CALLS
                      for m in RISK_METRICS + ("meeting",)]
        n_tests = max(1, len(risk_tests))
        for (dim, level), m in risk_tests:
            inside = seg_calls[(dim, level)]
            ids = {c.attempt_id for c in inside}
            outside = [c for c in calls if c.attempt_id not in ids and profiles.get(c.glid)]
            k1, k0 = sum(metric(c, m) for c in inside), sum(metric(c, m) for c in outside)
            f = _finding(
                f"SEG-{dim}={level}-{m}", "segment_outcome" if m == "meeting" else "segment_risk",
                f"{m} rate for {dim}={level}", m, {dim: level}, k1, len(inside), k0, len(outside), n_tests,
                "", f"{dim}={level}: {m} in {{rate:.1%}} of calls (n={{n}}) vs {{base:.1%}} for other sellers (n={{bn}}).")
            f.implication = _segment_implication(m, f.rate > f.base_rate)
            findings.append(f)

        # 3. Real script variants (closest thing to an A/B test) -----------------------
        by_version = defaultdict(list)
        for c in calls:
            by_version[c.bot_version or "unknown"].append(c)
        control = by_version.get("main_vani", [])
        variants = [v for v, cs in by_version.items() if v != "main_vani" and len(cs) >= MIN_VARIANT_CALLS]
        kc = sum(c.meeting_fixed for c in control)
        for v in variants:
            cs = by_version[v]
            k = sum(c.meeting_fixed for c in cs)
            findings.append(_finding(
                f"VAR-{v}", "variant", f"Bot version '{v}' vs main_vani", "meeting", {"bot_version": v},
                k, len(cs), kc, len(control), len(variants), VARIANT_NOTES.get(v, ""),
                f"Version '{v}' fixed {{rate:.1%}} meetings (n={{n}}) vs main_vani {{base:.1%}} (n={{bn}}).", causal=True))
            ed = sum(c.early_drop for c in cs)
            edc = sum(c.early_drop for c in control)
            findings.append(_finding(
                f"VAR-{v}-early_drop", "variant", f"Bot version '{v}' early drops vs main_vani", "early_drop",
                {"bot_version": v}, ed, len(cs), edc, len(control), len(variants), VARIANT_NOTES.get(v, ""),
                f"Version '{v}' lost {{rate:.1%}} of calls in the first 20s (n={{n}}) vs main_vani {{base:.1%}} (n={{bn}}).",
                causal=True))

        # 4. Transcript evidence: opening length and seller language ------------------
        tc = [c for c in calls if c.has_transcript and c.bot_words_first_turn is not None]
        if len(tc) >= 2 * MIN_VARIANT_CALLS // 2:
            cut = sorted(c.bot_words_first_turn for c in tc)[len(tc) // 2]   # median split, data-driven
            short = [c for c in tc if c.bot_words_first_turn < cut]
            long_ = [c for c in tc if c.bot_words_first_turn >= cut]
            if short and long_:   # a degenerate split says nothing
                findings.append(_finding(
                    "TRN-opening_length", "transcript", "Early drop: short vs long first bot turn", "early_drop", {},
                    sum(c.early_drop for c in short), len(short), sum(c.early_drop for c in long_), len(long_), 1,
                    "Opening length vs early hang-ups, from turn-level transcripts (directional).",
                    f"Calls whose first bot line had < {cut} words dropped within 20s in {{rate:.1%}} "
                    f"of cases (n={{n}}) vs {{base:.1%}} for longer openings (n={{bn}})."))
        lang = [c for c in calls if c.seller_language]
        if lang:
            en = [c for c in lang if c.seller_language == "en-IN"]
            hi = [c for c in lang if c.seller_language == "hi-IN"]
            findings.append(_finding(
                "TRN-seller_language", "transcript", "Meeting rate when the seller answers in English", "meeting", {},
                sum(c.meeting_fixed for c in en), len(en), sum(c.meeting_fixed for c in hi), len(hi), 1,
                "Language follow-the-seller rule; sample is small, treat as directional.",
                "Sellers who answered mostly in English fixed {rate:.1%} meetings (n={n}) vs {base:.1%} for Hinglish (n={bn})."))
            findings.append(Finding(
                id="TRN-language_mix", kind="descriptive", title="What language sellers actually speak", metric="language",
                rate=round(len(hi) / len(lang), 4), k=len(hi), n=len(lang), base_rate=round(len(hi) / len(lang), 4),
                ci95=tuple(round(x, 4) for x in wilson(len(hi), len(lang))), p_value=None,
                strength="strong" if len(lang) >= 100 else "moderate",
                statement=f"{len(hi) / len(lang):.0%} of transcribed sellers answered in (mostly Roman) Hinglish, "
                          f"{len(en) / len(lang):.0%} in English (n={len(lang)} calls).",
                implication="Default to Hinglish; switch only when the seller does."))

        book = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": {"calls": n_all, "sellers": len(profiles), "calls_with_transcript": sum(c.has_transcript for c in calls)},
            "baseline": {"meeting_rate": round(k_meet / n_all, 4), "early_drop_rate": round(share_drop, 4), "n": n_all},
            "caveats": [
                "VANI used one persona for everyone, so persona-option effects are inferred from behaviours and segments, not measured directly.",
                "Summary tags come from AI-written summaries matched with keywords; expect some noise.",
                "Only variant (bot_version) findings compare scripts side by side; all other findings are correlational.",
                f"Turn-level transcripts exist for {sum(c.has_transcript for c in calls)} of {n_all} calls; transcript findings are directional.",
            ],
            "findings": [asdict(f) for f in findings],
        }
        return book


VARIANT_NOTES = {
    "arrowhead": "Opens with a respectful 'Namaste ji, IndiaMART ki taraf se...' greeting.",
    "last_met_d": "References the seller's last interaction in the opening.",
    "main": "Named branch-manager persona with a category-specific market line in the opening.",
}


def _segment_implication(metric_name: str, higher: bool) -> str:
    if not higher:
        return ""
    return {
        "early_drop": "Drop-prone segment: one-line personalised opening, get to the reason for calling fast.",
        "busy": "Rush-prone segment: shorter turns, faster pace, offer slots early.",
        "confused": "Confusion-prone segment: slower pace, simpler words, fewer English terms.",
        "frustrated": "Frustration-prone segment: acknowledge first, keep it short.",
        "bot_question": "Segment asks if it's a bot: warmer, more human delivery; honest answer ready.",
        "not_interested": "Low-intent segment: lead with value specific to their category.",
        "meeting": "Higher baseline intent: move to the meeting ask sooner.",
    }.get(metric_name, "")


def save(book: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(book, indent=1, default=str))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    s = get_settings()
    repo = DuckDBSellerRepository(s.resolve(s.warehouse_path))
    book = EvidenceMiner(repo).mine()
    save(book, s.resolve(s.evidence_path))
    strong = [f for f in book["findings"] if f["strength"] in ("strong", "moderate")]
    print(f"{len(book['findings'])} findings, {len(strong)} strong/moderate -> {s.resolve(s.evidence_path)}")
