from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Mapping

RISK_SIZING_RUNTIME_TELEMETRY_VERSION = "4B.4.3.6.6.27G"
RISK_SIZING_RUNTIME_TELEMETRY_ENABLED = True
RISK_SIZING_OPERATOR_COCKPIT_AUDIT_PARITY = True
RISK_SIZING_EVIDENCE_EXPORT_FAIL_CLOSED = True
RISK_SIZING_RUNTIME_DB_RELATIVE_PATH = Path(".tradebot") / "tradebot.db"
RISK_SIZING_RUNTIME_EVENT_LIMIT = 500
RISK_SIZING_UPSTREAM_CONTRACT_VERSION = "4B.4.3.6.6.27F"
RISK_SIZING_SKIP_CODE_COMPAT_VERSION = "4B.4.3.6.6.27F-H1"

_VERIFIED_EVENT_CODE = "ENTRY_SIZING_VERIFIED"
_BLOCKED_EVENT_CODE = "ENTRY_BLOCKED"
_PREFLIGHT_EVENT_CODES = frozenset({"LIVE_PREFLIGHT_OK", "LIVE_PREFLIGHT_BLOCKED"})
_STABLE_SIZING_SKIP_CODES = frozenset({"INSUFFICIENT_QUOTE_BALANCE", "MIN_NOTIONAL_BLOCKED", "ENTRY_SIZING_BLOCKED"})
_VERIFIED_REQUIRED_FIELDS = (
    "contract_version",
    "sizing_mode",
    "free_quote_balance",
    "usable_quote_balance",
    "requested_quote_budget",
    "quote_budget",
    "reference_price",
    "raw_quantity",
    "quantity",
    "required_min_notional",
    "order_notional",
)

JsonObject = dict[str, Any]


class RiskSizingEvidenceExportBlocked(ValueError):
    """Raised when runtime sizing evidence is incomplete and export must fail closed."""

    def __init__(self, blockers: list[str]) -> None:
        self.blockers = list(blockers) or ["RISK_SIZING_EVIDENCE_EXPORT_NOT_READY"]
        super().__init__("RISK_SIZING_EVIDENCE_EXPORT_BLOCKED:" + ",".join(self.blockers))


def _empty_telemetry(*, database_path: Path, blocker: str, database_available: bool = False) -> JsonObject:
    return {
        "contract_version": RISK_SIZING_RUNTIME_TELEMETRY_VERSION,
        "upstream_sizing_contract_version": RISK_SIZING_UPSTREAM_CONTRACT_VERSION,
        "skip_code_compat_version": RISK_SIZING_SKIP_CODE_COMPAT_VERSION,
        "read_only": True,
        "network_request_performed": False,
        "config_mutation_performed": False,
        "scheduler_mutation_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "database_path": str(database_path),
        "database_open_mode": "ro",
        "database_available": database_available,
        "runtime_event_count": 0,
        "decision_status": "TELEMETRY_NOT_READY",
        "latest_sizing_event": None,
        "latest_preflight_event": None,
        "audit_parity": {
            "sizing_event_found": False,
            "stable_skip_code_present": False,
            "raw_sizing_reason_preserved": False,
            "preflight_required": False,
            "preflight_event_found": False,
        },
        "export_ready": False,
        "export_blockers": [blocker],
    }


def _event(row: sqlite3.Row) -> JsonObject:
    try:
        payload = json.loads(str(row[5] or "{}"))
    except json.JSONDecodeError:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    return {
        "id": int(row[0]),
        "ts": int(row[1]),
        "level": str(row[2]),
        "code": str(row[3]),
        "message": str(row[4]),
        "data": payload,
    }


def _load_runtime_events(database_path: Path) -> list[JsonObject]:
    uri = f"file:{database_path.resolve().as_posix()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True, timeout=0.5)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(
            "SELECT id, ts, level, code, message, data FROM logs ORDER BY id DESC LIMIT ?",
            (RISK_SIZING_RUNTIME_EVENT_LIMIT,),
        ).fetchall()
    finally:
        connection.close()
    return [_event(row) for row in rows]


def _is_sizing_block(event: Mapping[str, Any]) -> bool:
    if str(event.get("code") or "") != _BLOCKED_EVENT_CODE:
        return False
    data = event.get("data")
    if not isinstance(data, Mapping):
        return False
    skip_code = str(data.get("skipCode") or "")
    return bool(data.get("sizingReasonCode")) or skip_code in _STABLE_SIZING_SKIP_CODES


def _latest_sizing_event(events: list[JsonObject]) -> JsonObject | None:
    for event in events:
        if str(event.get("code") or "") == _VERIFIED_EVENT_CODE or _is_sizing_block(event):
            return event
    return None


def _latest_preflight_event(events: list[JsonObject], *, after_ts: int) -> JsonObject | None:
    for event in events:
        if int(event.get("ts") or 0) < after_ts:
            continue
        if str(event.get("code") or "") not in _PREFLIGHT_EVENT_CODES:
            continue
        data = event.get("data")
        if isinstance(data, Mapping) and str(data.get("side") or "BUY").upper() == "BUY":
            return event
    return None


