from __future__ import annotations

import io
import json
import sqlite3
import threading
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

import pytest

from tradebot.operator_cockpit_v2_desktop_wrapper import NATIVE_DESKTOP_ACTIONS, NATIVE_DESKTOP_EXPORT_BRIDGE_JS
from tradebot.operator_cockpit_v2_read_only import (
    DASHBOARD_HTML,
    OPERATOR_COCKPIT_V2_RISK_SIZING_AUDIT_PARITY,
    OPERATOR_COCKPIT_V2_RISK_SIZING_EVIDENCE_EXPORT_FAIL_CLOSED,
    OPERATOR_COCKPIT_V2_RISK_SIZING_RUNTIME_TELEMETRY,
    OPERATOR_COCKPIT_V2_RISK_SIZING_TELEMETRY_VERSION,
    _build_in_memory_evidence_pack,
    _build_risk_sizing_in_memory_evidence_pack,
    _safe_action_manifest,
    collect_operator_cockpit_snapshot,
    make_operator_cockpit_server,
)
from tradebot.risk_sizing_runtime_telemetry import (
    RiskSizingEvidenceExportBlocked,
    assert_risk_sizing_evidence_export_ready,
    collect_risk_sizing_runtime_telemetry,
)


def _seed_reports(root: Path) -> None:
    reports = root / "reports" / "hyp005_r1_isolated"
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "4B436625V_hyp005_shadow_observation_logger_20260612_160000.json").write_text(json.dumps({"decision": "READY"}), encoding="utf-8")
    (reports / "4B436625X_hyp005_shadow_collection_orchestrator_20260612_160000.json").write_text(json.dumps({"decision": "READY"}), encoding="utf-8")
    (reports / "4B436625Y_hyp005_shadow_operator_daily_audit_20260612_160000.json").write_text(json.dumps({"decision": "READY", "shadow_observation_count": 1, "shadow_sample_target": 30, "approved_for_live_real": False, "post_requests_allowed": False}), encoding="utf-8")
    (reports / "4B436625X_hyp005_shadow_merged_ledger_20260612_160000.jsonl").write_text(json.dumps({"symbol": "ETHUSDT", "timestamp_utc": "2026-06-12T16:00:00+00:00", "observation_id": "HYP005-R1-1", "forward_return_bps_final": 12.0, "spread_slippage_proxy_bps": 4.0}) + "\n", encoding="utf-8")


def _database(root: Path) -> sqlite3.Connection:
    path = root / ".tradebot" / "tradebot.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE logs (id INTEGER PRIMARY KEY AUTOINCREMENT, ts INTEGER NOT NULL, level TEXT NOT NULL, code TEXT NOT NULL, message TEXT NOT NULL, data TEXT NOT NULL)")
    return connection


def _insert(connection: sqlite3.Connection, ts: int, code: str, data: dict[str, object]) -> None:
    connection.execute("INSERT INTO logs(ts, level, code, message, data) VALUES(?, ?, ?, ?, ?)", (ts, "INFO", code, code, json.dumps(data)))
    connection.commit()


def _verified_payload() -> dict[str, object]:
    return {
        "contract_version": "4B.4.3.6.6.27F",
        "sizing_mode": "risk_percent_quote_balance",
        "free_quote_balance": 1000.0,
        "usable_quote_balance": 800.0,
        "requested_quote_budget": 20.0,
        "quote_budget": 20.0,
        "reference_price": 2500.0,
        "raw_quantity": 0.008,
        "quantity": 0.008,
        "required_min_notional": 5.5,
        "order_notional": 20.0,
    }


def _task_query(name: str) -> dict[str, object]:
    return {"task_name": name, "state": "Ready" if "R1" in name else "Disabled", "last_task_result": 0, "number_of_missed_runs": 0}


def _backend_probe(_: str) -> dict[str, object]:
    return {"reachable": True, "status_code": 200, "payload": {"ok": True}}


def test_27g_declares_read_only_runtime_telemetry_audit_parity_contract() -> None:
    assert OPERATOR_COCKPIT_V2_RISK_SIZING_TELEMETRY_VERSION == "4B.4.3.6.6.27G"
    assert OPERATOR_COCKPIT_V2_RISK_SIZING_RUNTIME_TELEMETRY is True
    assert OPERATOR_COCKPIT_V2_RISK_SIZING_AUDIT_PARITY is True
    assert OPERATOR_COCKPIT_V2_RISK_SIZING_EVIDENCE_EXPORT_FAIL_CLOSED is True


def test_27g_missing_database_probe_is_read_only_and_fails_closed(tmp_path: Path) -> None:
    telemetry = collect_risk_sizing_runtime_telemetry(tmp_path)
    assert telemetry["database_open_mode"] == "ro"
    assert telemetry["export_ready"] is False
    assert telemetry["export_blockers"] == ["RUNTIME_TELEMETRY_DB_NOT_FOUND"]
    assert not (tmp_path / ".tradebot" / "tradebot.db").exists()
    with pytest.raises(RiskSizingEvidenceExportBlocked, match="RUNTIME_TELEMETRY_DB_NOT_FOUND"):
        assert_risk_sizing_evidence_export_ready(telemetry)


def test_27g_verified_sizing_requires_preflight_parity_then_becomes_export_ready(tmp_path: Path) -> None:
    connection = _database(tmp_path)
    try:
        _insert(connection, 1000, "ENTRY_SIZING_VERIFIED", _verified_payload())
        blocked = collect_risk_sizing_runtime_telemetry(tmp_path)
        assert blocked["export_ready"] is False
        assert blocked["export_blockers"] == ["ENTRY_PREFLIGHT_RUNTIME_EVENT_NOT_FOUND"]
        _insert(connection, 1001, "LIVE_PREFLIGHT_OK", {"side": "BUY", "symbol": "ETHUSDT"})
    finally:
        connection.close()
    telemetry = collect_risk_sizing_runtime_telemetry(tmp_path)
    assert telemetry["decision_status"] == "SIZING_VERIFIED"
    assert telemetry["export_ready"] is True
    assert telemetry["audit_parity"]["preflight_event_found"] is True
    assert telemetry["latest_preflight_event"]["code"] == "LIVE_PREFLIGHT_OK"


