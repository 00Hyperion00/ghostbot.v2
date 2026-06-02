from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tradebot.research_hyp005_shadow_collection_orchestrator import (
    HYP005_R1_COLLECTION_DAG_BOOTSTRAP_HOTFIX_VERSION,
    HYP005_SHADOW_COLLECTION_BLOCK,
    HYP005_SHADOW_COLLECTION_READY,
    HYP005_SHADOW_COLLECTION_STATUS_IN_PROGRESS,
    HYP005_SHADOW_COLLECTION_STATUS_TARGET_MET,
    build_hyp005_shadow_collection_orchestrator_report,
)


def _candidate_spec() -> dict[str, object]:
    return {
        "hypothesis_id": "HYP-005",
        "branch_name": "liquidity_sweep_reversal_vol_compression",
        "selected_strategy_family": "long_liquidity_sweep_reversal",
        "no_order_shadow_only": True,
        "approved_for_training_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "live_real_allowed": False,
        "post_requests_allowed": False,
        "order_actions_performed": False,
        "guardrails": {"no_order_shadow_only": True},
    }


def _logger_report() -> dict[str, object]:
    return {
        "decision": "HYP005_SHADOW_OBSERVATION_LOGGER_READY",
        "approved_for_shadow_candidate": True,
        "approved_for_training_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "post_requests_allowed": False,
        "order_actions_performed": False,
    }


def _observation(index: int, symbol: str = "ADAUSDT") -> dict[str, object]:
    day = 1 + (index // 6)
    hour = (index % 6) * 4
    return {
        "timestamp_utc": f"2026-06-{day:02d}T{hour:02d}:00:00Z",
        "symbol": symbol,
        "timeframe": "4h",
        "strategy_family": "long_liquidity_sweep_reversal",
        "sweep_direction": "LONG",
        "entry_reference_price": 1.0 + index,
        "forward_return_bps_final": 10.0,
        "data_quality_ok": True,
    }


def _run(project_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args],
        cwd=project_root,
        text=True,
        capture_output=True,
        check=False,
    )


def _latest(directory: Path, pattern: str) -> Path:
    matches = sorted(directory.glob(pattern), key=lambda path: path.stat().st_mtime)
    assert matches, pattern
    return matches[-1]


def test_25aeh4_declares_collection_dag_bootstrap_version() -> None:
    assert HYP005_R1_COLLECTION_DAG_BOOTSTRAP_HOTFIX_VERSION == "4B.4.3.6.6.25AE-H4"


def test_25aeh4_25x_ready_without_prior_acceptance_report_and_exposes_top_level_progress() -> None:
    observations = [_observation(index) for index in range(20)]
    report = build_hyp005_shadow_collection_orchestrator_report(
        candidate_spec=_candidate_spec(),
        candidate_spec_path="reports/hyp005_r1_runtime_candidate_spec.json",
        logger_reports=[_logger_report()],
        acceptance_reports=[],
        observations=observations,
        duplicate_observation_count=0,
        ledger_source_count=1,
        symbols=["ADAUSDT", "BTCUSDT"],
    )
    assert report.decision == HYP005_SHADOW_COLLECTION_READY
    assert report.collection_status == HYP005_SHADOW_COLLECTION_STATUS_IN_PROGRESS
    assert report.shadow_observation_count == 20
    assert report.shadow_sample_target == 30
    assert report.progress_pct == 66.666667
    assert report.acceptance_report_required_for_collection_ready is False
    assert report.acceptance_report_seen is False
    assert report.previous_acceptance_informational_only is True
    assert "HYP005_SHADOW_ACCEPTANCE_REPORT_MISSING" not in report.reason_codes
    assert "HYP005_SHADOW_ACCEPTANCE_NOT_REQUIRED_FOR_25X_COLLECTION_READY" in report.reason_codes
    assert report.approved_for_paper_candidate is False
    assert report.approved_for_live_real is False