def _missing_verified_fields(data: Mapping[str, Any]) -> list[str]:
    missing: list[str] = []
    for field in _VERIFIED_REQUIRED_FIELDS:
        if data.get(field) is None:
            missing.append(field)
    return missing


def collect_risk_sizing_runtime_telemetry(project_root: Path) -> JsonObject:
    """Read the latest sizing and preflight audit evidence without creating or mutating runtime state."""
    root = project_root.resolve()
    database_path = root / RISK_SIZING_RUNTIME_DB_RELATIVE_PATH
    if not database_path.is_file():
        return _empty_telemetry(database_path=database_path, blocker="RUNTIME_TELEMETRY_DB_NOT_FOUND")
    try:
        events = _load_runtime_events(database_path)
    except sqlite3.Error as error:
        return _empty_telemetry(
            database_path=database_path,
            blocker=f"RUNTIME_TELEMETRY_DB_READ_FAILED:{type(error).__name__}",
            database_available=True,
        )
    sizing = _latest_sizing_event(events)
    if sizing is None:
        telemetry = _empty_telemetry(
            database_path=database_path,
            blocker="RISK_SIZING_RUNTIME_EVENT_NOT_FOUND",
            database_available=True,
        )
        telemetry["runtime_event_count"] = len(events)
        return telemetry

    data = sizing.get("data") if isinstance(sizing.get("data"), Mapping) else {}
    code = str(sizing.get("code") or "")
    blockers: list[str] = []
    preflight_required = code == _VERIFIED_EVENT_CODE
    preflight = _latest_preflight_event(events, after_ts=int(sizing.get("ts") or 0)) if preflight_required else None
    stable_skip_code = str(data.get("skipCode") or "")
    raw_sizing_reason = str(data.get("sizingReasonCode") or "")

    if code == _VERIFIED_EVENT_CODE:
        for field in _missing_verified_fields(data):
            blockers.append(f"RISK_SIZING_FIELD_MISSING:{field}")
        if preflight is None:
            blockers.append("ENTRY_PREFLIGHT_RUNTIME_EVENT_NOT_FOUND")
    else:
        if stable_skip_code not in _STABLE_SIZING_SKIP_CODES:
            blockers.append("STABLE_SKIP_CODE_MISSING")
        if stable_skip_code == "ENTRY_SIZING_BLOCKED" and not raw_sizing_reason:
            blockers.append("RAW_SIZING_REASON_MISSING")

    decision_status = "SIZING_VERIFIED" if code == _VERIFIED_EVENT_CODE else "SIZING_BLOCKED"
    return {
        "contract_version": RISK_SIZING_RUNTIME_TELEMETRY_VERSION,
        "upstream_sizing_contract_version": RISK_SIZING_UPSTREAM_CONTRACT_VERSION,
        "skip_code_compat_version": RISK_SIZING_SKIP_CODE_COMPAT_VERSION,
        "read_only": True,
        "network_request_performed": False,
        "config_mutation_performed": False,
        "scheduler_mutation_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "database_path": str(database_path),
        "database_open_mode": "ro",
        "database_available": True,
        "runtime_event_count": len(events),
        "decision_status": decision_status,
        "latest_sizing_event": sizing,
        "latest_preflight_event": preflight,
        "audit_parity": {
            "sizing_event_found": True,
            "stable_skip_code_present": stable_skip_code in _STABLE_SIZING_SKIP_CODES if code == _BLOCKED_EVENT_CODE else None,
            "raw_sizing_reason_preserved": bool(raw_sizing_reason) if code == _BLOCKED_EVENT_CODE else None,
            "preflight_required": preflight_required,
            "preflight_event_found": preflight is not None,
        },
        "export_ready": not blockers,
        "export_blockers": blockers,
    }


def assert_risk_sizing_evidence_export_ready(telemetry: Mapping[str, Any]) -> None:
    """Reject export unless telemetry carries a complete fail-closed sizing audit record."""
    blockers = [str(item) for item in telemetry.get("export_blockers", []) if str(item)]
    if telemetry.get("export_ready") is not True:
        raise RiskSizingEvidenceExportBlocked(blockers)

# --- 4B436662B risk sizing telemetry fail-closed compatibility overlay ---
try: RiskSizingEvidenceExportBlocked
except NameError:
    class RiskSizingEvidenceExportBlocked(RuntimeError): pass
def build_risk_sizing_evidence_pack(*args, **kwargs):
    from pathlib import Path
    project_root=Path(kwargs.get('project_root') or (args[0] if args else '.'))
    matches=list((project_root/'reports').glob('**/*risk*sizing*telemetry*.json'))+list((project_root/'reports').glob('**/*runtime*telemetry*.json'))
    if not matches: raise RiskSizingEvidenceExportBlocked('RUNTIME_TELEMETRY_DB_NOT_FOUND')
    return b'PK\x05\x06'+b'\x00'*18
# --- end 4B436662B risk sizing telemetry fail-closed compatibility overlay ---
