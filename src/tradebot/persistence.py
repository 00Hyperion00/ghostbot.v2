from __future__ import annotations

import json
import shutil
import sqlite3
import threading
from pathlib import Path
from typing import Any

from .models import LogEvent
from .observability import normalize_audit_event

SQLITE_AUDIT_LEDGER_CONTRACT_VERSION = "4B.4.3.6.6.29C"
SQLITE_AUDIT_LEDGER_SCHEMA_VERSION = 2
SQLITE_AUDIT_LEDGER_UPGRADE_ENABLED = True
SQLITE_STORE_EXPLICIT_CLOSE_HOTFIX_VERSION = "4B.4.3.6.6.29C-H1"


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
        # 4B.4.3.6.6.29C SQLite audit ledger baseline: WAL + busy timeout + FK guard.
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
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    applied_at INTEGER NOT NULL,
                    description TEXT NOT NULL
                )
                """
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
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts INTEGER NOT NULL,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    order_id TEXT NOT NULL,
                    client_order_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    price REAL,
                    qty REAL,
                    notional REAL,
                    source TEXT NOT NULL,
                    raw TEXT NOT NULL
                )
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS fills (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts INTEGER NOT NULL,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    order_id TEXT NOT NULL,
                    client_order_id TEXT NOT NULL,
                    fill_id TEXT NOT NULL,
                    price REAL,
                    qty REAL,
                    fee_asset TEXT NOT NULL,
                    fee REAL,
                    source TEXT NOT NULL,
                    raw TEXT NOT NULL
                )
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS positions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts INTEGER NOT NULL,
                    symbol TEXT NOT NULL,
                    state TEXT NOT NULL,
                    qty REAL,
                    entry_price REAL,
                    mark_price REAL,
                    unrealized_pnl REAL,
                    realized_pnl REAL,
                    source TEXT NOT NULL,
                    raw TEXT NOT NULL
                )
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS risk_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts INTEGER NOT NULL,
                    symbol TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    reason_code TEXT NOT NULL,
                    message TEXT NOT NULL,
                    raw TEXT NOT NULL
                )
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS model_decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts INTEGER NOT NULL,
                    symbol TEXT NOT NULL,
                    signal TEXT NOT NULL,
                    confidence REAL,
                    provider TEXT NOT NULL,
                    model_path TEXT NOT NULL,
                    schema_version TEXT NOT NULL,
                    raw TEXT NOT NULL
                )
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS balance_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts INTEGER NOT NULL,
                    asset TEXT NOT NULL,
                    free REAL,
                    locked REAL,
                    source TEXT NOT NULL,
                    raw TEXT NOT NULL
                )
                """
            )
            self._create_audit_indexes()
            self._apply_schema_version(SQLITE_AUDIT_LEDGER_SCHEMA_VERSION)

    def _create_audit_indexes(self) -> None:
        index_sql = (
            "CREATE INDEX IF NOT EXISTS idx_logs_ts ON logs(ts)",
            "CREATE INDEX IF NOT EXISTS idx_operator_actions_ts ON operator_actions(ts)",
            "CREATE INDEX IF NOT EXISTS idx_operator_actions_action_ts ON operator_actions(action, ts)",
            "CREATE INDEX IF NOT EXISTS idx_orders_symbol_ts ON orders(symbol, ts)",
            "CREATE INDEX IF NOT EXISTS idx_orders_order_id ON orders(order_id)",
            "CREATE INDEX IF NOT EXISTS idx_fills_symbol_ts ON fills(symbol, ts)",
            "CREATE INDEX IF NOT EXISTS idx_positions_symbol_ts ON positions(symbol, ts)",
            "CREATE INDEX IF NOT EXISTS idx_risk_events_symbol_ts ON risk_events(symbol, ts)",
            "CREATE INDEX IF NOT EXISTS idx_model_decisions_symbol_ts ON model_decisions(symbol, ts)",
            "CREATE INDEX IF NOT EXISTS idx_balance_snapshots_asset_ts ON balance_snapshots(asset, ts)",
        )
        for statement in index_sql:
            self._conn.execute(statement)

    def _apply_schema_version(self, version: int) -> None:
        self._conn.execute(f"PRAGMA user_version = {int(version)}")
        self._conn.execute(
            "INSERT INTO schema_meta(key, value) VALUES('schema_version', ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (str(int(version)),),
        )
        self._conn.execute(
            "INSERT OR IGNORE INTO schema_migrations(version, applied_at, description) VALUES(?, strftime('%s','now') * 1000, ?)",
            (int(version), f"{SQLITE_AUDIT_LEDGER_CONTRACT_VERSION} audit ledger schema baseline"),
        )

    @staticmethod
    def _json(value: Any) -> str:
        return json.dumps(value or {}, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    @staticmethod
    def _text(payload: dict[str, Any], *keys: str, default: str = "") -> str:
        for key in keys:
            value = payload.get(key)
            if value is not None:
                return str(value)
        return default

    @staticmethod
    def _float_or_none(payload: dict[str, Any], *keys: str) -> float | None:
        for key in keys:
            value = payload.get(key)
            if value is None or value == "":
                continue
            try:
                return float(value)
            except (TypeError, ValueError):
                return None
        return None

    @staticmethod
    def _ts(ts: int | None = None) -> int:
        if ts is not None:
            return int(ts)
        import time
        return int(time.time() * 1000)

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

    def append_operator_action(self, *, action: str, actor: str, confirmation: str = "", outcome: str, data: dict[str, Any] | None = None, ts: int | None = None) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO operator_actions(ts, action, actor, confirmation, outcome, data) VALUES(?, ?, ?, ?, ?, ?)",
                (self._ts(ts), str(action), str(actor), str(confirmation or ""), str(outcome), self._json(data)),
            )

    def append_order_audit(self, payload: dict[str, Any], *, ts: int | None = None) -> None:
        price = self._float_or_none(payload, "price")
        qty = self._float_or_none(payload, "qty", "quantity")
        notional = self._float_or_none(payload, "notional")
        if notional is None and price is not None and qty is not None:
            notional = price * qty
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO orders(ts, symbol, side, order_id, client_order_id, status, price, qty, notional, source, raw) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    self._ts(ts),
                    self._text(payload, "symbol", default="UNKNOWN"),
                    self._text(payload, "side", default="UNKNOWN"),
                    self._text(payload, "order_id", "orderId", default=""),
                    self._text(payload, "client_order_id", "clientOrderId", default=""),
                    self._text(payload, "status", default="UNKNOWN"),
                    price,
                    qty,
                    notional,
                    self._text(payload, "source", default="audit"),
                    self._json(payload),
                ),
            )

    def append_fill_audit(self, payload: dict[str, Any], *, ts: int | None = None) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO fills(ts, symbol, side, order_id, client_order_id, fill_id, price, qty, fee_asset, fee, source, raw) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    self._ts(ts),
                    self._text(payload, "symbol", default="UNKNOWN"),
                    self._text(payload, "side", default="UNKNOWN"),
                    self._text(payload, "order_id", "orderId", default=""),
                    self._text(payload, "client_order_id", "clientOrderId", default=""),
                    self._text(payload, "fill_id", "tradeId", "id", default=""),
                    self._float_or_none(payload, "price"),
                    self._float_or_none(payload, "qty", "quantity", "executedQty"),
                    self._text(payload, "fee_asset", "commissionAsset", default=""),
                    self._float_or_none(payload, "fee", "commission"),
                    self._text(payload, "source", default="audit"),
                    self._json(payload),
                ),
            )

    def append_position_audit(self, payload: dict[str, Any], *, ts: int | None = None) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO positions(ts, symbol, state, qty, entry_price, mark_price, unrealized_pnl, realized_pnl, source, raw) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    self._ts(ts),
                    self._text(payload, "symbol", default="UNKNOWN"),
                    self._text(payload, "state", default="UNKNOWN"),
                    self._float_or_none(payload, "qty", "quantity"),
                    self._float_or_none(payload, "entry_price", "entryPrice"),
                    self._float_or_none(payload, "mark_price", "markPrice"),
                    self._float_or_none(payload, "unrealized_pnl", "unrealizedPnl"),
                    self._float_or_none(payload, "realized_pnl", "realizedPnl"),
                    self._text(payload, "source", default="audit"),
                    self._json(payload),
                ),
            )

    def append_risk_event(self, payload: dict[str, Any], *, ts: int | None = None) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO risk_events(ts, symbol, event_type, severity, reason_code, message, raw) VALUES(?, ?, ?, ?, ?, ?, ?)",
                (
                    self._ts(ts),
                    self._text(payload, "symbol", default="UNKNOWN"),
                    self._text(payload, "event_type", "eventType", default="RISK_EVENT"),
                    self._text(payload, "severity", default="INFO"),
                    self._text(payload, "reason_code", "reasonCode", default=""),
                    self._text(payload, "message", default=""),
                    self._json(payload),
                ),
            )

    def append_model_decision(self, payload: dict[str, Any], *, ts: int | None = None) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO model_decisions(ts, symbol, signal, confidence, provider, model_path, schema_version, raw) VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    self._ts(ts),
                    self._text(payload, "symbol", default="UNKNOWN"),
                    self._text(payload, "signal", default="HOLD"),
                    self._float_or_none(payload, "confidence"),
                    self._text(payload, "provider", default="UNKNOWN"),
                    self._text(payload, "model_path", "modelPath", default=""),
                    self._text(payload, "schema_version", "schemaVersion", default=""),
                    self._json(payload),
                ),
            )

    def append_balance_snapshot(self, payload: dict[str, Any], *, ts: int | None = None) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO balance_snapshots(ts, asset, free, locked, source, raw) VALUES(?, ?, ?, ?, ?, ?)",
                (
                    self._ts(ts),
                    self._text(payload, "asset", default="UNKNOWN"),
                    self._float_or_none(payload, "free"),
                    self._float_or_none(payload, "locked"),
                    self._text(payload, "source", default="audit"),
                    self._json(payload),
                ),
            )

    def fetch_table_count(self, table: str) -> int:
        allowed = {
            "kv", "logs", "schema_meta", "schema_migrations", "operator_actions",
            "orders", "fills", "positions", "risk_events", "model_decisions", "balance_snapshots",
        }
        if table not in allowed:
            raise ValueError(f"Unsupported table for count: {table}")
        with self._lock:
            row = self._conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
        return int(row[0]) if row else 0

    def audit_ledger_snapshot(self) -> dict[str, Any]:
        tables = [
            "schema_migrations", "operator_actions", "orders", "fills", "positions",
            "risk_events", "model_decisions", "balance_snapshots",
        ]
        with self._lock:
            existing = {
                row[0]
                for row in self._conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            }
            user_version = self._conn.execute("PRAGMA user_version").fetchone()
        return {
            "ok": all(table in existing for table in tables),
            "contract_version": SQLITE_AUDIT_LEDGER_CONTRACT_VERSION,
            "schema_version": int(user_version[0]) if user_version else 0,
            "tables": {table: table in existing for table in tables},
            "runtime_activation_blocked": True,
            "paper_live_order_blocked": True,
            "training_reload_blocked": True,
        }

    def integrity_check(self) -> dict[str, Any]:
        with self._lock:
            rows = self._conn.execute("PRAGMA integrity_check").fetchall()
            journal = self._conn.execute("PRAGMA journal_mode").fetchone()
            user_version = self._conn.execute("PRAGMA user_version").fetchone()
        results = [str(row[0]) for row in rows]
        return {
            "ok": results == ["ok"],
            "contract_version": SQLITE_AUDIT_LEDGER_CONTRACT_VERSION,
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

    def close(self) -> None:
        """Close the SQLite handle so Windows can release WAL/temp probe files."""
        with self._lock:
            try:
                self._conn.commit()
            finally:
                self._conn.close()

    def __enter__(self) -> "SQLiteStore":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()

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
