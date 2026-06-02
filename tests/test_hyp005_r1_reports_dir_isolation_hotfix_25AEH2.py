from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tradebot.research_hyp005_r1_shadow_scheduler_regeneration_pack import (
    HYP005_R1_REPORTS_DIR_ISOLATION_HOTFIX_VERSION,
    HYP005_R1_SHADOW_SCHEDULER_PACK_BLOCK,
    HYP005_R1_SHADOW_SCHEDULER_PACK_READY,
    Hyp005R1SchedulerPackRequest,
    build_hyp005_r1_shadow_scheduler_regeneration_pack_report,
)
from tradebot.research_hyp005_shadow_operator_runbook import build_operator_commands

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
        "hypothesis_id": "HYP-005",
        "branch_name": "liquidity_sweep_reversal_vol_compression",
        "strategy_family": "long_liquidity_sweep_reversal",
        "no_order_shadow_only": True,
        "guardrails": {
            "no_order_shadow_only": True,
            "orders_allowed": False,
            "paper_trading_allowed": False,
            "live_trading_allowed": False,
            "post_requests_allowed": False,
        },
    }


def _write_inputs(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "4B436625AD_hyp005_baseline_freeze_refined_revalidation_planning_20260602_072834.json").write_text(
        json.dumps(_plan()), encoding="utf-8"
    )
    (root / "4B436625U_hyp005_no_order_shadow_candidate_spec_20260509_175722.json").write_text(
        json.dumps(_candidate_spec()), encoding="utf-8"
    )


def _build(tmp_path: Path):
    _write_inputs(tmp_path)
    return build_hyp005_r1_shadow_scheduler_regeneration_pack_report(
        tmp_path,
        out_dir=tmp_path,
        baseline_task_disabled_confirmed=True,
        review_ok=True,
        timestamp="20260602_120000",
    )


def test_25aeh2_declares_reports_dir_isolation_hotfix_version() -> None:
    assert HYP005_R1_REPORTS_DIR_ISOLATION_HOTFIX_VERSION == "4B.4.3.6.6.25AE-H2"


def test_25aeh2_generated_cycle_reads_only_isolated_r1_reports_dir(tmp_path: Path) -> None:
    report = _build(tmp_path)
    assert report["decision"] == HYP005_R1_SHADOW_SCHEDULER_PACK_READY
    assert report["reports_dir_isolation_enforced"] is True
    assert report["runtime_chain_reads_only_scoped_reports_dir"] is True
    assert report["baseline_reports_root_read_by_runtime_chain"] is False
    assert report["isolated_runtime_reports_dir"] == "reports\\hyp005_r1_isolated"
    cycle = Path(report["artifacts"]["shadow_cycle_ps1"]).read_text(encoding="utf-8")
    assert 'reports\\hyp005_r1_isolated' in cycle
    assert '--reports-dir "$R1ReportsDir"' in cycle
    assert '--reports-dir reports `' not in cycle
    assert '--logger-report-json "$($LatestLoggerReport.FullName)"' in cycle
    assert '--ledger-json "$($LatestLoggerLedger.FullName)"' in cycle
    assert '--collection-report-json "$($LatestCollectionReport.FullName)"' in cycle
    assert '--acceptance-report-json "$($LatestAcceptanceReport.FullName)"' in cycle
    assert 'project reports root is forbidden' in cycle


def test_25aeh2_blocks_nonisolated_runtime_reports_subdir(tmp_path: Path) -> None:
    _write_inputs(tmp_path)
    request = Hyp005R1SchedulerPackRequest(r1_reports_subdir="reports")
    report = build_hyp005_r1_shadow_scheduler_regeneration_pack_report(
        tmp_path,
        out_dir=tmp_path,
        request=request,
        baseline_task_disabled_confirmed=True,
        review_ok=True,
    )
    assert report["decision"] == HYP005_R1_SHADOW_SCHEDULER_PACK_BLOCK
    assert "R1_REPORTS_SUBDIR_NOT_ISOLATED" in report["blockers"]
    assert report["artifacts"] is None


def test_25aeh2_registration_requires_existing_r1_task_disabled_before_replacement(tmp_path: Path) -> None:
    report = _build(tmp_path)
    script = Path(report["artifacts"]["register_task_ps1"]).read_text(encoding="utf-8")
    assert '$ExistingR1Task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue' in script
    assert '$ExistingR1Task.State -ne "Disabled"' in script
    assert 'must be Disabled before H2 replacement' in script


def test_25aeh2_operator_audit_commands_display_scoped_reports_dir() -> None:
    commands = build_operator_commands(
        candidate_spec_path=r"C:\\project\\reports\\pack\\hyp005_r1_runtime_candidate_spec.json",
        symbols=REFINED,
        interval="4h",
        days=30,
        base_url="https://api.binance.com",
        out_dir=r"C:\\project\\reports\\hyp005_r1_isolated",
    )
    text = "\n\n".join(command.powershell for command in commands)
    assert '--reports-dir reports `' not in text
    assert r'--reports-dir C:\\project\\reports\\hyp005_r1_isolated `' in text
    assert '--candidate-spec-json' in text


def test_25aeh2_orchestrator_scope_does_not_import_root_baseline_ledger(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[1]
    tool = project_root / "tools" / "run_hyp005_shadow_collection_orchestrator_4B436625X.py"
    reports_root = tmp_path / "reports"
    r1 = reports_root / "hyp005_r1_isolated"
    r1.mkdir(parents=True)

    baseline_observation = {
        "symbol": "DOGEUSDT",
        "timestamp_utc": "2026-06-01T00:00:00Z",
        "timeframe": "4h",
        "strategy_family": "long_liquidity_sweep_reversal",
        "sweep_direction": "LONG",
        "entry_reference_price": 0.1,
    }
    (reports_root / "4B436625V_hyp005_shadow_observation_ledger_baseline.json").write_text(
        json.dumps([baseline_observation]), encoding="utf-8"
    )
    spec = r1 / "hyp005_r1_runtime_candidate_spec.json"
    logger = r1 / "4B436625V_hyp005_shadow_observation_logger_20260602_120000.json"
    ledger = r1 / "4B436625V_hyp005_shadow_observation_ledger_20260602_120000.json"
    spec.write_text(json.dumps(_candidate_spec()), encoding="utf-8")
    logger.write_text(
        json.dumps(
            {
                "decision": "HYP005_SHADOW_OBSERVATION_LOGGER_BLOCK",
                "approved_for_paper_candidate": False,
                "approved_for_live_real": False,
                "order_actions_performed": False,
                "post_requests_allowed": False,
            }
        ),
        encoding="utf-8",
    )
    ledger.write_text("[]", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(tool),
            "--candidate-spec-json",
            str(spec),
            "--logger-report-json",
            str(logger),
            "--ledger-json",
            str(ledger),
            "--reports-dir",
            str(r1),
            "--include-all",
            "--symbols",
            ",".join(REFINED),
            "--out-dir",
            str(r1),
            "--review-ok",
        ],
        cwd=project_root,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    merged = sorted(r1.glob("4B436625X_hyp005_shadow_merged_ledger_*.json"))[-1]
    payload = json.loads(merged.read_text(encoding="utf-8"))
    assert payload["observations"] == []
    assert "DOGEUSDT" not in merged.read_text(encoding="utf-8")


def test_25aeh2_no_order_guardrails_remain_closed(tmp_path: Path) -> None:
    report = _build(tmp_path)
    assert report["approved_for_paper_candidate"] is False
    assert report["approved_for_live_real"] is False
    assert report["post_requests_allowed"] is False
    assert report["windows_task_mutation_performed"] is False
