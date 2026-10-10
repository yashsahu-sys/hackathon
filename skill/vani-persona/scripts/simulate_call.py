"""Simulate a call by text and print every persona switch.

    python skill/vani-persona/scripts/simulate_call.py <glid> "seller line 1" "seller line 2" ... [--voice male] [--json]
"""
import argparse
import asyncio
import json
import sys

import _path  # noqa: F401

from vani.api.deps import Container
from vani.config import get_settings
from vani.runtime.service import CallClosed, NotFound


async def run(a) -> int:
    c = Container.build(get_settings())
    try:
        s, opening = await c.calls.start(a.glid, voice_gender=a.voice, speak=False)
    except NotFound:
        print(f"seller {a.glid} not found", file=sys.stderr)
        return 1
    print(f"persona v{s.persona.version}: {s.persona.label}\nVANI: {opening.text}\n")
    r = None
    for line in a.lines:
        try:
            r = await c.calls.seller_turn(s.session_id, line, speak=False)
        except CallClosed:
            print("(call already ended)")
            break
        sig = ", ".join(f"{x.type.value}:{x.confidence:.2f}" for x in r.signals) or "-"
        print(f"SELLER: {line}\n  signals: {sig}")
        for e in r.switches:
            ch = "; ".join(f"{x.field} {x.old} -> {x.new}" for x in e.changes)
            print(f"  SWITCH {e.signal.value} (v{e.from_version}->v{e.to_version}): {ch}\n    why: {e.reason}")
        print(f"VANI [{r.move}, {r.bot.pace}x, {r.bot.language_code}]: {r.bot.text}\n")
    if r is not None:
        print(f"outcome: {r.session.outcome.value} {r.session.meeting_slot or ''}")
        if a.json:
            print(json.dumps(r.session.model_dump(mode="json"), ensure_ascii=False, indent=1, default=str))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("glid")
    ap.add_argument("lines", nargs="+")
    ap.add_argument("--voice", choices=["male", "female"])
    ap.add_argument("--json", action="store_true")
    return asyncio.run(run(ap.parse_args()))


if __name__ == "__main__":
    sys.exit(main())
