from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tradebot.research_hyp005_shadow_quality_audit import (
    HYP005_SHADOW_QUALITY_AUDIT_BLOCK,
    HYP005_SHADOW_QUALITY_AUDIT_REVIEW_REQUIRED,
    build_hyp005_shadow_quality_audit_report,
)


def _obs(
    obs_id: str,
    symbol: str,
    final: float | None,
    slip: float = 4.0,
    ts: str = "2026-05-18T00:00:00+00:00",
) -> dict[str, object]:
    return {
        "observation_id": obs_id,
        "hypothesis_id": "HYP-005",
        "branch_name": "liquidity_sweep_reversal_vol_compression",
        "strategy_family": "long_liquidity_sweep_reversal",
        "symbol": symbol,
        "timeframe": "4h",
        "timestamp_utc": ts,
        "entry_reference_price": 1.0,
        "invalidation_level": 0.97,
        "lookback_low": 0.98,
        "swept_low": 0.97,
        "sweep_depth_bps": 30.0,
        "wick_pct": 55.0,
        "compression_ratio": 0.98,
        "spread_slippage_proxy_bps": slip,
        "mae_bps": -40.0,
        "mfe_bps": 80.0,
        "data_quality_ok": True,
        "no_order_shadow_only": True,
        "order_action": "NONE",
        "forward_return_bps_final": final,
    }


def _write_report_files(reports_dir: Path, observations: list[dict[str, object]]) -> None:
    ledger = reports_dir / "4B436625V_hyp005_shadow_observation_ledger_20260518_160008.json"
    ledger.write_text(json.dumps({"shadow_observations": observations}), encoding="utf-8")
    latest_25v = reports_dir / "4B436625V_hyp005_shadow_observation_logger_20260518_160008.json"
    latest_25v.write_text(
        json.dumps(
            {
                "decision": "HYP005_SHADOW_OBSERVATION_LOGGER_BLOCK",
                "reason_codes": ["NO_ORDER_SHADOW_LEDGER_NOT_READY", "SHADOW_MISSING_FIELDS_HIGH"],
                "shadow_observations": observations,
            }
        ),
        encoding="utf-8",
    )
    latest_25w = reports_dir / "4B436625W_hyp005_shadow_observation_acceptance_20260518_160009.json"
    latest_25w.write_text(json.dumps({"decision": "HYP005_SHADOW_PAPER_TRANSITION_BLOCK"}), encoding="utf-8")
    latest_25y = reports_dir / "4B436625Y_hyp005_shadow_operator_daily_audit_20260518_130009.json"
    latest_25y.write_text(
        json.dumps(
            {
                "decision": "HYP005_SHADOW_OPERATOR_AUDIT_READY",
                "latest_logger_decision": "HYP005_SHADOW_OBSERVATION_LOGGER_BLOCK",
                "latest_acceptance_decision": "HYP005_SHADOW_PAPER_TRANSITION_BLOCK",
                "shadow_observation_count": len(observations),
            }
        ),
        encoding="utf-8",
    )


def test_maturity_pending_not_counted_as_true_missing_field(tmp_path: Path) -> None:
    observations = [_obs("a", "ADAUSDT", 50.0), _obs("b", "BNBUSDT", None)]
    _write_report_files(tmp_path, observations)
    report = build_hyp005_shadow_quality_audit_report(tmp_path, include_all=True, review_ok=True)
    assert report["quality_summary"]["maturity_pending_count"] == 1
    assert report["quality_summary"]["true_missing_required_fields_pct"] == 0.0
    assert "MISSING_FINAL_RETURN_CLASSIFIED_AS_MATURITY_PENDING" in report["reason_codes"]
    assert report["approved_for_live_real"] is False
    assert report["post_requests_allowed"] is False


def test_high_slippage_is_flagged_per_symbol(tmp_path: Path) -> None:
    observations = [
        _obs("a", "DOGEUSDT", -20.0, slip=15.5),
        _obs("b", "ADAUSDT", 80.0, slip=4.5),
        _obs("c", "DOGEUSDT", None, slip=13.0),
    ]
    _write_report_files(tmp_path, observations)
    report = build_hyp005_shadow_quality_audit_report(tmp_path, include_all=True)
    assert "SHADOW_SLIPPAGE_PROXY_HIGH" in report["warnings"]
    assert report["quality_summary"]["high_slippage_count"] == 2
    doge = next(row for row in report["per_symbol_quality"] if row["symbol"] == "DOGEUSDT")
    assert "SYMBOL_SLIPPAGE_PROXY_HIGH" in doge["flags"]


def test_symbol_distribution_and_edge_metrics(tmp_path: Path) -> None:
    observations = [
        _obs("a", "ADAUSDT", 100.0),
        _obs("b", "BNBUSDT", -50.0),
        _obs("c", "XRPUSDT", 25.0),
        _obs("d", "XRPUSDT", None),
    ]
    _write_report_files(tmp_path, observations)
    report = build_hyp005_shadow_quality_audit_report(tmp_path, include_all=True)
    assert report["quality_summary"]["symbols_observed_count"] == 3
    assert report["quality_summary"]["matured_forward_return_count"] == 3
    assert report["quality_summary"]["mean_forward_edge_bps"] == 25.0
    assert report["quality_summary"]["profit_factor"] == 2.5


def test_no_observations_blocks_collection_quality_audit(tmp_path: Path) -> None:
    report = build_hyp005_shadow_quality_audit_report(tmp_path, include_all=True)
    assert report["decision"] == HYP005_SHADOW_QUALITY_AUDIT_BLOCK
    assert "NO_HYP005_SHADOW_OBSERVATIONS_FOUND" in report["blockers"]
    assert report["approved_for_live_real"] is False


def test_true_missing_required_field_blocks(tmp_path: Path) -> None:
    bad = _obs("a", "ADAUSDT", 25.0)
    del bad["entry_reference_price"]
    observations = [bad]
    _write_report_files(tmp_path, observations)
    report = build_hyp005_shadow_quality_audit_report(tmp_path, include_all=True)
    assert report["decision"] == HYP005_SHADOW_QUALITY_AUDIT_BLOCK
    assert "TRUE_REQUIRED_FIELDS_MISSING_HIGH" in report["blockers"]


def test_tool_writes_quality_audit_report(tmp_path: Path) -> None:
    observations = [_obs("a", "ADAUSDT", 25.0), _obs("b", "BNBUSDT", None)]
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    out_dir = tmp_path / "out"
    _write_report_files(reports_dir, observations)
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
    assert "HYP-005 shadow quality/slippage audit" in result.stdout
    reports = list(out_dir.glob("4B436625AB_hyp005_shadow_quality_slippage_audit_*.json"))
    assert reports
    payload = json.loads(reports[0].read_text(encoding="utf-8"))
    assert payload["decision"] in {HYP005_SHADOW_QUALITY_AUDIT_REVIEW_REQUIRED, HYP005_SHADOW_QUALITY_AUDIT_BLOCK}
    assert payload["approved_for_paper_candidate"] is False
