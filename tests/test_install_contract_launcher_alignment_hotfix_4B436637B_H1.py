from __future__ import annotations

import json
from pathlib import Path

from tradebot.install_contract_launcher_alignment_hotfix import (
    READY_DECISION,
    apply_bat_launcher_hotfix,
    evaluate,
    normalize_bat_launcher_text,
)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def seed_repo(root: Path) -> Path:
    write(root / "pyproject.toml", '''[project]
name = "tradebot"
dependencies = [
  "fastapi>=0.1",
  "pydantic>=2",
]
''')
    write(root / "requirements.txt", "# 4B436637B generated\nfastapi>=0.1\npydantic>=2\n")
    write(root / "README.md", "## Install Contract\nUse pyproject.toml and requirements.txt.\n")
    write(root / "run_dashboard.ps1", "# install contract\npython -m pip install -r requirements.txt\n")
    write(root / "run_dashboard.bat", "@echo off\npip install -r requirements.txt\npython -m tradebot.cockpit.app\n")
    write(root / "start_dashboard.bat", "@echo off\npy -m pip install -r requirements.txt\npython -m tradebot.cockpit.app\n")
    reports = root / "reports" / "recovery"
    source = {
        "status": "NOT_READY",
        "decision": "INSTALL_CONTRACT_ALIGNMENT_NOT_READY_NO_SUBMIT_LOCKED",
        "source_37a_complete": True,
        "source_37a_status": "SOURCE_37A_READY",
        "requirements_pyproject_aligned": True,
        "requirements_pyproject_mismatch_count": 0,
        "readme_contract_marker_present": True,
        "launcher_misaligned_count": 2,
        "approved_for_exchange_submit": False,
        "approved_for_live_real": False,
        "approved_for_paper_transition": False,
        "approved_for_runtime_overlay": False,
        "network_request_performed": False,
        "exchange_submit_performed": False,
        "order_submit_performed": False,
    }
    path = reports / "4B436637B_install_contract_alignment_20260703T124058Z_not_ready.json"
    write(path, json.dumps(source))
    return reports


def test_normalize_bat_launcher_text_rewrites_pip_variants() -> None:
    text = "@echo off\npip install -r requirements.txt\npy -m tradebot\n"
    new_text, changed = normalize_bat_launcher_text(text)
    assert changed is True
    assert "python -m pip install -r requirements.txt" in new_text.lower()
    assert "4B436637B-H1 INSTALL CONTRACT" in new_text


def test_hotfix_closes_p0_1_after_launcher_normalization(tmp_path: Path) -> None:
    reports = seed_repo(tmp_path)
    before = evaluate(tmp_path, reports_dir=reports, write=False)
    assert before["status"] == "NOT_READY"
    apply_result = apply_bat_launcher_hotfix(tmp_path)
    assert apply_result["bat_launcher_normalization_performed"] is True
    after = evaluate(tmp_path, reports_dir=reports, write=True)
    assert after["status"] == "READY"
    assert after["decision"] == READY_DECISION
    assert after["launcher_misaligned_count"] == 0
    assert after["p0_install_contract_alignment_closed"] is True
    assert after["p0_hardening_closed_gap_count_after_37b_h1"] == 1
    assert after["p0_hardening_open_gap_count_after_37b_h1"] == 9
    assert after["exchange_submit_allowed"] is False
    assert after["network_submit_allowed"] is False
    assert after["next_phase_unlock_allowed"] is False


def test_source_37b_missing_fails_closed(tmp_path: Path) -> None:
    reports = seed_repo(tmp_path)
    for path in reports.glob("4B436637B_install_contract_alignment_*_not_ready.json"):
        path.unlink()
    apply_bat_launcher_hotfix(tmp_path)
    result = evaluate(tmp_path, reports_dir=reports, write=False)
    assert result["status"] == "NOT_READY"
    assert result["source_37b_status"] == "SOURCE_37B_MISSING"
    assert result["exchange_submit_allowed"] is False
    assert result["paper_transition_blocked"] is True


def test_source_37b_safety_violation_fails_closed(tmp_path: Path) -> None:
    reports = seed_repo(tmp_path)
    source_path = next(reports.glob("4B436637B_install_contract_alignment_*_not_ready.json"))
    payload = json.loads(source_path.read_text(encoding="utf-8"))
    payload["network_request_performed"] = True
    source_path.write_text(json.dumps(payload), encoding="utf-8")
    apply_bat_launcher_hotfix(tmp_path)
    result = evaluate(tmp_path, reports_dir=reports, write=False)
    assert result["status"] == "NOT_READY"
    assert result["source_37b_safety_violation_count"] == 1
    assert "network_request_performed" in result["source_37b_safety_violations"]
    assert result["exchange_submit_allowed"] is False
