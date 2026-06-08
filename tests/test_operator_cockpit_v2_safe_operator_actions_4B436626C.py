from __future__ import annotations

import io
import json
import subprocess
import sys
import threading
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

import pytest

from tradebot.operator_cockpit_v2_read_only import (
    DASHBOARD_HTML,
    MAX_OPERATOR_COCKPIT_EVIDENCE_PACK_BYTES,
    MAX_OPERATOR_COCKPIT_EXPORT_FILE_BYTES,
    OPERATOR_COCKPIT_V2_GET_ONLY_ACTIONS,
    OPERATOR_COCKPIT_V2_IN_MEMORY_EXPORTS_ONLY,
    OPERATOR_COCKPIT_V2_NO_CONFIG_MUTATION,
    OPERATOR_COCKPIT_V2_NO_SCHEDULER_MUTATION,
    OPERATOR_COCKPIT_V2_NO_TRADING_ACTION,
    OPERATOR_COCKPIT_V2_READ_ONLY,
    OPERATOR_COCKPIT_V2_SAFE_ACTIONS_VERSION,
    OPERATOR_COCKPIT_V2_SAFE_OPERATOR_ACTIONS,
    _build_in_memory_evidence_pack,
    _read_bounded_export_bytes,
    _safe_action_manifest,
    _safe_latest_export_source,
    collect_operator_cockpit_snapshot,
    make_operator_cockpit_server,
)


def _task_query(name: str) -> dict[str, object]:
    if "R1" in name:
        return {
            "task_name": name,
            "state": "Ready",
            "last_run_time": "2026-06-06 20:00:00",
            "last_task_result": 0,
            "next_run_time": "2026-06-07 00:00:00",
            "number_of_missed_runs": 0,
        }
    return {"task_name": name, "state": "Disabled", "last_task_result": 0, "number_of_missed_runs": 0}


def _backend_probe(_: str) -> dict[str, object]:
    return {"reachable": True, "status_code": 200, "payload": {"ok": True, "running": True}}


