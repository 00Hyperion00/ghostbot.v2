from __future__ import annotations

import json
import subprocess
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from tradebot.operator_cockpit_v2_read_only import (
    DASHBOARD_HTML,
    OPERATOR_COCKPIT_V2_CONTRACT_VERSION,
    OPERATOR_COCKPIT_V2_NO_CONFIG_MUTATION,
    OPERATOR_COCKPIT_V2_NO_SCHEDULER_MUTATION,
    OPERATOR_COCKPIT_V2_NO_TRADING_ACTION,
    OPERATOR_COCKPIT_V2_READ_ONLY,
    collect_operator_cockpit_snapshot,
    make_operator_cockpit_server,
)


def _observation(symbol: str, timestamp: str, result: float | None, slippage: float) -> dict[str, object]:
    return {
        "symbol": symbol,
        "timestamp_utc": timestamp,
        "observation_id": f"HYP-005-{symbol}-{timestamp}",
        "forward_return_bps_final": result,
        "spread_slippage_proxy_bps": slippage,
    }


def _task_query(name: str) -> dict[str, object]:
    if "R1" in name:
        return {"task_name": name, "state": "Ready", "last_task_result": 0, "number_of_missed_runs": 0, "next_run_time": "2026-06-06 20:00:00"}
    return {"task_name": name, "state": "Disabled", "last_task_result": 0, "number_of_missed_runs": 0}


def _backend_probe(_: str) -> dict[str, object]:
    return {"reachable": True, "status_code": 200, "payload": {"ok": True}}


def _fixture_root(tmp_path: Path) -> Path:
    root = tmp_path / "trade_botV2"
    reports = root / "reports" / "hyp005_r1_isolated"
    reports.mkdir(parents=True)
    rows = [
        _observation("ADAUSDT", "2026-06-02T00:00:00+00:00", -842.1, 8.68),
        _observation("BTCUSDT", "2026-06-02T00:00:00+00:00", -719.3, 5.48),
        _observation("XRPUSDT", "2026-06-02T00:00:00+00:00", -700.2, 6.75),
        _observation("BNBUSDT", "2026-06-05T04:00:00+00:00", -239.3, 16.30),
        _observation("SOLUSDT", "2026-05-28T04:00:00+00:00", 120.6, 4.79),
    ]
    (reports / "4B436625X_hyp005_shadow_merged_ledger_20260606_120000.jsonl").write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
    (reports / "4B436625V_hyp005_shadow_observation_logger_20260606_120000.json").write_text(json.dumps({"decision": "HYP005_SHADOW_OBSERVATION_LOGGER_READY"}), encoding="utf-8")
    (reports / "4B436625X_hyp005_shadow_collection_orchestrator_20260606_120000.json").write_text(json.dumps({"decision": "HYP005_SHADOW_COLLECTION_ORCHESTRATOR_READY"}), encoding="utf-8")
    (reports / "4B436625Y_hyp005_shadow_operator_daily_audit_20260606_120000.json").write_text(json.dumps({
        "decision": "HYP005_SHADOW_OPERATOR_AUDIT_READY",
        "dashboard_status": "SHADOW_COLLECTION_IN_PROGRESS",
        "latest_logger_decision": "HYP005_SHADOW_OBSERVATION_LOGGER_READY",
        "latest_collection_decision": "HYP005_SHADOW_COLLECTION_ORCHESTRATOR_READY",
        "latest_acceptance_decision": "HYP005_SHADOW_PAPER_TRANSITION_BLOCK",
        "shadow_observation_count": 21,
        "shadow_sample_target": 30,
        "progress_pct": 70.0,
        "paper_transition_ready": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "post_requests_allowed": False,
        "order_actions_performed": False,
        "source_ledgers": 1,
        "source_reports": 3,
    }), encoding="utf-8")
    models = root / "models"
    models.mkdir()
    (models / "candidate_model.ubj").write_bytes(b"test-model")
    return root


def test_26a_declares_read_only_visual_ux_contract() -> None:
    assert OPERATOR_COCKPIT_V2_CONTRACT_VERSION == "4B.4.3.6.6.26A"
    assert OPERATOR_COCKPIT_V2_READ_ONLY is True
    assert OPERATOR_COCKPIT_V2_NO_CONFIG_MUTATION is True
    assert OPERATOR_COCKPIT_V2_NO_SCHEDULER_MUTATION is True
    assert OPERATOR_COCKPIT_V2_NO_TRADING_ACTION is True


