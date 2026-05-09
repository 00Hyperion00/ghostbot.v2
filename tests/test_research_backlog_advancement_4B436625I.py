from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tradebot.research_backlog_advancement import (
    ResearchHypothesisBacklogItem,
    build_research_backlog_advancement_gate,
    extract_closure_evidence,
    load_backlog_from_registry,
)


def _closure_25h() -> dict:
    return {
        "contract_version": "4B.4.3.6.6.25H",
        "decision": "FUTURES_BRANCH_CLOSURE_CONFIRMED",
        "hypothesis_id": "HYP-002",
        "branch_name": "futures_funding_trend_exhaustion",
        "final_25f_decision": "BRANCH_CLOSED_NO_GO",
        "primary_terminal_block_count": 5,
        "companion_terminal_block_count": 2,
        "approved_for_research_candidate": False,
        "approved_for_training_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "live_real_allowed": False,
        "reload_performed": False,
        "order_actions_performed": False,
        "config_mutation_performed": False,
        "reason_codes": [
            "HYPOTHESIS_BRANCH_CLOSED_NO_GO",
            "FINAL_25F_BRANCH_CLOSED_NO_GO",
            "PRIMARY_TERMINAL_AUDIT_BLOCK_CONFIRMED",
            "COMPANION_TERMINAL_AUDIT_BLOCK_CONFIRMED",
            "NO_TRAINING_PAPER_LIVE_APPROVALS_DETECTED",
        ],
    }


def _registry() -> list[ResearchHypothesisBacklogItem]:
    return [
        ResearchHypothesisBacklogItem(
            hypothesis_id="HYP-001",
            title="Higher timeframe trend following",
            status="BLOCKED",
            priority=10,
            acceptance_metrics={"status": "blocked"},
        ),
        ResearchHypothesisBacklogItem(
            hypothesis_id="HYP-002",
            title="Futures funding/open-interest trend exhaustion",
            status="REGISTERED",
            priority=20,
            acceptance_metrics={"status": "closed_by_25h"},
        ),
        ResearchHypothesisBacklogItem(
            hypothesis_id="HYP-003",
            title="Regime-filtered volatility expansion breakout",
            status="REGISTERED",
            family="volatility_breakout",
            priority=30,
            acceptance_metrics={"min_signal_count": 35, "min_profit_factor": 1.2},
        ),
    ]


def test_extract_closure_evidence_from_25h_pack() -> None:
    evidence = extract_closure_evidence([("25h.json", _closure_25h())])
    assert evidence is not None
    assert evidence.hypothesis_id == "HYP-002"
    assert evidence.decision == "FUTURES_BRANCH_CLOSURE_CONFIRMED"
    assert evidence.final_25f_decision == "BRANCH_CLOSED_NO_GO"
    assert evidence.approvals_detected is False


def test_backlog_advancement_selects_next_hypothesis_after_25h_closure() -> None:
    report = build_research_backlog_advancement_gate([("25h.json", _closure_25h())], backlog=_registry())
    assert report.decision == "NEXT_HYPOTHESIS_SELECTED"
    assert report.selected_next_hypothesis_id == "HYP-003"
    assert report.approved_for_research_candidate is True
    assert report.approved_for_training_candidate is False
    assert report.approved_for_paper_candidate is False
    assert report.approved_for_live_real is False
    assert "HYPOTHESIS_CLOSURE_EVIDENCE_CONFIRMED" in report.reason_codes
    assert "NEXT_HYPOTHESIS_SELECTED" in report.reason_codes
    h2 = next(item for item in report.backlog if item.hypothesis_id == "HYP-002")
    assert h2.status == "CLOSED_NO_GO"


def test_backlog_advancement_blocks_when_closure_pack_missing() -> None:
    report = build_research_backlog_advancement_gate([], backlog=_registry())
    assert report.decision == "BACKLOG_ADVANCEMENT_BLOCK"
    assert "CLOSURE_EVIDENCE_PACK_MISSING" in report.reason_codes
    assert report.approved_for_research_candidate is False
    assert report.approved_for_live_real is False


def test_registry_loader_accepts_hypotheses_json(tmp_path: Path) -> None:
    registry_json = tmp_path / "registry.json"
    registry_json.write_text(
        json.dumps({
            "hypotheses": [
                {"id": "HYP-003", "title": "Volatility breakout", "status": "REGISTERED", "priority": 30, "acceptance_metrics": {"min_signal_count": 35}},
            ]
        }),
        encoding="utf-8",
    )
    items, source = load_backlog_from_registry(registry_json)
    assert source == str(registry_json)
    assert len(items) == 1
    assert items[0].hypothesis_id == "HYP-003"


def test_tool_writes_report_and_registry_snapshot(tmp_path: Path) -> None:
    closure = tmp_path / "25h.json"
    closure.write_text(json.dumps(_closure_25h()), encoding="utf-8")
    registry = tmp_path / "registry.json"
    registry.write_text(json.dumps({"hypotheses": [item.__dict__ for item in _registry()]}), encoding="utf-8")
    out_dir = tmp_path / "reports"
    result = subprocess.run(
        [
            sys.executable,
            "tools/run_research_backlog_advancement_4B436625I.py",
            "--input-json",
            str(closure),
            "--registry-json",
            str(registry),
            "--out-dir",
            str(out_dir),
            "--review-ok",
        ],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert "NEXT_HYPOTHESIS_SELECTED" in result.stdout
    report_files = list(out_dir.glob("4B436625I_research_backlog_advancement_*.json"))
    snapshot_files = list(out_dir.glob("4B436625I_proposed_research_registry_snapshot_*.json"))
    assert report_files
    assert snapshot_files
    payload = json.loads(report_files[0].read_text(encoding="utf-8"))
    assert payload["approved_for_paper_candidate"] is False
    assert payload["approved_for_live_real"] is False
