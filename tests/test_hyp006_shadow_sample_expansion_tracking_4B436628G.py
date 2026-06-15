from __future__ import annotations

import json
from pathlib import Path

from tradebot.hyp006_shadow_sample_expansion_tracking import (
    CONTRACT_VERSION,
    baseline_report_is_ready,
    build_shadow_sample_expansion_report,
    compute_expansion_delta,
    compute_ledger_metrics,
    load_json,
    load_jsonl,
    write_report_bundle,
)


def _baseline(unique: int = 20) -> dict[str, object]:
    return {
        "contract_version": "4B.4.3.6.6.28F",
        "decision": "HYP006_R1_SHADOW_OPERATOR_COCKPIT_BASELINE_READY",
        "ok": True,
        "branch_id": "HYP-006-R1",
        "approved_for_acceptance_tracking": True,
        "approved_for_shadow_collection_continuity": True,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "order_actions_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "baseline_summary": {
            "unique_observation_ids": unique,
            "mean_return_bps": 108.911085,
            "median_return_bps": 9.884293,
            "profit_factor": 2.776782,
            "win_rate_pct": 50.0,
            "data_quality_pct": 100.0,
            "max_slippage_proxy_bps": 11.729452,
        },
        "no_order_continuity_monitor": {
            "unique_observation_ids": unique,
            "duplicate_observation_count": 0,
            "unsafe_row_count": 0,
        },
    }


def _rows(count: int = 24, *, win_rate_high: bool = False) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for idx in range(count):
        if win_rate_high:
            value = 90.0 if idx < int(count * 0.7) else -30.0
        else:
            value = 100.0 if idx % 2 == 0 else -20.0
        rows.append(
            {
                "contract_version": "4B.4.3.6.6.28D",
                "hypothesis_id": "HYP-006",
                "branch_id": "HYP-006-R1",
                "branch_name": "failed_downside_sweep_reversal_continuation_short",
                "strategy_family": "short_failed_liquidity_sweep_continuation",
                "no_order_measurement_only": True,
                "observation_id": f"HYP-006-BTCUSDT-4h-2026-06-{idx + 1:02d}T000000Z",
                "symbol": "BTCUSDT" if idx % 2 == 0 else "ETHUSDT",
                "timestamp_utc": f"2026-06-{idx + 1:02d}T00:00:00+00:00",
                "forward_return_bps_final_short_probe": value,
                "spread_slippage_proxy_bps": 5.0,
            }
        )
    return rows


def test_contract_and_baseline_contract_valid() -> None:
    assert CONTRACT_VERSION == "4B.4.3.6.6.28G"
    assert baseline_report_is_ready(_baseline()) is True


def test_expansion_delta_from_28f_baseline() -> None:
    metrics = compute_ledger_metrics(_rows(24))
    delta = compute_expansion_delta(metrics, _baseline(20))
    assert delta.previous_unique_observation_ids == 20
    assert delta.current_unique_observation_ids == 24
    assert delta.new_unique_observation_count == 4
    assert delta.target_remaining_count == 6
    assert delta.sample_progress_delta_pct > 0


def test_tracking_report_keeps_paper_live_order_blocked() -> None:
    payload = build_shadow_sample_expansion_report(baseline_report=_baseline(), ledger_rows=_rows(24))
    assert payload["ok"] is True
    assert payload["sample_expansion_tracking_ready"] is True
    assert payload["approved_for_shadow_collection_continuity"] is True
    assert payload["approved_for_acceptance_tracking"] is True
    assert payload["approved_for_paper_candidate"] is False
    assert payload["approved_for_live_real"] is False
    assert payload["order_actions_performed"] is False
    assert payload["training_performed"] is False
    assert payload["reload_performed"] is False


def test_tracking_report_remains_blocked_until_sample_target() -> None:
    payload = build_shadow_sample_expansion_report(baseline_report=_baseline(), ledger_rows=_rows(24))
    blockers = set(payload["blockers"])
    assert "SHADOW_SAMPLE_COUNT_BELOW_TARGET" in blockers
    assert "ACCEPTANCE_TRACKING_REQUIREMENTS_NOT_MET" in blockers
    assert "PAPER_LIVE_TRAINING_RELOAD_ORDER_ENABLEMENT_NOT_PRESENT" in blockers
    assert payload["approved_for_acceptance_review_candidate"] is False
    assert payload["paper_transition_candidate_found"] is False


