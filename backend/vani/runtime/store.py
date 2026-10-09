"""Session persistence. Interface + SQLite (default) + in-memory (tests).

Sessions are stored as JSON documents; switch events also go to their own table
so the switch log can be queried across calls. Swap for Redis/Postgres by
implementing SessionStore.
"""
import json
import sqlite3
import threading
from abc import ABC, abstractmethod
from pathlib import Path

from vani.domain.live import CallSession, SwitchEvent


class SessionStore(ABC):
    @abstractmethod
    def get(self, session_id: str) -> CallSession | None: ...

    @abstractmethod
    def save(self, session: CallSession, new_events: list[SwitchEvent] | None = None) -> None: ...

    @abstractmethod
    def switch_log(self, seller_glid: str | None = None, limit: int = 200) -> list[SwitchEvent]: ...

    @abstractmethod
    def list_sessions(self, limit: int = 50) -> list[dict]: ...


class MemorySessionStore(SessionStore):
    def __init__(self):
        self._s: dict[str, str] = {}
        self._events: list[tuple[str, SwitchEvent]] = []

    def get(self, session_id):
        raw = self._s.get(session_id)
        return CallSession.model_validate_json(raw) if raw else None

    def save(self, session, new_events=None):
        self._s[session.session_id] = session.model_dump_json()
        self._events += [(session.seller_glid, e) for e in new_events or []]

    def switch_log(self, seller_glid=None, limit=200):
        return [e for g, e in reversed(self._events) if seller_glid in (None, g)][:limit]

    def list_sessions(self, limit=50):
        out = [CallSession.model_validate_json(v) for v in self._s.values()]
        out.sort(key=lambda s: s.created_at, reverse=True)
        return [_summary(s) for s in out[:limit]]


class SQLiteSessionStore(SessionStore):
    def __init__(self, path: Path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._db = sqlite3.connect(str(path), check_same_thread=False)
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY, seller_glid TEXT NOT NULL, channel TEXT, status TEXT,
                outcome TEXT, created_at TEXT, updated_at TEXT DEFAULT CURRENT_TIMESTAMP, doc TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS ix_sessions_seller ON sessions(seller_glid);
            CREATE TABLE IF NOT EXISTS switch_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, seller_glid TEXT, turn INTEGER,
                signal TEXT, doc TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS ix_events_seller ON switch_events(seller_glid);
        """)

    def get(self, session_id):
        row = self._db.execute("SELECT doc FROM sessions WHERE session_id = ?", (session_id,)).fetchone()
        return CallSession.model_validate_json(row[0]) if row else None

    def save(self, session, new_events=None):
        with self._lock, self._db:
            self._db.execute(
                "INSERT INTO sessions (session_id, seller_glid, channel, status, outcome, created_at, doc) "
                "VALUES (?,?,?,?,?,?,?) ON CONFLICT(session_id) DO UPDATE SET status=excluded.status, "
                "outcome=excluded.outcome, doc=excluded.doc, updated_at=CURRENT_TIMESTAMP",
                (session.session_id, session.seller_glid, session.channel.value, session.status.value,
                 session.outcome.value, session.created_at.isoformat(), session.model_dump_json()))
            for e in new_events or []:
                self._db.execute(
                    "INSERT INTO switch_events (session_id, seller_glid, turn, signal, doc) VALUES (?,?,?,?,?)",
                    (session.session_id, session.seller_glid, e.turn, e.signal.value, e.model_dump_json()))

    def switch_log(self, seller_glid=None, limit=200):
        sql, params = "SELECT doc FROM switch_events", []
        if seller_glid:
            sql += " WHERE seller_glid = ?"
            params.append(seller_glid)
        rows = self._db.execute(sql + " ORDER BY id DESC LIMIT ?", (*params, limit)).fetchall()
        return [SwitchEvent.model_validate_json(r[0]) for r in rows]

    def list_sessions(self, limit=50):
        rows = self._db.execute("SELECT doc FROM sessions ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [_summary(CallSession.model_validate_json(r[0])) for r in rows]

    def close(self):
        self._db.close()


def _summary(s: CallSession) -> dict:
    return {"session_id": s.session_id, "seller_glid": s.seller_glid, "channel": s.channel.value,
            "status": s.status.value, "outcome": s.outcome.value, "switches": len(s.switch_log),
            "turns": len(s.transcript), "persona": s.persona.label, "created_at": s.created_at.isoformat()}
