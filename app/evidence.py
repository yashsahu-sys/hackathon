"""Learn which persona choices fix meetings for which seller segments.

The question we ask the data is the business one: "for sellers like this one,
which option beats what today's bot does, and by how much?"

1. For each persona dimension, learn over ALL calls which seller attribute
   drives it (e.g. region drives language, age drives pace).
2. For a seller, look only at their segment on that attribute, pick the option
   with the best (smoothed) meeting-fix rate, and test it against today's
   default with a two-proportion z-test.
3. If the evidence isn't there (p >= 0.2), keep today's default and say so.

Why not search every segment the seller falls in? We tried: it "found" a
voice-gender effect that isn't in the data. Learning the driver once over all
sellers avoids cherry-picking a lucky slice per seller.
"""
import json
import math
from dataclasses import dataclass, asdict
from pathlib import Path

from .config import DATA

SEGMENT_ATTRS = ("region", "business_type", "age_band", "turnover_band")
MIN_SEGMENT_CALLS = 150
MIN_OPTION_CALLS = 30
PRIOR_WEIGHT = 5.0
ALPHA = 0.05
MIN_DRIVER_GAIN = 0.02  # below this, personalising the dimension isn't worth it

# What the Voice Bot does for every seller today.
CURRENT_DEFAULT = {
    "language_style": "hindi",
    "pace": "normal",
    "formality": "neutral",
    "opening": "detailed",
    "voice_gender": "female",
}


@dataclass
class Finding:
    dimension: str
    choice: str
    rate: float
    n: int
    baseline: str
    baseline_rate: float
    baseline_n: int
    p_value: float | None      # choice vs today's default
    confidence: str            # strong | moderate | none
    segment: dict
    segment_calls: int
    option_rates: dict

    @property
    def lift(self) -> float:
        return self.rate - self.baseline_rate

    def to_dict(self) -> dict:
        d = asdict(self)
        d["lift"] = round(self.lift, 3)
        d["summary"] = self.summary()
        return d

    def segment_label(self) -> str:
        return ", ".join(f"{k}={v}" for k, v in self.segment.items()) or "all sellers"

    def summary(self) -> str:
        if self.choice == self.baseline:
            if self.p_value is None and self.option_rates.get(self.baseline):
                return (f"today's '{self.baseline}' is already the best option for [{self.segment_label()}] "
                        f"({self.baseline_rate:.0%}, n={self.baseline_n}); keeping it")
            return f"no option reliably beats today's '{self.baseline}' for [{self.segment_label()}]; keeping it"
        return (f"{self.choice} fixed {self.rate:.0%} of meetings vs {self.baseline_rate:.0%} for today's "
                f"'{self.baseline}' among [{self.segment_label()}] (n={self.n} vs {self.baseline_n}, "
                f"p={self.p_value:.3f})")


def _two_proportion_p(k1: int, n1: int, k2: int, n2: int) -> float:
    if n1 == 0 or n2 == 0:
        return 1.0
    pooled = (k1 + k2) / (n1 + n2)
    se = math.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    if se == 0:
        return 1.0
    z = abs(k1 / n1 - k2 / n2) / se
    return math.erfc(z / math.sqrt(2))  # two-sided


def _confidence(p: float | None) -> str:
    if p is None or p >= 0.2:
        return "none"
    return "strong" if p < ALPHA else "moderate"


class EvidenceStore:
    def __init__(self, calls: list[dict], synthetic: bool = False):
        self.calls = calls
        self.synthetic = synthetic
        self.global_rate = sum(c["meeting_fixed"] for c in calls) / max(1, len(calls))
        self._drivers: dict = {}

    @classmethod
    def load(cls, path: Path | None = None) -> "EvidenceStore":
        private = DATA / "private" / "past_calls.json"
        path = path or (private if private.exists() else DATA / "evidence" / "past_calls.json")
        raw = json.loads(Path(path).read_text())
        return cls(raw["calls"], synthetic=raw.get("synthetic", False))

    def _stats(self, dimension: str, calls: list[dict]) -> dict:
        stats = {}
        for c in calls:
            opt = c["persona"][dimension]
            k, n = stats.get(opt, (0, 0))
            stats[opt] = (k + int(c["meeting_fixed"]), n + 1)
        return stats

    def _smoothed(self, k: int, n: int) -> float:
        return (k + PRIOR_WEIGHT * self.global_rate) / (n + PRIOR_WEIGHT)

    def driver(self, dimension: str) -> tuple[str | None, float]:
        """Seller attribute that decides the best option for this dimension.

        gain(a) = extra meetings per call from picking the best option per
        value of `a`, instead of one best option for everyone.
        """
        if dimension in self._drivers:
            return self._drivers[dimension]
        glob = self._stats(dimension, self.calls)
        one_size = max(glob, key=lambda o: self._smoothed(*glob[o]))
        best_attr, best_gain = None, 0.0
        for a in SEGMENT_ATTRS:
            gain = 0.0
            for level in {c["seller"][a] for c in self.calls}:
                calls = [c for c in self.calls if c["seller"][a] == level]
                rates = {o: self._smoothed(k, n) for o, (k, n) in self._stats(dimension, calls).items()}
                gain += len(calls) / len(self.calls) * (max(rates.values()) - rates.get(one_size, 0.0))
            if gain > best_gain:
                best_attr, best_gain = a, gain
        result = (best_attr, round(best_gain, 4)) if best_gain >= MIN_DRIVER_GAIN else (None, round(best_gain, 4))
        self._drivers[dimension] = result
        return result

    def best(self, dimension: str, seller_attrs: dict) -> Finding:
        baseline = CURRENT_DEFAULT[dimension]
        attr, _ = self.driver(dimension)
        segment = {attr: seller_attrs[attr]} if attr and seller_attrs.get(attr) else {}
        calls = [c for c in self.calls if all(c["seller"].get(k) == v for k, v in segment.items())]
        if len(calls) < MIN_SEGMENT_CALLS:
            segment, calls = {}, self.calls
        stats = self._stats(dimension, calls)
        bk, bn = stats.get(baseline, (0, 0))
        eligible = [(o, k, n) for o, (k, n) in stats.items() if n >= MIN_OPTION_CALLS] or \
                   [(o, k, n) for o, (k, n) in stats.items()]
        opt, k, n = max(eligible, key=lambda x: self._smoothed(x[1], x[2]))
        p = None if opt == baseline or bn == 0 else _two_proportion_p(k, n, bk, bn)
        confidence = _confidence(p)
        if opt != baseline and confidence == "none":
            # Not enough evidence to move away from what the bot does today.
            opt, k, n = baseline, bk, bn
        return Finding(
            dimension=dimension, choice=opt, rate=k / n if n else 0.0, n=n,
            baseline=baseline, baseline_rate=bk / bn if bn else 0.0, baseline_n=bn,
            p_value=p, confidence=confidence, segment=segment, segment_calls=len(calls),
            option_rates={o: {"rate": round(kk / nn, 3), "n": nn} for o, (kk, nn) in stats.items()},
        )
