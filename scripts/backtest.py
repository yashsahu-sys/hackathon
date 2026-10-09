"""Held-out backtest: does the generator's persona fix more meetings than today's bot?

Train the evidence store on 70% of calls, then on the other 30%:
  - "generator-matched" calls: the persona actually used agreed with what the
    generator would pick for that seller on >= K of 4 style dimensions
  - "default-matched" calls: the persona used agreed with today's default bot
Compare meeting-fix rates, with a bootstrap 95% CI on the lift.

This is a valid comparison only when past personas were assigned at random
(as in the synthetic data, or an A/B log). On observational data, re-weight
or run a live A/B test before trusting the number; see README.
"""
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.evidence import CURRENT_DEFAULT, EvidenceStore  # noqa: E402

DIMS = ("language_style", "pace", "formality", "opening")
K = 3


def main(seed: int = 11) -> dict:
    full = EvidenceStore.load()
    calls = list(full.calls)
    rng = random.Random(seed)
    rng.shuffle(calls)
    cut = int(len(calls) * 0.7)
    train, test = EvidenceStore(calls[:cut]), calls[cut:]

    cache = {}
    def policy(seller: dict) -> dict:
        key = tuple(seller[a] for a in ("region", "business_type", "age_band", "turnover_band"))
        if key not in cache:
            cache[key] = {d: train.best(d, seller).choice for d in DIMS}
        return cache[key]

    gen, dflt = [], []
    for c in test:
        pick = policy(c["seller"])
        if sum(c["persona"][d] == pick[d] for d in DIMS) >= K:
            gen.append(c["meeting_fixed"])
        if sum(c["persona"][d] == CURRENT_DEFAULT[d] for d in DIMS) >= K:
            dflt.append(c["meeting_fixed"])

    rate = lambda xs: sum(xs) / len(xs)
    lifts = []
    for _ in range(2000):
        g = [rng.choice(gen) for _ in gen]
        d = [rng.choice(dflt) for _ in dflt]
        lifts.append(rate(g) - rate(d))
    lifts.sort()
    result = {
        "synthetic_data": full.synthetic,
        "train_calls": cut, "test_calls": len(test),
        "generator_matched": {"calls": len(gen), "meeting_rate": round(rate(gen), 3)},
        "default_matched": {"calls": len(dflt), "meeting_rate": round(rate(dflt), 3)},
        "absolute_lift": round(rate(gen) - rate(dflt), 3),
        "relative_lift": round(rate(gen) / rate(dflt) - 1, 3),
        "lift_95ci": [round(lifts[50], 3), round(lifts[1949], 3)],
        "calls_per_meeting": {"generator": round(1 / rate(gen), 2), "default": round(1 / rate(dflt), 2)},
    }
    return result


if __name__ == "__main__":
    r = main()
    out = Path(__file__).resolve().parent.parent / "samples" / "backtest.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(r, indent=2))
    print(json.dumps(r, indent=2))
    print(f"\nGenerator personas fixed {r['generator_matched']['meeting_rate']:.0%} of meetings vs "
          f"{r['default_matched']['meeting_rate']:.0%} for today's bot on held-out calls "
          f"({r['relative_lift']:+.0%}, 95% CI on absolute lift {r['lift_95ci'][0]:+.1%} to {r['lift_95ci'][1]:+.1%}).")