def test_25aeh4_target_met_collection_does_not_grant_paper_or_live_permission() -> None:
    observations = [_observation(index) for index in range(30)]
    report = build_hyp005_shadow_collection_orchestrator_report(
        candidate_spec=_candidate_spec(),
        candidate_spec_path="reports/hyp005_r1_runtime_candidate_spec.json",
        logger_reports=[_logger_report()],
        acceptance_reports=[],
        observations=observations,
        duplicate_observation_count=0,
        ledger_source_count=1,
        symbols=["ADAUSDT"],
    )
    assert report.decision == HYP005_SHADOW_COLLECTION_READY
    assert report.collection_status == HYP005_SHADOW_COLLECTION_STATUS_TARGET_MET
    assert report.shadow_observation_count == 30
    assert report.approved_for_paper_transition_candidate is False
    assert report.approved_for_paper_candidate is False
    assert report.approved_for_live_real is False
    assert report.post_requests_allowed is False
    assert report.order_actions_performed is False


def test_25aeh4_unsafe_previous_acceptance_metadata_still_blocks_collection() -> None:
    unsafe_acceptance = {
        "decision": "HYP005_SHADOW_PAPER_TRANSITION_READY",
        "approved_for_paper_candidate": True,
        "approved_for_live_real": False,
        "post_requests_allowed": False,
        "order_actions_performed": False,
    }
    report = build_hyp005_shadow_collection_orchestrator_report(
        candidate_spec=_candidate_spec(),
        candidate_spec_path="reports/hyp005_r1_runtime_candidate_spec.json",
        logger_reports=[_logger_report()],
        acceptance_reports=[unsafe_acceptance],
        observations=[_observation(0)],
        duplicate_observation_count=0,
        ledger_source_count=1,
        symbols=["ADAUSDT"],
    )
    assert report.decision == HYP005_SHADOW_COLLECTION_BLOCK
    assert "ACCEPTANCE_REPORT_UNSAFE_APPROVAL_DETECTED" in report.reason_codes
    assert report.approved_for_shadow_collection is False