def test_27g_stable_blocked_sizing_is_export_ready_without_preflight(tmp_path: Path) -> None:
    connection = _database(tmp_path)
    try:
        _insert(connection, 1000, "ENTRY_BLOCKED", {"skipCode": "MIN_NOTIONAL_BLOCKED", "sizingReasonCode": "SIZING_QUOTE_BUDGET_BELOW_MIN_NOTIONAL", "sizingContractVersion": "4B.4.3.6.6.27F", "skipCodeCompatVersion": "4B.4.3.6.6.27F-H1"})
    finally:
        connection.close()
    telemetry = collect_risk_sizing_runtime_telemetry(tmp_path)
    assert telemetry["decision_status"] == "SIZING_BLOCKED"
    assert telemetry["export_ready"] is True
    assert telemetry["audit_parity"]["stable_skip_code_present"] is True
    assert telemetry["audit_parity"]["raw_sizing_reason_preserved"] is True
    assert telemetry["audit_parity"]["preflight_required"] is False


def test_27g_snapshot_manifest_and_legacy_pack_remain_backward_compatible(tmp_path: Path) -> None:
    _seed_reports(tmp_path)
    snapshot = collect_operator_cockpit_snapshot(tmp_path, task_query=_task_query, backend_probe=_backend_probe)
    telemetry = snapshot["risk_sizing_runtime_telemetry"]
    assert telemetry["export_ready"] is False
    manifest = _safe_action_manifest(tmp_path)
    enabled = {item["code"]: item for item in manifest["enabled"]}
    assert enabled["DOWNLOAD_RISK_SIZING_EVIDENCE_PACK_ZIP"]["available"] is False
    assert manifest["risk_sizing_evidence_export_gate"]["fail_closed"] is True
    legacy = _build_in_memory_evidence_pack(tmp_path, task_query=_task_query, backend_probe=_backend_probe)
    with zipfile.ZipFile(io.BytesIO(legacy)) as archive:
        assert "operator-cockpit/snapshot.json" in archive.namelist()


def test_27g_risk_sizing_evidence_pack_gate_rejects_missing_and_exports_ready_telemetry(tmp_path: Path) -> None:
    _seed_reports(tmp_path)
    with pytest.raises(RiskSizingEvidenceExportBlocked, match="RUNTIME_TELEMETRY_DB_NOT_FOUND"):
        _build_risk_sizing_in_memory_evidence_pack(tmp_path, task_query=_task_query, backend_probe=_backend_probe)
    connection = _database(tmp_path)
    try:
        _insert(connection, 1000, "ENTRY_SIZING_VERIFIED", _verified_payload())
        _insert(connection, 1001, "LIVE_PREFLIGHT_BLOCKED", {"side": "BUY", "symbol": "ETHUSDT", "reasonCode": "PREFLIGHT_POLICY_BLOCKED"})
    finally:
        connection.close()
    payload = _build_risk_sizing_in_memory_evidence_pack(tmp_path, task_query=_task_query, backend_probe=_backend_probe)
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        names = set(archive.namelist())
        assert "operator-cockpit/risk-sizing-runtime-telemetry.json" in names
        telemetry = json.loads(archive.read("operator-cockpit/risk-sizing-runtime-telemetry.json"))
        assert telemetry["export_ready"] is True
        assert telemetry["latest_preflight_event"]["code"] == "LIVE_PREFLIGHT_BLOCKED"


def test_27g_http_gate_returns_412_until_runtime_evidence_is_ready(tmp_path: Path) -> None:
    _seed_reports(tmp_path)
    server = make_operator_cockpit_server(tmp_path, port=0, task_query=_task_query, backend_probe=_backend_probe)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    base = f"http://{host}:{port}"
    try:
        with urllib.request.urlopen(base + "/api/operator-cockpit-v2/view/risk-sizing-runtime-telemetry.json", timeout=3) as response:
            telemetry = json.loads(response.read().decode("utf-8"))
            assert telemetry["export_ready"] is False
        with pytest.raises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(base + "/api/operator-cockpit-v2/export/risk-sizing-evidence-pack.zip", timeout=3)
        assert caught.value.code == 412
        payload = json.loads(caught.value.read().decode("utf-8"))
        assert "RUNTIME_TELEMETRY_DB_NOT_FOUND" in payload["blockers"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def test_27g_desktop_bridge_and_dashboard_expose_additive_risk_sizing_routes() -> None:
    assert "OPEN_RISK_SIZING_RUNTIME_TELEMETRY_JSON" in NATIVE_DESKTOP_ACTIONS
    assert "DOWNLOAD_RISK_SIZING_EVIDENCE_PACK_ZIP" in NATIVE_DESKTOP_ACTIONS
    assert "/api/operator-cockpit-v2/view/risk-sizing-runtime-telemetry.json" in NATIVE_DESKTOP_EXPORT_BRIDGE_JS
    assert "/api/operator-cockpit-v2/export/risk-sizing-evidence-pack.zip" in NATIVE_DESKTOP_EXPORT_BRIDGE_JS
    assert "Risk-Sizing Telemetry JSON Aç" in DASHBOARD_HTML
    assert "Risk-Sizing Evidence ZIP İndir" in DASHBOARD_HTML