def test_26a_snapshot_integrates_r1_audit_scheduler_model_and_tail_risk(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    snapshot = collect_operator_cockpit_snapshot(root, task_query=_task_query, backend_probe=_backend_probe)
    assert snapshot["read_only"] is True
    assert snapshot["mode"] == "SHADOW"
    assert snapshot["branch_id"] == "HYP-005-R1"
    assert snapshot["audit"]["shadow_observation_count"] == 21
    assert snapshot["audit"]["shadow_sample_target"] == 30
    assert snapshot["scheduler"]["baseline_task"]["state"] == "Disabled"
    assert snapshot["scheduler"]["r1_task"]["state"] == "Ready"
    assert snapshot["performance"]["matured_count"] == 5
    assert snapshot["worst_timestamp_cluster"]["timestamp_utc"] == "2026-06-02T00:00:00+00:00"
    assert snapshot["worst_timestamp_cluster"]["sample_count"] == 3
    assert {item["code"] for item in snapshot["risk_items"]} >= {"TIMESTAMP_CLUSTER_TAIL_LOSS_HIGH", "SLIPPAGE_PROXY_HIGH", "SHADOW_SAMPLE_TARGET_INCOMPLETE"}
    assert snapshot["model"]["file_name"] == "candidate_model.ubj"
    assert len(snapshot["model"]["sha256"]) == 64


def test_26a_dashboard_html_is_layered_professional_and_contains_no_live_action() -> None:
    assert "Operator Cockpit V2" in DASHBOARD_HTML
    assert "HYP-005-R1 Shadow Validation" in DASHBOARD_HTML
    assert "Risk Merkezi" in DASHBOARD_HTML
    assert "Son Observation Akışı" in DASHBOARD_HTML
    assert "Scheduler" in DASHBOARD_HTML
    assert "Read-only foundation" in DASHBOARD_HTML
    assert "LIVE MODE AÇ" not in DASHBOARD_HTML
    assert "fetch('/api/operator-cockpit-v2/snapshot'" in DASHBOARD_HTML


def test_26a_http_server_serves_dashboard_snapshot_and_health(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    server = make_operator_cockpit_server(root, port=0, task_query=_task_query, backend_probe=_backend_probe)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    try:
        with urllib.request.urlopen(f"http://{host}:{port}/dashboard", timeout=3) as response:
            assert response.status == 200
            assert "Operator Cockpit V2" in response.read().decode("utf-8")
            assert response.headers["X-Operator-Cockpit-Mode"] == "read-only"
        with urllib.request.urlopen(f"http://{host}:{port}/api/operator-cockpit-v2/snapshot", timeout=3) as response:
            payload = json.loads(response.read().decode("utf-8"))
            assert payload["read_only"] is True
            assert payload["audit"]["shadow_observation_count"] == 21
        with urllib.request.urlopen(f"http://{host}:{port}/api/operator-cockpit-v2/health", timeout=3) as response:
            payload = json.loads(response.read().decode("utf-8"))
            assert payload == {"ok": True, "read_only": True, "contract_version": "4B.4.3.6.6.26A"}
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def test_26a_http_server_blocks_all_mutation_methods(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    server = make_operator_cockpit_server(root, port=0, task_query=_task_query, backend_probe=_backend_probe)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    try:
        for method in ("POST", "PUT", "PATCH", "DELETE"):
            request = urllib.request.Request(f"http://{host}:{port}/api/operator-cockpit-v2/snapshot", data=b"{}", method=method)
            with pytest.raises(urllib.error.HTTPError) as caught:
                urllib.request.urlopen(request, timeout=3)
            assert caught.value.code == 405
            payload = json.loads(caught.value.read().decode("utf-8"))
            assert payload["error"] == "READ_ONLY_DASHBOARD_MUTATION_BLOCKED"
            assert payload["read_only"] is True
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def test_26a_launcher_once_json_is_safe_and_parseable(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    project_root = Path(__file__).resolve().parents[1]
    completed = subprocess.run(
        [sys.executable, "tools/run_operator_cockpit_v2_4B436626A.py", "--project-root", str(root), "--once-json"],
        cwd=project_root,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["read_only"] is True
    assert payload["contract_version"] == "4B.4.3.6.6.26A"