def test_no_new_observation_is_tracked_but_not_hard_failed() -> None:
    payload = build_shadow_sample_expansion_report(baseline_report=_baseline(20), ledger_rows=_rows(20))
    assert payload["ok"] is True
    assert "NO_NEW_SHADOW_OBSERVATIONS_SINCE_28F_BASELINE" in payload["blockers"]
    assert payload["sample_expansion_delta"]["new_unique_observation_count"] == 0


def test_duplicate_observation_hard_blocks_report() -> None:
    rows = _rows(5)
    rows.append(dict(rows[0]))
    payload = build_shadow_sample_expansion_report(baseline_report=_baseline(5), ledger_rows=rows)
    assert payload["ok"] is False
    assert "DUPLICATE_OBSERVATION_IDS_PRESENT" in payload["blockers"]
    assert payload["operator_cockpit_continuity_delta"]["duplicate_observation_count"] == 1


def test_invalid_baseline_fail_closed() -> None:
    baseline = _baseline()
    baseline["approved_for_live_real"] = True
    payload = build_shadow_sample_expansion_report(baseline_report=baseline, ledger_rows=_rows(24))
    assert payload["ok"] is False
    assert "VALID_28F_OPERATOR_COCKPIT_BASELINE_NOT_FOUND" in payload["blockers"]
    assert payload["approved_for_live_real"] is False


def test_acceptance_review_candidate_only_not_paper_candidate() -> None:
    payload = build_shadow_sample_expansion_report(baseline_report=_baseline(20), ledger_rows=_rows(30, win_rate_high=True))
    assert payload["acceptance_tracking_metrics"]["acceptance_requirements_met"] is True
    assert payload["approved_for_acceptance_review_candidate"] is True
    assert payload["next_required_gate"] == "28H_HYP006_SHADOW_ACCEPTANCE_REVIEW_AND_NO_ORDER_MATURITY_DECISION"
    assert payload["approved_for_paper_candidate"] is False
    assert payload["approved_for_live_real"] is False


def test_json_loaders_support_bom(tmp_path: Path) -> None:
    json_path = tmp_path / "baseline.json"
    json_path.write_text("\ufeff" + json.dumps(_baseline()), encoding="utf-8")
    assert load_json(json_path)["contract_version"] == "4B.4.3.6.6.28F"

    jsonl_path = tmp_path / "ledger.jsonl"
    jsonl_path.write_text("\ufeff" + "\n".join(json.dumps(row) for row in _rows(2)) + "\n", encoding="utf-8")
    assert len(load_jsonl(jsonl_path)) == 2


def test_report_bundle_writes_artifacts(tmp_path: Path) -> None:
    payload = build_shadow_sample_expansion_report(baseline_report=_baseline(), ledger_rows=_rows(24))
    report_json, acceptance_json, continuity_json, dashboard_json, report_md = write_report_bundle(payload, tmp_path)
    assert report_json.exists()
    assert acceptance_json.exists()
    assert continuity_json.exists()
    assert dashboard_json.exists()
    assert report_md.exists()
    assert json.loads(report_json.read_text(encoding="utf-8"))["contract_version"] == "4B.4.3.6.6.28G"


def test_dashboard_delta_seed_schema_is_operator_safe() -> None:
    payload = build_shadow_sample_expansion_report(baseline_report=_baseline(), ledger_rows=_rows(24))
    seed = payload["dashboard_delta_seed"]
    assert seed["operator_cockpit_visibility"] is True
    assert seed["read_only"] is True
    assert seed["no_order_shadow_only"] is True
    assert seed["gate_status"]["approved_for_paper_candidate"] is False
    assert seed["gate_status"]["approved_for_live_real"] is False
    assert seed["gate_status"]["order_actions_allowed"] is False
