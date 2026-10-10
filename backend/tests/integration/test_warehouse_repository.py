import pytest

from vani.data.warehouse import WarehouseError, build
from vani.domain.seller import BusinessKind


def test_build_counts(raw_dir, tmp_path):
    counts = build(raw_dir, tmp_path / "w.duckdb")
    assert counts == {"seller_profile": 4, "bot_calls": 3, "bot_call_turns": 4}


def test_build_is_idempotent(raw_dir, tmp_path):
    p = tmp_path / "w.duckdb"
    assert build(raw_dir, p) == build(raw_dir, p)


def test_missing_required_file_raises(tmp_path):
    with pytest.raises(WarehouseError):
        build(tmp_path, tmp_path / "w.duckdb")


def test_get_profile(repo):
    p = repo.get_profile("1002")
    assert p.state == "Tamil Nadu" and p.business_kind == BusinessKind.wholesaler
    assert repo.get_profile("does-not-exist") is None


def test_context_includes_calls_newest_first_and_turns(repo):
    ctx = repo.get_context("1001")
    assert [c.attempt_id for c in ctx.calls] == ["5002", "5001"]
    assert ctx.calls[1].bot_version == "main_vani" and ctx.calls[0].meeting_fixed
    assert [t.text for t in ctx.turns][1] == "Haan bolo, abhi busy hoon"   # only calls with transcripts


def test_context_for_seller_without_calls(repo):
    ctx = repo.get_context("1004")
    assert ctx.calls == [] and ctx.turns == []


def test_iter_profiles(repo):
    assert sorted(p.glid for p in repo.iter_profiles()) == ["1001", "1002", "1003", "1004"]


def test_search(repo):
    assert [p.glid for p in repo.search(with_transcripts=True)] == ["1001", "1002"]
    assert [p.glid for p in repo.search(state="delhi")] == ["1004"]
    assert [p.glid for p in repo.search(business_kind="wholesaler")] == ["1002"]
    assert len(repo.search(limit=2)) == 2


@pytest.mark.realdata
def test_real_dataset_loads_cleanly(real_repo):
    profiles = list(real_repo.iter_profiles())
    assert len(profiles) == 5000
    assert len({p.glid for p in profiles}) == 5000
    ctx = real_repo.get_context(real_repo.search(with_transcripts=True, limit=1)[0].glid)
    assert ctx.calls and ctx.turns
