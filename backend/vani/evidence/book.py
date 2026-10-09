"""Read-side of the evidence: what the persona generator queries and cites."""
import json
from pathlib import Path

from vani.domain.seller import SellerProfile

from .miner import segments_of

RANK = {"strong": 3, "moderate": 2, "weak": 1}


class EvidenceBook:
    def __init__(self, book: dict):
        self.raw = book
        self.baseline = book.get("baseline", {})
        self.caveats = book.get("caveats", [])
        self._by_id = {f["id"]: f for f in book.get("findings", [])}

    @classmethod
    def load(cls, path: Path) -> "EvidenceBook":
        return cls(json.loads(Path(path).read_text()))

    @classmethod
    def empty(cls) -> "EvidenceBook":
        return cls({"baseline": {}, "findings": [], "caveats": ["No evidence book loaded; all choices are informed guesses."]})

    def __len__(self) -> int:
        return len(self._by_id)

    def get(self, fid: str) -> dict | None:
        return self._by_id.get(fid)

    def usable(self, fid: str, min_strength: str = "moderate") -> dict | None:
        f = self._by_id.get(fid)
        return f if f and RANK.get(f["strength"], 0) >= RANK[min_strength] else None

    def elevated(self, profile: SellerProfile, metric: str, min_strength: str = "moderate") -> dict | None:
        """Strongest finding that this seller's segment has MORE of `metric` than other sellers."""
        best = None
        for dim, level in segments_of(profile).items():
            f = self._by_id.get(f"SEG-{dim}={level}-{metric}")
            if not f or f["rate"] <= f["base_rate"] or RANK.get(f["strength"], 0) < RANK[min_strength]:
                continue
            if best is None or (RANK[f["strength"]], f["rate"] / max(f["base_rate"], 1e-9)) > \
                    (RANK[best["strength"]], best["rate"] / max(best["base_rate"], 1e-9)):
                best = f
        return best

    def segment_findings(self, profile: SellerProfile, min_strength: str = "moderate") -> list[dict]:
        out = []
        for dim, level in segments_of(profile).items():
            prefix = f"SEG-{dim}={level}-"
            out += [f for fid, f in self._by_id.items()
                    if fid.startswith(prefix) and RANK.get(f["strength"], 0) >= RANK[min_strength]]
        return sorted(out, key=lambda f: -RANK[f["strength"]])

    @staticmethod
    def cite(f: dict) -> str:
        return f"{f['statement']} [{f['strength']}, {f['id']}]"
