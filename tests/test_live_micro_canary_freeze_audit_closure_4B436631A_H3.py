from __future__ import annotations

import json
from pathlib import Path

from tradebot.config import Settings
from tradebot.live_micro_canary_freeze_audit_closure import (
    READY_DECISION,
    build_from_explicit_30z_risk_review_report,
    evaluate_source_30z_risk_review,
)


def compact_30z_ready() -> dict[str, object]:
    return {
        "contract_version": "4B.4.3.6.6.30Z",
        "decision": "POST_LIVE_MICRO_CANARY_RISK_REVIEW_READY_PNL_FEE_SLIPPAGE_EMERGENCY_STOP_NO_ADDITIONAL_LIVE_ORDER",
        "ok": True,
        "approved_for_additional_exchange_submit": False,
        "approved_for_live_real_continuation": False,
        "patch_exchange_submit_performed": False,
        "patch_network_submit_attempted": False,
        "patch_live_real_order_performed": False,
        "additional_exchange_submit_performed": False,
        "additional_network_submit_attempted": False,
        "additional_live_real_order_performed": False,
    }


def test_explicit_30z_ready_override_normalizes_compact_summary(tmp_path: Path) -> None:
    source = compact_30z_ready()
    source["_explicit_source_30z_report_override"] = True
    status = evaluate_source_30z_risk_review(source, source_report_path="explicit.json")
    assert status.ok is True
    assert status.source_30y_h1_reconciliation_verified is True
    assert status.pnl_review_verified is True
    assert status.fee_review_verified is True
    assert status.slippage_review_verified is True
    assert status.emergency_stop_continuity_verified is True
    assert status.no_additional_live_order_verified is True


def test_explicit_source_report_builds_ready_closure(tmp_path: Path) -> None:
    reports = tmp_path / "production_hardening"
    reports.mkdir()
    # evidence pack required patterns
    for name in (
        "4B436630X_first_live_real_micro_canary_submit_request.json",
        "4B436630Y_live_real_micro_canary_reconciliation_ready.json",
        "4B436630Z_post_live_micro_canary_risk_review_20260622T081654Z_ready.json",
    ):
        (reports / name).write_text("{}", encoding="utf-8")
    source = reports / "4B436630Z_post_live_micro_canary_risk_review_20260622T081654Z_ready.json"
    source.write_text(json.dumps(compact_30z_ready()), encoding="utf-8")
    payload = build_from_explicit_30z_risk_review_report(
        Settings(),
        reports,
        source_30z_report=source,
        operator_id="operator-31a",
        finalization_token="FINALIZE_LIVE_MICRO_CANARY_AUDIT",
        audit_comment="explicit source override test",
        evidence_pack_id="LIVE_MICRO_CANARY_8114595899_CLOSURE_H3",
        acknowledge_hyp006_report_separation=True,
    )
    assert payload["decision"] == READY_DECISION
    assert payload["source_30z_risk_review_verified"] is True
    assert payload["approved_for_additional_exchange_submit"] is False
    assert payload["patch_network_submit_attempted"] is False
