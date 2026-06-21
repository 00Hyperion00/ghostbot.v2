from __future__ import annotations

import json
from pathlib import Path

from tradebot.config import Settings
from tradebot.paper_sandbox_submit_arm_preflight import (
    READY_DECISION,
    build_from_latest_30o_ready_report,
    build_paper_sandbox_submit_arm_preflight_snapshot,
    evaluate_source_30o_reconciliation,
)

def real_30o_h6_fixture() -> dict[str, object]:
    return {
        "contract_version": "4B.4.3.6.6.30O-H6",
        "decision": "PAPER_SANDBOX_EXECUTION_RECONCILIATION_GATE_READY_MISMATCH_ZERO_SQLITE_MIRROR_NO_EXCHANGE_SUBMIT_NO_LIVE_REAL",
        "mismatch_count": 0,
        "sqlite_mirror_ok": True,
        "module_probe": {
            "reconciliation_ok": True,
            "mismatch_zero": True,
            "sqlite_mirror_ok": True,
            "module_probe_ledger_consumed": True,
        },
        "approved_for_exchange_submit": False,
        "approved_for_live_real": False,
        "exchange_submit_performed": False,
        "trading_action_performed": False,
        "order_actions_performed": False,
    }

def test_30p_h3_consumes_real_h6_ledger_key_shape() -> None:
    source = evaluate_source_30o_reconciliation(real_30o_h6_fixture())
    assert source.ok is True
    payload = build_paper_sandbox_submit_arm_preflight_snapshot(Settings(), real_30o_h6_fixture())
    assert payload["decision"] == READY_DECISION
    assert payload["approved_for_30o_reconciliation_proof_consumption"] is True
    assert payload["approved_for_exchange_submit"] is False
    assert payload["approved_for_live_real"] is False

def test_30p_h3_selects_valid_30o_report_over_newer_invalid(tmp_path: Path) -> None:
    invalid = real_30o_h6_fixture()
    invalid["module_probe"] = {"reconciliation_ok": True, "mismatch_zero": True, "sqlite_mirror_ok": True}
    valid = real_30o_h6_fixture()
    (tmp_path / "4B436630O_paper_sandbox_execution_reconciliation_gate_20260621T130000Z_ready.json").write_text(json.dumps(invalid), encoding="utf-8")
    (tmp_path / "4B436630O_paper_sandbox_execution_reconciliation_gate_20260621T120000Z_ready.json").write_text(json.dumps(valid), encoding="utf-8")
    payload = build_from_latest_30o_ready_report(Settings(), reports_dir=tmp_path)
    assert payload["decision"] == READY_DECISION
    assert payload["approved_for_30o_reconciliation_proof_consumption"] is True
    assert payload["submit_order_still_blocked"] is True
