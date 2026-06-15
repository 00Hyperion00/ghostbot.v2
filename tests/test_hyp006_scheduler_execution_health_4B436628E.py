from __future__ import annotations

import json
from pathlib import Path

from tradebot.hyp006_scheduler_health_verify import (
    BRANCH_ID,
    CONTRACT_VERSION,
    PROPOSED_SCHEDULER_TASK_NAME,
    build_scheduler_execution_health_report,
    probe_windows_task_scheduler,
    summarize_ledger_continuity,
    validate_ledger_continuity,
    validate_scheduler_task_health,
    write_health_bundle,
)


def valid_registration() -> dict:
    return {
        "contract_version": "4B.4.3.6.6.28D",
        "decision": "HYP006_R1_CANONICAL_NO_ORDER_SHADOW_REGISTRATION_APPROVED",
        "approved_for_canonical_no_order_shadow_registration": True,
        "approved_for_shadow_collection": True,
        "approved_for_training_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "config_mutation_performed": False,
        "scheduler_mutation_performed": False,
        "scheduler_task_created": False,
        "scheduler_task_modified": False,
        "trading_action_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "order_actions_performed": False,
    }


def valid_cycle() -> dict:
    return {
        "contract_version": "4B.4.3.6.6.28D",
        "decision": "HYP006_R1_CANONICAL_NO_ORDER_SHADOW_COLLECTION_CYCLE_READY",
        "branch_id": BRANCH_ID,
        "approved_for_shadow_collection": True,
        "approved_for_training_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "config_mutation_performed": False,
        "scheduler_mutation_performed": False,
        "scheduler_task_created": False,
        "scheduler_task_modified": False,
        "trading_action_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "order_actions_performed": False,
        "shadow_summary": {
            "shadow_observation_count": 2,
            "new_unique_shadow_observation_count": 2,
        },
    }


def valid_rows() -> list[dict]:
    return [
        {"contract_version": "4B.4.3.6.6.28D", "branch_id": BRANCH_ID, "observation_id": "HYP-006-BTC", "symbol": "BTCUSDT", "forward_return_bps_final_short_probe": 100.0},
        {"contract_version": "4B.4.3.6.6.28D", "branch_id": BRANCH_ID, "observation_id": "HYP-006-ETH", "symbol": "ETHUSDT", "forward_return_bps_final_short_probe": -25.0},
    ]


def valid_task_probe() -> dict:
    return {
        "exists": True,
        "task_name": PROPOSED_SCHEDULER_TASK_NAME,
        "state": "Ready",
        "last_task_result": 0,
        "number_of_missed_runs": 0,
        "action_execute": "python",
        "action_arguments": "tools/run_4B436628D_hyp006_canonical_shadow_cycle.py --registration-approval-json x --registration-json y --out-dir reports/hyp006_r1_canonical --review-ok",
        "working_directory": "C:/Users/muhas/OneDrive/Masaüstü/trade_botV2",
    }


def test_contract_version() -> None:
    assert CONTRACT_VERSION == "4B.4.3.6.6.28E"


def test_valid_health_report_ready_and_fail_closed_flags() -> None:
    payload = build_scheduler_execution_health_report(
        registration_approval_report=valid_registration(),
        cycle_report=valid_cycle(),
        ledger_rows=valid_rows(),
        task_probe=valid_task_probe(),
        operator_execution_review=True,
    )
    assert payload["ok"] is True
    assert payload["decision"] == "HYP006_R1_CANONICAL_SHADOW_SCHEDULER_EXECUTION_HEALTH_READY"
    assert payload["approved_for_shadow_collection_continuity"] is True
    assert payload["approved_for_paper_candidate"] is False
    assert payload["approved_for_live_real"] is False
    assert payload["scheduler_mutation_performed"] is False
    assert payload["scheduler_task_created"] is False


def test_missing_operator_execution_review_blocks() -> None:
    payload = build_scheduler_execution_health_report(
        registration_approval_report=valid_registration(),
        cycle_report=valid_cycle(),
        ledger_rows=valid_rows(),
        task_probe=valid_task_probe(),
        operator_execution_review=False,
    )
    assert payload["ok"] is False
    assert "NO_OPERATOR_EXECUTION_HEALTH_REVIEW" in payload["blockers"]


def test_invalid_scheduler_task_blocks() -> None:
    ok, reasons, _ = validate_scheduler_task_health({"exists": False, "task_name": PROPOSED_SCHEDULER_TASK_NAME})
    assert ok is False
    assert "SCHEDULER_TASK_NOT_FOUND" in reasons


def test_ledger_duplicate_blocks() -> None:
    rows = valid_rows() + [dict(valid_rows()[0])]
    ok, reasons, summary = validate_ledger_continuity(rows)
    assert ok is False
    assert summary["duplicate_observation_count"] == 1
    assert "LEDGER_DUPLICATE_OBSERVATION_IDS_PRESENT" in reasons


def test_ledger_summary_profit_factor() -> None:
    summary = summarize_ledger_continuity(valid_rows())
    assert summary["ledger_row_count"] == 2
    assert summary["net_return_bps"] == 75.0
    assert summary["profit_factor"] == 4.0
    assert summary["symbols_observed_count"] == 2


def test_write_health_bundle(tmp_path: Path) -> None:
    payload = build_scheduler_execution_health_report(
        registration_approval_report=valid_registration(),
        cycle_report=valid_cycle(),
        ledger_rows=valid_rows(),
        task_probe=valid_task_probe(),
        operator_execution_review=True,
    )
    report_json, continuity_json, report_md = write_health_bundle(payload, tmp_path)
    assert report_json.exists()
    assert continuity_json.exists()
    assert report_md.exists()
    loaded = json.loads(report_json.read_text(encoding="utf-8"))
    assert loaded["contract_version"] == CONTRACT_VERSION


def test_non_windows_probe_fails_closed_shape() -> None:
    probe = probe_windows_task_scheduler(PROPOSED_SCHEDULER_TASK_NAME)
    assert "exists" in probe
    assert probe["task_name"] == PROPOSED_SCHEDULER_TASK_NAME
