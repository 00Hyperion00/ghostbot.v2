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
    OPERATOR_COCKPIT_V2_READ_ONLY,
    OPERATOR_COCKPIT_V2_SELF_CONTAINED_CHARTS,
    OPERATOR_COCKPIT_V2_SHADOW_AUDIT_VISUALIZATION_PACK,
    OPERATOR_COCKPIT_V2_VISUALIZATION_PACK_VERSION,
    collect_operator_cockpit_snapshot,
    make_operator_cockpit_server,
)


def _observation(
    symbol: str,
    timestamp: str,
    result: float | None,
    slippage: float,
    *,
    mae: float | None = None,
    mfe: float | None = None,
) -> dict[str, object]:
    return {
        "symbol": symbol,
        "timestamp_utc": timestamp,
        "observation_id": f"HYP-005-{symbol}-{timestamp}",
        "forward_return_bps_final": result,
        "spread_slippage_proxy_bps": slippage,
        "mae_bps": mae,
        "mfe_bps": mfe,
    }


def _task_query(name: str) -> dict[str, object]:
    if "R1" in name:
        return {
            "task_name": name,
            "state": "Ready",
            "last_task_result": 0,
            "number_of_missed_runs": 0,
            "next_run_time": "2026-06-06 20:00:00",
        }
    return {"task_name": name, "state": "Disabled", "last_task_result": 0, "number_of_missed_runs": 0}


def _backend_probe(_: str) -> dict[str, object]:
    return {"reachable": True, "status_code": 200, "payload": {"ok": True}}


def _fixture_root(tmp_path: Path, *, empty: bool = False) -> Path:
    root = tmp_path / "trade_botV2"
    reports = root / "reports" / "hyp005_r1_isolated"
    reports.mkdir(parents=True)
    rows = [] if empty else [
        _observation("ADAUSDT", "2026-06-02T00:00:00+00:00", -842.1, 8.68, mae=910.0, mfe=80.0),
        _observation("BTCUSDT", "2026-06-02T00:00:00+00:00", -719.3, 5.48, mae=760.0, mfe=95.0),
        _observation("XRPUSDT", "2026-06-02T00:00:00+00:00", -700.2, 6.75, mae=730.0, mfe=75.0),
        _observation("BNBUSDT", "2026-06-05T04:00:00+00:00", -239.3, 16.30, mae=260.0, mfe=35.0),
        _observation("SOLUSDT", "2026-05-28T04:00:00+00:00", 120.6, 4.79, mae=35.0, mfe=150.0),
        _observation("BNBUSDT", "2026-05-28T12:00:00+00:00", 78.0, 3.98, mae=15.0, mfe=100.0),
        _observation("LINKUSDT", "2026-05-27T16:00:00+00:00", None, 7.53, mae=60.0, mfe=40.0),
    ]
    (reports / "4B436625X_hyp005_shadow_merged_ledger_20260606_120000.jsonl").write_text(
        "\n".join(json.dumps(row) for row in rows), encoding="utf-8"
    )
    (reports / "4B436625V_hyp005_shadow_observation_logger_20260606_120000.json").write_text(
        json.dumps({"decision": "HYP005_SHADOW_OBSERVATION_LOGGER_READY"}), encoding="utf-8"
    )
    (reports / "4B436625X_hyp005_shadow_collection_orchestrator_20260606_120000.json").write_text(
        json.dumps({"decision": "HYP005_SHADOW_COLLECTION_ORCHESTRATOR_READY"}), encoding="utf-8"
    )
    (reports / "4B436625Y_hyp005_shadow_operator_daily_audit_20260606_120000.json").write_text(
        json.dumps(
            {
                "decision": "HYP005_SHADOW_OPERATOR_AUDIT_READY",
                "dashboard_status": "SHADOW_COLLECTION_IN_PROGRESS",
                "latest_logger_decision": "HYP005_SHADOW_OBSERVATION_LOGGER_READY",
                "latest_collection_decision": "HYP005_SHADOW_COLLECTION_ORCHESTRATOR_READY",
                "latest_acceptance_decision": "HYP005_SHADOW_PAPER_TRANSITION_BLOCK",
                "shadow_observation_count": len(rows),
                "shadow_sample_target": 30,
                "progress_pct": round((len(rows) / 30) * 100, 6),
                "paper_transition_ready": False,
                "approved_for_paper_candidate": False,
                "approved_for_live_real": False,
                "post_requests_allowed": False,
                "order_actions_performed": False,
                "source_ledgers": 1,
                "source_reports": 3,
            }
        ),
        encoding="utf-8",
    )
    return root


def test_26b_declares_visualization_pack_without_weakening_read_only_contract() -> None:
    assert OPERATOR_COCKPIT_V2_VISUALIZATION_PACK_VERSION == "4B.4.3.6.6.26B"
    assert OPERATOR_COCKPIT_V2_SHADOW_AUDIT_VISUALIZATION_PACK is True
    assert OPERATOR_COCKPIT_V2_SELF_CONTAINED_CHARTS is True
    assert OPERATOR_COCKPIT_V2_READ_ONLY is True


