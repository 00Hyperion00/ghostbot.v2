from __future__ import annotations

import json
from pathlib import Path

from tradebot.hyp006_operator_cockpit_baseline import (
    CONTRACT_VERSION,
    build_acceptance_baseline_report,
    compute_acceptance_baseline,
    health_report_is_ready,
    load_json,
    load_jsonl,
    write_report_bundle,
)


def _health() -> dict[str, object]:
    return {
        "contract_version": "4B.4.3.6.6.28E",
        "decision": "HYP006_R1_CANONICAL_SHADOW_SCHEDULER_EXECUTION_HEALTH_READY",
        "ok": True,
        "branch_id": "HYP-006-R1",
        "approved_for_shadow_collection_continuity": True,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "order_actions_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "scheduler_task_health": {
            "task_name": "TradeBot_HYP006_R1_Canonical_NoOrderShadowCollection",
            "last_task_result": 0,
            "number_of_missed_runs": 0,
            "state": "Ready",
        },
        "scheduler_task_health_validation": {"ok": True, "reasons": []},
    }


def _rows(count: int = 20) -> list[dict[str, object]]:
    values = [842.105263, -98.386462, -63.566254, -77.978544, -147.389007, 719.312836, 56.09227, -233.05228, 208.605715, 42.060988,
              352.928556, -110.062893, -22.292402, -120.600541, 82.762557, 221.181556, -206.459224, -146.148684, 178.852054, 700.256191]
    symbols = ["ADAUSDT", "ADAUSDT", "BNBUSDT", "BNBUSDT", "BTCUSDT", "BTCUSDT", "ETHUSDT", "ETHUSDT", "ETHUSDT", "LINKUSDT",
               "LINKUSDT", "LINKUSDT", "LTCUSDT", "SOLUSDT", "XRPUSDT", "XRPUSDT", "XRPUSDT", "XRPUSDT", "XRPUSDT", "XRPUSDT"]
    rows: list[dict[str, object]] = []
    for idx, value in enumerate(values[:count]):
        rows.append(
            {
                "contract_version": "4B.4.3.6.6.28D",
                "hypothesis_id": "HYP-006",
                "branch_id": "HYP-006-R1",
                "branch_name": "failed_downside_sweep_reversal_continuation_short",
                "strategy_family": "short_failed_liquidity_sweep_continuation",
                "no_order_measurement_only": True,
                "observation_id": f"HYP-006-{symbols[idx]}-4h-2026-06-{idx + 1:02d}T000000Z",
                "symbol": symbols[idx],
                "timestamp_utc": f"2026-06-{idx + 1:02d}T00:00:00+00:00",
                "forward_return_bps_final_short_probe": value,
                "spread_slippage_proxy_bps": 5.0,
            }
        )
    return rows


def test_health_report_contract_is_valid() -> None:
    assert CONTRACT_VERSION == "4B.4.3.6.6.28F"
    assert health_report_is_ready(_health()) is True


def test_baseline_computation_detects_incomplete_sample() -> None:
    comp = compute_acceptance_baseline(_rows())
    assert comp.ledger_row_count == 20
    assert comp.unique_observation_ids == 20
    assert comp.duplicate_observation_count == 0
    assert comp.sample_target == 30
    assert comp.sample_target_reached is False
    assert comp.acceptance_requirements_met is False
    assert comp.mean_return_bps is not None and comp.mean_return_bps > 0
    assert comp.profit_factor is not None and comp.profit_factor > 1.15


def test_report_keeps_paper_live_order_blocked() -> None:
    payload = build_acceptance_baseline_report(health_report=_health(), ledger_rows=_rows())
    assert payload["ok"] is True
    assert payload["dashboard_seed_ready"] is True
    assert payload["approved_for_shadow_collection_continuity"] is True
    assert payload["approved_for_paper_candidate"] is False
    assert payload["approved_for_live_real"] is False
    assert payload["order_actions_performed"] is False
    assert payload["training_performed"] is False
    assert payload["reload_performed"] is False


def test_report_contains_expected_blockers_until_acceptance_matures() -> None:
    payload = build_acceptance_baseline_report(health_report=_health(), ledger_rows=_rows())
    blockers = set(payload["blockers"])
    assert "SHADOW_SAMPLE_COUNT_BELOW_TARGET" in blockers
    assert "ACCEPTANCE_BASELINE_REQUIREMENTS_NOT_MET" in blockers
    assert "PAPER_LIVE_TRAINING_RELOAD_ORDER_ENABLEMENT_NOT_PRESENT" in blockers
    assert payload["acceptance_baseline_metrics"]["acceptance_requirements_met"] is False
    assert payload["paper_transition_candidate_found"] is False


def test_duplicate_observation_blocks_continuity_ok() -> None:
    rows = _rows(3)
    rows.append(dict(rows[0]))
    payload = build_acceptance_baseline_report(health_report=_health(), ledger_rows=rows)
    assert payload["ok"] is False
    assert "DUPLICATE_OBSERVATION_IDS_PRESENT" in payload["blockers"]
    assert payload["no_order_continuity_monitor"]["duplicate_observation_count"] == 1


def test_invalid_health_report_fail_closed() -> None:
    health = _health()
    health["approved_for_live_real"] = True
    payload = build_acceptance_baseline_report(health_report=health, ledger_rows=_rows())
    assert payload["ok"] is False
    assert "VALID_28E_SCHEDULER_HEALTH_EVIDENCE_NOT_FOUND" in payload["blockers"]
    assert payload["approved_for_live_real"] is False


def test_json_loaders_support_bom(tmp_path: Path) -> None:
    json_path = tmp_path / "health.json"
    json_path.write_text("\ufeff" + json.dumps(_health()), encoding="utf-8")
    assert load_json(json_path)["contract_version"] == "4B.4.3.6.6.28E"

    jsonl_path = tmp_path / "ledger.jsonl"
    jsonl_path.write_text("\ufeff" + "\n".join(json.dumps(row) for row in _rows(2)) + "\n", encoding="utf-8")
    assert len(load_jsonl(jsonl_path)) == 2


def test_report_bundle_writes_artifacts(tmp_path: Path) -> None:
    payload = build_acceptance_baseline_report(health_report=_health(), ledger_rows=_rows())
    report_json, dashboard_json, acceptance_json, continuity_json, report_md = write_report_bundle(payload, tmp_path)
    assert report_json.exists()
    assert dashboard_json.exists()
    assert acceptance_json.exists()
    assert continuity_json.exists()
    assert report_md.exists()
    assert json.loads(report_json.read_text(encoding="utf-8"))["contract_version"] == "4B.4.3.6.6.28F"


def test_dashboard_seed_schema_is_operator_safe() -> None:
    payload = build_acceptance_baseline_report(health_report=_health(), ledger_rows=_rows())
    seed = payload["dashboard_seed"]
    assert seed["operator_cockpit_visibility"] is True
    assert seed["read_only"] is True
    assert seed["no_order_shadow_only"] is True
    assert seed["gate_status"]["approved_for_paper_candidate"] is False
    assert seed["gate_status"]["approved_for_live_real"] is False
    assert seed["gate_status"]["order_actions_allowed"] is False
