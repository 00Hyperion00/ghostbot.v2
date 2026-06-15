from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from tradebot.hyp006_shadow_runner_dry_run import BRANCH_ID, BRANCH_NAME, STRATEGY_FAMILY, Candle
from tradebot.hyp006_shadow_registration_operator_approval import (
    CONTRACT_VERSION,
    build_canonical_shadow_cycle_report,
    build_registration_approval_report,
    build_runtime_artifact_retention_policy,
    validate_28c_dry_run_report,
    validate_registration_approval_report,
    write_cycle_bundle,
    write_registration_bundle,
)


def registration_report() -> dict:
    return {
        "contract_version": "4B.4.3.6.6.28B",
        "candidate_spec_draft": {
            "contract_version": "4B.4.3.6.6.28B",
            "hypothesis_id": "HYP-006",
            "branch_id": BRANCH_ID,
            "branch_name": BRANCH_NAME,
            "strategy_family": STRATEGY_FAMILY,
            "no_order_shadow_only": True,
            "approvals": {
                "approved_for_shadow_collection": False,
                "approved_for_training_candidate": False,
                "approved_for_paper_candidate": False,
                "approved_for_live_real": False,
                "order_actions_allowed": False,
            },
            "registration_gate": {
                "registration_requires_28c_runner": True,
                "next_required_gate": "28C_NO_ORDER_SHADOW_RUNNER_DRY_RUN_AND_OPERATOR_REGISTRATION_APPROVAL",
            },
            "entry_signal_definition": {
                "timeframe": "4h",
                "parameters": {
                    "lookback_bars": 3,
                    "hold_bars": 3,
                    "min_sweep_bps": 10.0,
                    "min_wick_pct_reference": 40.0,
                    "compression_window": 2,
                    "compression_baseline_bars": 4,
                    "max_compression_ratio_reference": 2.0,
                },
            },
            "required_shadow_acceptance_metrics": [
                {"name": "max_slippage_proxy_bps", "operator": "<=", "threshold": 12.0}
            ],
        },
    }


def dry_run_report() -> dict:
    return {
        "contract_version": "4B.4.3.6.6.28C",
        "decision": "HYP006_R1_NO_ORDER_SHADOW_RUNNER_DRY_RUN_READY",
        "hypothesis_id": "HYP-006",
        "branch_id": BRANCH_ID,
        "branch_name": BRANCH_NAME,
        "runner_dry_run_ready": True,
        "operator_registration_approval_gate_ready": True,
        "canonical_scheduler_registration_preflight_ready": True,
        "approved_for_no_order_shadow_collection_registration_candidate": True,
        "approved_for_shadow_collection": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "approved_for_training_candidate": False,
        "config_mutation_performed": False,
        "scheduler_mutation_performed": False,
        "trading_action_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "order_actions_performed": False,
        "dry_run_summary": {"new_unique_dry_run_observation_count": 1, "profit_factor": 2.0},
        "symbols_requested": ["BTCUSDT"],
    }


def candles() -> list[Candle]:
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    rows = [
        Candle((base + timedelta(hours=4 * idx)).isoformat(), "BTCUSDT", 101.0, 102.0, 100.0, 101.0, 1000.0)
        for idx in range(8)
    ]
    rows.append(Candle((base + timedelta(hours=32)).isoformat(), "BTCUSDT", 101.0, 103.0, 99.5, 101.5, 2000.0))
    for step, close in enumerate((100.0, 99.0, 98.0), start=9):
        rows.append(Candle((base + timedelta(hours=4 * step)).isoformat(), "BTCUSDT", 101.0, 102.0, close - 0.5, close, 900.0))
    return rows


def test_28c_dry_run_validation_accepts_ready_report_and_blocks_unsafe_source() -> None:
    ok, reasons = validate_28c_dry_run_report(dry_run_report())
    assert ok is True
    assert reasons == []
    bad = dry_run_report()
    bad["approved_for_live_real"] = True
    ok, reasons = validate_28c_dry_run_report(bad)
    assert ok is False
    assert "UNSAFE_SOURCE_APPROVED_FOR_LIVE_REAL" in reasons


def test_operator_approval_required_before_shadow_collection_registration() -> None:
    blocked = build_registration_approval_report(dry_run_report=dry_run_report(), operator_approval=False, symbols=["BTCUSDT"])
    assert blocked["ok"] is False
    assert blocked["approved_for_shadow_collection"] is False
    assert "NO_OPERATOR_REGISTRATION_APPROVAL" in blocked["blockers"]
    approved = build_registration_approval_report(dry_run_report=dry_run_report(), operator_approval=True, symbols=["BTCUSDT"])
    assert approved["ok"] is True
    assert approved["approved_for_shadow_collection"] is True
    assert approved["approved_for_paper_candidate"] is False
    assert approved["scheduler_mutation_performed"] is False
    assert approved["scheduler_task_created"] is False


