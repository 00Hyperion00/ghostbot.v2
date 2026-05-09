from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tradebot.research_hyp005_shadow_operator_runbook import (
    HYP005_SHADOW_OPERATOR_AUDIT_BLOCK,
    HYP005_SHADOW_OPERATOR_AUDIT_CONTRACT_VERSION,
    HYP005_SHADOW_OPERATOR_AUDIT_READY,
    build_hyp005_shadow_operator_audit_report,
    load_json,
)


def _candidate_spec() -> dict:
    return {
        "contract_version": "4B.4.3.6.6.25U",
        "hypothesis_id": "HYP-005",
        "branch_name": "liquidity_sweep_reversal_vol_compression",
        "selected_strategy_family": "long_liquidity_sweep_reversal",
        "no_order_shadow_only": True,
        "approved_for_training_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "post_requests_allowed": False,
        "order_actions_performed": False,
    }


def _logger_report() -> dict:
    return {
        "decision": "HYP005_SHADOW_OBSERVATION_LOGGER_READY",
        "hypothesis_id": "HYP-005",
        "branch_name": "liquidity_sweep_reversal_vol_compression",
        "selected_strategy_family": "long_liquidity_sweep_reversal",
        "approved_for_training_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "post_requests_allowed": False,
        "order_actions_performed": False,
    }


def _collection_report(count: int = 0) -> dict:
    return {
        "decision": "HYP005_SHADOW_COLLECTION_ORCHESTRATOR_READY",
        "hypothesis_id": "HYP-005",
        "branch_name": "liquidity_sweep_reversal_vol_compression",
        "selected_strategy_family": "long_liquidity_sweep_reversal",
        "progress": {
            "shadow_observation_count": count,
            "shadow_sample_target": 30,
            "progress_pct": round(count / 30 * 100, 6),
        },
        "approved_for_shadow_collection": True,
        "approved_for_paper_transition_candidate": False,
        "approved_for_training_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "post_requests_allowed": False,
        "order_actions_performed": False,
    }


def _acceptance_report(count: int = 0, ready: bool = False) -> dict:
    return {
        "decision": "HYP005_SHADOW_PAPER_TRANSITION_READY" if ready else "HYP005_SHADOW_PAPER_TRANSITION_BLOCK",
        "hypothesis_id": "HYP-005",
        "branch_name": "liquidity_sweep_reversal_vol_compression",
        "selected_strategy_family": "long_liquidity_sweep_reversal",
        "shadow_observation_count": count,
        "paper_transition_ready": ready,
        "approved_for_paper_transition_candidate": ready,
        "approved_for_training_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "post_requests_allowed": False,
        "order_actions_performed": False,
    }


def test_25y_builds_daily_no_order_audit_pack_from_ready_chain() -> None:
    report = build_hyp005_shadow_operator_audit_report(
        candidate_spec=_candidate_spec(),
        candidate_spec_path="reports/spec.json",
        logger_reports=[_logger_report()],
        collection_reports=[_collection_report(count=0)],
        acceptance_reports=[_acceptance_report(count=0, ready=False)],
        observations=[],
        ledger_source_count=2,
        symbols=["BTCUSDT", "ETHUSDT"],
        interval="4h",
        days=30,
        base_url="https://api.binance.com",
        out_dir="reports",
    )
    assert report.contract_version == HYP005_SHADOW_OPERATOR_AUDIT_CONTRACT_VERSION
    assert report.decision == HYP005_SHADOW_OPERATOR_AUDIT_READY
    assert report.dashboard_status == "SHADOW_COLLECTION_IN_PROGRESS"
    assert report.shadow_observation_count == 0
    assert report.shadow_sample_target == 30
    assert report.approved_for_operator_audit is True
    assert report.approved_for_paper_transition_candidate is False
    assert report.approved_for_paper_candidate is False
    assert report.approved_for_live_real is False
    assert report.order_actions_performed is False
    assert "SHADOW_SAMPLE_COUNT_BELOW_TARGET" in report.active_blockers


def test_25y_blocks_when_collection_orchestrator_missing() -> None:
    report = build_hyp005_shadow_operator_audit_report(
        candidate_spec=_candidate_spec(),
        candidate_spec_path="reports/spec.json",
        logger_reports=[_logger_report()],
        collection_reports=[],
        acceptance_reports=[_acceptance_report()],
        observations=[],
        ledger_source_count=1,
        symbols=["BTCUSDT"],
        interval="4h",
        days=30,
        base_url="https://api.binance.com",
        out_dir="reports",
    )
    assert report.decision == HYP005_SHADOW_OPERATOR_AUDIT_BLOCK
    assert "HYP005_SHADOW_COLLECTION_ORCHESTRATOR_NOT_CONFIRMED" in report.reason_codes
    assert report.approved_for_paper_candidate is False
    assert report.approved_for_live_real is False


