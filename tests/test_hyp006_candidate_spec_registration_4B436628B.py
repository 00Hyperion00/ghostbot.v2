from __future__ import annotations

import json
from pathlib import Path

from tradebot.hyp006_candidate_spec_registration import (
    BRANCH_ID,
    CONTRACT_VERSION,
    NEXT_REQUIRED_GATE,
    build_hyp006_candidate_spec_draft,
    build_hyp006_registration_gate_report,
    discovery_supports_hyp006,
    validate_candidate_spec_draft,
    write_report_bundle,
)


def _discovery() -> dict[str, object]:
    return {
        "contract_version": "4B.4.3.6.6.28A",
        "decision": "HYP005_FAILED_BRANCH_LESSONS_CANDIDATE_DISCOVERY_READY",
        "selected_research_candidate": {
            "candidate_id": "HYP-006-R1",
            "branch_name": "failed_downside_sweep_reversal_continuation_short",
            "score": 63.361056,
            "risk_level": "HIGH",
            "expected_edge_proxy_bps": 115.12272,
            "approved_for_candidate_spec_drafting": True,
            "approved_for_shadow_collection": False,
            "approved_for_paper_candidate": False,
            "approved_for_live_real": False,
        },
    }


def test_contract_version() -> None:
    assert CONTRACT_VERSION == "4B.4.3.6.6.28B"


def test_discovery_supports_selected_hyp006() -> None:
    assert discovery_supports_hyp006(_discovery()) is True


def test_candidate_spec_draft_contains_fail_closed_hyp006_fields() -> None:
    spec = build_hyp006_candidate_spec_draft(_discovery())
    assert spec["branch_id"] == BRANCH_ID
    assert spec["no_order_shadow_only"] is True
    assert spec["registration_gate"]["next_required_gate"] == NEXT_REQUIRED_GATE
    assert spec["approvals"]["approved_for_shadow_collection"] is False
    assert spec["approvals"]["approved_for_paper_candidate"] is False
    assert spec["approvals"]["approved_for_live_real"] is False


def test_validate_candidate_spec_blocks_unsafe_approval() -> None:
    spec = build_hyp006_candidate_spec_draft(_discovery())
    ok, reasons = validate_candidate_spec_draft(spec)
    assert ok is True
    assert reasons == []
    spec["approvals"]["approved_for_live_real"] = True
    ok2, reasons2 = validate_candidate_spec_draft(spec)
    assert ok2 is False
    assert "UNSAFE_APPROVAL_APPROVED_FOR_LIVE_REAL" in reasons2


def test_report_is_ready_but_does_not_start_shadow_collection() -> None:
    report = build_hyp006_registration_gate_report(discovery_report=_discovery())
    assert report["decision"] == "HYP006_R1_CANDIDATE_SPEC_DRAFT_REGISTRATION_GATE_READY"
    assert report["approved_for_no_order_shadow_registration_candidate"] is True
    assert report["approved_for_shadow_collection"] is False
    assert report["approved_for_training_candidate"] is False
    assert report["approved_for_paper_candidate"] is False
    assert report["approved_for_live_real"] is False
    assert report["scheduler_mutation_performed"] is False
    assert report["trading_action_performed"] is False


def test_wrong_discovery_blocks_gate() -> None:
    wrong = _discovery()
    wrong["selected_research_candidate"] = {"candidate_id": "HYP-007-R1"}
    report = build_hyp006_registration_gate_report(discovery_report=wrong)
    assert report["ok"] is False
    assert report["decision"] == "HYP006_R1_CANDIDATE_SPEC_DRAFT_REGISTRATION_GATE_BLOCKED"
    assert "VALID_28A_HYP006_SELECTION_NOT_FOUND" in report["blockers"]


def test_report_bundle_writes_report_and_candidate_spec(tmp_path: Path) -> None:
    report = build_hyp006_registration_gate_report(discovery_report=_discovery())
    report_json, spec_json, report_md = write_report_bundle(report, tmp_path)
    assert report_json.exists()
    assert spec_json.exists()
    assert report_md.exists()
    parsed = json.loads(spec_json.read_text(encoding="utf-8"))
    assert parsed["contract_version"] == CONTRACT_VERSION
    assert parsed["branch_id"] == BRANCH_ID
