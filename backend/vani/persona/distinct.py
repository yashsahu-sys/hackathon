"""How different are two personas? Used to pick contrasting demo sellers and to
report distinctness (PS04 criterion: 'clearly different personas, not minor
variations of one')."""
from itertools import combinations

from vani.domain.persona import PersonaSpec


def distance(a: PersonaSpec, b: PersonaSpec) -> float:
    d = 0.0
    d += 2.0 * (a.language.code != b.language.code)
    d += 1.0 * (a.language.formality != b.language.formality)
    d += min(2.0, abs(a.voice.pace - b.voice.pace) * 10)          # 0.1x pace ≈ 1 point
    d += 1.0 * (a.decisions["plan.opening"].value != b.decisions["plan.opening"].value)
    d += 0.5 * (a.voice.speaker != b.voice.speaker)
    d += 0.5 * (a.tone.empathy != b.tone.empathy)
    d += 0.5 * (a.tone.max_words_per_turn != b.tone.max_words_per_turn)
    d += 0.5 * (list(a.plan.objection_playbook)[:2] != list(b.plan.objection_playbook)[:2])
    return round(d, 2)


def most_distinct(personas: list[PersonaSpec], k: int = 3) -> tuple[list[PersonaSpec], float]:
    """Greedy: start from the farthest pair, then add the persona farthest from the chosen set."""
    if len(personas) <= k:
        return personas, 0.0
    a, b = max(combinations(personas, 2), key=lambda pair: distance(*pair))
    chosen = [a, b]
    while len(chosen) < k:
        chosen.append(max((p for p in personas if p not in chosen), key=lambda p: min(distance(p, c) for c in chosen)))
    return chosen, min(distance(x, y) for x, y in combinations(chosen, 2))
