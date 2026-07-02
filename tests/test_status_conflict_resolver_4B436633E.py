from __future__ import annotations

import json
from pathlib import Path

from tradebot.status_conflict_resolver import (
    READY_DECISION,
    build_status_conflict_resolver_report,
    check_status_conflict_resolver,
    run_status_conflict_resolver,
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _seed_repo(tmp_path: Path) -> None:
    recovery = tmp_path / "reports" / "recovery"
    recovery.mkdir(parents=True, exist_ok=True)
    _write_json(
        recovery / "4B436633D_runtime_safety_lockdown_20260702T105700Z_ready.json",
        {
            "status": "READY",
            "decision": "RUNTIME_SAFETY_LOCKDOWN_READY_ALL_RUNTIME_SUBMIT_PATHS_BLOCKED",
            "runtime_safety_lockdown_complete": True,
            "unguarded_destructive_endpoint_count": 0,
        },
    )
    _write_json(tmp_path / "reports" / "production_hardening" / "4B436630P_demo_20260621T125234Z_not_ready.json", {"ok": True})
    _write_json(tmp_path / "reports" / "production_hardening" / "4B436630X_first_live_real_micro_canary_submit_request.json", {"symbol": "BTCUSDT", "request_id": "abc"})
    _write_json(tmp_path / "reports" / "hyp006_r1_canonical" / "4B436628G_H3_runtime_candidate_scan_gate_level_near_miss_20260627T210506Z.json", {"near_miss_count": 3})
    bad = tmp_path / "reports" / "bad" / "4B436628E_manual_task_probe.json"
    bad.parent.mkdir(parents=True, exist_ok=True)
    bad.write_bytes(b"\xef\xbb\xbf{\"ok\": true}")
    _write_json(tmp_path / "reports" / "bad" / "4B436625V_hyp005_shadow_observation_ledger_20260616_090008Z.json", [1, 2, 3])


def test_status_conflict_resolver_ready_with_triage(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    report = build_status_conflict_resolver_report(project_root=tmp_path, reports_root="reports")
    assert report.status == "READY"
    assert report.decision == READY_DECISION
    assert report.source_gate.complete is True
    assert report.status_conflict_summary.conflict_count == 1
    assert report.status_conflict_summary.unresolved_conflict_count == 0
    assert report.unknown_evidence_summary.unknown_count >= 1
    assert report.malformed_json_summary.malformed_count == 2


def test_check_preserves_fail_closed_safety_fields(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    payload = check_status_conflict_resolver(project_root=tmp_path, reports_root="reports")
    assert payload["status"] == "READY"
    assert payload["approved_for_live_real"] is False
    assert payload["approved_for_exchange_submit"] is False
    assert payload["trading_action_performed"] is False
    assert payload["training_performed"] is False
    assert payload["runtime_overlay_activated"] is False


def test_run_writes_all_ledgers(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    payload = run_status_conflict_resolver(project_root=tmp_path, reports_root="reports", output_dir="reports/recovery")
    assert payload["status"] == "READY"
    for key in (
        "report_path",
        "status_conflict_resolution_ledger_path",
        "unknown_evidence_classifier_ledger_path",
        "malformed_json_triage_ledger_path",
    ):
        assert Path(payload[key]).exists(), key
