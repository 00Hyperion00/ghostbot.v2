from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tradebot.research_hyp005_r1_shadow_scheduler_regeneration_pack import (
    HYP005_R1_RUNTIME_CHAIN_HOTFIX_VERSION,
    HYP005_R1_SHADOW_SCHEDULER_PACK_READY,
    build_hyp005_r1_shadow_scheduler_regeneration_pack_report,
)
from tradebot.research_hyp005_shadow_observation_logger import validate_candidate_spec

REFINED = ["ADAUSDT", "BNBUSDT", "BTCUSDT", "ETHUSDT", "LINKUSDT", "LTCUSDT", "SOLUSDT", "XRPUSDT"]
PRUNED = ["AVAXUSDT", "DOGEUSDT"]


def _plan() -> dict[str, object]:
    return {
        "contract_version": "4B.4.3.6.6.25AD",
        "decision": "HYP005_R1_REVALIDATION_PLANNING_READY",
        "refined_branch_id": "HYP-005-R1",
        "fresh_ledger_namespace": "HYP005_R1",
        "starting_unique_shadow_observation_count": 0,
        "recommended_pruned_symbols": PRUNED,
        "recommended_refined_symbols": REFINED,
        "approved_for_next_scheduler_pack_patch": True,
        "approved_for_scheduler_regeneration": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "post_requests_allowed": False,
        "baseline_observations_reused_in_refined_branch": False,
        "refined_candidate_spec": {
            "symbols": REFINED,
            "symbols_arg": ",".join(REFINED),
            "excluded_symbols": PRUNED,
            "shadow_sample_target": 30,
            "starting_unique_shadow_observation_count": 0,
            "legacy_baseline_observation_reuse_allowed": False,
            "legacy_baseline_observations_reused": False,
        },
    }


def _candidate_spec() -> dict[str, object]:
    return {
        "status": "NO_ORDER_SHADOW_PLAN_READY",
        "hypothesis_id": "HYP-005",
        "branch_name": "liquidity_sweep_reversal_vol_compression",
        "strategy_family": "long_liquidity_sweep_reversal",
        "no_order_shadow_only": True,
        "entry_signal_definition": {
            "strategy_family": "long_liquidity_sweep_reversal",
            "timeframe": "4h",
            "parameters": {
                "lookback_bars": 24,
                "hold_bars": 6,
                "min_sweep_bps": 18.0,
                "min_wick_pct": 42.0,
                "compression_window": 12,
                "compression_baseline_bars": 48,
                "max_compression_ratio": 1.05,
            },
        },
        "risk_observation_fields": [
            "timestamp_utc",
            "symbol",
            "timeframe",
            "strategy_family",
            "sweep_direction",
            "lookback_low",
            "swept_low",
            "sweep_depth_bps",
            "wick_pct",
            "compression_ratio",
            "entry_reference_price",
            "invalidation_level",
            "forward_return_bps_final",
            "mae_bps",
            "mfe_bps",
            "spread_slippage_proxy_bps",
            "data_quality_ok",
            "operator_review_status",
        ],
        "guardrails": {
            "no_order_shadow_only": True,
            "orders_allowed": False,
            "paper_trading_allowed": False,
            "live_trading_allowed": False,
            "training_allowed": False,
            "model_reload_allowed": False,
            "post_requests_allowed": False,
            "paper_transition_requires_new_gate": True,
            "live_transition_requires_separate_gate": True,
        },
    }


def _write_inputs(reports: Path) -> None:
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "4B436625AD_hyp005_baseline_freeze_refined_revalidation_planning_20260602_072834.json").write_text(
        json.dumps(_plan()), encoding="utf-8"
    )
    (reports / "4B436625U_hyp005_no_order_shadow_candidate_spec_20260509_175722.json").write_text(
        json.dumps(_candidate_spec()), encoding="utf-8"
    )


def _build(tmp_path: Path) -> dict[str, object]:
    reports = tmp_path / "reports"
    _write_inputs(reports)
    return build_hyp005_r1_shadow_scheduler_regeneration_pack_report(
        reports,
        out_dir=reports,
        baseline_task_disabled_confirmed=True,
        review_ok=True,
        timestamp="20260602_130000",
    )


def _latest(directory: Path, pattern: str) -> Path:
    matches = sorted(directory.glob(pattern))
    assert matches, f"missing {pattern} in {directory}"
    return matches[-1]


def _run(project_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args],
        cwd=project_root,
        text=True,
        capture_output=True,
        check=False,
    )


