from __future__ import annotations

import json
from pathlib import Path

from tradebot.hypothesis_candidate_discovery import (
    CONTRACT_VERSION,
    build_hypothesis_candidate_discovery_report,
    summarize_ledger,
    write_report_bundle,
)


def _ledger_rows() -> list[dict[str, object]]:
    return [
        {"observation_id": "A", "symbol": "ADAUSDT", "timestamp_utc": "2026-01-01T00:00:00+00:00", "forward_return_bps_final": -100.0},
        {"observation_id": "B", "symbol": "BTCUSDT", "timestamp_utc": "2026-01-01T00:00:00+00:00", "forward_return_bps_final": -200.0},
        {"observation_id": "C", "symbol": "ETHUSDT", "timestamp_utc": "2026-01-02T00:00:00+00:00", "forward_return_bps_final": 50.0},
    ]


def _h3() -> dict[str, object]:
    return {"stagnation": {"status": "STAGNATED"}, "candidate_diagnostics": {"top_bottleneck_filter": "min_sweep_bps"}}


def _h4() -> dict[str, object]:
    return {"research_summary": {"paper_transition_candidate_found": False, "promising_research_only_variant_count": 0, "best_research_status": "REJECTED_NEGATIVE_EXPECTANCY"}}


def _h5() -> dict[str, object]:
    return {"closure_status": "CLOSE_NO_PROMOTION_RECOMMENDED", "closure_criteria": {"h3_stagnation_confirmed": True, "h4_relaxation_rejected": True, "sample_target_incomplete": True}}


def test_contract_version() -> None:
    assert CONTRACT_VERSION == "4B.4.3.6.6.28A"


def test_ledger_summary_detects_negative_expectancy() -> None:
    summary = summarize_ledger(_ledger_rows())
    assert summary.net_return_bps == -250.0
    assert summary.mean_return_bps < 0
    assert summary.profit_factor < 1.0


def test_report_selects_no_order_research_candidate() -> None:
    report = build_hypothesis_candidate_discovery_report(ledger_rows=_ledger_rows(), h3_diagnostics=_h3(), h4_sensitivity=_h4(), h5_closure=_h5())
    selected = report["selected_research_candidate"]
    assert selected["candidate_id"] == "HYP-006-R1"
    assert selected["required_next_gate"].startswith("28B")
    assert report["candidate_spec_generation_required_next"] is True


def test_failed_branch_lessons_are_integrated() -> None:
    report = build_hypothesis_candidate_discovery_report(ledger_rows=_ledger_rows(), h3_diagnostics=_h3(), h4_sensitivity=_h4(), h5_closure=_h5())
    lessons = report["failed_branch_lessons"]
    assert lessons["negative_expectancy_confirmed"] is True
    assert lessons["stagnation_confirmed"] is True
    assert lessons["parameter_relaxation_rejected"] is True


def test_report_never_approves_shadow_paper_live_or_training() -> None:
    report = build_hypothesis_candidate_discovery_report(ledger_rows=_ledger_rows(), h3_diagnostics=_h3(), h4_sensitivity=_h4(), h5_closure=_h5())
    assert report["approved_for_shadow_collection"] is False
    assert report["approved_for_training_candidate"] is False
    assert report["approved_for_paper_candidate"] is False
    assert report["approved_for_live_real"] is False
    assert report["trading_action_performed"] is False
    assert report["branch_state_mutation_performed"] is False


def test_report_bundle_is_written_ascii_safe(tmp_path: Path) -> None:
    report = build_hypothesis_candidate_discovery_report(ledger_rows=_ledger_rows(), h3_diagnostics=_h3(), h4_sensitivity=_h4(), h5_closure=_h5())
    json_path, md_path = write_report_bundle(report, tmp_path)
    assert json_path.exists()
    assert md_path.exists()
    parsed = json.loads(json_path.read_text(encoding="utf-8"))
    assert parsed["contract_version"] == CONTRACT_VERSION
