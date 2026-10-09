"""Score the live detector on real VANI calls.

Labels: the AI summary of each call (busy, confused, frustrated, bot question,
not interested). They are call-level and noisy, so treat the numbers as
estimates. Also reports WHEN a signal first fires (turn index), the 'well-timed'
half of the PS04 criterion.

    python -m vani.live.evaluate
"""
import json
from collections import defaultdict

from vani.config import get_settings
from vani.data.repository import DuckDBSellerRepository, _call
from vani.domain.live import SignalType
from vani.evidence.features import summary_tags

from .signals import SignalDetector

LABEL_FOR = {
    SignalType.rush: "busy", SignalType.confusion: "confused", SignalType.frustration: "frustrated",
    SignalType.bot_question: "bot_question", SignalType.refusal: "not_interested",
}


def evaluate(repo: DuckDBSellerRepository) -> dict:
    det = SignalDetector()
    calls = [_call(r) for r in repo._rows("SELECT * FROM v_bot_calls WHERE has_turn_transcript = 1")]
    turns = defaultdict(list)
    for t in repo.get_turns([c.attempt_id for c in calls]):
        turns[t.attempt_id].append(t)
    counts = {s: {"tp": 0, "fp": 0, "fn": 0, "tn": 0, "first_turn": []} for s in LABEL_FOR}
    for c in calls:
        tags = summary_tags(c.summary)
        seller_turns = [t for t in sorted(turns[c.attempt_id], key=lambda t: t.turn_no) if t.speaker == "seller"]
        fired: dict[SignalType, int] = {}
        history: list[str] = []
        for i, t in enumerate(seller_turns):
            for s in det.detect(t.text, "hi-IN", recent_seller_turns=history):
                if s.confidence >= 0.6 and s.type not in fired:
                    fired[s.type] = i
            history.append(t.text)
        for sig, label in LABEL_FOR.items():
            hit, truth = sig in fired, label in tags
            key = "tp" if hit and truth else "fp" if hit else "fn" if truth else "tn"
            counts[sig][key] += 1
            if hit and truth:
                counts[sig]["first_turn"].append(fired[sig] + 1)
    report = {}
    for sig, c in counts.items():
        tp, fp, fn = c["tp"], c["fp"], c["fn"]
        report[sig.value] = {
            "label": LABEL_FOR[sig], "support": tp + fn, "fired": tp + fp,
            "precision": round(tp / (tp + fp), 3) if tp + fp else None,
            "recall": round(tp / (tp + fn), 3) if tp + fn else None,
            "median_first_seller_turn": sorted(c["first_turn"])[len(c["first_turn"]) // 2] if c["first_turn"] else None,
            **{k: c[k] for k in ("tp", "fp", "fn", "tn")},
        }
    return {"calls": len(calls), "signals": report,
            "note": "Labels are keyword tags on AI call summaries: call-level and noisy. A 'false positive' "
                    "can be a real moment the summary didn't mention."}


if __name__ == "__main__":
    s = get_settings()
    rep = evaluate(DuckDBSellerRepository(s.resolve(s.warehouse_path)))
    out = s.resolve(s.evidence_path).with_name("signal_eval.json")
    out.write_text(json.dumps(rep, indent=1))
    for k, v in rep["signals"].items():
        print(f"{k:13s} support={v['support']:3d} fired={v['fired']:3d} precision={v['precision']} recall={v['recall']} "
              f"first_turn={v['median_first_seller_turn']}")
