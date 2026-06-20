from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def repo_root() -> Path:
    start = Path.cwd().resolve()
    for item in [start, *start.parents]:
        if (item / "src" / "tradebot").is_dir() and (item / "tools").is_dir():
            return item
    return start


def sample_30k_ready() -> dict[str, Any]:
    return {
        "contract_version": "4B.4.3.6.6.30K",
        "decision": "PAPER_SANDBOX_OPERATOR_FINAL_GO_NO_GO_GATE_READY_PAPER_CANDIDATE_STILL_BLOCKED_NO_LIVE_REAL",
        "approved_for_paper_sandbox_operator_final_go_no_go_gate": True,
        "approved_for_operator_final_paper_sandbox_approval": True,
        "approved_for_kill_switch_caps_checklist": True,
        "approved_for_paper_sandbox_go_no_go_candidate": True,
        "approved_for_paper_sandbox_dry_run_execution": False,
        "approved_for_exchange_submit": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "paper_order_enablement_still_blocked": True,
        "exchange_submit_performed": False,
        "trading_action_performed": False,
        "order_actions_performed": False,
    }


def test_30l_default_requires_explicit_unlock() -> None:
    from tradebot.config import Settings
    from tradebot.paper_sandbox_candidate_unlock_gate import UNLOCK_REQUIRED_DECISION, build_paper_sandbox_candidate_unlock_snapshot

    payload = build_paper_sandbox_candidate_unlock_snapshot(Settings(), sample_30k_ready(), now_ms=1_800_000_000_000)
    assert payload["decision"] == UNLOCK_REQUIRED_DECISION
    assert payload["approved_for_paper_sandbox_candidate_unlock_gate"] is False
    assert payload["approved_for_paper_candidate"] is False
    assert payload["approved_for_exchange_submit"] is False
    assert payload["approved_for_live_real"] is False


def test_30l_explicit_unlock_ready_candidate_only() -> None:
    from tradebot.config import Settings
    from tradebot.paper_sandbox_candidate_unlock_gate import READY_DECISION, build_paper_sandbox_candidate_unlock_snapshot

    payload = build_paper_sandbox_candidate_unlock_snapshot(
        Settings(),
        sample_30k_ready(),
        operator_id="operator-30l",
        unlock_token="UNLOCK_PAPER_SANDBOX_CANDIDATE",
        issue_candidate_unlock=True,
        now_ms=1_800_000_000_000,
    )
    assert payload["decision"] == READY_DECISION
    assert payload["approved_for_paper_sandbox_candidate_unlock_gate"] is True
    assert payload["approved_for_explicit_paper_candidate_unlock"] is True
    assert payload["approved_for_sandbox_only_order_enablement_preflight"] is True
    assert payload["approved_for_paper_candidate"] is True
    assert payload["approved_for_paper_sandbox_candidate"] is True
    assert payload["approved_for_paper_sandbox_dry_run_execution"] is False
    assert payload["approved_for_exchange_submit"] is False
    assert payload["approved_for_live_real"] is False
    assert payload["paper_order_enablement_still_blocked"] is True
    assert payload["exchange_submit_performed"] is False
    assert payload["trading_action_performed"] is False


def test_30l_blocks_bad_source_with_exchange_submit() -> None:
    from tradebot.config import Settings
    from tradebot.paper_sandbox_candidate_unlock_gate import SOURCE_30K_REQUIRED_DECISION, build_paper_sandbox_candidate_unlock_snapshot

    source = sample_30k_ready()
    source["approved_for_exchange_submit"] = True
    payload = build_paper_sandbox_candidate_unlock_snapshot(
        Settings(),
        source,
        operator_id="operator-30l",
        unlock_token="UNLOCK_PAPER_SANDBOX_CANDIDATE",
        issue_candidate_unlock=True,
        now_ms=1_800_000_000_000,
    )
    assert payload["decision"] == SOURCE_30K_REQUIRED_DECISION
    assert payload["approved_for_paper_candidate"] is False
    assert payload["approved_for_exchange_submit"] is False
    assert payload["exchange_submit_performed"] is False


def test_30l_checker_cli_ok() -> None:
    root = repo_root()
    checker = root / "tools/check_4B436630L_paper_sandbox_candidate_unlock_gate.py"
    if not checker.exists():
        return
    proc = subprocess.run([sys.executable, str(checker), "--once-json"], cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=300)
    assert proc.returncode == 0, proc.stdout[-4000:] + proc.stderr[-4000:]
    payload = json.loads(proc.stdout)
    assert payload["ok"] is True
    assert payload["checks"]["exchange_submit_still_blocked"] is True
    assert payload["checks"]["live_real_still_blocked"] is True
