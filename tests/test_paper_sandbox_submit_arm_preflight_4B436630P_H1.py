from __future__ import annotations

from tradebot.config import Settings
from tradebot.paper_sandbox_submit_arm_preflight import READY_DECISION, build_paper_sandbox_submit_arm_preflight_snapshot, evaluate_source_30o_reconciliation


def h6_summary_payload() -> dict[str, object]:
    return {
        "contract_version": "4B.4.3.6.6.30O-H6",
        "checks": {
            "target_30o_checker_ok": True,
            "target_ledger_consumed": True,
            "target_mismatch_zero": True,
            "target_reconciliation_ok": True,
            "target_sqlite_mirror_ok": True,
            "target_exchange_submit_blocked": True,
            "target_live_real_blocked": True,
        },
        "target_30o_report_summary": {
            "contract_version": "4B.4.3.6.6.30O",
            "ok": True,
            "module_probe": {
                "decision": "PAPER_SANDBOX_EXECUTION_RECONCILIATION_GATE_READY_MISMATCH_ZERO_SQLITE_MIRROR_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL",
                "ledger_consumed": True,
                "mismatch_zero": True,
                "reconciliation_ok": True,
                "sqlite_mirror_ok": True,
                "exchange_submit_blocked": True,
                "live_real_blocked": True,
            },
        },
        "exchange_submit_performed": False,
        "trading_action_performed": False,
        "order_actions_performed": False,
    }


def test_h1_consumes_30o_h6_nested_summary_as_valid_source() -> None:
    source = h6_summary_payload()
    status = evaluate_source_30o_reconciliation(source)
    assert status.ok is True
    assert status.ledger_consumed is True
    assert status.mismatch_zero is True
    assert status.sqlite_mirror_ok is True


def test_h1_run_decision_ready_with_30o_h6_nested_summary() -> None:
    payload = build_paper_sandbox_submit_arm_preflight_snapshot(Settings(), h6_summary_payload())
    assert payload["decision"] == READY_DECISION
    assert payload["approved_for_30o_reconciliation_proof_consumption"] is True
    assert payload["approved_for_paper_sandbox_submit_arm_preflight"] is True
    assert payload["approved_for_exchange_submit"] is False
    assert payload["approved_for_live_real"] is False
    assert payload["submit_order_still_blocked"] is True
