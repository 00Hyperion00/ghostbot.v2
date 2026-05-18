from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tradebot.research_hyp005_shadow_quality_audit import (
    HYP005_SHADOW_QUALITY_HOTFIX_VERSION,
    OBSERVATION_CANONICAL_DEDUPLICATION_APPLIED,
    OBSERVATION_DUPLICATES_REMOVED,
    build_hyp005_shadow_quality_audit_report,
    load_hyp005_shadow_observations,
)


def _obs(
    obs_id: str,
    symbol: str,
    ts: str,
    final: float | None,
    slip: float = 4.0,
    entry: float = 1.0,
) -> dict[str, object]:
    return {
        "observation_id": obs_id,
        "hypothesis_id": "HYP-005",
        "branch_name": "liquidity_sweep_reversal_vol_compression",
        "strategy_family": "long_liquidity_sweep_reversal",
        "symbol": symbol,
        "timeframe": "4h",
        "timestamp_utc": ts,
        "entry_reference_price": entry,
        "invalidation_level": round(entry * 0.97, 6),
        "lookback_low": round(entry * 0.98, 6),
        "swept_low": round(entry * 0.97, 6),
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


def _write_common_side_reports(reports_dir: Path, count: int = 0) -> None:
    (reports_dir / "4B436625W_hyp005_shadow_observation_acceptance_20260518_160009.json").write_text(
        json.dumps({"decision": "HYP005_SHADOW_PAPER_TRANSITION_BLOCK"}),
        encoding="utf-8",
    )
    (reports_dir / "4B436625Y_hyp005_shadow_operator_daily_audit_20260518_130009.json").write_text(
        json.dumps(
            {
                "decision": "HYP005_SHADOW_OPERATOR_AUDIT_READY",
                "latest_logger_decision": "HYP005_SHADOW_OBSERVATION_LOGGER_BLOCK",
                "latest_acceptance_decision": "HYP005_SHADOW_PAPER_TRANSITION_BLOCK",
                "shadow_observation_count": count,
            }
        ),
        encoding="utf-8",
    )


def test_25abh1_canonical_dedupes_rolling_row_index_duplicates(tmp_path: Path) -> None:
    # Same symbol/timeframe/timestamp, but different observation_id row index across scheduler cycles.
    t = "2026-05-18T04:00:00+00:00"
    first = _obs("HYP-005-AVAXUSDT-4h-92-2026-05-18T040000Z0000", "AVAXUSDT", t, -100.0)
    duplicate = _obs("HYP-005-AVAXUSDT-4h-88-2026-05-18T040000Z0000", "AVAXUSDT", t, -100.0)
    other = _obs("HYP-005-ADAUSDT-4h-256-2026-05-18T080000Z0000", "ADAUSDT", "2026-05-18T08:00:00Z", 50.0)
    (tmp_path / "4B436625V_hyp005_shadow_observation_ledger_20260518_120000.json").write_text(
        json.dumps({"shadow_observations": [first, other]}), encoding="utf-8"
    )
    (tmp_path / "4B436625V_hyp005_shadow_observation_ledger_20260518_160000.json").write_text(
        json.dumps({"shadow_observations": [duplicate, other]}), encoding="utf-8"
    )
    (tmp_path / "4B436625V_hyp005_shadow_observation_logger_20260518_160000.json").write_text(
        json.dumps(
            {
                "decision": "HYP005_SHADOW_OBSERVATION_LOGGER_BLOCK",
                "reason_codes": ["NO_ORDER_SHADOW_LEDGER_NOT_READY", "SHADOW_MISSING_FIELDS_HIGH"],
                "shadow_observations": [duplicate, other],
            }
        ),
        encoding="utf-8",
    )
    _write_common_side_reports(tmp_path, count=2)

    report = build_hyp005_shadow_quality_audit_report(tmp_path, include_all=True, review_ok=True)
    assert report["hotfix_version"] == HYP005_SHADOW_QUALITY_HOTFIX_VERSION
    assert report["quality_summary"]["shadow_observation_count"] == 2
    assert report["deduplication"]["raw_observation_count"] == 4
    assert report["deduplication"]["duplicate_removed_count"] == 2
    assert OBSERVATION_CANONICAL_DEDUPLICATION_APPLIED in report["reason_codes"]
    assert OBSERVATION_DUPLICATES_REMOVED in report["reason_codes"]
    assert report["approved_for_live_real"] is False
    assert report["post_requests_allowed"] is False


def test_25abh1_prefers_matured_duplicate_over_pending_duplicate(tmp_path: Path) -> None:
    t = "2026-05-18T12:00:00+00:00"
    pending = _obs("HYP-005-BNBUSDT-4h-101-2026-05-18T120000Z0000", "BNBUSDT", t, None)
    matured = _obs("HYP-005-BNBUSDT-4h-97-2026-05-18T120000Z0000", "BNBUSDT", t, 42.5)
    (tmp_path / "4B436625V_hyp005_shadow_observation_ledger_20260518_120000.json").write_text(
        json.dumps({"shadow_observations": [pending]}), encoding="utf-8"
    )
    (tmp_path / "4B436625V_hyp005_shadow_observation_ledger_20260518_160000.json").write_text(
        json.dumps({"shadow_observations": [matured]}), encoding="utf-8"
    )
    _write_common_side_reports(tmp_path, count=1)

    observations, _sources = load_hyp005_shadow_observations(tmp_path, include_all=True)
    assert len(observations) == 1
    assert observations[0]["forward_return_bps_final"] == 42.5
    report = build_hyp005_shadow_quality_audit_report(tmp_path, include_all=True)
    assert report["quality_summary"]["matured_forward_return_count"] == 1
    assert report["quality_summary"]["maturity_pending_count"] == 0


def test_25abh1_jsonl_wrapper_rows_are_not_counted_as_observations(tmp_path: Path) -> None:
    obs_a = _obs("a", "ADAUSDT", "2026-05-18T00:00:00Z", 10.0)
    obs_b = _obs("b", "XRPUSDT", "2026-05-18T04:00:00Z", -5.0)
    jsonl = tmp_path / "4B436625V_hyp005_shadow_observation_ledger_20260518_160000.jsonl"
    jsonl.write_text(
        "\n".join(
            [
                json.dumps({"report_type": "wrapper", "shadow_observations": [obs_a]}),
                json.dumps({"report_type": "wrapper", "shadow_observations": [obs_b]}),
            ]
        ),
        encoding="utf-8",
    )
    _write_common_side_reports(tmp_path, count=2)
    report = build_hyp005_shadow_quality_audit_report(tmp_path, include_all=True)
    assert report["deduplication"]["raw_observation_count"] == 2
    assert report["quality_summary"]["shadow_observation_count"] == 2
    assert sorted(report["quality_summary"]["symbols_observed"]) == ["ADAUSDT", "XRPUSDT"]


def test_25abh1_tool_writes_deduped_report(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    out_dir = tmp_path / "out"
    t = "2026-05-18T04:00:00+00:00"
    a1 = _obs("HYP-005-DOGEUSDT-4h-200-2026-05-18T040000Z0000", "DOGEUSDT", t, -20.0, slip=15.0)
    a2 = _obs("HYP-005-DOGEUSDT-4h-196-2026-05-18T040000Z0000", "DOGEUSDT", t, -20.0, slip=15.0)
    (reports_dir / "4B436625V_hyp005_shadow_observation_ledger_20260518_120000.json").write_text(
        json.dumps({"shadow_observations": [a1]}), encoding="utf-8"
    )
    (reports_dir / "4B436625V_hyp005_shadow_observation_ledger_20260518_160000.json").write_text(
        json.dumps({"shadow_observations": [a2]}), encoding="utf-8"
    )
    _write_common_side_reports(reports_dir, count=1)
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
    assert "25AB-H1" in result.stdout
    assert "duplicate_removed_count: 1" in result.stdout
    reports = list(out_dir.glob("4B436625AB_H1_hyp005_shadow_quality_slippage_audit_*.json"))
    assert reports
    payload = json.loads(reports[0].read_text(encoding="utf-8"))
    assert payload["quality_summary"]["shadow_observation_count"] == 1
    assert payload["deduplication"]["duplicate_removed_count"] == 1
    assert payload["approved_for_paper_candidate"] is False