def _fixture_root(tmp_path: Path) -> Path:
    root = tmp_path / "trade_botV2"
    reports = root / "reports" / "hyp005_r1_isolated"
    reports.mkdir(parents=True)
    rows = [
        {
            "symbol": "BTCUSDT",
            "timestamp_utc": "2026-06-02T00:00:00+00:00",
            "observation_id": "HYP-005-BTCUSDT-1",
            "spread_slippage_proxy_bps": 5.48,
            "forward_return_bps_final": -719.31,
            "mae_bps": -975.8,
            "mfe_bps": 81.2,
        },
        {
            "symbol": "BNBUSDT",
            "timestamp_utc": "2026-06-05T04:00:00+00:00",
            "observation_id": "HYP-005-BNBUSDT-2",
            "spread_slippage_proxy_bps": 16.30,
            "forward_return_bps_final": -239.36,
            "mae_bps": -322.3,
            "mfe_bps": 412.9,
        },
    ]
    (reports / "4B436625V_hyp005_shadow_observation_logger_20260606_200000.json").write_text(
        json.dumps({"decision": "HYP005_SHADOW_OBSERVATION_LOGGER_READY"}), encoding="utf-8"
    )
    (reports / "4B436625X_hyp005_shadow_collection_orchestrator_20260606_200000.json").write_text(
        json.dumps({"decision": "HYP005_SHADOW_COLLECTION_ORCHESTRATOR_READY"}), encoding="utf-8"
    )
    (reports / "4B436625Y_hyp005_shadow_operator_daily_audit_20260606_200000.json").write_text(
        json.dumps(
            {
                "decision": "HYP005_SHADOW_OPERATOR_AUDIT_READY",
                "dashboard_status": "SHADOW_COLLECTION_IN_PROGRESS",
                "latest_logger_decision": "HYP005_SHADOW_OBSERVATION_LOGGER_READY",
                "latest_collection_decision": "HYP005_SHADOW_COLLECTION_ORCHESTRATOR_READY",
                "latest_acceptance_decision": "HYP005_SHADOW_PAPER_TRANSITION_BLOCK",
                "shadow_observation_count": 2,
                "shadow_sample_target": 30,
                "progress_pct": 6.666667,
                "paper_transition_ready": False,
                "approved_for_paper_candidate": False,
                "approved_for_live_real": False,
                "post_requests_allowed": False,
                "order_actions_performed": False,
                "source_ledgers": 1,
                "source_reports": 3,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (reports / "4B436625X_hyp005_shadow_merged_ledger_20260606_200000.jsonl").write_text(
        "\n".join(json.dumps(row) for row in rows), encoding="utf-8"
    )
    (root / "outside-secret.txt").write_text("must-not-export", encoding="utf-8")
    return root


def _start_server(root: Path):
    server = make_operator_cockpit_server(root, port=0, task_query=_task_query, backend_probe=_backend_probe)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread, server.server_address


def _urlopen_json(url: str) -> tuple[dict[str, object], object]:
    with urllib.request.urlopen(url, timeout=3) as response:
        return json.loads(response.read().decode("utf-8")), response.headers


def test_26c_declares_get_only_safe_actions_without_weakening_read_only() -> None:
    assert OPERATOR_COCKPIT_V2_SAFE_ACTIONS_VERSION == "4B.4.3.6.6.26C"
    assert OPERATOR_COCKPIT_V2_SAFE_OPERATOR_ACTIONS is True
    assert OPERATOR_COCKPIT_V2_GET_ONLY_ACTIONS is True
    assert OPERATOR_COCKPIT_V2_IN_MEMORY_EXPORTS_ONLY is True
    assert OPERATOR_COCKPIT_V2_READ_ONLY is True
    assert OPERATOR_COCKPIT_V2_NO_CONFIG_MUTATION is True
    assert OPERATOR_COCKPIT_V2_NO_SCHEDULER_MUTATION is True
    assert OPERATOR_COCKPIT_V2_NO_TRADING_ACTION is True
    assert MAX_OPERATOR_COCKPIT_EXPORT_FILE_BYTES == 5 * 1024 * 1024
    assert MAX_OPERATOR_COCKPIT_EVIDENCE_PACK_BYTES == 12 * 1024 * 1024


def test_26c_snapshot_manifest_exposes_enabled_get_actions_and_locked_control_plane(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    snapshot = collect_operator_cockpit_snapshot(root, task_query=_task_query, backend_probe=_backend_probe)
    actions = snapshot["safe_operator_actions"]
    assert actions["version"] == "4B.4.3.6.6.26C"
    assert actions["read_only"] is True
    assert actions["get_only"] is True
    enabled = {item["code"] for item in actions["enabled"]}
    locked = {item["code"] for item in actions["locked"]}
    assert {"REFRESH_SNAPSHOT", "RECHECK_BACKEND_HEALTH", "DOWNLOAD_SNAPSHOT_JSON", "OPEN_LATEST_AUDIT_JSON", "DOWNLOAD_EVIDENCE_PACK_ZIP"} <= enabled
    assert {"EMERGENCY_STOP", "PAPER_MODE_ENABLE", "LIVE_MODE_ENABLE", "MODEL_RELOAD", "SCHEDULER_MUTATION", "SYMBOL_SET_MUTATION"} <= locked
    assert all(item["available"] is True for item in actions["exports"])


def test_26c_dashboard_html_contains_safe_action_panel_and_no_control_plane_post() -> None:
    assert "Güvenli Operatör Aksiyonları" in DASHBOARD_HTML
    assert "26C · GET ONLY" in DASHBOARD_HTML
    assert "Evidence Pack ZIP İndir" in DASHBOARD_HTML
    assert "Backend Probe Tekrarla" in DASHBOARD_HTML
    assert "Emergency stop" in DASHBOARD_HTML or "locked-actions" in DASHBOARD_HTML
    assert "fetch('/api/operator-cockpit-v2/actions/backend-probe'" in DASHBOARD_HTML
    assert "method:'POST'" not in DASHBOARD_HTML
    assert 'method: "POST"' not in DASHBOARD_HTML


def test_26c_allowlisted_source_resolution_and_bounded_read(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    assert _safe_latest_export_source(root, "audit") is not None
    assert _safe_latest_export_source(root, "ledger") is not None
    assert _safe_latest_export_source(root, "../../outside-secret") is None
    large = root / "reports" / "hyp005_r1_isolated" / "4B436625Y_hyp005_shadow_operator_daily_audit_20260606_210000.json"
    large.write_bytes(b"x" * (MAX_OPERATOR_COCKPIT_EXPORT_FILE_BYTES + 1))
    with pytest.raises(ValueError, match="OPERATOR_COCKPIT_EXPORT_FILE_TOO_LARGE"):
        _read_bounded_export_bytes(large)


def test_26c_get_endpoints_return_manifest_probe_and_allowlisted_exports(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    server, thread, (host, port) = _start_server(root)
    base = f"http://{host}:{port}"
    try:
        manifest, _ = _urlopen_json(base + "/api/operator-cockpit-v2/actions/manifest")
        assert manifest["get_only"] is True
        probe, _ = _urlopen_json(base + "/api/operator-cockpit-v2/actions/backend-probe")
        assert probe == {"reachable": True, "status_code": 200, "payload": {"ok": True, "running": True}, "read_only": True, "action": "RECHECK_BACKEND_HEALTH"}
        with urllib.request.urlopen(base + "/api/operator-cockpit-v2/export/snapshot.json", timeout=3) as response:
            assert response.headers.get_content_type() == "application/json"
            assert "attachment" in (response.headers.get("Content-Disposition") or "")
            snapshot = json.loads(response.read().decode("utf-8"))
            assert snapshot["read_only"] is True
        with urllib.request.urlopen(base + "/api/operator-cockpit-v2/view/latest-audit.json", timeout=3) as response:
            assert response.headers.get_content_type() == "application/json"
            assert response.headers.get("Content-Disposition") is None
            audit = json.loads(response.read().decode("utf-8"))
            assert audit["decision"] == "HYP005_SHADOW_OPERATOR_AUDIT_READY"
        with urllib.request.urlopen(base + "/api/operator-cockpit-v2/export/latest-ledger", timeout=3) as response:
            assert response.headers.get_content_type() == "application/x-ndjson"
            assert "attachment" in (response.headers.get("Content-Disposition") or "")
            assert b"BNBUSDT" in response.read()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def test_26c_evidence_pack_is_built_in_memory_and_contains_only_allowlisted_sources(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    before = {path.relative_to(root) for path in root.rglob("*") if path.is_file()}
    payload = _build_in_memory_evidence_pack(root, task_query=_task_query, backend_probe=_backend_probe)
    after = {path.relative_to(root) for path in root.rglob("*") if path.is_file()}
    assert before == after
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        names = set(archive.namelist())
        assert "operator-cockpit/snapshot.json" in names
        assert "operator-cockpit/safe-actions-manifest.json" in names
        assert "operator-cockpit/sources/latest-25v-logger.json" in names
        assert "operator-cockpit/sources/latest-25x-collection.json" in names
        assert "operator-cockpit/sources/latest-25y-audit.json" in names
        assert "operator-cockpit/sources/latest-merged-ledger.jsonl" in names
        assert all("outside-secret" not in name for name in names)
        assert b"must-not-export" not in payload


def test_26c_all_mutation_methods_remain_stable_405_on_safe_action_routes(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    before = {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()}
    server, thread, (host, port) = _start_server(root)
    base = f"http://{host}:{port}"
    routes = [
        "/api/operator-cockpit-v2/actions/manifest",
        "/api/operator-cockpit-v2/actions/backend-probe",
        "/api/operator-cockpit-v2/export/snapshot.json",
        "/api/operator-cockpit-v2/export/evidence-pack.zip",
    ]
    try:
        for route in routes:
            for method in ("POST", "PUT", "PATCH", "DELETE"):
                request = urllib.request.Request(base + route, data=b"{}", method=method, headers={"Content-Type": "application/json"})
                with pytest.raises(urllib.error.HTTPError) as caught:
                    urllib.request.urlopen(request, timeout=3)
                assert caught.value.code == 405
                blocked = json.loads(caught.value.read().decode("utf-8"))
                assert blocked == {"ok": False, "error": "READ_ONLY_DASHBOARD_MUTATION_BLOCKED", "read_only": True}
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
    after = {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()}
    assert before == after


def test_26c_runner_once_json_exposes_safe_actions(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    runner = Path(__file__).resolve().parents[1] / "tools" / "run_operator_cockpit_v2_4B436626C.py"
    completed = subprocess.run(
        [sys.executable, str(runner), "--project-root", str(root), "--once-json"],
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
        timeout=10,
    )
    assert completed.returncode == 0, completed.stderr
    snapshot = json.loads(completed.stdout)
    assert snapshot["safe_operator_actions"]["get_only"] is True
    assert snapshot["read_only"] is True