def test_25aeh3_declares_runtime_chain_hotfix_version() -> None:
    assert HYP005_R1_RUNTIME_CHAIN_HOTFIX_VERSION == "4B.4.3.6.6.25AE-H3"


def test_25aeh3_generated_cycle_uses_join_path_and_has_no_control_character_risk(tmp_path: Path) -> None:
    report = _build(tmp_path)
    assert report["decision"] == HYP005_R1_SHADOW_SCHEDULER_PACK_READY
    assert report["runtime_path_join_safety_enforced"] is True
    cycle = Path(report["artifacts"]["shadow_cycle_ps1"]).read_text(encoding="utf-8")  # type: ignore[index]
    assert 'Join-Path $R1ReportsDir "4B436625V_hyp005_shadow_observation_logger_*.json"' in cycle
    assert 'Join-Path $R1ReportsDir "4B436625X_hyp005_shadow_merged_ledger_*.json"' in cycle
    assert '$R1ReportsDir\\4B436625' not in cycle
    assert "--strict-explicit-chain" in cycle
    assert '--collection-report-json "$($LatestCollectionReport.FullName)"' in cycle
    assert '--ledger-json "$($LatestMergedLedger.FullName)"' in cycle
    disallowed = [ord(char) for char in cycle if ord(char) < 32 and char not in {"\n", "\r", "\t"}]
    assert disallowed == []


def test_25aeh3_runtime_candidate_spec_preserves_canonical_branch_and_r1_metadata(tmp_path: Path) -> None:
    report = _build(tmp_path)
    candidate_path = Path(report["artifacts"]["r1_runtime_candidate_spec_json"])  # type: ignore[index]
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    assert candidate["branch_name"] == "liquidity_sweep_reversal_vol_compression"
    assert candidate["refined_branch_name"] == "liquidity_sweep_reversal_vol_compression_r1_pruned_symbol_revalidation"
    assert candidate["candidate_variant"] == "r1_pruned_symbol_revalidation"
    assert candidate["refined_branch_id"] == "HYP-005-R1"
    assert candidate["fresh_ledger_namespace"] == "HYP005_R1"
    _runtime, reasons, _warnings = validate_candidate_spec(candidate)
    assert "HYP005_SPEC_BRANCH_MISMATCH" not in reasons
    assert reasons == []


def test_25aeh3_25w_cli_supports_collection_report_and_strict_chain() -> None:
    project_root = Path(__file__).resolve().parents[1]
    result = _run(project_root, "tools/run_hyp005_shadow_acceptance_readiness_4B436625W.py", "--help")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "--collection-report-json" in result.stdout
    assert "--strict-explicit-chain" in result.stdout


