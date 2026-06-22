from __future__ import annotations

from pathlib import Path

from tradebot.config import Settings
from tradebot.live_micro_canary_freeze_audit_closure import (
    FINALIZATION_TOKEN,
    OPERATOR_AUDIT_REQUIRED_DECISION,
    READY_DECISION,
    build_from_latest_30z_risk_review_report,
    build_live_micro_canary_freeze_audit_closure_snapshot,
    evaluate_source_30z_risk_review,
    latest_valid_30z_risk_review_report,
    write_report_bundle,
)


def source_30z() -> dict[str, object]:
    return {
        "contract_version": "4B.4.3.6.6.30Z",
        "decision": "POST_LIVE_MICRO_CANARY_RISK_REVIEW_READY_PNL_FEE_SLIPPAGE_EMERGENCY_STOP_NO_ADDITIONAL_LIVE_ORDER",
        "approved_for_post_live_micro_canary_risk_review": True,
        "approved_for_post_canary_observation_window": True,
        "approved_for_additional_exchange_submit": False,
        "approved_for_live_real_continuation": False,
        "source_30y_h1_reconciliation_verified": True,
        "pnl_review_verified": True,
        "fee_review_verified": True,
        "slippage_review_verified": True,
        "emergency_stop_continuity_verified": True,
        "no_additional_live_order_verified": True,
        "patch_exchange_submit_performed": False,
        "patch_network_submit_attempted": False,
        "patch_live_real_order_performed": False,
        "additional_exchange_submit_performed": False,
        "additional_network_submit_attempted": False,
        "additional_live_real_order_performed": False,
        "mismatch_count": 0,
        "fill_notional_usd": 4.968744,
        "requested_notional_usd": 5.0,
        "fee_value_usd": 0.004968744,
        "fee_bps": 10.0,
        "slippage_bps": -62.512,
        "unrealized_pnl_usd": -0.004968744,
        "unrealized_pnl_pct": -0.1,
    }


def write_minimal_evidence_chain(tmp_path: Path) -> None:
    (tmp_path / "4B436630X_first_live_real_micro_canary_20260621T000000Z_ready.json").write_text("{}", encoding="utf-8")
    (tmp_path / "4B436630Y_live_real_micro_canary_reconciliation_20260621T000001Z_ready.json").write_text("{}", encoding="utf-8")
    (tmp_path / "4B436630Z_post_live_micro_canary_risk_review_20260621T000002Z_ready.json").write_text(__import__("json").dumps(source_30z()), encoding="utf-8")


def test_source_30z_ready_required() -> None:
    assert evaluate_source_30z_risk_review(source_30z()).ok is True
    bad = source_30z()
    bad["additional_live_real_order_performed"] = True
    assert evaluate_source_30z_risk_review(bad).ok is False


def test_operator_audit_required_without_token(tmp_path: Path) -> None:
    write_minimal_evidence_chain(tmp_path)
    payload = build_live_micro_canary_freeze_audit_closure_snapshot(Settings(), source_30z(), reports_dir=tmp_path)
    assert payload["decision"] == OPERATOR_AUDIT_REQUIRED_DECISION
    assert payload["source_30z_risk_review_verified"] is True
    assert payload["evidence_pack_sealed"] is True
    assert payload["approved_for_additional_exchange_submit"] is False
    assert payload["patch_network_submit_attempted"] is False


def test_ready_freeze_audit_closure(tmp_path: Path) -> None:
    write_minimal_evidence_chain(tmp_path)
    payload = build_live_micro_canary_freeze_audit_closure_snapshot(
        Settings(),
        source_30z(),
        reports_dir=tmp_path,
        operator_id="operator-31a",
        finalization_token=FINALIZATION_TOKEN,
        audit_comment="no further live orders approved",
        evidence_pack_id="LIVE_MICRO_CANARY_8114595899_CLOSURE",
    )
    assert payload["decision"] == READY_DECISION
    assert payload["approved_for_live_micro_canary_freeze_audit_closure"] is True
    assert payload["approved_for_release_evidence_archive"] is True
    assert payload["approved_for_additional_exchange_submit"] is False
    assert payload["approved_for_live_real_order"] is False
    assert payload["evidence_pack_file_count"] >= 3
    assert len(payload["evidence_pack_manifest_sha256"]) == 64


def test_latest_valid_30z_and_bundle_round_trip(tmp_path: Path) -> None:
    write_minimal_evidence_chain(tmp_path)
    selected, payload = latest_valid_30z_risk_review_report(tmp_path)
    assert selected is not None
    assert payload["contract_version"] == "4B.4.3.6.6.30Z"
    built = build_from_latest_30z_risk_review_report(
        Settings(),
        tmp_path,
        operator_id="operator-31a",
        finalization_token=FINALIZATION_TOKEN,
        evidence_pack_id="LIVE_MICRO_CANARY_8114595899_CLOSURE",
    )
    assert built["decision"] == READY_DECISION
    json_path, md_path = write_report_bundle(built, tmp_path)
    assert json_path.exists()
    assert md_path.exists()
