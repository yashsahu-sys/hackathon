import json

import pytest

from vani.data.normalize import profile_from_row
from vani.evidence.book import EvidenceBook
from vani.evidence.miner import EvidenceMiner, age_band, engagement_band, save, segments_of
from tests.conftest import seller_row


@pytest.fixture(scope="module")
def book_dict(repo):
    return EvidenceMiner(repo).mine()


def test_baseline(book_dict):
    assert book_dict["source"] == {"calls": 3, "sellers": 4, "calls_with_transcript": 2}
    assert book_dict["baseline"]["meeting_rate"] == pytest.approx(1 / 3, abs=1e-3)
    assert book_dict["caveats"]


def test_outcome_finding_numbers(book_dict):
    f = {x["id"]: x for x in book_dict["findings"]}["OUT-busy"]
    assert (f["k"], f["n"], f["base_k"], f["base_n"]) == (0, 1, 1, 2)
    assert f["strength"] == "weak"   # tiny sample can never be strong


def test_every_finding_is_well_formed(book_dict):
    for f in book_dict["findings"]:
        assert f["id"] and f["statement"] and f["strength"] in ("strong", "moderate", "weak")
        assert 0 <= f["rate"] <= 1
        assert (f["p_value"] is None) == (f["kind"] == "descriptive")
        assert f["p_value"] is None or 0 <= f["p_value"] <= 1
        assert f["ci95"][0] <= f["rate"] + 1e-9 and f["rate"] <= f["ci95"][1] + 1e-9


def test_variant_findings_marked_causal(book_dict):
    assert all(f["causal"] for f in book_dict["findings"] if f["kind"] == "variant")
    assert not any(f["causal"] for f in book_dict["findings"] if f["kind"] != "variant")


def test_save_and_load_roundtrip(book_dict, tmp_path):
    save(book_dict, tmp_path / "e.json")
    book = EvidenceBook.load(tmp_path / "e.json")
    assert len(book) == len(book_dict["findings"]) and book.get("OUT-busy")


def test_segment_helpers():
    assert [age_band(x) for x in (None, 2, 10, 30)] == ["unknown", "new", "established", "veteran"]
    assert [engagement_band(x) for x in (None, 0.1, 0.5, 0.9)] == ["unknown", "low", "mid", "high"]
    seg = segments_of(profile_from_row(seller_row("1", seller_state="Kerala")))
    assert seg["region"] == "south" and seg["business_kind"] == "manufacturer"


def _book(findings):
    return EvidenceBook({"baseline": {}, "findings": findings})


def _seg(fid, rate, base, strength, n=100, bn=400):
    return {"id": fid, "rate": rate, "base_rate": base, "strength": strength, "statement": fid,
            "k": round(rate * n), "n": n, "base_k": round(base * bn), "base_n": bn}


def test_book_elevated_picks_strongest_higher_risk():
    p = profile_from_row(seller_row("1", seller_state="Delhi", eng_pickup_ratio_90d="0.1"))
    book = _book([
        _seg("SEG-region=north-busy", 0.12, 0.10, "moderate"),
        _seg("SEG-pickup=low-busy", 0.20, 0.10, "strong"),
        _seg("SEG-business_kind=manufacturer-busy", 0.05, 0.10, "strong"),   # lower risk: ignored
    ])
    assert book.elevated(p, "busy")["id"] == "SEG-pickup=low-busy"
    assert book.elevated(p, "confused") is None


def test_book_elevated_uses_overall_rate_not_rest():
    # Segment is 90% of calls: 49% vs 40% for "the rest" but only ~1.02x the overall rate.
    p = profile_from_row(seller_row("1", seller_state="Delhi"))
    book = _book([_seg("SEG-region=north-early_drop", 0.49, 0.40, "strong", n=900, bn=100)])
    assert book.elevated(p, "early_drop") is None


def test_book_ignores_weak_by_default():
    p = profile_from_row(seller_row("1", seller_state="Delhi"))
    book = _book([_seg("SEG-region=north-busy", 0.5, 0.1, "weak")])
    assert book.elevated(p, "busy") is None
    assert book.elevated(p, "busy", min_strength="weak")["id"] == "SEG-region=north-busy"


def test_book_usable_and_cite():
    book = _book([_seg("X", 0.1, 0.2, "moderate")])
    assert book.usable("X") and not book.usable("X", "strong") and book.usable("missing") is None
    assert "[moderate, X]" in EvidenceBook.cite(book.get("X"))
    assert len(EvidenceBook.empty()) == 0


@pytest.mark.realdata
def test_real_evidence_headline_findings(real_repo):
    book = EvidenceBook(EvidenceMiner(real_repo).mine())
    assert 0.05 < book.baseline["meeting_rate"] < 0.25
    assert book.get("OUT-early_drop")["rate"] < 0.005             # almost no meeting is fixed in under 20s
    assert book.usable("OUT-confused", "strong")                  # confusion kills meetings
    assert book.get("OUT-confused")["rate"] < book.get("OUT-confused")["base_rate"]
    f = book.get("VAR-last_met_d-early_drop")                       # real A/B-style variant
    assert f and f["causal"] and f["rate"] < f["base_rate"]


@pytest.mark.realdata
def test_real_generator_covers_all_sellers(real_repo):
    from collections import Counter

    from vani.persona.generator import PersonaGenerator
    book = EvidenceBook(EvidenceMiner(real_repo).mine())
    gen = PersonaGenerator(book)
    labels, defaults = Counter(), 0
    for prof in real_repo.iter_profiles():
        p = gen.generate(real_repo.get_context(prof.glid, max_calls=5))
        labels[p.label] += 1
        for dec in p.decisions.values():
            assert dec.reason
            assert all(book.get(fid) for fid in dec.evidence_ids)
    assert sum(labels.values()) == 5000
    assert len(labels) >= 20                       # personas differ across seller types
    assert max(labels.values()) / 5000 < 0.6       # no single persona dominates


@pytest.mark.realdata
def test_real_signal_evaluation_runs(real_repo):
    from vani.live.evaluate import evaluate
    rep = evaluate(real_repo)
    assert rep["calls"] > 400
    for name in ("rush", "refusal", "frustration"):
        s = rep["signals"][name]
        assert s["support"] > 0 and s["recall"] is not None
    assert rep["signals"]["refusal"]["precision"] >= 0.5
