"""Read access to sellers and their call history. Interface + DuckDB implementation.

The API and generator depend on SellerRepository, not DuckDB, so a Postgres or
API-backed repository can replace it without touching callers.
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterator

import duckdb

from vani.domain.seller import BotCall, CallTurn, SellerContext, SellerProfile

from .normalize import is_missing, profile_from_row, to_float


class SellerRepository(ABC):
    @abstractmethod
    def get_profile(self, glid: str) -> SellerProfile | None: ...

    @abstractmethod
    def get_context(self, glid: str, max_calls: int = 20) -> SellerContext | None: ...

    @abstractmethod
    def iter_profiles(self) -> Iterator[SellerProfile]: ...

    @abstractmethod
    def search(self, *, state: str | None = None, business_kind: str | None = None,
               with_transcripts: bool | None = None, limit: int = 20) -> list[SellerProfile]: ...


class DuckDBSellerRepository(SellerRepository):
    def __init__(self, warehouse_path: Path, reference_year: int = 2026):
        self.path = str(warehouse_path)
        self.reference_year = reference_year
        self._con = duckdb.connect(self.path, read_only=True)

    def _rows(self, sql: str, params: list | None = None) -> list[dict]:
        cur = self._con.cursor()   # one cursor per call: safe across threads
        try:
            res = cur.execute(sql, params or [])
            cols = [d[0] for d in res.description]
            return [dict(zip(cols, r)) for r in res.fetchall()]
        finally:
            cur.close()

    def get_profile(self, glid: str) -> SellerProfile | None:
        rows = self._rows("SELECT * FROM v_seller WHERE glid = ? LIMIT 1", [str(glid)])
        return profile_from_row(rows[0], self.reference_year) if rows else None

    def get_calls(self, glid: str, limit: int = 20) -> list[BotCall]:
        rows = self._rows(
            "SELECT * FROM v_bot_calls WHERE glid = ? ORDER BY call_start_time DESC NULLS LAST LIMIT ?",
            [str(glid), limit])
        return [_call(r) for r in rows]

    def get_turns(self, attempt_ids: list[str]) -> list[CallTurn]:
        if not attempt_ids:
            return []
        rows = self._rows(
            f"SELECT * FROM v_turns WHERE attempt_key IN ({','.join('?' * len(attempt_ids))}) "
            "ORDER BY attempt_key, turn_no", attempt_ids)
        return [CallTurn(attempt_id=r["attempt_key"], turn_no=int(r["turn_no"]), speaker=str(r["speaker"] or "unknown"),
                         start_s=to_float(r.get("start_sec")), end_s=to_float(r.get("end_sec")),
                         text="" if is_missing(r.get("text")) else str(r["text"])) for r in rows]

    def get_context(self, glid: str, max_calls: int = 20) -> SellerContext | None:
        profile = self.get_profile(glid)
        if profile is None:
            return None
        calls = self.get_calls(glid, max_calls)
        turns = self.get_turns([c.attempt_id for c in calls if c.has_transcript])
        return SellerContext(profile=profile, calls=calls, turns=turns)

    def iter_profiles(self) -> Iterator[SellerProfile]:
        for r in self._rows("SELECT * FROM v_seller"):
            yield profile_from_row(r, self.reference_year)

    def search(self, *, state=None, business_kind=None, with_transcripts=None, limit=20) -> list[SellerProfile]:
        sql = "SELECT s.* FROM v_seller s WHERE 1=1"
        params: list = []
        if state:
            sql += " AND lower(s.seller_state) = lower(?)"
            params.append(state)
        if with_transcripts is not None:
            op = "" if with_transcripts else "NOT "
            sql += f" AND {op}EXISTS (SELECT 1 FROM v_bot_calls c WHERE c.glid = s.glid AND c.has_turn_transcript = 1)"
        sql += " ORDER BY s.glid LIMIT ?"
        params.append(limit * 5 if business_kind else limit)
        profiles = [profile_from_row(r, self.reference_year) for r in self._rows(sql, params)]
        if business_kind:
            profiles = [p for p in profiles if p.business_kind.value == business_kind]
        return profiles[:limit]

    def close(self) -> None:
        self._con.close()


def _call(r: dict) -> BotCall:
    return BotCall(
        attempt_id=r["attempt_key"], glid=r["glid"],
        bot_version=None if is_missing(r.get("lead_bot_version")) else str(r["lead_bot_version"]),
        bucket=None if is_missing(r.get("redis_bucket")) else str(r["redis_bucket"]),
        started_at=r.get("call_start_time") if not is_missing(r.get("call_start_time")) else None,
        duration_s=to_float(r.get("lead_call_duration")),
        summary=None if is_missing(r.get("lead_call_summary")) else str(r["lead_call_summary"]),
        disposition=None if is_missing(r.get("disposition_label")) else str(r["disposition_label"]),
        meeting_fixed=bool(to_float(r.get("meeting_fixed")) or 0),
        has_transcript=bool(to_float(r.get("has_turn_transcript")) or 0),
    )