def test_25aeh3_empty_ledger_pipeline_is_scoped_unicode_safe_and_emits_all_block_reports(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[1]
    unicode_root = tmp_path / "Masaüstü"
    reports = unicode_root / "reports"
    r1 = reports / "hyp005_r1_isolated"
    r1.mkdir(parents=True)
    _write_inputs(reports)

    pack_report = build_hyp005_r1_shadow_scheduler_regeneration_pack_report(
        reports,
        out_dir=reports,
        baseline_task_disabled_confirmed=True,
        review_ok=True,
        timestamp="20260602_131000",
    )
    candidate = Path(pack_report["artifacts"]["r1_runtime_candidate_spec_json"])  # type: ignore[index]

    # Baseline contamination sentinel must never be imported by the R1 strict chain.
    baseline_observation = {
        "timestamp_utc": "2026-06-01T00:00:00Z",
        "symbol": "DOGEUSDT",
        "timeframe": "4h",
        "strategy_family": "long_liquidity_sweep_reversal",
        "sweep_direction": "LONG",
        "entry_reference_price": 0.1,
    }
    (reports / "4B436625V_hyp005_shadow_observation_ledger_baseline.json").write_text(
        json.dumps([baseline_observation]), encoding="utf-8"
    )

    # Deterministic no-signal CSV: the first cycle must remain a safe BLOCK but complete end-to-end.
    csv_path = unicode_root / "flat.csv"
    csv_path.write_text(
        "timestamp_utc,symbol,open,high,low,close,volume\n"
        "2026-06-01T00:00:00Z,ADAUSDT,1,1,1,1,100\n"
        "2026-06-01T04:00:00Z,ADAUSDT,1,1,1,1,100\n",
        encoding="utf-8",
    )
    logger_result = _run(
        project_root,
        "tools/run_hyp005_shadow_observation_logger_4B436625V.py",
        "--candidate-spec-json", str(candidate),
        "--input-csv", str(csv_path),
        "--symbols", ",".join(REFINED),
        "--out-dir", str(r1),
        "--review-ok",
    )
    assert logger_result.returncode == 0, logger_result.stdout + logger_result.stderr
    logger_report = _latest(r1, "4B436625V_hyp005_shadow_observation_logger_*.json")
    logger_ledger = _latest(r1, "4B436625V_hyp005_shadow_observation_ledger_*.json")
    logger_payload = json.loads(logger_report.read_text(encoding="utf-8"))
    assert "HYP005_SPEC_BRANCH_MISMATCH" not in logger_payload["reason_codes"]

    x_result = _run(
        project_root,
        "tools/run_hyp005_shadow_collection_orchestrator_4B436625X.py",
        "--candidate-spec-json", str(candidate),
        "--logger-report-json", str(logger_report),
        "--ledger-json", str(logger_ledger),
        "--reports-dir", str(r1),
        "--strict-explicit-chain",
        "--symbols", ",".join(REFINED),
        "--out-dir", str(r1),
        "--review-ok",
    )
    assert x_result.returncode == 0, x_result.stdout + x_result.stderr
    collection_report = _latest(r1, "4B436625X_hyp005_shadow_collection_orchestrator_*.json")
    merged_ledger = _latest(r1, "4B436625X_hyp005_shadow_merged_ledger_*.json")
    merged_payload = json.loads(merged_ledger.read_text(encoding="utf-8"))
    assert merged_payload["observations"] == []
    assert "DOGEUSDT" not in merged_ledger.read_text(encoding="utf-8")

    w_result = _run(
        project_root,
        "tools/run_hyp005_shadow_acceptance_readiness_4B436625W.py",
        "--collection-report-json", str(collection_report),
        "--ledger-json", str(merged_ledger),
        "--reports-dir", str(r1),
        "--strict-explicit-chain",
        "--out-dir", str(r1),
        "--review-ok",
    )
    assert w_result.returncode == 0, w_result.stdout + w_result.stderr
    acceptance_report = _latest(r1, "4B436625W_hyp005_shadow_observation_acceptance_*.json")
    acceptance_payload = json.loads(acceptance_report.read_text(encoding="utf-8"))
    assert acceptance_payload["strict_explicit_chain"] is True
    assert acceptance_payload["collection_report_paths"] == [str(collection_report)]

    y_result = _run(
        project_root,
        "tools/run_hyp005_shadow_operator_runbook_4B436625Y.py",
        "--candidate-spec-json", str(candidate),
        "--logger-report-json", str(logger_report),
        "--collection-report-json", str(collection_report),
        "--acceptance-report-json", str(acceptance_report),
        "--ledger-json", str(merged_ledger),
        "--reports-dir", str(r1),
        "--strict-explicit-chain",
        "--symbols", ",".join(REFINED),
        "--out-dir", str(r1),
        "--review-ok",
    )
    assert y_result.returncode == 0, y_result.stdout + y_result.stderr
    daily_audit = _latest(r1, "4B436625Y_hyp005_shadow_operator_daily_audit_*.json")
    daily_payload = json.loads(daily_audit.read_text(encoding="utf-8"))
    assert daily_payload["shadow_observation_count"] == 0
    assert daily_payload["approved_for_paper_candidate"] is False
    assert daily_payload["approved_for_live_real"] is False
    assert daily_payload["post_requests_allowed"] is False


def test_25aeh3_strict_chain_rejects_out_of_scope_ledger(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[1]
    r1 = tmp_path / "reports" / "hyp005_r1_isolated"
    r1.mkdir(parents=True)
    candidate = tmp_path / "candidate.json"
    candidate.write_text(json.dumps(_candidate_spec()), encoding="utf-8")
    logger = r1 / "4B436625V_hyp005_shadow_observation_logger_test.json"
    logger.write_text(json.dumps({"decision": "HYP005_SHADOW_OBSERVATION_LOGGER_BLOCK"}), encoding="utf-8")
    outside_ledger = tmp_path / "reports" / "4B436625V_hyp005_shadow_observation_ledger_baseline.json"
    outside_ledger.write_text("[]", encoding="utf-8")
    result = _run(
        project_root,
        "tools/run_hyp005_shadow_collection_orchestrator_4B436625X.py",
        "--candidate-spec-json", str(candidate),
        "--logger-report-json", str(logger),
        "--ledger-json", str(outside_ledger),
        "--reports-dir", str(r1),
        "--strict-explicit-chain",
        "--out-dir", str(r1),
        "--review-ok",
    )
    assert result.returncode != 0
    assert "must remain inside scoped reports-dir" in (result.stdout + result.stderr)
