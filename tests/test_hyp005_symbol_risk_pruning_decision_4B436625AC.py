from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tradebot.research_hyp005_symbol_risk_pruning_decision import (
    HYP005_BRANCH_CLOSURE_RECOMMENDED,
    HYP005_BRANCH_REFINEMENT_REQUIRED,
    HYP005_CONTINUE_WITH_BASELINE_SYMBOLS,
    HYP005_CONTINUE_WITH_PRUNED_SYMBOL_SET,
    build_hyp005_symbol_risk_pruning_decision_report,
)

SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "LINKUSDT", "LTCUSDT")


def _observation(index: int, symbol: str, *, edge: float, slippage: float = 4.0) -> dict[str, object]:
    hour = (index % 6) * 4
    day = 1 + (index // 6)
    timestamp = f"2026-05-{day:02d}T{hour:02d}:00:00+00:00"
    compact = f"2026-05-{day:02d}T{hour:02d}0000Z"
    return {
        "observation_id": f"HYP-005-{symbol}-4h-{index}-{compact}0000",
        "hypothesis_id": "HYP-005",
        "branch_name": "liquidity_sweep_reversal_vol_compression",
        "strategy_family": "long_liquidity_sweep_reversal",
        "symbol": symbol,
        "timeframe": "4h",
        "timestamp_utc": timestamp,
        "entry_reference_price": 100.0,
        "invalidation_level": 98.0,
        "lookback_low": 99.0,
        "swept_low": 98.0,
        "sweep_depth_bps": 30.0,
        "wick_pct": 55.0,
        "compression_ratio": 0.98,
        "spread_slippage_proxy_bps": slippage,
        "mae_bps": -40.0,
        "mfe_bps": 80.0,
        "data_quality_ok": True,
        "no_order_shadow_only": True,
        "order_action": "NONE",
        "forward_return_bps_final": edge,
    }


def _write_ledger(reports_dir: Path, observations: list[dict[str, object]]) -> None:
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "4B436625V_hyp005_shadow_observation_ledger_20260602_080009.json").write_text(
        json.dumps({"shadow_observations": observations}),
        encoding="utf-8",
    )
    (reports_dir / "4B436625AB_H2_hyp005_shadow_quality_slippage_audit_20260602_080010.json").write_text(
        json.dumps({"decision": "HYP005_SHADOW_QUALITY_AUDIT_REVIEW_REQUIRED", "deduplication": {"unique_observation_count": len(observations)}}),
        encoding="utf-8",
    )


def test_25ac_pruned_symbol_set_can_pass_when_avax_doge_removal_repairs_edge(tmp_path: Path) -> None:
    observations: list[dict[str, object]] = []
    for index in range(32):
        symbol = SYMBOLS[index % len(SYMBOLS)]
        edge = 45.0
        slippage = 4.0
        if symbol in {"AVAXUSDT", "DOGEUSDT"}:
            edge = -450.0
            slippage = 18.0
        observations.append(_observation(index, symbol, edge=edge, slippage=slippage))
    _write_ledger(tmp_path, observations)
    report = build_hyp005_symbol_risk_pruning_decision_report(tmp_path, include_all=True, review_ok=True)
    assert report["decision"] == HYP005_CONTINUE_WITH_PRUNED_SYMBOL_SET
    assert report["recommended_pruned_symbols"] == ["AVAXUSDT", "DOGEUSDT"]
    assert report["selected_scenario"]["passes_continuation_gate"] is True
    assert report["approved_for_scheduler_regeneration"] is False
    assert report["config_mutation_performed"] is False
    assert report["approved_for_paper_candidate"] is False
    assert report["approved_for_live_real"] is False


def test_25ac_baseline_can_pass_without_risk_symbols(tmp_path: Path) -> None:
    observations = [_observation(index, SYMBOLS[index % len(SYMBOLS)], edge=35.0) for index in range(32)]
    _write_ledger(tmp_path, observations)
    report = build_hyp005_symbol_risk_pruning_decision_report(tmp_path, include_all=True, review_ok=True)
    assert report["decision"] == HYP005_CONTINUE_WITH_BASELINE_SYMBOLS
    assert report["recommended_pruned_symbols"] == []
    assert report["recommended_symbols"] == sorted(SYMBOLS)


def test_25ac_unique_target_not_met_requires_refinement(tmp_path: Path) -> None:
    observations = [_observation(index, SYMBOLS[index % len(SYMBOLS)], edge=35.0) for index in range(12)]
    _write_ledger(tmp_path, observations)
    report = build_hyp005_symbol_risk_pruning_decision_report(tmp_path, include_all=True, review_ok=True)
    assert report["decision"] == HYP005_BRANCH_REFINEMENT_REQUIRED
    assert "UNIQUE_SHADOW_SAMPLE_TARGET_NOT_MET" in report["reason_codes"]
    assert report["approved_for_paper_candidate"] is False


def test_25ac_closure_requires_mature_bad_evidence_across_scenarios(tmp_path: Path) -> None:
    observations = [_observation(index, SYMBOLS[index % len(SYMBOLS)], edge=-80.0) for index in range(42)]
    _write_ledger(tmp_path, observations)
    report = build_hyp005_symbol_risk_pruning_decision_report(tmp_path, include_all=True, review_ok=True)
    assert report["decision"] == HYP005_BRANCH_CLOSURE_RECOMMENDED
    assert "ALL_CONTROLLED_SYMBOL_SCENARIOS_REMAIN_ECONOMICALLY_WEAK" in report["reason_codes"]
    assert report["approved_for_continued_no_order_shadow_collection"] is False
    assert report["approved_for_live_real"] is False


def test_25ac_all_transition_guardrails_remain_closed(tmp_path: Path) -> None:
    observations = [_observation(index, SYMBOLS[index % len(SYMBOLS)], edge=35.0) for index in range(32)]
    _write_ledger(tmp_path, observations)
    report = build_hyp005_symbol_risk_pruning_decision_report(tmp_path, include_all=True, review_ok=True)
    assert report["approved_for_scheduler_regeneration"] is False
    assert report["scheduler_regeneration_requires_separate_operator_patch"] is True
    assert report["approved_for_paper_transition_candidate"] is False
    assert report["approved_for_paper_candidate"] is False
    assert report["approved_for_live_real"] is False
    assert report["order_actions_performed"] is False
    assert report["post_requests_allowed"] is False
    assert report["reload_performed"] is False
    assert report["training_performed"] is False
    assert report["config_mutation_performed"] is False


def test_25ac_tool_writes_report(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports"
    out_dir = tmp_path / "out"
    observations = [_observation(index, SYMBOLS[index % len(SYMBOLS)], edge=35.0) for index in range(32)]
    _write_ledger(reports_dir, observations)
    project_root = Path(__file__).resolve().parents[1]
    tool = project_root / "tools" / "run_hyp005_symbol_risk_pruning_decision_4B436625AC.py"
    result = subprocess.run(
        [
            sys.executable,
            str(tool),
            "--reports-dir",
            str(reports_dir),
            "--out-dir",
            str(out_dir),
            "--include-all",
            "--review-ok",
        ],
        cwd=project_root,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert "4B.4.3.6.6.25AC" in result.stdout
    assert "HYP005_CONTINUE_WITH_BASELINE_SYMBOLS" in result.stdout
    assert list(out_dir.glob("4B436625AC_hyp005_symbol_risk_pruning_decision_*.json"))
    assert list(out_dir.glob("4B436625AC_hyp005_symbol_risk_pruning_decision_*.md"))
