from __future__ import annotations

import csv
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from tradebot.hyp006_shadow_runner_dry_run import (
    BRANCH_ID,
    BRANCH_NAME,
    CONTRACT_VERSION,
    STRATEGY_FAMILY,
    Candle,
    build_hyp006_shadow_runner_dry_run_report,
    scan_hyp006_short_probe_observations,
    runtime_spec_from_candidate_spec,
    stable_observation_id,
    validate_candidate_spec_source,
    write_report_bundle,
)


def registration_report() -> dict:
    return {
        "contract_version": "4B.4.3.6.6.28B",
        "candidate_spec_draft": {
            "contract_version": "4B.4.3.6.6.28B",
            "hypothesis_id": "HYP-006",
            "branch_id": BRANCH_ID,
            "branch_name": BRANCH_NAME,
            "strategy_family": STRATEGY_FAMILY,
            "no_order_shadow_only": True,
            "approvals": {
                "approved_for_shadow_collection": False,
                "approved_for_training_candidate": False,
                "approved_for_paper_candidate": False,
                "approved_for_live_real": False,
                "order_actions_allowed": False,
            },
            "registration_gate": {
                "registration_requires_28c_runner": True,
                "next_required_gate": "28C_NO_ORDER_SHADOW_RUNNER_DRY_RUN_AND_OPERATOR_REGISTRATION_APPROVAL",
            },
            "entry_signal_definition": {
                "timeframe": "4h",
                "parameters": {
                    "lookback_bars": 3,
                    "hold_bars": 3,
                    "min_sweep_bps": 10.0,
                    "min_wick_pct_reference": 40.0,
                    "compression_window": 2,
                    "compression_baseline_bars": 4,
                    "max_compression_ratio_reference": 2.0,
                },
            },
            "required_shadow_acceptance_metrics": [
                {"name": "max_slippage_proxy_bps", "operator": "<=", "threshold": 12.0}
            ],
        },
    }


def candles() -> list[Candle]:
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    rows = [
        Candle((base + timedelta(hours=4 * idx)).isoformat(), "BTCUSDT", 101.0, 102.0, 100.0, 101.0, 1000.0)
        for idx in range(8)
    ]
    rows.append(Candle((base + timedelta(hours=32)).isoformat(), "BTCUSDT", 101.0, 103.0, 99.5, 101.5, 2000.0))
    for step, close in enumerate((100.0, 99.0, 98.0), start=9):
        rows.append(Candle((base + timedelta(hours=4 * step)).isoformat(), "BTCUSDT", 101.0, 102.0, close - 0.5, close, 900.0))
    return rows


def test_validates_28b_registration_and_blocks_unsafe_approvals() -> None:
    ok, reasons, _ = validate_candidate_spec_source(registration_report())
    assert ok is True
    assert reasons == []
    bad = registration_report()
    bad["candidate_spec_draft"]["approvals"]["approved_for_live_real"] = True
    ok, reasons, _ = validate_candidate_spec_source(bad)
    assert ok is False
    assert "UNSAFE_APPROVAL_APPROVED_FOR_LIVE_REAL" in reasons


def test_scan_detects_short_probe_and_positive_short_return() -> None:
    spec = runtime_spec_from_candidate_spec(registration_report())
    observations = scan_hyp006_short_probe_observations(candles(), runtime_spec=spec)
    assert len(observations) == 1
    obs = observations[0]
    assert obs.observation_id.startswith("HYP-006-BTCUSDT-4h-")
    assert obs.forward_return_bps_final_short_probe is not None
    assert obs.forward_return_bps_final_short_probe > 0
    assert obs.no_order_measurement_only is True


def test_report_is_fail_closed_for_paper_live_and_scheduler_mutation() -> None:
    report = build_hyp006_shadow_runner_dry_run_report(
        candidate_spec_source=registration_report(),
        candles=candles(),
        symbols=["BTCUSDT"],
        existing_ledger_rows=[],
        network_request_performed=False,
        out_dir="reports/hyp006_r1_canonical",
    )
    assert report["ok"] is True
    assert report["contract_version"] == CONTRACT_VERSION
    assert report["operator_registration_approval_gate_ready"] is True
    assert report["canonical_scheduler_registration_preflight_ready"] is True
    assert report["approved_for_shadow_collection"] is False
    assert report["approved_for_paper_candidate"] is False
    assert report["approved_for_live_real"] is False
    assert report["scheduler_registration_preflight"]["scheduler_task_created"] is False
    assert report["scheduler_mutation_performed"] is False


def test_duplicate_guard_marks_existing_observation() -> None:
    signal_ts = candles()[8].timestamp_utc
    existing_id = stable_observation_id("BTCUSDT", "4h", signal_ts)
    report = build_hyp006_shadow_runner_dry_run_report(
        candidate_spec_source=registration_report(),
        candles=candles(),
        symbols=["BTCUSDT"],
        existing_ledger_rows=[{"observation_id": existing_id}],
        network_request_performed=False,
        out_dir="reports/hyp006_r1_canonical",
    )
    assert report["dry_run_summary"]["duplicate_existing_observation_count"] == 1
    assert report["dry_run_summary"]["new_unique_dry_run_observation_count"] == 0


def test_invalid_spec_fails_closed() -> None:
    report = build_hyp006_shadow_runner_dry_run_report(
        candidate_spec_source={"contract_version": "BAD"},
        candles=candles(),
        symbols=["BTCUSDT"],
        existing_ledger_rows=[],
        network_request_performed=False,
        out_dir="reports/hyp006_r1_canonical",
    )
    assert report["ok"] is False
    assert report["approved_for_shadow_collection"] is False
    assert report["approved_for_paper_candidate"] is False
    assert "SOURCE_CONTRACT_VERSION_MISMATCH" in report["candidate_spec_validation"]["reasons"]


def test_write_report_bundle_outputs_json_jsonl_and_markdown(tmp_path: Path) -> None:
    report = build_hyp006_shadow_runner_dry_run_report(
        candidate_spec_source=registration_report(),
        candles=candles(),
        symbols=["BTCUSDT"],
        existing_ledger_rows=[],
        network_request_performed=False,
        out_dir=tmp_path,
    )
    report_json, ledger_jsonl, report_md = write_report_bundle(report, tmp_path)
    assert report_json.exists()
    assert ledger_jsonl.exists()
    assert report_md.exists()
    assert json.loads(report_json.read_text(encoding="utf-8"))["contract_version"] == CONTRACT_VERSION
    assert ledger_jsonl.read_text(encoding="utf-8").count("\n") == 1


def test_runner_requires_review_ok(tmp_path: Path) -> None:
    registration_path = tmp_path / "registration.json"
    registration_path.write_text(json.dumps(registration_report()), encoding="utf-8")
    cmd = [
        sys.executable,
        "tools/run_4B436628C_hyp006_shadow_runner_dry_run.py",
        "--registration-json",
        str(registration_path),
        "--input-csv",
        str(tmp_path / "missing.csv"),
        "--out-dir",
        str(tmp_path),
    ]
    completed = subprocess.run(cmd, cwd=Path(__file__).resolve().parents[1], text=True, capture_output=True)
    assert completed.returncode != 0
    assert "REVIEW_OK_REQUIRED_FOR_28C_NO_ORDER_DRY_RUN" in (completed.stderr + completed.stdout)
