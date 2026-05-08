from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tradebot.research_hypothesis_registry import (
    build_research_hypothesis_registry,
    default_research_hypotheses,
    load_hypotheses_json,
    write_default_registry_files,
)


def test_default_registry_is_ready_but_blocks_paper_and_live() -> None:
    report = build_research_hypothesis_registry(default_research_hypotheses())

    assert report["decision"] == "REGISTRY_READY"
    assert report["approved_for_research_candidate"] is True
    assert report["approved_for_training_candidate"] is False
    assert report["approved_for_paper_candidate"] is False
    assert report["approved_for_live_real"] is False
    assert report["post_requests_allowed"] is False
    assert report["selected_next_hypothesis_id"] == "HYP-001"


def test_invalid_live_auto_approval_blocks_registry() -> None:
    hypotheses = default_research_hypotheses()
    raw = {
        **hypotheses[0].__dict__,
        "symbols": list(hypotheses[0].symbols),
        "timeframes": list(hypotheses[0].timeframes),
        "data_requirements": list(hypotheses[0].data_requirements),
        "acceptance_metrics": hypotheses[0].acceptance_metrics.__dict__,
        "guardrails": {**hypotheses[0].guardrails, "live_allowed_if_pass": True},
    }
    from tradebot.research_hypothesis_registry import ResearchHypothesis

    report = build_research_hypothesis_registry([ResearchHypothesis.from_mapping(raw)])

    assert report["decision"] == "BLOCK"
    assert report["approved_for_live_real"] is False
    assert "NO_VALID_RESEARCH_HYPOTHESIS_REGISTERED" in report["reason_codes"]
    assert "LIVE_AUTO_APPROVAL_FORBIDDEN" in report["hypotheses"][0]["reason_codes"]


def test_missing_cost_and_oos_blocks_hypothesis(tmp_path: Path) -> None:
    payload = {
        "hypotheses": [
            {
                "hypothesis_id": "BAD-001",
                "name": "Bad hypothesis",
                "status": "PROPOSED",
                "market": "spot",
                "symbols": ["ETHUSDT"],
                "timeframes": ["1m"],
                "strategy_family": "unsafe",
                "acceptance_metrics": {
                    "min_net_edge_bps": 0,
                    "min_profit_factor": 1.0,
                    "min_trade_count": 10,
                    "max_drawdown_pct": 50,
                    "oos_required": False,
                    "fee_slippage_included": False,
                },
            }
        ]
    }
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    report = build_research_hypothesis_registry(load_hypotheses_json(path))
    reasons = set(report["hypotheses"][0]["reason_codes"])

    assert report["decision"] == "BLOCK"
    assert "ACCEPTANCE_MIN_NET_EDGE_NOT_POSITIVE" in reasons
    assert "OOS_VALIDATION_REQUIRED" in reasons
    assert "FEE_SLIPPAGE_MUST_BE_INCLUDED" in reasons


def test_write_default_registry_files_round_trips(tmp_path: Path) -> None:
    paths = write_default_registry_files(tmp_path)
    assert Path(paths["json"]).exists()
    assert Path(paths["yaml"]).exists()

    hypotheses = load_hypotheses_json(paths["json"])
    report = build_research_hypothesis_registry(hypotheses)

    assert len(hypotheses) >= 5
    assert report["decision"] == "REGISTRY_READY"


def test_tool_writes_default_registry_and_report(tmp_path: Path) -> None:
    tool = Path(__file__).resolve().parents[1] / "tools" / "run_research_hypothesis_registry_4B436624O.py"
    result = subprocess.run(
        [
            sys.executable,
            str(tool),
            "--out-dir",
            str(tmp_path / "reports"),
            "--config-dir",
            str(tmp_path / "config"),
            "--write-default-registry",
            "--review-ok",
        ],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert "REGISTRY_READY" in result.stdout
    assert list((tmp_path / "reports").glob("4B436624O_research_hypothesis_registry_*.json"))
    assert (tmp_path / "config" / "research_hypotheses_4B436624O.json").exists()
