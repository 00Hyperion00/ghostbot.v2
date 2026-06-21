from __future__ import annotations

import json
from pathlib import Path

from tradebot.config import Settings
from tradebot.first_paper_sandbox_canary_submit_gate import (
    APPROVAL_REQUIRED_DECISION,
    READY_DECISION,
    build_first_paper_sandbox_canary_submit_gate_snapshot,
)


def source_30p_ready() -> dict[str, object]:
    return {
        "contract_version": "4B.4.3.6.6.30P",
        "decision": "PAPER_SANDBOX_SUBMIT_ARM_PREFLIGHT_READY_SUBMIT_STILL_BLOCKED_NO_LIVE_REAL",
        "approved_for_paper_sandbox_submit_arm_preflight": True,
        "api_mode_ok": True,
        "endpoint_ok": True,
        "min_notional_ok": True,
        "lot_size_ok": True,
        "risk_caps_ok": True,
        "kill_switch_ok": True,
        "approved_for_paper_candidate": True,
        "approved_for_exchange_submit": False,
        "approved_for_live_real": False,
        "submit_still_blocked": True,
        "exchange_submit_performed": False,
        "trading_action_performed": False,
        "order_actions_performed": False,
    }


def test_default_requires_explicit_operator_approval(tmp_path: Path) -> None:
    payload = build_first_paper_sandbox_canary_submit_gate_snapshot(
        Settings(),
        source_30p_ready(),
        intent_path=tmp_path / "intent.json",
        now_ms=1_800_000_000_000,
    )
    assert payload["decision"] == APPROVAL_REQUIRED_DECISION
    assert payload["approved_for_first_paper_sandbox_canary_submit_gate"] is False
    assert payload["approved_for_exchange_submit"] is False
    assert payload["approved_for_live_real"] is False


def test_ready_builds_single_order_intent_submit_guarded(tmp_path: Path) -> None:
    intent_path = tmp_path / "intent.json"
    payload = build_first_paper_sandbox_canary_submit_gate_snapshot(
        Settings(),
        source_30p_ready(),
        operator_id="operator-30q",
        approval_token="APPROVE_FIRST_PAPER_SANDBOX_CANARY_SUBMIT_GATE",
        issue_canary_approval=True,
        intent_path=intent_path,
        write_intent=True,
        now_ms=1_800_000_001_000,
    )
    assert payload["decision"] == READY_DECISION
    assert payload["approved_for_single_sandbox_order_intent"] is True
    assert payload["single_sandbox_order_intent_built"] is True
    assert payload["canary_order_intent_written"] is True
    intent = json.loads(intent_path.read_text(encoding="utf-8"))
    assert intent["submit_to_exchange"] is False
    assert intent["exchange_submit_performed"] is False
    assert intent["network_submit_attempted"] is False


def test_ready_keeps_exchange_submit_and_live_real_blocked(tmp_path: Path) -> None:
    payload = build_first_paper_sandbox_canary_submit_gate_snapshot(
        Settings(),
        source_30p_ready(),
        operator_id="operator-30q",
        approval_token="APPROVE_FIRST_PAPER_SANDBOX_CANARY_SUBMIT_GATE",
        issue_canary_approval=True,
        intent_path=tmp_path / "intent.json",
        write_intent=True,
        now_ms=1_800_000_002_000,
    )
    assert payload["approved_for_exchange_submit"] is False
    assert payload["approved_for_live_real"] is False
    assert payload["submit_still_blocked"] is True
    assert payload["exchange_submit_path_guarded"] is True
    assert payload["trading_action_performed"] is False


def test_blocks_source_with_exchange_submit_enabled(tmp_path: Path) -> None:
    source = source_30p_ready()
    source["approved_for_exchange_submit"] = True
    payload = build_first_paper_sandbox_canary_submit_gate_snapshot(
        Settings(),
        source,
        operator_id="operator-30q",
        approval_token="APPROVE_FIRST_PAPER_SANDBOX_CANARY_SUBMIT_GATE",
        issue_canary_approval=True,
        intent_path=tmp_path / "intent.json",
        write_intent=True,
        now_ms=1_800_000_003_000,
    )
    assert payload["decision"] != READY_DECISION
    assert payload["approved_for_exchange_submit"] is False
    assert not (tmp_path / "intent.json").exists()


def test_blocks_min_notional_failure(tmp_path: Path) -> None:
    settings = Settings(first_paper_sandbox_canary_quote_notional_usd=2.0, first_paper_sandbox_canary_min_notional_usd=5.0)
    payload = build_first_paper_sandbox_canary_submit_gate_snapshot(
        settings,
        source_30p_ready(),
        operator_id="operator-30q",
        approval_token="APPROVE_FIRST_PAPER_SANDBOX_CANARY_SUBMIT_GATE",
        issue_canary_approval=True,
        intent_path=tmp_path / "intent.json",
        write_intent=True,
        now_ms=1_800_000_004_000,
    )
    assert payload["decision"] != READY_DECISION
    assert payload["min_notional_gate"] is False
    assert payload["approved_for_exchange_submit"] is False
