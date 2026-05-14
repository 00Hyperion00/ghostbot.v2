from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from tradebot.research_hyp005_symbol_coverage_expansion import (
    DEFAULT_HYP005_SYMBOLS_10,
    HYP005_SYMBOL_COVERAGE_BLOCK,
    HYP005_SYMBOL_COVERAGE_READY,
    build_hyp005_symbol_coverage_report,
    write_symbol_coverage_outputs,
)


def _write_operator_audit(path: Path, **overrides: object) -> Path:
    payload = {
        "decision": "HYP005_SHADOW_OPERATOR_AUDIT_READY",
        "no_order_operator_audit_only": True,
        "shadow_observation_count": 0,
        "shadow_sample_target": 30,
        "paper_transition_ready": False,
        "latest_acceptance_decision": "HYP005_SHADOW_PAPER_TRANSITION_BLOCK",
        "approved_for_live_real": False,
        "approved_for_paper_candidate": False,
        "approved_for_training_candidate": False,
        "order_actions_performed": False,
    }
    payload.update(overrides)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_default_10_symbol_coverage_passes(tmp_path: Path) -> None:
    audit_path = _write_operator_audit(tmp_path / "reports" / "4B436625Y_hyp005_shadow_operator_daily_audit_20260513_120000.json")
    report = build_hyp005_symbol_coverage_report(
        input_json=audit_path,
        reports_dir=tmp_path / "reports",
        review_ok=True,
    )

    assert report.ok is True
    assert report.decision == HYP005_SYMBOL_COVERAGE_READY
    assert report.approved_symbols == DEFAULT_HYP005_SYMBOLS_10
    assert report.symbol_count == 10
    assert report.baseline_symbol_count == 4
    assert report.expansion_symbol_count == 6
    assert report.approved_for_shadow_collection is True
    assert report.approved_for_scheduler_regeneration is True
    assert report.approved_for_paper_candidate is False
    assert report.approved_for_live_real is False
    assert report.post_requests_allowed is False


def test_duplicate_symbol_blocks() -> None:
    symbols = "BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,XRPUSDT,DOGEUSDT,ADAUSDT,AVAXUSDT,LINKUSDT,BTCUSDT"
    report = build_hyp005_symbol_coverage_report(symbols=symbols, review_ok=True)

    assert report.ok is False
    assert report.decision == HYP005_SYMBOL_COVERAGE_BLOCK
    assert "DUPLICATE_SYMBOLS_PRESENT" in report.reason_codes
    assert "ONE_OR_MORE_SYMBOLS_FAILED_VALIDATION" in report.reason_codes
    assert report.approved_for_scheduler_regeneration is False


def test_more_than_10_symbols_blocks() -> None:
    symbols = "BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,XRPUSDT,DOGEUSDT,ADAUSDT,AVAXUSDT,LINKUSDT,LTCUSDT,DOTUSDT"
    report = build_hyp005_symbol_coverage_report(symbols=symbols, review_ok=True)

    assert report.ok is False
    assert "SYMBOL_COUNT_ABOVE_ALLOWED_10" in report.reason_codes
    assert "EXACTLY_10_SYMBOLS_REQUIRED" in report.reason_codes
    assert report.approved_symbols == tuple()


def test_source_audit_live_approval_blocks(tmp_path: Path) -> None:
    audit_path = _write_operator_audit(
        tmp_path / "reports" / "4B436625Y_hyp005_shadow_operator_daily_audit_20260513_120000.json",
        approved_for_live_real=True,
    )
    report = build_hyp005_symbol_coverage_report(input_json=audit_path, review_ok=True)

    assert report.ok is False
    assert "SOURCE_AUDIT_LIVE_APPROVAL_DETECTED" in report.reason_codes
    assert report.approved_for_live_real is False
    assert report.order_actions_performed is False


def test_write_outputs_and_config(tmp_path: Path) -> None:
    audit_path = _write_operator_audit(tmp_path / "reports" / "4B436625Y_hyp005_shadow_operator_daily_audit_20260513_120000.json")
    report = build_hyp005_symbol_coverage_report(input_json=audit_path, review_ok=True)
    outputs = write_symbol_coverage_outputs(
        report,
        out_dir=tmp_path / "reports",
        config_dir=tmp_path / "config",
        write_config=True,
    )

    assert outputs["report_json"].exists()
    assert outputs["report_md"].exists()
    assert outputs["config_json"].exists()
    config = json.loads(outputs["config_json"].read_text(encoding="utf-8"))
    assert config["symbols"] == list(DEFAULT_HYP005_SYMBOLS_10)
    assert config["no_order_shadow_collection_only"] is True
    assert config["approved_for_live_real"] is False


def test_tool_writes_config_and_report(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[1]
    reports_dir = tmp_path / "reports"
    config_dir = tmp_path / "config"
    _write_operator_audit(reports_dir / "4B436625Y_hyp005_shadow_operator_daily_audit_20260513_120000.json")

    result = subprocess.run(
        [
            sys.executable,
            str(project_root / "tools" / "run_hyp005_symbol_coverage_expansion_4B436625AA.py"),
            "--reports-dir",
            str(reports_dir),
            "--config-dir",
            str(config_dir),
            "--out-dir",
            str(reports_dir),
            "--write-config",
            "--review-ok",
        ],
        cwd=project_root,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert "HYP005_SYMBOL_COVERAGE_EXPANSION_READY" in result.stdout
    assert (config_dir / "hyp005_shadow_symbols_4B436625AA.json").exists()
    assert list(reports_dir.glob("4B436625AA_hyp005_symbol_coverage_expansion_*.json"))
