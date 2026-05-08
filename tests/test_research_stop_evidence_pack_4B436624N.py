from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tradebot.research_stop_evidence_pack import (
    RESEARCH_STOP_CONTRACT_VERSION,
    build_research_stop_evidence_pack,
    build_markdown_report,
)


def _report(phase: str, decision: str, reasons: list[str]) -> dict[str, object]:
    return {
        "contract_version": phase,
        "phase": phase,
        "decision": decision,
        "ok": decision != "BLOCK",
        "approved_for_training_candidate": False,
        "approved_for_research_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "live_real_allowed": False,
        "reload_performed": False,
        "config_mutation_performed": False,
        "order_actions_performed": False,
        "no_post_actions": True,
        "reason_codes": reasons,
        "recommendation": "synthetic recommendation",
    }


def test_research_stop_pack_confirms_no_go_from_terminal_blocks(tmp_path: Path) -> None:
    sources = []
    for phase in ("4B.4.3.6.6.24J", "4B.4.3.6.6.24K", "4B.4.3.6.6.24L", "4B.4.3.6.6.24M"):
        path = tmp_path / f"{phase.replace('.', '')}.json"
        report = _report(phase, "BLOCK", ["EXPECTED_EDGE_PROXY_LOW"])
        path.write_text(json.dumps(report), encoding="utf-8")
        sources.append((path, report))

    pack = build_research_stop_evidence_pack(sources, generated_at="2026-05-07T00:00:00+00:00")

    assert pack["contract_version"] == RESEARCH_STOP_CONTRACT_VERSION
    assert pack["decision"] == "RESEARCH_STOP_NO_GO"
    assert pack["approved_for_paper_candidate"] is False
    assert pack["approved_for_live_real"] is False
    assert "NO_EDGE_EVIDENCE_CONFIRMED" in pack["reason_codes"]
    assert pack["summary"]["terminal_no_go_block_count"] == 4
    assert pack["guardrails"]["post_requests_allowed"] is False
    assert len(pack["next_hypothesis_backlog"]) >= 3


def test_research_stop_pack_detects_live_approval_contradiction(tmp_path: Path) -> None:
    path = tmp_path / "4B436624M_bad.json"
    report = _report("4B.4.3.6.6.24M", "BLOCK", ["EDGE_EXPECTED_EDGE_LOW"])
    report["approved_for_live_real"] = True
    path.write_text(json.dumps(report), encoding="utf-8")

    pack = build_research_stop_evidence_pack([(path, report)], generated_at="2026-05-07T00:00:00+00:00")

    assert pack["decision"] == "RESEARCH_STOP_NO_GO"
    assert "LIVE_REAL_APPROVAL_DETECTED_IN_SOURCE_REPORT" in pack["reason_codes"]


def test_markdown_report_contains_phase_table(tmp_path: Path) -> None:
    path = tmp_path / "4B436624M.json"
    report = _report("4B.4.3.6.6.24M", "BLOCK", ["EDGE_EXPECTED_EDGE_LOW"])
    pack = build_research_stop_evidence_pack([(path, report)], generated_at="2026-05-07T00:00:00+00:00")

    markdown = build_markdown_report(pack)

    assert "# 4B.4.3.6.6.24N Research Stop" in markdown
    assert "## Phase Evidence" in markdown
    assert "4B.4.3.6.6.24M" in markdown
    assert "## Next Hypothesis Backlog" in markdown


def test_tool_writes_report_from_explicit_input_json(tmp_path: Path) -> None:
    source = tmp_path / "4B436624M_edge.json"
    source.write_text(json.dumps(_report("4B.4.3.6.6.24M", "BLOCK", ["EDGE_EXPECTED_EDGE_LOW"])), encoding="utf-8")
    out_dir = tmp_path / "reports"
    tool = Path(__file__).resolve().parents[1] / "tools" / "run_research_stop_evidence_pack_4B436624N.py"

    result = subprocess.run(
        [
            sys.executable,
            str(tool),
            "--input-json",
            str(source),
            "--out-dir",
            str(out_dir),
            "--review-ok",
        ],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 0
    assert "RESEARCH_STOP_NO_GO" in result.stdout
    assert list(out_dir.glob("4B436624N_research_stop_evidence_pack_*.json"))
    assert list(out_dir.glob("4B436624N_research_stop_evidence_pack_*.md"))


def test_tool_requires_review_ok(tmp_path: Path) -> None:
    source = tmp_path / "4B436624M_edge.json"
    source.write_text(json.dumps(_report("4B.4.3.6.6.24M", "BLOCK", ["EDGE_EXPECTED_EDGE_LOW"])), encoding="utf-8")
    tool = Path(__file__).resolve().parents[1] / "tools" / "run_research_stop_evidence_pack_4B436624N.py"

    result = subprocess.run(
        [sys.executable, str(tool), "--input-json", str(source)],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    assert result.returncode == 2
    assert "--review-ok is required" in result.stderr
