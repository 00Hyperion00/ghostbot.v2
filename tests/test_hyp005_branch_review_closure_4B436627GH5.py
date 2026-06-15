from __future__ import annotations

import json
from pathlib import Path

from tradebot.hyp005_branch_review_closure import (
    CONTRACT_VERSION,
    build_branch_review_closure_report,
    load_jsonl,
    summarize_ledger,
    write_json_atomic,
)


def _ledger() -> list[dict[str, object]]:
    return [
        {"observation_id": "HYP-005-BTCUSDT-4h-2026-06-01T000000Z", "symbol": "BTCUSDT", "timeframe": "4h", "timestamp_utc": "2026-06-01T00:00:00+00:00", "forward_return_bps_final": -120.0},
        {"observation_id": "HYP-005-ETHUSDT-4h-2026-06-01T040000Z", "symbol": "ETHUSDT", "timeframe": "4h", "timestamp_utc": "2026-06-01T04:00:00+00:00", "forward_return_bps_final": 20.0},
        {"observation_id": "HYP-005-XRPUSDT-4h-2026-06-01T080000Z", "symbol": "XRPUSDT", "timeframe": "4h", "timestamp_utc": "2026-06-01T08:00:00+00:00", "forward_return_bps_final": -80.0},
    ]


def _h3() -> dict[str, object]:
    return {
        "contract_version": "4B.4.3.6.6.27G-H3",
        "stagnation": {"status": "STAGNATED", "new_unique_observation_available": False, "duplicate_only_current_candidates": True},
        "candidate_diagnostics": {"exact_candidate_count": 21, "new_unique_candidate_count": 0, "duplicate_candidate_count": 21, "near_miss_count": 73, "top_bottleneck_filter": "min_sweep_bps"},
    }


def _h4(status: str = "REJECTED_NEGATIVE_EXPECTANCY", promising: int = 0) -> dict[str, object]:
    return {
        "contract_version": "4B.4.3.6.6.27G-H4",
        "research_summary": {
            "variant_count": 27,
            "variants_with_new_unique_candidates": 26,
            "promising_research_only_variant_count": promising,
            "paper_transition_candidate_found": False,
            "strategy_parameter_mutation_recommended": False,
            "best_research_variant_id": "sweep_12p0__wick_38p0__compression_1p15",
            "best_research_status": status,
        },
        "top_variants": [{"new_unique_candidate_count": 10, "performance": {"net_return_bps": -4100.0, "mean_return_bps": -132.0, "profit_factor": 0.29}}],
    }


def test_contract_version() -> None:
    assert CONTRACT_VERSION == "4B.4.3.6.6.27G-H5"


def test_negative_expectancy_closure_recommended() -> None:
    report = build_branch_review_closure_report(ledger_rows=_ledger(), h3_report=_h3(), h4_report=_h4())
    assert report["branch_closure_recommended"] is True
    assert report["decision"] == "HYP005_R1_BRANCH_REVIEW_NO_PROMOTION_CLOSURE_READY"
    assert report["approved_for_paper_candidate"] is False
    assert report["approved_for_live_real"] is False
    assert report["branch_state_mutation_performed"] is False
    assert report["operator_review_required_for_closure"] is True


def test_promising_h4_blocks_closure_recommendation() -> None:
    report = build_branch_review_closure_report(ledger_rows=_ledger(), h3_report=_h3(), h4_report=_h4("PROMISING_RESEARCH_ONLY_VARIANT", promising=1))
    assert report["branch_closure_recommended"] is False
    assert report["approved_for_paper_candidate"] is False
    assert report["closure_criteria"]["h4_relaxation_rejected"] is False


def test_non_stagnated_h3_blocks_closure_recommendation() -> None:
    h3 = _h3()
    h3["stagnation"] = {"status": "ACTIVE", "new_unique_observation_available": True}
    report = build_branch_review_closure_report(ledger_rows=_ledger(), h3_report=h3, h4_report=_h4())
    assert report["branch_closure_recommended"] is False
    assert report["closure_criteria"]["h3_stagnation_confirmed"] is False


def test_ledger_summary_negative_expectancy() -> None:
    summary = summarize_ledger(_ledger())
    assert summary["profit_factor"] < 1.0
    assert summary["mean_return_bps"] < 0.0
    assert summary["shadow_sample_target_met"] is False


def test_jsonl_loader_and_ascii_json_writer(tmp_path: Path) -> None:
    path = tmp_path / "ledger.jsonl"
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in _ledger()) + "\n", encoding="utf-8")
    rows = load_jsonl(path)
    assert len(rows) == 3
    output = tmp_path / "Masaüstü" / "closure.json"
    write_json_atomic(output, {"path": "Masaüstü", "rows": len(rows)})
    raw = output.read_text(encoding="utf-8")
    assert "\\u00fc" in raw
    assert json.loads(raw)["path"] == "Masaüstü"