def test_26b_snapshot_adds_visualization_payloads_and_scenario_comparison(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    snapshot = collect_operator_cockpit_snapshot(root, task_query=_task_query, backend_probe=_backend_probe)
    assert snapshot["visualization_pack_version"] == "4B.4.3.6.6.26B"
    visuals = snapshot["visualizations"]
    assert visuals["sample_timeline"][-1]["cumulative_samples"] == 7
    assert sum(item["count"] for item in visuals["return_distribution"]) == 6
    assert {item["symbol"] for item in visuals["symbol_performance"]} >= {"ADAUSDT", "BNBUSDT", "SOLUSDT"}
    assert visuals["timestamp_clusters"][0]["timestamp_utc"] == "2026-06-02T00:00:00+00:00"
    assert visuals["timestamp_clusters"][0]["sample_count"] == 3
    assert visuals["slippage_observations"][0]["symbol"] == "BNBUSDT"
    assert visuals["slippage_observations"][0]["spread_slippage_proxy_bps"] == 16.3
    assert len(visuals["mae_mfe_scatter"]) == 7
    scenarios = {item["scenario"]: item for item in visuals["performance_comparison"]}
    assert set(scenarios) == {"Tüm R1", "Worst cluster hariç", "Slippage < 15 bps"}
    assert scenarios["Worst cluster hariç"]["sample_count"] == 4
    assert scenarios["Slippage < 15 bps"]["sample_count"] == 6


def test_26b_dashboard_is_self_contained_layered_and_contains_quant_visual_tabs() -> None:
    assert "Shadow Audit Visualization" in DASHBOARD_HTML
    assert "Quant Görseller" in DASHBOARD_HTML
    assert "Unique sample zaman çizgisi" in DASHBOARD_HTML
    assert "Forward return dağılımı" in DASHBOARD_HTML
    assert "Timestamp-cluster net edge" in DASHBOARD_HTML
    assert "MAE / MFE execution görünümü" in DASHBOARD_HTML
    assert "renderVisuals(s.visualizations||{})" in DASHBOARD_HTML
    assert "https://" not in DASHBOARD_HTML
    assert "<script src=" not in DASHBOARD_HTML
    assert "LIVE MODE AÇ" not in DASHBOARD_HTML


def test_26b_empty_ledger_visualization_payload_is_safe(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path, empty=True)
    snapshot = collect_operator_cockpit_snapshot(root, task_query=_task_query, backend_probe=_backend_probe)
    visuals = snapshot["visualizations"]
    assert visuals["sample_timeline"] == []
    assert sum(item["count"] for item in visuals["return_distribution"]) == 0
    assert visuals["symbol_performance"] == []
    assert visuals["timestamp_clusters"] == []
    assert visuals["slippage_observations"] == []
    assert visuals["mae_mfe_scatter"] == []
    assert len(visuals["performance_comparison"]) >= 2


def test_26b_http_snapshot_exposes_visualizations_and_mutation_remains_blocked(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    server = make_operator_cockpit_server(root, port=0, task_query=_task_query, backend_probe=_backend_probe)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    try:
        with urllib.request.urlopen(f"http://{host}:{port}/api/operator-cockpit-v2/snapshot", timeout=3) as response:
            payload = json.loads(response.read().decode("utf-8"))
            assert payload["read_only"] is True
            assert payload["visualization_pack_version"] == "4B.4.3.6.6.26B"
            assert payload["visualizations"]["sample_timeline"][-1]["cumulative_samples"] == 7
        request = urllib.request.Request(
            f"http://{host}:{port}/api/operator-cockpit-v2/snapshot", data=b"{}", method="POST"
        )
        with pytest.raises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(request, timeout=3)
        assert caught.value.code == 405
        blocked = json.loads(caught.value.read().decode("utf-8"))
        assert blocked["error"] == "READ_ONLY_DASHBOARD_MUTATION_BLOCKED"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def test_26b_health_keeps_foundation_contract_and_exposes_read_only_mode(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    server = make_operator_cockpit_server(root, port=0, task_query=_task_query, backend_probe=_backend_probe)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    try:
        with urllib.request.urlopen(f"http://{host}:{port}/api/operator-cockpit-v2/health", timeout=3) as response:
            payload = json.loads(response.read().decode("utf-8"))
            assert payload["ok"] is True
            assert payload["read_only"] is True
            assert payload["contract_version"] == "4B.4.3.6.6.26A"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def test_26b_launcher_once_json_is_safe_and_parseable(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    project_root = Path(__file__).resolve().parents[1]
    completed = subprocess.run(
        [sys.executable, "tools/run_operator_cockpit_v2_4B436626B.py", "--project-root", str(root), "--once-json"],
        cwd=project_root,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["read_only"] is True
    assert payload["visualization_pack_version"] == "4B.4.3.6.6.26B"
    assert payload["visualizations"]["sample_timeline"][-1]["cumulative_samples"] == 7
