from __future__ import annotations

import json
from pathlib import Path

from tradebot.hyp006_shadow_registration_operator_approval import (
    CANDIDATE_SCAN_ARTIFACT_PREFIX,
    build_canonical_shadow_cycle_report,
    write_cycle_bundle,
)
from tradebot.hyp006_shadow_runner_dry_run import (
    BRANCH_ID,
    BRANCH_NAME,
    HYPOTHESIS_ID,
    STRATEGY_FAMILY,
    CANDIDATE_SCAN_HOOK_CONTRACT_VERSION,
    Candle,
    RuntimeSpec,
    scan_hyp006_short_probe_observations_with_diagnostics,
)


def _candles(symbol: str, *, trigger_idx: int | None = None, near_miss_idx: int | None = None) -> list[Candle]:
    rows: list[Candle] = []
    for idx in range(70):
        open_price = 101.0
        high = 102.0
        low = 100.0
        close = 101.0
        if trigger_idx is not None and idx == trigger_idx:
            open_price = 100.2
            high = 101.0
            low = 99.4
            close = 100.2
        if near_miss_idx is not None and idx == near_miss_idx:
            open_price = 99.9
            high = 101.0
            low = 99.7
            close = 100.8
        rows.append(
            Candle(
                timestamp_utc=f"2026-06-{(idx // 6) + 1:02d}T{(idx % 6) * 4:02d}:00:00+00:00",
                symbol=symbol,
                open=open_price,
                high=high,
                low=low,
                close=close,
                volume=1000.0,
            )
        )
    return rows


def _candidate_spec() -> dict[str, object]:
    return {
        "contract_version": "4B.4.3.6.6.28B",
        "hypothesis_id": HYPOTHESIS_ID,
        "branch_id": BRANCH_ID,
        "branch_name": BRANCH_NAME,
        "strategy_family": STRATEGY_FAMILY,
        "no_order_shadow_only": True,
        "entry_signal_definition": {
            "timeframe": "4h",
            "parameters": {
                "lookback_bars": 24,
                "hold_bars": 6,
                "min_sweep_bps": 18.0,
                "min_wick_pct_reference": 42.0,
                "compression_window": 12,
                "compression_baseline_bars": 48,
                "max_compression_ratio_reference": 1.05,
            },
        },
        "required_shadow_acceptance_metrics": [
            {"name": "max_slippage_proxy_bps", "threshold": 12.0},
        ],
        "registration_gate": {
            "registration_requires_28c_runner": True,
            "next_required_gate": "28C_NO_ORDER_SHADOW_RUNNER_DRY_RUN_AND_OPERATOR_REGISTRATION_APPROVAL",
        },
        "approvals": {
            "approved_for_shadow_collection": False,
            "approved_for_training_candidate": False,
            "approved_for_paper_candidate": False,
            "approved_for_live_real": False,
            "order_actions_allowed": False,
        },
    }


def _approval() -> dict[str, object]:
    return {
        "contract_version": "4B.4.3.6.6.28D",
        "decision": "HYP006_R1_CANONICAL_NO_ORDER_SHADOW_REGISTRATION_APPROVED",
        "approved_for_canonical_no_order_shadow_registration": True,
        "approved_for_shadow_collection": True,
        "approved_for_training_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "config_mutation_performed": False,
        "scheduler_mutation_performed": False,
        "scheduler_task_created": False,
        "scheduler_task_modified": False,
        "trading_action_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "order_actions_performed": False,
    }


def test_runtime_scan_hook_counts_trigger_and_near_miss() -> None:
    runtime = RuntimeSpec()
    observations, diagnostics = scan_hyp006_short_probe_observations_with_diagnostics(
        _candles("BTCUSDT", trigger_idx=62, near_miss_idx=55),
        runtime_spec=runtime,
    )

    assert diagnostics["contract_version"] == CANDIDATE_SCAN_HOOK_CONTRACT_VERSION
    assert diagnostics["read_only"] is True
    assert diagnostics["candidate_count"] >= 2
    assert diagnostics["trigger_count"] == len(observations) == 1
    assert diagnostics["near_miss_count"] >= 1
    assert diagnostics["approved_for_parameter_relaxation_candidate"] is False
    assert diagnostics["approved_for_paper_candidate"] is False
    assert "MIN_WICK_PCT_REFERENCE" in diagnostics["gate_block_counter"]


def test_canonical_cycle_report_contains_candidate_scan_diagnostics() -> None:
    candles = _candles("BTCUSDT", trigger_idx=62, near_miss_idx=55)
    payload = build_canonical_shadow_cycle_report(
        registration_approval_report=_approval(),
        candidate_spec_source=_candidate_spec(),
        candles=candles,
        existing_ledger_rows=[],
        rows_by_symbol={"BTCUSDT": len(candles)},
        network_request_performed=False,
    )

    diagnostics = payload["candidate_scan_diagnostics"]
    assert payload["runtime_candidate_scan_hook_contract_version"] == CANDIDATE_SCAN_HOOK_CONTRACT_VERSION
    assert diagnostics["raw_candidate_scan_artifact_found"] is True
    assert diagnostics["trigger_count"] == 1
    assert diagnostics["near_miss_count"] >= 1
    assert payload["approved_for_paper_candidate"] is False
    assert payload["approved_for_live_real"] is False
    assert payload["training_performed"] is False
    assert payload["trading_action_performed"] is False


def test_write_cycle_bundle_emits_h3_candidate_scan_artifact(tmp_path: Path) -> None:
    candles = _candles("BTCUSDT", trigger_idx=62, near_miss_idx=55)
    payload = build_canonical_shadow_cycle_report(
        registration_approval_report=_approval(),
        candidate_spec_source=_candidate_spec(),
        candles=candles,
        existing_ledger_rows=[],
        rows_by_symbol={"BTCUSDT": len(candles)},
        network_request_performed=False,
    )

    report_json, ledger_jsonl, report_md = write_cycle_bundle(payload, tmp_path)
    assert report_json.exists()
    assert ledger_jsonl.exists()
    assert report_md.exists()
    h3_files = sorted(tmp_path.glob(f"{CANDIDATE_SCAN_ARTIFACT_PREFIX}_*.json"))
    assert h3_files
    h3_payload = json.loads(h3_files[0].read_text(encoding="utf-8"))
    assert h3_payload["contract_version"] == CANDIDATE_SCAN_HOOK_CONTRACT_VERSION
    assert h3_payload["candidate_count"] >= 2
    assert h3_payload["approved_for_live_real"] is False
