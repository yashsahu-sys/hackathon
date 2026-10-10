"""Export deliverables from real data (written to data/private/out, never committed):

  * one persona spec per seller (JSON) for a sample of sellers
  * 3 maximally contrasting sellers for the voice demo, with a side-by-side table

    python -m vani.tools.export --sample 50
"""
import argparse
import json
from collections import Counter

from vani.config import get_settings
from vani.data.repository import DuckDBSellerRepository
from vani.evidence.book import EvidenceBook
from vani.persona.distinct import distance, most_distinct
from vani.persona.generator import PersonaGenerator
from vani.persona.prompt import agent_variables


def main(sample: int = 50) -> None:
    s = get_settings()
    repo = DuckDBSellerRepository(s.resolve(s.warehouse_path))
    gen = PersonaGenerator(EvidenceBook.load(s.resolve(s.evidence_path)))
    out = s.resolve(s.evidence_path).parent / "out"
    (out / "personas").mkdir(parents=True, exist_ok=True)

    # Candidates: sellers with real call history (their personas rest on the most evidence)
    candidates = repo.search(with_transcripts=True, limit=400)
    personas, profiles = [], {}
    for prof in candidates:
        p = gen.generate(repo.get_context(prof.glid))
        personas.append(p)
        profiles[p.seller_glid] = prof
    for p in personas[:sample]:
        (out / "personas" / f"{p.seller_glid}.json").write_text(p.model_dump_json(indent=2))

    chosen, min_d = most_distinct(personas, 3)
    rows = ["| | " + " | ".join(f"Seller {i + 1}" for i in range(len(chosen))) + " |",
            "|---|" + "---|" * len(chosen)]
    def row(name, f):
        rows.append(f"| {name} | " + " | ".join(str(f(p)) for p in chosen) + " |")
    row("glid", lambda p: p.seller_glid)
    row("Business", lambda p: f"{profiles[p.seller_glid].business_kind.value}, {profiles[p.seller_glid].state}, "
                              f"{profiles[p.seller_glid].turnover_raw or 'turnover n/a'}")
    row("Persona", lambda p: p.label)
    row("Language", lambda p: f"{p.language.code} ({p.language.style}, {p.language.english_mix:.0%} English)")
    row("Voice", lambda p: f"{p.voice.speaker}, pace {p.voice.pace}x")
    row("Formality / empathy", lambda p: f"{p.language.formality} / {p.tone.empathy}")
    row("Opening", lambda p: p.plan.opening)
    row("Top objections", lambda p: ", ".join(list(p.plan.objection_playbook)[:3]))
    labels = Counter(p.label for p in personas)
    md = [f"# Demo sellers (min pairwise distance {min_d})", "", *rows, "",
          f"Across {len(personas)} sellers with call history: {len(labels)} distinct persona labels.", ""]
    for p in chosen:
        md += [f"## {p.seller_glid}: {p.label}", ""]
        md += [f"- **{k}** = `{d.value}` ({d.source.value}, {d.confidence.value}): {d.reason}" for k, d in p.decisions.items()]
        md += ["", "Agent variables:", "```json", json.dumps(agent_variables(p, profiles[p.seller_glid]),
                                                          ensure_ascii=False, indent=1), "```", ""]
    (out / "demo_sellers.md").write_text("\n".join(md))
    print(f"wrote {min(sample, len(personas))} persona specs and demo_sellers.md to {out}")
    for p in chosen:
        print(" ", p.seller_glid, p.label)
    print("pairwise distances:", [distance(a, b) for a, b in [(chosen[0], chosen[1]), (chosen[0], chosen[2]), (chosen[1], chosen[2])]])


if __name__ == "__main__":
    from vani.tools.console import utf8_console
    utf8_console()
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=50)
    main(ap.parse_args().sample)
