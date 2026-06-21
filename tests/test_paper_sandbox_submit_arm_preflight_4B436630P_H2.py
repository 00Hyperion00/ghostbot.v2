from __future__ import annotations

from tradebot.config import Settings
from tradebot.paper_sandbox_submit_arm_preflight import READY_DECISION, build_paper_sandbox_submit_arm_preflight_snapshot


def direct_30o_h6_ready_report() -> dict[str, object]:
    return {
        "contract_version": "4B.4.3.6.6.30O-H6",
        "decision": "PAPER_SANDBOX_EXECUTION_RECONCILIATION_GATE_READY_MISMATCH_ZERO_SQLITE_MIRROR_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL",
        "reconciliation": {"mismatch_count": 0, "mismatch_zero": True, "reconciliation_ok": True},
        "sqlite_audit_mirror": {"sqlite_mirror_ok": True, "sqlite_ok": True, "mirror_path": "audit.sqlite"},
        "source_30n": {"ledger_consumed": True, "ledger_event": {"event_id": "paper-exec-1"}},
        "risk": {"approved_for_exchange_submit": False, "exchange_submit_performed": False, "approved_for_live_real": False},
        "trading_action_performed": False,
        "order_actions_performed": False,
    }


def test_30p_h2_consumes_direct_30o_h6_ready_evidence() -> None:
    payload = build_paper_sandbox_submit_arm_preflight_snapshot(Settings(), direct_30o_h6_ready_report())
    assert payload["decision"] == READY_DECISION
    assert payload["approved_for_30o_reconciliation_proof_consumption"] is True
    assert payload["source_30o_reconciliation_verified"] is True
    assert payload["approved_for_exchange_submit"] is False
    assert payload["approved_for_paper_sandbox_canary_submit"] is False
    assert payload["approved_for_live_real"] is False


def test_30p_h2_blocks_direct_30o_h6_with_exchange_submit_flag() -> None:
    source = direct_30o_h6_ready_report()
    source["exchange_submit_performed"] = True
    payload = build_paper_sandbox_submit_arm_preflight_snapshot(Settings(), source)
    assert payload["decision"] != READY_DECISION
    assert payload["approved_for_exchange_submit"] is False
    assert payload["exchange_submit_performed"] is False
