from __future__ import annotations

from pathlib import Path

from tradebot.paper_transition_approval_evidence_capture import build_from_operator_inputs, write_report_bundle as write_30d_report
from tradebot.paper_transition_review_rerun import (
    EVIDENCE_REQUIRED_DECISION,
    READY_DECISION,
    build_from_latest_30d_ready_report,
    write_report_bundle as write_30e_report,
)

NOW_MS = 1_800_000_000_000


def _write_ready_30d(reports_dir: Path) -> Path:
    payload = build_from_operator_inputs(
        operator_id="operator-30d",
        confirmation_token="CONFIRM_PAPER_TRANSITION_CANDIDATE",
        freeze_token="FREEZE_PAPER_TRANSITION_SANDBOX_ENVELOPE",
        issue_approval=True,
        freeze_runtime_envelope=True,
        verify_final_risk_cap=True,
        reports_dir=reports_dir,
        now_ms=NOW_MS,
    )
    json_path, _ = write_30d_report(payload, reports_dir)
    assert json_path.name.endswith("_ready.json")
    return json_path


def test_review_rerun_requires_30d_ready_evidence(tmp_path: Path) -> None:
    payload = build_from_latest_30d_ready_report(tmp_path)
    assert payload["decision"] == EVIDENCE_REQUIRED_DECISION
    assert payload["approved_for_paper_transition_review_rerun"] is False
    assert payload["approved_for_paper_transition_candidate_review"] is False
    assert payload["approved_for_paper_transition_candidate"] is False
    assert payload["approved_for_paper_candidate"] is False
    assert payload["approved_for_live_real"] is False
    assert payload["paper_order_enablement_still_blocked"] is True


def test_ready_30d_evidence_reruns_30c_review_only(tmp_path: Path) -> None:
    _write_ready_30d(tmp_path)
    payload = build_from_latest_30d_ready_report(tmp_path)
    assert payload["decision"] == READY_DECISION
    assert payload["source_30d_ready_evidence_verified"] is True
    assert payload["source_30c_review_rerun_verified"] is True
    assert payload["approved_for_paper_transition_review_rerun"] is True
    assert payload["approved_for_paper_transition_candidate_review"] is True
    assert payload["approved_for_paper_transition_candidate"] is False
    assert payload["approved_for_paper_candidate"] is False
    assert payload["approved_for_live_real"] is False
    assert payload["runtime_activation_blocked"] is True
    assert payload["paper_live_order_blocked"] is True
    assert payload["training_reload_blocked"] is True
    assert payload["trading_action_performed"] is False
    assert payload["order_actions_performed"] is False
    assert payload["paper_live_order_enablement_present"] is False


def test_input_required_30d_report_is_not_consumed_as_ready(tmp_path: Path) -> None:
    input_required = build_from_operator_inputs(reports_dir=tmp_path, now_ms=NOW_MS)
    write_30d_report(input_required, tmp_path)
    payload = build_from_latest_30d_ready_report(tmp_path)
    assert payload["decision"] == EVIDENCE_REQUIRED_DECISION
    assert payload["source_30d_ready_evidence_verified"] is False
    assert payload["source_30c_review_rerun_verified"] is False


def test_30e_report_collision_guard_uses_decision_suffix(tmp_path: Path) -> None:
    missing = build_from_latest_30d_ready_report(tmp_path)
    _write_ready_30d(tmp_path)
    ready = build_from_latest_30d_ready_report(tmp_path)
    first, _ = write_30e_report(missing, tmp_path)
    second, _ = write_30e_report(ready, tmp_path)
    assert first.exists()
    assert second.exists()
    assert first != second
    assert first.name.endswith("_30d_required.json")
    assert second.name.endswith("_ready.json")