def test_25y_paper_ready_still_does_not_enable_paper() -> None:
    observations = [
        {
            "timestamp_utc": f"2026-05-{day:02d}T00:00:00Z",
            "symbol": "BTCUSDT",
            "timeframe": "4h",
            "strategy_family": "long_liquidity_sweep_reversal",
            "sweep_direction": "long",
            "entry_reference_price": 100000 + day,
        }
        for day in range(1, 31)
    ]
    report = build_hyp005_shadow_operator_audit_report(
        candidate_spec=_candidate_spec(),
        candidate_spec_path="reports/spec.json",
        logger_reports=[_logger_report()],
        collection_reports=[_collection_report(count=30)],
        acceptance_reports=[_acceptance_report(count=30, ready=True)],
        observations=observations,
        ledger_source_count=1,
        symbols=["BTCUSDT"],
        interval="4h",
        days=30,
        base_url="https://api.binance.com",
        out_dir="reports",
    )
    assert report.decision == HYP005_SHADOW_OPERATOR_AUDIT_READY
    assert report.paper_transition_ready is True
    assert report.dashboard_status == "PAPER_TRANSITION_READY_REVIEW_ONLY"
    assert report.approved_for_paper_transition_candidate is False
    assert report.approved_for_paper_candidate is False
    assert report.paper_trading_started is False
    assert "PAPER_TRANSITION_READY_REQUIRES_SEPARATE_ENABLEMENT" in report.warnings


def test_25y_blocks_unsafe_paper_approval_in_input() -> None:
    unsafe_logger = _logger_report()
    unsafe_logger["approved_for_paper_candidate"] = True
    report = build_hyp005_shadow_operator_audit_report(
        candidate_spec=_candidate_spec(),
        candidate_spec_path="reports/spec.json",
        logger_reports=[unsafe_logger],
        collection_reports=[_collection_report()],
        acceptance_reports=[_acceptance_report()],
        observations=[],
        ledger_source_count=1,
        symbols=["BTCUSDT"],
        interval="4h",
        days=30,
        base_url="https://api.binance.com",
        out_dir="reports",
    )
    assert report.decision == HYP005_SHADOW_OPERATOR_AUDIT_BLOCK
    assert any("UNSAFE" in code for code in report.reason_codes)
    assert report.approved_for_paper_candidate is False
    assert report.approved_for_live_real is False


def test_tool_writes_report_dashboard_and_runbook(tmp_path: Path) -> None:
    reports = tmp_path / "reports"
    reports.mkdir()
    spec = reports / "4B436625U_hyp005_no_order_shadow_candidate_spec_20260509_175722.json"
    logger = reports / "4B436625V_hyp005_shadow_observation_logger_20260509_201003.json"
    collection = reports / "4B436625X_hyp005_shadow_collection_orchestrator_20260509_174233.json"
    acceptance = reports / "4B436625W_hyp005_shadow_observation_acceptance_20260509_202658.json"
    ledger = reports / "4B436625V_hyp005_shadow_observation_ledger_20260509_201003.json"
    spec.write_text(json.dumps(_candidate_spec()), encoding="utf-8")
    logger.write_text(json.dumps(_logger_report()), encoding="utf-8")
    collection.write_text(json.dumps(_collection_report()), encoding="utf-8")
    acceptance.write_text(json.dumps(_acceptance_report()), encoding="utf-8")
    ledger.write_text(json.dumps({"observations": []}), encoding="utf-8")

    root = Path(__file__).resolve().parents[1]
    cmd = [
        sys.executable,
        str(root / "tools" / "run_hyp005_shadow_operator_runbook_4B436625Y.py"),
        "--reports-dir",
        str(reports),
        "--include-all",
        "--out-dir",
        str(reports),
        "--review-ok",
    ]
    result = subprocess.run(cmd, cwd=root, text=True, capture_output=True, check=True)
    assert "HYP005_SHADOW_OPERATOR_AUDIT_READY" in result.stdout
    report_files = list(reports.glob("4B436625Y_hyp005_shadow_operator_daily_audit_*.json"))
    dashboard_files = list(reports.glob("4B436625Y_hyp005_shadow_operator_dashboard_*.json"))
    runbook_files = list(reports.glob("4B436625Y_hyp005_shadow_operator_runbook_*.md"))
    assert report_files
    assert dashboard_files
    assert runbook_files
    payload = load_json(report_files[0])
    assert payload["approved_for_paper_candidate"] is False
    assert payload["approved_for_live_real"] is False
    assert payload["dashboard_status"] == "SHADOW_COLLECTION_IN_PROGRESS"