def test_25aeh4_strict_25x_cli_bootstraps_without_previous_25w_and_writes_top_level_counts(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[1]
    r1 = tmp_path / "reports" / "hyp005_r1_isolated"
    r1.mkdir(parents=True)
    candidate = tmp_path / "hyp005_r1_runtime_candidate_spec.json"
    logger = r1 / "4B436625V_hyp005_shadow_observation_logger_test.json"
    ledger = r1 / "4B436625V_hyp005_shadow_observation_ledger_test.json"
    candidate.write_text(json.dumps(_candidate_spec()), encoding="utf-8")
    logger.write_text(json.dumps(_logger_report()), encoding="utf-8")
    ledger.write_text(json.dumps({"observations": [_observation(index) for index in range(20)]}), encoding="utf-8")

    result = _run(
        project_root,
        "tools/run_hyp005_shadow_collection_orchestrator_4B436625X.py",
        "--candidate-spec-json", str(candidate),
        "--logger-report-json", str(logger),
        "--ledger-json", str(ledger),
        "--reports-dir", str(r1),
        "--strict-explicit-chain",
        "--out-dir", str(r1),
        "--review-ok",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "HYP005_SHADOW_COLLECTION_ORCHESTRATOR_READY" in result.stdout
    assert "shadow_observation_count: 20" in result.stdout
    report_path = _latest(r1, "4B436625X_hyp005_shadow_collection_orchestrator_*.json")
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["decision"] == HYP005_SHADOW_COLLECTION_READY
    assert payload["collection_status"] == HYP005_SHADOW_COLLECTION_STATUS_IN_PROGRESS
    assert payload["shadow_observation_count"] == 20
    assert payload["shadow_sample_target"] == 30
    assert payload["progress_pct"] == 66.666667
    assert payload["acceptance_report_required_for_collection_ready"] is False
    assert "HYP005_SHADOW_ACCEPTANCE_REPORT_MISSING" not in payload["reason_codes"]


def test_25aeh4_strict_dag_runs_25x_then_25w_then_25y_without_cycle_dependency(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[1]
    r1 = tmp_path / "Masaüstü" / "reports" / "hyp005_r1_isolated"
    r1.mkdir(parents=True)
    candidate = tmp_path / "hyp005_r1_runtime_candidate_spec.json"
    logger = r1 / "4B436625V_hyp005_shadow_observation_logger_test.json"
    ledger = r1 / "4B436625V_hyp005_shadow_observation_ledger_test.json"
    candidate.write_text(json.dumps(_candidate_spec()), encoding="utf-8")
    logger.write_text(json.dumps(_logger_report()), encoding="utf-8")
    ledger.write_text(json.dumps({"observations": [_observation(index) for index in range(20)]}), encoding="utf-8")

    x_result = _run(
        project_root,
        "tools/run_hyp005_shadow_collection_orchestrator_4B436625X.py",
        "--candidate-spec-json", str(candidate),
        "--logger-report-json", str(logger),
        "--ledger-json", str(ledger),
        "--reports-dir", str(r1),
        "--strict-explicit-chain",
        "--out-dir", str(r1),
        "--review-ok",
    )
    assert x_result.returncode == 0, x_result.stdout + x_result.stderr
    collection = _latest(r1, "4B436625X_hyp005_shadow_collection_orchestrator_*.json")
    merged = _latest(r1, "4B436625X_hyp005_shadow_merged_ledger_*.json")
    collection_payload = json.loads(collection.read_text(encoding="utf-8"))
    assert collection_payload["decision"] == HYP005_SHADOW_COLLECTION_READY

    w_result = _run(
        project_root,
        "tools/run_hyp005_shadow_acceptance_readiness_4B436625W.py",
        "--collection-report-json", str(collection),
        "--ledger-json", str(merged),
        "--reports-dir", str(r1),
        "--strict-explicit-chain",
        "--out-dir", str(r1),
        "--review-ok",
    )
    assert w_result.returncode == 0, w_result.stdout + w_result.stderr
    acceptance = _latest(r1, "4B436625W_hyp005_shadow_observation_acceptance_*.json")
    acceptance_payload = json.loads(acceptance.read_text(encoding="utf-8"))
    assert acceptance_payload["decision"] == "HYP005_SHADOW_PAPER_TRANSITION_BLOCK"
    assert acceptance_payload["paper_transition_ready"] is False

    y_result = _run(
        project_root,
        "tools/run_hyp005_shadow_operator_runbook_4B436625Y.py",
        "--candidate-spec-json", str(candidate),
        "--logger-report-json", str(logger),
        "--collection-report-json", str(collection),
        "--acceptance-report-json", str(acceptance),
        "--ledger-json", str(merged),
        "--reports-dir", str(r1),
        "--strict-explicit-chain",
        "--symbols", "ADAUSDT",
        "--out-dir", str(r1),
        "--review-ok",
    )
    assert y_result.returncode == 0, y_result.stdout + y_result.stderr
    audit = _latest(r1, "4B436625Y_hyp005_shadow_operator_daily_audit_*.json")
    audit_payload = json.loads(audit.read_text(encoding="utf-8"))
    assert audit_payload["latest_collection_decision"] == HYP005_SHADOW_COLLECTION_READY
    assert audit_payload["latest_acceptance_decision"] == "HYP005_SHADOW_PAPER_TRANSITION_BLOCK"
    assert audit_payload["shadow_observation_count"] == 20
    assert audit_payload["dashboard_status"] == "SHADOW_COLLECTION_IN_PROGRESS"
    assert audit_payload["approved_for_paper_candidate"] is False
    assert audit_payload["approved_for_live_real"] is False
