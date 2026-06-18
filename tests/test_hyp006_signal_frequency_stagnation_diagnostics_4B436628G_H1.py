from __future__ import annotations

import json
from pathlib import Path

from tradebot.hyp006_signal_frequency_stagnation_diagnostics import (
    CONTRACT_VERSION,
    build_diagnostics_report,
)


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def sample_rows(count: int = 20) -> list[dict[str, object]]:
    symbols = ["ADAUSDT", "BNBUSDT", "BTCUSDT", "ETHUSDT", "LINKUSDT", "LTCUSDT", "SOLUSDT", "XRPUSDT"]
    rows: list[dict[str, object]] = []
    for idx in range(count):
        symbol = symbols[idx % len(symbols)]
        rows.append(
            {
                "observation_id": f"HYP-006-{symbol}-4h-2026-06-{idx + 1:02d}T000000Z",
                "symbol": symbol,
                "timestamp_utc": f"2026-06-{idx + 1:02d}T00:00:00+00:00",
                "forward_return_bps_final": float(idx - 10),
            }
        )
    return rows


def write_tracking(path: Path) -> None:
    write_json(
        path,
        {
            "blockers": [
                "ACCEPTANCE_METRIC_FAILED_MIN_SHADOW_SAMPLE_TARGET",
                "NO_NEW_SHADOW_OBSERVATIONS_SINCE_28F_BASELINE",
            ],
            "acceptance_tracking_metrics": {
                "metric_results": [
                    {"name": "min_shadow_sample_target", "value": 20, "threshold": 30, "operator": ">=", "passed": False, "delta": 0},
                    {"name": "shadow_profit_factor", "value": 2.7, "threshold": 1.15, "operator": ">=", "passed": True, "delta": 0.0},
                ]
            },
        },
    )


def test_detects_repeated_ledger_stagnation(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "hyp006_r1_canonical"
    rows = sample_rows(20)
    write_jsonl(reports / "4B436628D_hyp006_r1_shadow_ledger_20260615T210506Z.jsonl", rows)
    write_jsonl(reports / "4B436628D_hyp006_r1_shadow_ledger_20260616T210506Z.jsonl", rows)
    write_jsonl(reports / "4B436628D_hyp006_r1_shadow_ledger_20260617T210506Z.jsonl", rows)
    write_tracking(reports / "4B436628G_hyp006_r1_shadow_sample_expansion_acceptance_tracking_20260617T210626Z.json")

    payload = build_diagnostics_report(reports, reports, write_outputs=True)

    assert payload["ok"] is True
    assert payload["contract_version"] == CONTRACT_VERSION
    assert payload["current_unique_observation_ids"] == 20
    assert payload["new_unique_observation_count_latest_delta"] == 0
    assert payload["stagnation_detected"] is True
    assert payload["target_remaining_count"] == 10
    assert "HYP006_SIGNAL_FREQUENCY_STAGNATION_DETECTED" in payload["blockers"]
    assert payload["approved_for_paper_candidate"] is False
    assert payload["trading_action_performed"] is False
    assert Path(str(payload["report_json"])).exists()
    assert Path(str(payload["report_md"])).exists()


def test_detects_candidate_scan_artifacts_when_present(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "hyp006_r1_canonical"
    rows = sample_rows(20)
    write_jsonl(reports / "4B436628D_hyp006_r1_shadow_ledger_20260615T210506Z.jsonl", rows)
    write_tracking(reports / "4B436628G_hyp006_r1_shadow_sample_expansion_acceptance_tracking_20260617T210626Z.json")
    write_json(
        reports / "hyp006_candidate_near_miss_scan_20260617.json",
        {
            "gate_counts": {"failed_sweep_condition": 12, "failed_continuation_confirmation": 7},
            "symbol_counts": {"BTCUSDT": 4, "ETHUSDT": 3},
            "near_miss_count": 6,
            "trigger_count": 1,
        },
    )

    payload = build_diagnostics_report(reports, reports, write_outputs=False)
    candidate = payload["candidate_trigger_diagnostics"]

    assert candidate["candidate_scan_data_available"] is True
    assert candidate["candidate_scan_files_found"] == 1
    assert candidate["gate_block_counter"]["failed_sweep_condition"] == 12
    assert candidate["near_miss_count"] == 6
    assert candidate["trigger_count"] == 1


def test_no_ledger_fails_closed_without_mutations(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "hyp006_r1_canonical"
    reports.mkdir(parents=True)

    payload = build_diagnostics_report(reports, reports, write_outputs=False)

    assert payload["ok"] is False
    assert payload["decision"] == "HYP006_R1_SIGNAL_FREQUENCY_DIAGNOSTICS_BLOCKED_NO_LEDGER"
    assert payload["read_only"] is True
    assert payload["config_mutation_performed"] is False
    assert payload["scheduler_mutation_performed"] is False
    assert payload["training_performed"] is False
    assert payload["reload_performed"] is False
    assert payload["trading_action_performed"] is False
    assert payload["approved_for_live_real"] is False
