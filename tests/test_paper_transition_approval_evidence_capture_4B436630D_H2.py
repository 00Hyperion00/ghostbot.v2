from __future__ import annotations

from pathlib import Path

import tradebot.paper_transition_approval_evidence_capture as module

NOW_MS = 1_800_000_000_000


def test_30d_h2_report_collision_guard_uses_unique_decision_paths(tmp_path: Path, monkeypatch) -> None:
    default_payload = module.build_from_operator_inputs(now_ms=NOW_MS)
    ready_payload = module.build_from_operator_inputs(
        operator_id="operator-30d",
        confirmation_token="CONFIRM_PAPER_TRANSITION_CANDIDATE",
        freeze_token="FREEZE_PAPER_TRANSITION_SANDBOX_ENVELOPE",
        issue_approval=True,
        freeze_runtime_envelope=True,
        verify_final_risk_cap=True,
        now_ms=NOW_MS,
    )
    monkeypatch.setattr(module, "utc_stamp", lambda: "20300101T000000Z")
    default_json, default_md = module.write_report_bundle(default_payload, tmp_path)
    ready_json, ready_md = module.write_report_bundle(ready_payload, tmp_path)
    assert default_json != ready_json
    assert default_md != ready_md
    assert default_json.exists()
    assert default_md.exists()
    assert ready_json.exists()
    assert ready_md.exists()
    assert "input_required" in default_json.name
    assert "ready" in ready_json.name


def test_30d_h2_ready_evidence_still_blocks_paper_and_live_real() -> None:
    payload = module.build_from_operator_inputs(
        operator_id="operator-30d",
        confirmation_token="CONFIRM_PAPER_TRANSITION_CANDIDATE",
        freeze_token="FREEZE_PAPER_TRANSITION_SANDBOX_ENVELOPE",
        issue_approval=True,
        freeze_runtime_envelope=True,
        verify_final_risk_cap=True,
        now_ms=NOW_MS,
    )
    assert payload["approved_for_operator_approval_evidence_capture"] is True
    assert payload["approved_for_paper_transition_candidate_review"] is True
    assert payload["approved_for_paper_transition_candidate"] is False
    assert payload["approved_for_paper_candidate"] is False
    assert payload["approved_for_live_real"] is False
    assert payload["paper_live_order_blocked"] is True
    assert payload["runtime_activation_blocked"] is True
    assert payload["training_reload_blocked"] is True
    assert payload["trading_action_performed"] is False
    assert payload["order_actions_performed"] is False
