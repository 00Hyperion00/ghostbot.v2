from __future__ import annotations

import json
from pathlib import Path

from tradebot.project_recovery_baseline import (
    READY_DECISION,
    build_recovery_baseline,
    run_project_recovery_baseline,
)


def _write_minimal_repo(root: Path) -> None:
    (root / "src" / "tradebot").mkdir(parents=True)
    (root / "tools").mkdir()
    (root / "tests").mkdir()
    (root / "docs").mkdir()
    (root / "reports" / "production_hardening").mkdir(parents=True)
    (root / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    (root / "README.md").write_text("# x\n", encoding="utf-8")
    (root / "src" / "tradebot" / "__init__.py").write_text("", encoding="utf-8")
    (root / "src" / "tradebot" / "config.py").write_text(
        "from dataclasses import asdict, dataclass\n"
        "@dataclass\n"
        "class Settings:\n"
        "    strict_config_validation: bool = True\n"
        "    runtime_lock_enabled: bool = True\n"
        "    sqlite_wal_enabled: bool = True\n"
        "    promotion_gate_isolation_enabled: bool = True\n"
        "    paper_kill_switch_enabled: bool = True\n"
        "    paper_mode_runtime_guardrail_kill_switch_enabled: bool = True\n"
        "    paper_soak_evidence_window_kill_switch_enabled: bool = True\n"
        "    live_real_preflight_hard_submit_block_required: bool = True\n"
        "    live_real_final_hard_submit_block_required: bool = True\n"
        "    live_real_micro_canary_kill_switch_armed: bool = True\n"
        "    live_real_micro_canary_hard_caps_required: bool = True\n"
        "    live_real_micro_canary_reconciliation_emergency_stop_armed: bool = True\n"
        "    live_real_micro_canary_reconciliation_kill_switch_armed: bool = True\n"
        "    live_real_hard_block_required: bool = True\n"
        "    live_trading_armed: bool = False\n"
        "    live_real_double_confirm: bool = False\n"
        "    auto_trade_on_signal: bool = False\n"
        "    paper_transition_operator_approved: bool = False\n"
        "    paper_transition_runtime_envelope_frozen: bool = False\n"
        "    paper_sandbox_dry_run_operator_lock_issued: bool = False\n"
        "    paper_sandbox_operator_final_approval_issued: bool = False\n"
        "    paper_sandbox_candidate_unlock_issued: bool = False\n"
        "    paper_sandbox_execution_preflight_authorization_issued: bool = False\n"
        "    paper_sandbox_dry_run_execution_authorization_issued: bool = False\n"
        "    first_paper_sandbox_canary_operator_approval_issued: bool = False\n"
        "    live_real_micro_canary_perform_network_submit: bool = False\n"
        "    api_key: str = ''\n"
        "    api_secret: str = ''\n"
        "    api_auth_token: str = ''\n"
        "    def to_dict(self, include_secrets: bool = False):\n"
        "        payload = asdict(self)\n"
        "        if not include_secrets:\n"
        "            payload['api_key'] = '[REDACTED]' if self.api_key else ''\n"
        "            payload['api_secret'] = '[REDACTED]' if self.api_secret else ''\n"
        "            payload['api_auth_token'] = '[REDACTED]' if self.api_auth_token else ''\n"
        "        return payload\n",
        encoding="utf-8",
    )
    (root / "tools" / "apply_4B436629A_demo.py").write_text("# demo\n", encoding="utf-8")
    (root / "tools" / "check_4B436629A_demo.py").write_text("# demo\n", encoding="utf-8")
    (root / "tools" / "run_4B436629A_demo.py").write_text("# demo\n", encoding="utf-8")
    (root / "tools" / "rollback_4B436629A_demo.py").write_text("# demo\n", encoding="utf-8")
    (root / "tests" / "test_demo_4B436629A.py").write_text("def test_demo(): assert True\n", encoding="utf-8")
    (root / "docs" / "DEMO_4B436629A.md").write_text("# demo\n", encoding="utf-8")
    (root / "reports" / "production_hardening" / "4B436629A_demo_20260101T000000Z_ready.json").write_text(
        json.dumps({"status": "READY"}),
        encoding="utf-8",
    )


def test_recovery_baseline_ready_for_minimal_safe_repo(tmp_path: Path, monkeypatch) -> None:
    _write_minimal_repo(tmp_path)
    monkeypatch.syspath_prepend(str(tmp_path / "src"))

    report = build_recovery_baseline(tmp_path)

    assert report.status == "READY"
    assert report.decision == READY_DECISION
    assert report.repo_inventory.complete is True
    assert report.phase_inventory.complete is True
    assert report.evidence_inventory.complete is True
    assert report.config_inventory.complete is True
    assert report.safety_snapshot.complete is True
    assert report.approved_for_live_real is False
    assert report.approved_for_paper_transition is False
    assert report.approved_for_exchange_submit is False
    assert report.approved_for_runtime_overlay is False
    assert report.safety_snapshot.trading_action_performed is False
    assert report.safety_snapshot.training_performed is False
    assert report.safety_snapshot.reload_performed is False


def test_recovery_baseline_blocks_live_network_submit_default(tmp_path: Path, monkeypatch) -> None:
    _write_minimal_repo(tmp_path)
    config_path = tmp_path / "src" / "tradebot" / "config.py"
    config_path.write_text(
        config_path.read_text(encoding="utf-8").replace(
            "live_real_micro_canary_perform_network_submit: bool = False",
            "live_real_micro_canary_perform_network_submit: bool = True",
        ),
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path / "src"))

    report = build_recovery_baseline(tmp_path)

    assert report.status == "NOT_READY"
    assert report.safety_snapshot.live_real_allowed is True
    assert report.approved_for_live_real is False
    assert report.approved_for_exchange_submit is False


def test_run_project_recovery_baseline_writes_report(tmp_path: Path, monkeypatch) -> None:
    _write_minimal_repo(tmp_path)
    monkeypatch.syspath_prepend(str(tmp_path / "src"))

    report, path = run_project_recovery_baseline(tmp_path, tmp_path / "reports" / "recovery")

    assert report.status == "READY"
    assert path.is_file()
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["status"] == "READY"
    assert payload["approved_for_live_real"] is False
