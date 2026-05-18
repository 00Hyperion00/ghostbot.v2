from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tradebot.research_hyp005_shadow_quality_audit import (
    BLOCK_WITH_UNIQUE_OBSERVATIONS_RECOMMENDATION,
    HYP005_SHADOW_QUALITY_AUDIT_BLOCK,
    HYP005_SHADOW_QUALITY_HOTFIX_VERSION,
    RECOMMENDATION_MESSAGE_CONSISTENCY_APPLIED,
    build_hyp005_shadow_quality_audit_report,
)


def _obs(obs_id: str, symbol: str = "ADAUSDT", *, missing_entry: bool = False) -> dict[str, object]:
    row: dict[str, object] = {
        "observation_id": obs_id,
        "hypothesis_id": "HYP-005",
        "branch_name": "liquidity_sweep_reversal_vol_compression",
        "strategy_family": "long_liquidity_sweep_reversal",
        "symbol": symbol,
        "timeframe": "4h",
        "timestamp_utc": "2026-05-18T12:00:00+00:00",
        "entry_reference_price": 1.0,
        "invalidation_level": 0.97,
        "lookback_low": 0.98,
        "swept_low": 0.97,
        "sweep_depth_bps": 30.0,
        "wick_pct": 55.0,
        "compression_ratio": 0.98,
        "spread_slippage_proxy_bps": 4.0,
        "mae_bps": -40.0,
        "mfe_bps": 80.0,
        "data_quality_ok": True,
        "no_order_shadow_only": True,
        "order_action": "NONE",
        "forward_return_bps_final": -25.0,
    }
    if missing_entry:
        del row["entry_reference_price"]
    return row


def _write_ledger(reports_dir: Path, observations: list[dict[str, object]]) -> None:
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "4B436625V_hyp005_shadow_observation_ledger_20260518_160008.json").write_text(
        json.dumps({"shadow_observations": observations}),
        encoding="utf-8",
    )
    (reports_dir / "4B436625V_hyp005_shadow_observation_logger_20260518_160008.json").write_text(
        json.dumps(
            {
                "decision": "HYP005_SHADOW_OBSERVATION_LOGGER_BLOCK",
                "reason_codes": ["NO_ORDER_SHADOW_LEDGER_NOT_READY", "SHADOW_MISSING_FIELDS_HIGH"],
                "shadow_observations": observations,
            }
        ),
        encoding="utf-8",
    )
    (reports_dir / "4B436625W_hyp005_shadow_observation_acceptance_20260518_160009.json").write_text(
        json.dumps({"decision": "HYP005_SHADOW_PAPER_TRANSITION_BLOCK"}),
        encoding="utf-8",
    )
    (reports_dir / "4B436625Y_hyp005_shadow_operator_daily_audit_20260518_130009.json").write_text(
        json.dumps({"decision": "HYP005_SHADOW_OPERATOR_AUDIT_READY", "shadow_observation_count": len(observations)}),
        encoding="utf-8",
    )


def test_25abh2_block_with_unique_observations_does_not_claim_no_unique_obs(tmp_path: Path) -> None:
    _write_ledger(tmp_path, [_obs("bad-1", missing_entry=True), _obs("good-1", "BNBUSDT")])
    report = build_hyp005_shadow_quality_audit_report(tmp_path, include_all=True, review_ok=True)
    assert report["hotfix_version"] == HYP005_SHADOW_QUALITY_HOTFIX_VERSION
    assert report["decision"] == HYP005_SHADOW_QUALITY_AUDIT_BLOCK
    assert report["quality_summary"]["shadow_observation_count"] == 2
    assert "no unique shadow observations" not in report["recommendation"]
    assert "2 unique shadow observations" in report["recommendation"]
    assert report["recommendation_consistency"]["recommendation_type"] == BLOCK_WITH_UNIQUE_OBSERVATIONS_RECOMMENDATION
    assert RECOMMENDATION_MESSAGE_CONSISTENCY_APPLIED in report["reason_codes"]
    assert BLOCK_WITH_UNIQUE_OBSERVATIONS_RECOMMENDATION in report["reason_codes"]


def test_25abh2_no_observations_keeps_no_unique_observation_recommendation(tmp_path: Path) -> None:
    report = build_hyp005_shadow_quality_audit_report(tmp_path, include_all=True)
    assert report["decision"] == HYP005_SHADOW_QUALITY_AUDIT_BLOCK
    assert report["quality_summary"]["shadow_observation_count"] == 0
    assert "no unique shadow observations" in report["recommendation"]
    assert report["recommendation_consistency"]["no_unique_observation_claim_allowed"] is True


def test_25abh2_tool_writes_h2_and_backward_compatible_reports(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports"
    out_dir = tmp_path / "out"
    _write_ledger(reports_dir, [_obs("bad-1", missing_entry=True), _obs("good-1", "BNBUSDT")])
    repo_root = Path(__file__).resolve().parents[1]
    tool = repo_root / "tools" / "run_hyp005_shadow_quality_audit_4B436625AB.py"
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
        check=True,
        text=True,
        capture_output=True,
    )
    assert "25AB-H2" in result.stdout
    assert "25AB-H1" in result.stdout  # backward-compatible report glob line
    assert list(out_dir.glob("4B436625AB_H2_hyp005_shadow_quality_slippage_audit_*.json"))
    assert list(out_dir.glob("4B436625AB_H1_hyp005_shadow_quality_slippage_audit_*.json"))
    assert list(out_dir.glob("4B436625AB_hyp005_shadow_quality_slippage_audit_*.json"))


def test_25abh2_no_order_guardrails_remain_closed(tmp_path: Path) -> None:
    _write_ledger(tmp_path, [_obs("bad-1", missing_entry=True)])
    report = build_hyp005_shadow_quality_audit_report(tmp_path, include_all=True)
    assert report["approved_for_paper_candidate"] is False
    assert report["approved_for_live_real"] is False
    assert report["order_actions_performed"] is False
    assert report["post_requests_allowed"] is False
    assert report["reload_performed"] is False
    assert report["training_performed"] is False
