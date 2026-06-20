from __future__ import annotations

from pathlib import Path

from tradebot.config import Settings
from tradebot.paper_sandbox_operator_final_go_no_go_gate import (
    OPERATOR_APPROVAL_REQUIRED_DECISION,
    READY_DECISION,
    SOURCE_30J_REQUIRED_DECISION,
    build_paper_sandbox_operator_final_go_no_go_snapshot,
    write_report_bundle,
)


def source_30j_ready() -> dict[str, object]:
    return {
        "contract_version": "4B.4.3.6.6.30J",
        "ok": True,
        "decision": "PAPER_SANDBOX_DRY_RUN_RECONCILIATION_AUDIT_LEDGER_PROOF_READY_MISMATCH_ZERO_NO_EXCHANGE_SUBMIT_PAPER_CANDIDATE_BLOCKED_LIVE_REAL_BLOCKED",
        "approved_for_paper_sandbox_dry_run_reconciliation_audit_ledger_proof": True,
        "approved_for_30i_simulated_fill_ledger_consumption": True,
        "approved_for_mismatch_zero_proof": True,
        "approved_for_sqlite_audit_mirror": True,
        "approved_for_no_exchange_submit_verification": True,
        "approved_for_paper_sandbox_dry_run_execution": False,
        "approved_for_exchange_submit": False,
        "approved_for_paper_transition_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "reconciliation_mismatch_zero_verified": True,
        "sqlite_audit_mirror_verified": True,
        "no_exchange_submit_verified": True,
        "mismatch_count": 0,
        "exchange_submit_performed": False,
        "trading_action_performed": False,
        "order_actions_performed": False,
        "paper_live_order_enablement_present": False,
    }


def test_30k_requires_operator_final_approval_by_default() -> None:
    payload = build_paper_sandbox_operator_final_go_no_go_snapshot(Settings(), source_30j_ready(), now_ms=1_800_000_000_000)
    assert payload["decision"] == OPERATOR_APPROVAL_REQUIRED_DECISION
    assert payload["approved_for_paper_sandbox_operator_final_go_no_go_gate"] is False
    assert payload["approved_for_paper_candidate"] is False
    assert payload["approved_for_live_real"] is False


def test_30k_ready_with_explicit_operator_approval_and_checklist() -> None:
    payload = build_paper_sandbox_operator_final_go_no_go_snapshot(
        Settings(),
        source_30j_ready(),
        operator_id="operator-30k",
        approval_token="APPROVE_PAPER_SANDBOX_GO_NO_GO",
        issue_final_approval=True,
        confirm_kill_switch=True,
        confirm_caps=True,
        now_ms=1_800_000_000_000,
    )
    assert payload["decision"] == READY_DECISION
    assert payload["approved_for_operator_final_paper_sandbox_approval"] is True
    assert payload["approved_for_kill_switch_caps_checklist"] is True
    assert payload["approved_for_paper_sandbox_go_no_go_candidate"] is True
    assert payload["approved_for_paper_candidate"] is False
    assert payload["approved_for_exchange_submit"] is False
    assert payload["approved_for_live_real"] is False
    assert payload["exchange_submit_performed"] is False
    assert payload["trading_action_performed"] is False


def test_30k_blocks_bad_30j_source() -> None:
    bad = source_30j_ready()
    bad["mismatch_count"] = 1
    payload = build_paper_sandbox_operator_final_go_no_go_snapshot(
        Settings(),
        bad,
        operator_id="operator-30k",
        approval_token="APPROVE_PAPER_SANDBOX_GO_NO_GO",
        issue_final_approval=True,
        confirm_kill_switch=True,
        confirm_caps=True,
        now_ms=1_800_000_000_000,
    )
    assert payload["decision"] == SOURCE_30J_REQUIRED_DECISION
    assert payload["source_30j_reconciliation_proof_verified"] is False
    assert payload["approved_for_paper_candidate"] is False
    assert payload["approved_for_live_real"] is False


def test_30k_report_collision_and_no_runtime_action(tmp_path: Path) -> None:
    payload = build_paper_sandbox_operator_final_go_no_go_snapshot(
        Settings(),
        source_30j_ready(),
        operator_id="operator-30k",
        approval_token="APPROVE_PAPER_SANDBOX_GO_NO_GO",
        issue_final_approval=True,
        confirm_kill_switch=True,
        confirm_caps=True,
        now_ms=1_800_000_000_000,
    )
    first_json, first_md = write_report_bundle(payload, tmp_path)
    second_json, second_md = write_report_bundle(payload, tmp_path)
    assert first_json.exists()
    assert first_md.exists()
    assert second_json.exists()
    assert second_md.exists()
    assert first_json != second_json
    assert payload["runtime_overlay_activation_performed"] is False
    assert payload["training_performed"] is False
    assert payload["reload_performed"] is False
