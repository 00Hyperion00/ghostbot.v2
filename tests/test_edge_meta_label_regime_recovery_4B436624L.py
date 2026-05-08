from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tradebot.edge_meta_label_regime_recovery import (
    EDGE_META_LABEL_REGIME_CONTRACT_VERSION,
    build_edge_meta_label_recovery_report,
    evaluate_edge_meta_label_samples,
)


def _sample_rows(*, positive_subset: bool = True) -> list[dict]:
    rows: list[dict] = []
    # Base staged actions are mediocre/negative; trend+volume+confidence subset is positive.
    for i in range(160):
        pred = 1 if i % 2 == 0 else 2
        subset = i < 60
        if positive_subset:
            net_edge = 16.0 if subset else -11.0
            actual = pred if subset or i % 5 == 0 else 0
        else:
            net_edge = -8.0
            actual = 0 if i % 4 else pred
        rows.append(
            {
                "actual_target": actual,
                "staged_pred": pred,
                "action_prob": 0.72 if subset else 0.43,
                "side_margin": 0.32 if subset else 0.04,
                "net_edge_bps": net_edge,
                "ema_spread_pct": 0.4 if pred == 1 else -0.4,
                "mtf_15m_trend_flag": 1 if pred == 1 else -1,
                "volume_ratio": 1.4 if subset else 0.7,
                "abs_close_to_vwap_pct": 0.05 if subset else 0.9,
                "atr_pct": 0.25,
            }
        )
    # Add non-action validation rows so coverage is not too high.
    for _ in range(360):
        rows.append({"actual_target": 0, "staged_pred": 0, "net_edge_bps": 0.0})
    return rows


def test_edge_meta_label_gate_passes_positive_regime_subset() -> None:
    report = evaluate_edge_meta_label_samples(_sample_rows(positive_subset=True), candidate_name="mock", total_validation_samples=520)
    assert report["contract_version"] == EDGE_META_LABEL_REGIME_CONTRACT_VERSION
    assert report["decision"] == "PASS"
    best_filter = report["selection"]["best_filter"]
    assert best_filter["metrics"]["mean_net_edge_bps"] > 1.0
    assert best_filter["metrics"]["edge_lift_bps"] > 5.0
    assert report["approved_for_live_real"] is False
    assert report["reload_allowed"] is False


def test_edge_meta_label_gate_blocks_negative_edge_subset() -> None:
    report = evaluate_edge_meta_label_samples(_sample_rows(positive_subset=False), candidate_name="mock", total_validation_samples=520)
    assert report["decision"] == "BLOCK"
    assert "NO_EDGE_META_LABEL_REGIME_FILTER_PASSED" in report["reason_codes"]


def test_build_edge_meta_label_recovery_report_selects_best_candidate() -> None:
    good = evaluate_edge_meta_label_samples(_sample_rows(positive_subset=True), candidate_name="good", total_validation_samples=520)
    bad = evaluate_edge_meta_label_samples(_sample_rows(positive_subset=False), candidate_name="bad", total_validation_samples=520)
    report = build_edge_meta_label_recovery_report([bad, good], source="unit")
    assert report["decision"] == "PASS"
    assert report["selected_candidate"] == "good"
    assert report["approved_for_paper_candidate"] is False


def test_tool_writes_report_from_candidate_json(tmp_path: Path) -> None:
    payload = {"candidate_name": "mock", "total_validation_samples": 520, "samples": _sample_rows(positive_subset=True)}
    candidate_json = tmp_path / "candidate.json"
    candidate_json.write_text(json.dumps(payload), encoding="utf-8")
    out_dir = tmp_path / "reports"
    cmd = [
        sys.executable,
        "tools/run_edge_meta_label_regime_recovery_4B436624L.py",
        "--candidate-json",
        str(candidate_json),
        "--out-dir",
        str(out_dir),
        "--review-ok",
    ]
    result = subprocess.run(cmd, cwd=Path(__file__).resolve().parents[1], text=True, capture_output=True, check=True)
    assert "4B.4.3.6.6.24L edge-aware meta-label / regime recovery PASS" in result.stdout
    reports = list(out_dir.glob("4B436624L_edge_meta_label_regime_recovery_*.json"))
    assert reports
    loaded = json.loads(reports[0].read_text(encoding="utf-8"))
    assert loaded["decision"] == "PASS"
    assert loaded["guardrails"]["post_requests_allowed"] is False


def test_report_blocks_empty_samples() -> None:
    report = evaluate_edge_meta_label_samples([], candidate_name="empty")
    assert report["decision"] == "BLOCK"
    assert "META_LABEL_SAMPLE_COUNT_LOW" in report["reason_codes"]
