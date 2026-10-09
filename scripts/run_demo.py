"""Generate submission sample outputs: a persona spec per seller and scripted
calls with mid-call switches. Runs offline (no API key needed).

    python scripts/run_demo.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app.conversation import Session  # noqa: E402
from app.evidence import EvidenceStore  # noqa: E402
from app.persona import generate_persona, system_prompt  # noqa: E402

SCENARIOS = {
    "S101": ["Haan bolo", "Yaar point pe aao, kitni der se bol rahe ho!", "Accha kitna paisa lagega?",
             "Haan theek hai, kal 11 baje chalega"],
    "S102": ["Yes, tell me", "Sorry, I did not understand, what is this about?", "Okay. What is the charge for this?",
             "Alright, tomorrow 11 AM is fine"],
    "S103": ["Haan bolo", "Main already TradeIndia pe hoon", "Sorry, can you speak in English please",
             "Yes okay, 11 AM tomorrow works, confirm it"],
    "S104": ["जी बताइए", "Abhi busy hoon, customer aaya hai", "हाँ ठीक है, कल 11 बजे आ जाइए"],
}


def main():
    evidence = EvidenceStore.load()
    out = ROOT / "samples"
    (out / "personas").mkdir(parents=True, exist_ok=True)
    (out / "calls").mkdir(parents=True, exist_ok=True)
    sellers = {p.stem: json.loads(p.read_text()) for p in sorted((ROOT / "data" / "sellers").glob("*.json"))}

    for sid, seller in sellers.items():
        persona = generate_persona(seller, evidence)
        public = {k: v for k, v in persona.items() if not k.startswith("_")}
        (out / "personas" / f"{sid}.json").write_text(json.dumps(public, indent=2, ensure_ascii=False))
        (out / "personas" / f"{sid}_system_prompt.txt").write_text(system_prompt(persona, seller))
        print(f"{sid} {seller['name']:<18} -> {persona['label']}")

    print()
    for sid, turns in SCENARIOS.items():
        session = Session(sellers[sid], evidence, client=None)
        print(f"=== {sid} {sellers[sid]['name']} [{session.persona['label']}]")
        print(f"  BOT: {session.open()['text']}")
        for text in turns:
            r = session.seller_turn(text)
            print(f"  SELLER: {text}")
            for e in r["switches"]:
                changes = ", ".join(f"{c['field']} {c['from']}→{c['to']}" for c in e["changes"])
                print(f"    >> SWITCH [{e['signal']}] {changes}")
            print(f"  BOT (v{r['persona']['version']}, pace {r['bot']['voice']['pace']}x): {r['bot']['text']}")
        summary = session.summary()
        (out / "calls" / f"{sid}.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))
        print(f"  OUTCOME: {summary['outcome']}, {len(summary['switch_log'])} switch(es)\n")


if __name__ == "__main__":
    main()
