from __future__ import annotations

import json
from pathlib import Path

from tradebot.hyp006_candidate_near_miss_instrumentation import (
    CONTRACT_VERSION,
    build_instrumentation_report,
    run_report,
)


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def rows(count: int = 20) -> list[dict[str, object]]:
    symbols = ["ADAUSDT", "BNBUSDT", "BTCUSDT", "ETHUSDT", "LINKUSDT", "LTCUSDT", "SOLUSDT", "XRPUSDT"]
    return [
        {
            "observation_id": f"HYP-006-{symbols[idx % len(symbols)]}-4h-2026-06-{idx + 1:02d}T000000Z",
            "symbol": symbols[idx % len(symbols)],
            "timestamp_utc": f"2026-06-{idx + 1:02d}T00:00:00+00:00",
            "forward_return_bps_final": 10.0 - idx,
        }
        for idx in range(count)
    ]


def test_report_is_read_only_when_no_candidate_artifacts(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "hyp006_r1_canonical"
    write_jsonl(reports / "4B436628D_hyp006_r1_shadow_ledger_20260616T210506Z.jsonl", rows())
    write_jsonl(reports / "4B436628D_hyp006_r1_shadow_ledger_20260617T210506Z.jsonl", rows())
    write_json(
        reports / "4B436628G_H1_hyp006_r1_signal_frequency_stagnation_diagnostics_20260618T071133Z.json",
        {
            "blockers": ["CANDIDATE_SCAN_ARTIFACT_NOT_FOUND", "SHADOW_SAMPLE_COUNT_BELOW_TARGET"],
            "gate_diagnostics": [
                {"name": "min_shadow_sample_target", "passed": False},
                {"name": "shadow_profit_factor", "passed": True},
            ],
        },
    )

    report = build_instrumentation_report(reports)

    assert report["contract_version"] == CONTRACT_VERSION
    assert report["read_only"] is True
    assert report["trading_action_performed"] is False
    assert report["approved_for_parameter_relaxation_candidate"] is False
    assert report["current_unique_observation_ids"] == 20
    assert report["new_unique_observation_count_latest_delta"] == 0
    assert report["candidate_trigger_instrumentation"]["raw_candidate_scan_artifact_found"] is False
    assert report["candidate_trigger_instrumentation"]["fallback_acceptance_block_counter_used"] is True
    assert "RAW_CANDIDATE_NEAR_MISS_SCAN_ARTIFACT_NOT_FOUND" in report["blockers"]


def test_report_counts_candidate_near_miss_records(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "hyp006_r1_canonical"
    write_jsonl(reports / "4B436628D_hyp006_r1_shadow_ledger_20260617T210506Z.jsonl", rows())
    write_json(
        reports / "hyp006_candidate_near_miss_scan_20260618.json",
        {
            "candidate_events": [
                {
                    "symbol": "BTCUSDT",
                    "near_miss": True,
                    "blocked_gate": "spread_slippage",
                    "status": "near_miss",
                },
                {
                    "symbol": "ETHUSDT",
                    "triggered": True,
                    "gate": "continuation",
                    "status": "triggered",
                },
            ],
            "rejection_events": [
                {"symbol": "XRPUSDT", "reject_reason": "sweep"},
            ],
        },
    )

    report = build_instrumentation_report(reports)
    summary = report["candidate_trigger_instrumentation"]

    assert summary["raw_candidate_scan_artifact_found"] is True
    assert summary["candidate_count"] >= 3
    assert summary["near_miss_count"] >= 1
    assert summary["trigger_count"] >= 1
    assert summary["symbol_candidate_counter"]["BTCUSDT"] >= 1
    assert summary["gate_block_counter"]["SPREAD_SLIPPAGE_FILTER"] >= 1
    assert summary["gate_block_counter"]["CONTINUATION_CONFIRMATION"] >= 1
    assert summary["gate_block_counter"]["SWEEP_CONDITION"] >= 1


def test_run_report_writes_json_and_markdown(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "hyp006_r1_canonical"
    out = tmp_path / "out"
    write_jsonl(reports / "4B436628D_hyp006_r1_shadow_ledger_20260617T210506Z.jsonl", rows())

    payload = run_report(reports, out)

    assert Path(str(payload["report_json"])).exists()
    assert Path(str(payload["report_md"])).exists()
    saved = json.loads(Path(str(payload["report_json"])).read_text(encoding="utf-8"))
    assert saved["contract_version"] == CONTRACT_VERSION
    assert saved["training_performed"] is False
    assert saved["paper_live_order_enablement_present"] is False
