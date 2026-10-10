"""Persona for one seller, with the reason behind every decision.

    python skill/vani-persona/scripts/persona.py <glid> [--voice male|female] [--json]
"""
import argparse
import json
import sys

import _path  # noqa: F401

from vani.api.deps import Container
from vani.config import get_settings
from vani.runtime.service import NotFound


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("glid")
    ap.add_argument("--voice", choices=["male", "female"])
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    c = Container.build(get_settings())
    try:
        p, profile = c.calls.persona_for(a.glid, a.voice)
    except NotFound:
        print(f"seller {a.glid} not found", file=sys.stderr)
        return 1
    if a.json:
        print(json.dumps(p.model_dump(mode="json"), ensure_ascii=False, indent=1))
        return 0
    print(f"{p.label}\nseller {a.glid}: {profile.city}, {profile.state} | {profile.business_kind.value} | "
          f"turnover {profile.turnover_raw} | missing: {', '.join(profile.missing_fields) or 'none'}")
    print(f"\nopening: {p.plan.opening}\n")
    for k, d in p.decisions.items():
        ev = f" [{', '.join(d.evidence_ids)}]" if d.evidence_ids else ""
        print(f"- {k} = {d.value}  ({d.source.value}, {d.confidence.value}){ev}\n    {d.reason}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
