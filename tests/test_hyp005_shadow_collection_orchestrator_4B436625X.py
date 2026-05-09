from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from tradebot.research_hyp005_shadow_collection_orchestrator import (
    HYP005_SHADOW_COLLECTION_READY,
    build_hyp005_shadow_collection_orchestrator_report,
    load_observations_from_json,
    merge_observations,
)


def _candidate_spec() -> dict:
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
    }


def _logger_report() -> dict:
    return {
        "decision": "HYP005_SHADOW_OBSERVATION_LOGGER_READY",
        "approved_for_shadow_candidate": True,
        "approved_for_training_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "post_requests_allowed": False,
        "order_actions_performed": False,
    }


def _acceptance_report() -> dict:
    return {
        "decision": "HYP005_SHADOW_PAPER_TRANSITION_BLOCK",
        "approved_for_paper_transition_candidate": False,
        "approved_for_training_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "post_requests_allowed": False,
        "order_actions_performed": False,
    }


def _observation(symbol: str = "BTCUSDT", timestamp: str = "2026-05-09T16:00:00Z") -> dict:
    return {
        "timestamp_utc": timestamp,
        "symbol": symbol,
        "timeframe": "4h",
        "strategy_family": "long_liquidity_sweep_reversal",
        "sweep_direction": "long",
        "entry_reference_price": 100.0,
        "forward_return_bps_final": 80.0,
        "data_quality_ok": True,
    }


def test_25x_builds_no_order_collection_plan_from_ready_chain() -> None:
    report = build_hyp005_shadow_collection_orchestrator_report(
        candidate_spec=_candidate_spec(),
        candidate_spec_path="reports/spec.json",
        logger_reports=[_logger_report()],
        acceptance_reports=[_acceptance_report()],
        observations=[],
        duplicate_observation_count=0,
        ledger_source_count=1,
        symbols=["BTCUSDT", "ETHUSDT"],
    )
    assert report.decision == HYP005_SHADOW_COLLECTION_READY
    assert report.no_order_collection_only is True
    assert report.approved_for_shadow_collection is True
    assert report.approved_for_paper_transition_candidate is False
    assert report.approved_for_paper_candidate is False
    assert report.approved_for_live_real is False
    assert report.post_requests_allowed is False
    assert report.order_actions_performed is False
    assert "NO_ORDER_SHADOW_COLLECTION_PLAN_READY" in report.reason_codes
    assert report.plan["guardrails"]["paper_transition_requires_separate_gate"] is True


def test_25x_merges_ledgers_and_deduplicates_observations() -> None:
    obs = _observation()
    merged, duplicates = merge_observations([[obs, obs], [_observation("ETHUSDT", "2026-05-09T20:00:00Z")]])
    assert len(merged) == 2
    assert duplicates == 1


def test_25x_blocks_when_logger_report_missing() -> None:
    report = build_hyp005_shadow_collection_orchestrator_report(
        candidate_spec=_candidate_spec(),
        candidate_spec_path="reports/spec.json",
        logger_reports=[],
        acceptance_reports=[_acceptance_report()],
        observations=[],
        duplicate_observation_count=0,
        ledger_source_count=0,
        symbols=["BTCUSDT"],
    )
    assert report.decision == "HYP005_SHADOW_COLLECTION_ORCHESTRATOR_BLOCK"
    assert report.approved_for_shadow_collection is False
    assert "HYP005_SHADOW_LOGGER_REPORT_MISSING" in report.reason_codes


def test_25x_loads_observations_from_common_ledger_shape(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.json"
    ledger.write_text(json.dumps({"observations": [_observation()]}), encoding="utf-8")
    rows = load_observations_from_json(ledger)
    assert len(rows) == 1
    assert rows[0]["symbol"] == "BTCUSDT"


def test_tool_writes_report_plan_and_merged_ledger(tmp_path: Path) -> None:
    spec = tmp_path / "spec.json"
    logger = tmp_path / "logger.json"
    acceptance = tmp_path / "acceptance.json"
    ledger = tmp_path / "ledger.json"
    out_dir = tmp_path / "reports"
    spec.write_text(json.dumps(_candidate_spec()), encoding="utf-8")
    logger.write_text(json.dumps(_logger_report()), encoding="utf-8")
    acceptance.write_text(json.dumps(_acceptance_report()), encoding="utf-8")
    ledger.write_text(json.dumps({"observations": [_observation(), _observation()]}), encoding="utf-8")

    cmd = [
        sys.executable,
        "tools/run_hyp005_shadow_collection_orchestrator_4B436625X.py",
        "--candidate-spec-json",
        str(spec),
        "--logger-report-json",
        str(logger),
        "--acceptance-report-json",
        str(acceptance),
        "--ledger-json",
        str(ledger),
        "--out-dir",
        str(out_dir),
        "--review-ok",
    ]
    result = subprocess.run(cmd, cwd=Path.cwd(), text=True, capture_output=True, check=True)
    assert "HYP005_SHADOW_COLLECTION_ORCHESTRATOR_READY" in result.stdout
    assert list(out_dir.glob("4B436625X_hyp005_shadow_collection_orchestrator_*.json"))
    assert list(out_dir.glob("4B436625X_hyp005_shadow_collection_plan_*.json"))
    merged_files = list(out_dir.glob("4B436625X_hyp005_shadow_merged_ledger_*.json"))
    assert merged_files
    payload = json.loads(merged_files[0].read_text(encoding="utf-8"))
    assert len(payload["observations"]) == 1
