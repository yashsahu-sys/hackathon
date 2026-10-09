"""Generate SYNTHETIC past-call outcomes for development.

Real call data from the organisers replaces this file (same schema). Patterns
are planted on purpose so we can check the generator rediscovers them:
  - South India sellers fix more meetings in English / their regional language
  - Sellers over 50 respond to slow, formal delivery
  - Young traders respond to fast, casual, short openings
  - Large sellers and distributors respond to value/ROI-led openings
  - Voice gender has NO planted effect (generator should say "no evidence")
"""
import json
import random
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "data" / "evidence" / "past_calls.json"

REGIONS = {
    "north": ["Delhi", "Ludhiana", "Jaipur", "Lucknow", "Kanpur"],
    "south": ["Coimbatore", "Chennai", "Bengaluru", "Hyderabad", "Kochi"],
    "west": ["Mumbai", "Ahmedabad", "Surat", "Pune", "Rajkot"],
    "east": ["Kolkata", "Patna", "Bhubaneswar", "Guwahati", "Ranchi"],
}
BUSINESS = ["trader", "manufacturer", "distributor"]
AGE = ["under_35", "35_50", "over_50"]
TURNOVER = ["small", "mid", "large"]
OPTIONS = {
    "language_style": ["hinglish", "hindi", "english", "regional"],
    "pace": ["slow", "normal", "fast"],
    "formality": ["casual", "neutral", "formal"],
    "opening": ["short", "value", "detailed"],
    "voice_gender": ["female", "male"],
}


def meeting_probability(s: dict, p: dict) -> float:
    prob = 0.20
    lang, region = p["language_style"], s["region"]
    prob += {
        "south": {"english": 0.15, "regional": 0.18, "hindi": -0.10, "hinglish": -0.06},
        "north": {"hinglish": 0.18, "hindi": 0.05, "english": -0.04, "regional": 0.0},
        "west": {"hinglish": 0.10, "english": 0.06, "hindi": 0.02, "regional": 0.03},
        "east": {"hindi": 0.05, "regional": 0.08, "hinglish": 0.02, "english": 0.0},
    }[region][lang]

    age, biz, size = s["age_band"], s["business_type"], s["turnover_band"]
    if age == "over_50":
        prob += {"slow": 0.10, "normal": 0.02, "fast": -0.10}[p["pace"]]
        prob += {"formal": 0.10, "neutral": 0.02, "casual": -0.08}[p["formality"]]
    if age == "under_35":
        prob += {"fast": 0.10, "normal": 0.02, "slow": -0.08}[p["pace"]]
        prob += {"casual": 0.08, "neutral": 0.02, "formal": -0.05}[p["formality"]]
    if biz == "trader":
        prob += {"short": 0.20, "value": -0.04, "detailed": -0.12}[p["opening"]]
    if biz == "manufacturer":
        prob += {"detailed": 0.07, "value": 0.03, "short": -0.02}[p["opening"]]
    if biz == "distributor" or size == "large":
        prob += {"value": 0.14, "detailed": 0.02, "short": -0.03}[p["opening"]]
        prob += {"formal": 0.05, "neutral": 0.02, "casual": -0.03}[p["formality"]]
    return min(0.9, max(0.02, prob))


def main(n: int = 6000, seed: int = 7) -> None:
    rng = random.Random(seed)
    calls = []
    for i in range(n):
        region = rng.choice(list(REGIONS))
        seller = {
            "region": region,
            "city": rng.choice(REGIONS[region]),
            "business_type": rng.choice(BUSINESS),
            "age_band": rng.choice(AGE),
            "turnover_band": rng.choice(TURNOVER),
        }
        persona = {dim: rng.choice(opts) for dim, opts in OPTIONS.items()}
        fixed = rng.random() < meeting_probability(seller, persona)
        calls.append({
            "call_id": f"C{i:05d}",
            "seller": seller,
            "persona": persona,
            "meeting_fixed": fixed,
            "duration_s": rng.randint(90, 300) if fixed else rng.randint(15, 160),
        })
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"synthetic": True, "calls": calls}, indent=1))
    rate = sum(c["meeting_fixed"] for c in calls) / n
    print(f"wrote {n} calls to {OUT} (overall meeting rate {rate:.1%})")


if __name__ == "__main__":
    main()
