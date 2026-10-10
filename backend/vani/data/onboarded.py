"""Sellers who joined after the dataset snapshot: stored in SQLite, served next to the warehouse.

A new seller is saved as a row with the SAME column names as v_seller, so the one
normaliser (profile_from_row) and the one persona generator handle both. They have
no call history, so the persona falls back to what similar real sellers did
(state, business type, turnover segments in the evidence book) and adapts live.
"""
import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from vani.domain.seller import SellerContext, SellerProfile

from .normalize import profile_from_row
from .repository import SellerRepository

NEW_SELLER_TYPE = "New seller (onboarded)"


class OnboardedSellerStore:
    def __init__(self, path: Path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._con = sqlite3.connect(str(path), check_same_thread=False)
        self._lock = threading.Lock()
        with self._lock:
            self._con.execute("PRAGMA journal_mode=WAL")
            self._con.execute("CREATE TABLE IF NOT EXISTS onboarded_sellers "
                              "(glid TEXT PRIMARY KEY, row TEXT NOT NULL, created_at TEXT NOT NULL)")
            self._con.commit()

    def put(self, row: dict) -> str:
        glid = str(row.get("fk_glusr_usr_id") or f"new{uuid.uuid4().int % 10**8:08d}")
        row = {**row, "fk_glusr_usr_id": glid, "glid": glid, "customer_type": NEW_SELLER_TYPE}
        with self._lock:
            self._con.execute("INSERT OR REPLACE INTO onboarded_sellers VALUES (?, ?, ?)",
                              (glid, json.dumps(row, ensure_ascii=False), datetime.now(timezone.utc).isoformat()))
            self._con.commit()
        return glid

    def get(self, glid: str) -> dict | None:
        with self._lock:
            r = self._con.execute("SELECT row FROM onboarded_sellers WHERE glid = ?", (str(glid),)).fetchone()
        return json.loads(r[0]) if r else None

    def all(self) -> list[dict]:
        with self._lock:
            rows = self._con.execute("SELECT row FROM onboarded_sellers ORDER BY created_at DESC").fetchall()
        return [json.loads(r[0]) for r in rows]

    def delete(self, glid: str) -> bool:
        with self._lock:
            n = self._con.execute("DELETE FROM onboarded_sellers WHERE glid = ?", (str(glid),)).rowcount
            self._con.commit()
        return n > 0


class OnboardingRepository(SellerRepository):
    """The warehouse first, then sellers onboarded since the snapshot."""

    def __init__(self, base: SellerRepository, store: OnboardedSellerStore, reference_year: int = 2026):
        self.base, self.store, self.reference_year = base, store, reference_year

    def exists_in_base(self, glid: str) -> bool:
        return self.base.get_profile(glid) is not None

    def get_profile(self, glid: str) -> SellerProfile | None:
        p = self.base.get_profile(glid)
        if p is not None:
            return p
        row = self.store.get(glid)
        return profile_from_row(row, self.reference_year) if row else None

    def get_context(self, glid: str, max_calls: int = 20) -> SellerContext | None:
        ctx = self.base.get_context(glid, max_calls)
        if ctx is not None:
            return ctx
        row = self.store.get(glid)
        return SellerContext(profile=profile_from_row(row, self.reference_year), calls=[], turns=[]) if row else None

    def iter_profiles(self) -> Iterator[SellerProfile]:
        yield from self.base.iter_profiles()
        for row in self.store.all():
            yield profile_from_row(row, self.reference_year)

    def search(self, *, state=None, business_kind=None, with_transcripts=None, limit=20) -> list[SellerProfile]:
        return self.base.search(state=state, business_kind=business_kind, with_transcripts=with_transcripts, limit=limit)

    def onboarded(self) -> list[SellerProfile]:
        return [profile_from_row(r, self.reference_year) for r in self.store.all()]

    def __getattr__(self, name):          # get_calls / get_turns / close on the warehouse
        return getattr(self.base, name)