def test_registration_approval_report_validation_blocks_mutation_flags() -> None:
    approved = build_registration_approval_report(dry_run_report=dry_run_report(), operator_approval=True, symbols=["BTCUSDT"])
    ok, reasons = validate_registration_approval_report(approved)
    assert ok is True
    assert reasons == []
    approved["scheduler_task_created"] = True
    ok, reasons = validate_registration_approval_report(approved)
    assert ok is False
    assert "UNSAFE_MUTATION_SCHEDULER_TASK_CREATED" in reasons


def test_retention_policy_declares_gitignore_recommendation_without_mutation() -> None:
    policy = build_runtime_artifact_retention_policy(max_runtime_reports_retained=10)
    assert policy["max_runtime_reports_retained"] == 10
    assert policy["accepted_baseline_artifacts_are_protected"] is True
    assert policy["gitignore_mutation_performed"] is False
    assert policy["scheduler_mutation_performed"] is False
    assert policy["recommended_gitignore_patterns_after_accepted_baseline"]


def test_canonical_cycle_uses_approval_and_generates_no_order_shadow_rows() -> None:
    approval = build_registration_approval_report(dry_run_report=dry_run_report(), operator_approval=True, symbols=["BTCUSDT"])
    report = build_canonical_shadow_cycle_report(
        registration_approval_report=approval,
        candidate_spec_source=registration_report(),
        candles=candles(),
        existing_ledger_rows=[],
        rows_by_symbol={"BTCUSDT": len(candles())},
        network_request_performed=False,
    )
    assert report["ok"] is True
    assert report["contract_version"] == CONTRACT_VERSION
    assert report["shadow_summary"]["shadow_observation_count"] == 1
    assert report["shadow_summary"]["new_unique_shadow_observation_count"] == 1
    assert report["shadow_observations"][0]["contract_version"] == CONTRACT_VERSION
    assert report["trading_action_performed"] is False
    assert report["order_actions_performed"] is False
    assert report["approved_for_paper_candidate"] is False


def test_canonical_cycle_fails_closed_without_approved_registration() -> None:
    blocked = build_registration_approval_report(dry_run_report=dry_run_report(), operator_approval=False, symbols=["BTCUSDT"])
    report = build_canonical_shadow_cycle_report(
        registration_approval_report=blocked,
        candidate_spec_source=registration_report(),
        candles=candles(),
        existing_ledger_rows=[],
    )
    assert report["ok"] is False
    assert report["approved_for_shadow_collection"] is False
    assert report["shadow_summary"]["shadow_observation_count"] == 0


def test_write_bundles_and_runner_requires_review_ok(tmp_path: Path) -> None:
    approved = build_registration_approval_report(dry_run_report=dry_run_report(), operator_approval=True, symbols=["BTCUSDT"])
    report_json, retention_json, report_md, script_path = write_registration_bundle(
        approved,
        tmp_path,
        project_root=tmp_path,
        symbols=["BTCUSDT"],
        interval="4h",
        days=30,
        emit_registration_script=True,
    )
    assert report_json.exists()
    assert retention_json.exists()
    assert report_md.exists()
    assert script_path is not None and script_path.exists()
    cycle = build_canonical_shadow_cycle_report(
        registration_approval_report=approved,
        candidate_spec_source=registration_report(),
        candles=candles(),
        existing_ledger_rows=[],
    )
    cycle_report, ledger, md = write_cycle_bundle(cycle, tmp_path)
    assert cycle_report.exists()
    assert ledger.exists()
    assert md.exists()
    assert json.loads(report_json.read_text(encoding="utf-8"))["contract_version"] == CONTRACT_VERSION
    cmd = [
        sys.executable,
        "tools/run_4B436628D_hyp006_shadow_registration_approval.py",
        "--dry-run-report-json",
        str(report_json),
        "--out-dir",
        str(tmp_path),
        "--operator-approval",
    ]
    completed = subprocess.run(cmd, cwd=Path(__file__).resolve().parents[1], text=True, capture_output=True)
    assert completed.returncode != 0
    assert "FAIL_CLOSED_REQUIRES_REVIEW_OK" in (completed.stderr + completed.stdout)
