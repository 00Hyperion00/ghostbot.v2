from __future__ import annotations

import json
from pathlib import Path

from tradebot.phase_chain_validator import (
    build_phase_chain_validator_report,
    extract_phase_token,
    phase_sort_key,
    write_phase_chain_validator_report,
)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def create_minimal_repo(root: Path) -> list[str]:
    write(root / "src" / "tradebot" / "__init__.py", "")
    write(
        root / "src" / "tradebot" / "config.py",
        """
from __future__ import annotations
from dataclasses import dataclass, asdict

@dataclass
class Settings:
    execution_mode: str = 'dry_run'
    market_type: str = 'spot_demo'
    live_trading_armed: bool = False
    live_real_double_confirm: bool = False
    auto_trade_on_signal: bool = False
    live_real_micro_canary_perform_network_submit: bool = False
    paper_transition_operator_approved: bool = False
    paper_sandbox_candidate_unlock_issued: bool = False
    paper_sandbox_operator_final_approval_issued: bool = False
    strict_config_validation: bool = True
    runtime_lock_enabled: bool = True
    promotion_gate_isolation_enabled: bool = True
    live_real_hard_block_required: bool = True
    live_real_preflight_hard_submit_block_required: bool = True
    live_real_final_hard_submit_block_required: bool = True
    live_real_micro_canary_hard_caps_required: bool = True
    second_micro_canary_submit_gate_no_live_submit_required: bool = True
    paper_mode_runtime_guardrail_no_exchange_submit_required: bool = True
    paper_mode_runtime_guardrail_no_live_real_required: bool = True
    live_real_preflight_network_submit_cap: int = 0
    live_real_final_network_submit_cap: int = 0
    live_real_final_exchange_submit_cap: int = 0
    paper_mode_runtime_guardrail_exchange_submit_cap: int = 0
    paper_mode_runtime_guardrail_network_submit_cap: int = 0

    def to_dict(self, include_secrets: bool = False) -> dict[str, object]:
        return asdict(self)
""",
    )
    required = ["4B436633A", "4B436633B"]
    for token in required:
        write(root / "tools" / f"apply_{token}_sample.py", "# sample\n")
        write(root / "tools" / f"check_{token}_sample.py", "# sample\n")
        write(root / "tools" / f"run_{token}_sample.py", "# sample\n")
        write(root / "tests" / f"test_{token}_sample.py", "def test_ok():\n    assert True\n")
        write(root / "docs" / f"DOC_{token}.md", "# doc\n")
        write(root / f"README_APPLY_{token}.txt", "apply\n")
        write(
            root / "reports" / "recovery" / f"{token}_sample_20260702T000000Z_ready.json",
            json.dumps({"status": "READY", "phase": token}),
        )
    write(
        root / "reports" / "recovery" / "4B436633B_canonical_evidence_phase_hygiene_20260702T000001Z_ready.json",
        json.dumps({"status": "READY", "decision": "CANONICAL_EVIDENCE_PHASE_HYGIENE_READY_NO_TRADING_ACTIONS"}),
    )
    return required


def test_phase_token_extraction_and_sorting() -> None:
    assert extract_phase_token("tools/run_4B436630P_paper_sandbox.py") == "4B436630P"
    assert extract_phase_token("reports/4B436632B_H1_snapshot.json") == "4B436632B_H1"
    assert phase_sort_key("4B436630A") < phase_sort_key("4B436630B") < phase_sort_key("4B436633A")


def test_phase_chain_validator_ready_for_minimal_chain(tmp_path: Path) -> None:
    required = create_minimal_repo(tmp_path)
    report = build_phase_chain_validator_report(tmp_path, required_phase_tokens=required)
    assert report.status == "READY"
    assert report.canonical_phase_dag.complete is True
    assert report.evidence_source_resolution.complete is True
    assert report.submit_capability_assertion.passed is True
    assert report.submit_capability_assertion.exchange_submit_allowed is False
    assert report.submit_capability_assertion.network_submit_allowed is False


def test_phase_chain_validator_writes_report(tmp_path: Path) -> None:
    required = create_minimal_repo(tmp_path)
    output = write_phase_chain_validator_report(
        tmp_path,
        reports_dir=tmp_path / "reports" / "recovery",
        required_phase_tokens=required,
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["patch_id"] == "4B436633C"
    assert payload["status"] == "READY"
    assert payload["submit_capability_assertion"]["approved_for_live_real"] is False
