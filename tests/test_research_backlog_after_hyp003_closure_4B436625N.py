from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tradebot.research_backlog_after_hyp003_closure import build_research_backlog_after_hyp003_closure


def _closure_25m() -> dict:
    return {
        "contract_version": "4B.4.3.6.6.25M",
        "decision": "HYP003_BRANCH_CLOSURE_CONFIRMED",
        "hypothesis_id": "HYP-003",
        "branch_name": "regime_specific_strategy_family",
        "approved_for_research_candidate": False,
        "approved_for_training_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "live_real_allowed": False,
        "reload_performed": False,
        "order_actions_performed": False,
        "config_mutation_performed": False,
        "reason_codes": [
            "HYP003_EXPLORATION_PASS_CONFIRMED",
            "HYP003_ROBUSTNESS_BLOCK_CONFIRMED",
            "NO_HYP003_ALTERNATE_CANDIDATE_AVAILABLE_CONFIRMED",
            "NO_TRAINING_PAPER_LIVE_APPROVALS_DETECTED",
        ],
    }


def test_25n_selects_next_hypothesis_after_hyp003_closure() -> None:
    report = build_research_backlog_after_hyp003_closure(_closure_25m())
    assert report["decision"] == "NEXT_HYPOTHESIS_SELECTED"
    assert report["closed_hypothesis_id"] == "HYP-003"
    assert report["selected_next_hypothesis_id"] == "HYP-004"
    assert report["approved_for_research_candidate"] is True
    assert report["approved_for_training_candidate"] is False
    assert report["approved_for_paper_candidate"] is False
    assert report["approved_for_live_real"] is False
    hyp003 = next(item for item in report["registry_snapshot"]["hypotheses"] if item["hypothesis_id"] == "HYP-003")
    assert hyp003["status"] == "CLOSED_NO_GO"


def test_25n_blocks_when_hyp003_closure_missing() -> None:
    bad = _closure_25m()
    bad["decision"] = "HYP003_BRANCH_CLOSURE_RECOMMENDED"
    report = build_research_backlog_after_hyp003_closure(bad)
    assert report["decision"] == "BACKLOG_ADVANCEMENT_BLOCKED"
    assert "HYP003_CLOSURE_NOT_CONFIRMED" in report["reason_codes"]
    assert report["approved_for_research_candidate"] is False


def test_25n_uses_registry_next_hypothesis_priority() -> None:
    registry = {
        "hypotheses": [
            {"hypothesis_id": "HYP-003", "title": "Regime", "branch_name": "regime_specific_strategy_family", "priority": 30, "status": "REGISTERED"},
            {"hypothesis_id": "HYP-010", "title": "Late idea", "branch_name": "late_idea", "priority": 100, "status": "REGISTERED"},
            {"hypothesis_id": "HYP-004", "title": "Custom next", "branch_name": "custom_next", "priority": 40, "status": "REGISTERED"},
        ]
    }
    report = build_research_backlog_after_hyp003_closure(_closure_25m(), registry=registry)
    assert report["selected_next_hypothesis_id"] == "HYP-004"
    assert report["selected_next_hypothesis_title"] == "Custom next"


def test_25n_exhausted_when_no_selectable_hypothesis() -> None:
    registry = {"hypotheses": [{"hypothesis_id": "HYP-003", "priority": 30, "status": "CLOSED_NO_GO"}]}
    report = build_research_backlog_after_hyp003_closure(_closure_25m(), registry=registry)
    assert report["decision"] == "RESEARCH_BACKLOG_EXHAUSTED"
    assert report["selected_next_hypothesis_id"] is None


def test_tool_writes_report_and_registry_snapshot(tmp_path: Path) -> None:
    closure_path = tmp_path / "25m.json"
    closure_path.write_text(json.dumps(_closure_25m()), encoding="utf-8")
    out_dir = tmp_path / "reports"
    result = subprocess.run(
        [
            sys.executable,
            "tools/run_research_backlog_after_hyp003_closure_4B436625N.py",
            "--input-json",
            str(closure_path),
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
    assert list(out_dir.glob("4B436625N_research_backlog_after_hyp003_closure_*.json"))
    snapshots = list(out_dir.glob("4B436625N_proposed_research_registry_snapshot_*.json"))
    assert snapshots
    snapshot = json.loads(snapshots[0].read_text(encoding="utf-8"))
    assert snapshot["selected_next_hypothesis_id"] == "HYP-004"
