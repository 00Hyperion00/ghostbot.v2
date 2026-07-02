from __future__ import annotations

import json
from pathlib import Path

from tradebot.runtime_safety_lockdown import build_runtime_safety_lockdown


def write_config(root: Path, *, live_trading_armed: bool = False) -> None:
    package = root / "src" / "tradebot"
    package.mkdir(parents=True, exist_ok=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "config.py").write_text(
        f'''
from __future__ import annotations

class Settings:
    def to_dict(self, include_secrets: bool = False):
        return {{
            "execution_mode": "dry_run",
            "live_trading_armed": {str(live_trading_armed)},
            "live_real_double_confirm": False,
            "auto_trade_on_signal": False,
            "live_real_micro_canary_perform_network_submit": False,
            "paper_transition_operator_approved": False,
            "paper_transition_runtime_envelope_frozen": False,
            "paper_sandbox_candidate_unlock_issued": False,
            "paper_sandbox_dry_run_operator_lock_issued": False,
            "paper_sandbox_dry_run_execution_authorization_issued": False,
            "paper_sandbox_execution_preflight_authorization_issued": False,
            "paper_sandbox_operator_final_approval_issued": False,
            "first_paper_sandbox_canary_operator_approval_issued": False,
            "strict_config_validation": True,
            "runtime_lock_enabled": True,
            "promotion_gate_isolation_enabled": True,
            "paper_kill_switch_enabled": True,
            "paper_mode_runtime_guardrail_kill_switch_enabled": True,
            "paper_soak_evidence_window_kill_switch_enabled": True,
            "live_real_hard_block_required": True,
            "live_real_preflight_hard_submit_block_required": True,
            "live_real_final_hard_submit_block_required": True,
            "live_real_micro_canary_kill_switch_armed": True,
            "live_real_micro_canary_hard_caps_required": True,
            "live_real_micro_canary_reconciliation_emergency_stop_armed": True,
            "live_real_micro_canary_reconciliation_kill_switch_armed": True,
            "second_micro_canary_submit_gate_no_live_submit_required": True,
            "paper_mode_runtime_guardrail_no_exchange_submit_required": True,
            "paper_mode_runtime_guardrail_no_live_real_required": True,
            "paper_soak_evidence_window_no_exchange_submit_required": True,
            "paper_soak_evidence_window_no_live_real_required": True,
            "paper_mode_runtime_guardrail_exchange_submit_cap": 0,
            "paper_mode_runtime_guardrail_network_submit_cap": 0,
            "paper_mode_runtime_guardrail_order_action_cap": 0,
            "paper_soak_evidence_window_exchange_submit_cap": 0,
            "paper_soak_evidence_window_network_submit_cap": 0,
            "paper_soak_evidence_window_order_action_cap": 0,
            "paper_promotion_review_max_total_notional_usd": 0.0,
            "live_real_preflight_exchange_submit_cap": 0,
            "live_real_preflight_network_submit_cap": 0,
            "live_real_preflight_order_action_cap": 0,
            "live_real_preflight_max_total_notional_usd": 0.0,
            "live_real_final_exchange_submit_cap": 0,
            "live_real_final_network_submit_cap": 0,
            "live_real_final_order_action_cap": 0,
            "live_real_final_max_total_notional_usd": 0.0,
        }}
''',
        encoding="utf-8",
    )


def write_33c_report(root: Path) -> None:
    recovery = root / "reports" / "recovery"
    recovery.mkdir(parents=True, exist_ok=True)
    (recovery / "4B436633C_phase_chain_validator_20260702T000000Z_ready.json").write_text(
        json.dumps({"status": "READY", "decision": "PHASE_CHAIN_VALIDATOR_READY_SUBMIT_CAPABILITY_BLOCKED"}),
        encoding="utf-8",
    )


def test_runtime_safety_lockdown_ready_when_all_paths_blocked(tmp_path: Path) -> None:
    write_config(tmp_path)
    write_33c_report(tmp_path)
    report = build_runtime_safety_lockdown(tmp_path)
    assert report.status == "READY"
    assert report.central_submit_guard.passed is True
    assert report.operator_action_guard.passed is True
    assert report.runtime_overlay_guard.passed is True
    assert report.approved_for_exchange_submit is False
    assert report.safety_snapshot.exchange_submit_performed is False


def test_runtime_safety_lockdown_blocks_live_armed_config(tmp_path: Path) -> None:
    write_config(tmp_path, live_trading_armed=True)
    write_33c_report(tmp_path)
    report = build_runtime_safety_lockdown(tmp_path)
    assert report.status == "NOT_READY"
    assert report.central_submit_guard.passed is False
    assert report.central_submit_guard.live_real_submit_allowed is True
    assert any("live_trading_armed" in item for item in report.central_submit_guard.violations)


def test_destructive_endpoint_audit_detects_unguarded_submit_endpoint(tmp_path: Path) -> None:
    write_config(tmp_path)
    write_33c_report(tmp_path)
    api = tmp_path / "src" / "tradebot" / "api.py"
    api.write_text(
        '''
from fastapi import FastAPI
app = FastAPI()

@app.post("/submit-order")
def submit_order():
    return {"ok": True}
''',
        encoding="utf-8",
    )
    report = build_runtime_safety_lockdown(tmp_path)
    assert report.status == "NOT_READY"
    assert report.destructive_endpoint_audit.unguarded_destructive_endpoint_count == 1
