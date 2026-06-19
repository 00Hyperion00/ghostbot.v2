from __future__ import annotations

import json
import shutil
import sqlite3
import threading
from pathlib import Path
from typing import Any

from .models import LogEvent
from .observability import normalize_audit_event


class SQLiteStore:
    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._configure_connection()
        self._bootstrap()

    def _configure_connection(self) -> None:
        # 4B.4.3.6.6.29A SQLite audit baseline: avoid silent lock errors and enable WAL.
        self._conn.execute("PRAGMA busy_timeout = 5000")
        self._conn.execute("PRAGMA journal_mode = WAL")
        self._conn.execute("PRAGMA foreign_keys = ON")

    def _bootstrap(self) -> None:
        with self._conn:
            self._conn.execute(
                "CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts INTEGER NOT NULL,
                    level TEXT NOT NULL,
                    code TEXT NOT NULL,
                    message TEXT NOT NULL,
                    data TEXT NOT NULL
                )
                """
            )

            self._conn.execute(
                "CREATE TABLE IF NOT EXISTS schema_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS operator_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    confirmation TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    data TEXT NOT NULL
                )
                """
            )
            self._conn.execute("PRAGMA user_version = 1")
            self._conn.execute(
                "INSERT INTO schema_meta(key, value) VALUES('schema_version', '1') "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value"
            )

    def set_json(self, key: str, value: Any) -> None:
        payload = json.dumps(value, ensure_ascii=False, sort_keys=True)
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO kv(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, payload),
            )

    def get_json(self, key: str, default: Any = None) -> Any:
        with self._lock:
            row = self._conn.execute("SELECT value FROM kv WHERE key=?", (key,)).fetchone()
        if not row:
            return default
        return json.loads(row[0])

    def append_log(self, event: LogEvent) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO logs(ts, level, code, message, data) VALUES(?, ?, ?, ?, ?)",
                (event.ts, event.level, event.code, event.message, json.dumps(event.data, ensure_ascii=False, sort_keys=True)),
            )

    def fetch_logs(self, limit: int = 200, *, order: str = 'desc') -> list[dict[str, Any]]:
        order_sql = 'ASC' if order.lower() == 'asc' else 'DESC'
        sql = f"SELECT ts, level, code, message, data FROM logs ORDER BY id {order_sql}"
        params: tuple[Any, ...] = ()
        if limit > 0:
            sql += ' LIMIT ?'
            params = (limit,)
        with self._lock:
            rows = self._conn.execute(sql, params).fetchall()
        out: list[dict[str, Any]] = []
        for row in rows:
            out.append(normalize_audit_event({
                'ts': row[0],
                'level': row[1],
                'code': row[2],
                'message': row[3],
                'data': json.loads(row[4]),
            }))
        return out



    def integrity_check(self) -> dict[str, Any]:
        with self._lock:
            rows = self._conn.execute("PRAGMA integrity_check").fetchall()
            journal = self._conn.execute("PRAGMA journal_mode").fetchone()
            user_version = self._conn.execute("PRAGMA user_version").fetchone()
        results = [str(row[0]) for row in rows]
        return {
            "ok": results == ["ok"],
            "contract_version": "4B.4.3.6.6.29A",
            "integrity_check": results,
            "journal_mode": str(journal[0]) if journal else None,
            "schema_version": int(user_version[0]) if user_version else 0,
        }

    def backup_to(self, destination: str | Path) -> Path:
        target = Path(destination)
        target.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            self._conn.commit()
            shutil.copy2(self.path, target)
        return target

    def fetch_audit_events(
        self,
        limit: int = 200,
        *,
        order: str = 'desc',
        category: str | None = None,
        severity: str | None = None,
        code_prefix: str | None = None,
        since_ts: int | None = None,
    ) -> list[dict[str, Any]]:
        events = self.fetch_logs(limit=0, order=order)
        category_q = str(category or '').strip().lower()
        severity_q = str(severity or '').strip().lower()
        code_q = str(code_prefix or '').strip().upper()
        filtered: list[dict[str, Any]] = []
        for event in events:
            if since_ts is not None and int(event.get('ts') or 0) < int(since_ts):
                continue
            if category_q and str(event.get('category') or '').lower() != category_q:
                continue
            if severity_q and str(event.get('severity') or '').lower() != severity_q:
                continue
            if code_q and not str(event.get('code') or '').upper().startswith(code_q):
                continue
            filtered.append(event)
        if limit > 0:
            return filtered[:limit]
        return filtered
