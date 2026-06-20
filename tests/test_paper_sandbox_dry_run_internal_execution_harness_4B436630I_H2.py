from __future__ import annotations

from pathlib import Path

from tools.check_4B436630I_H2_internal_execution_harness_acceptance_pytest_compat_hotfix import repo_root, run_check


def test_30i_h2_h1_pytest_compat_hotfix_ok() -> None:
    report = run_check(repo_root())
    assert report["ok"] is True, report["checks"]
    assert report["checks"]["h1_checker_cli_ok"] is True
    assert report["checks"]["h1_test_uses_cli_checker"] is True


def test_30i_h2_preserves_fail_closed_risk_flags() -> None:
    report = run_check(repo_root())
    assert report["checks"]["exchange_submit_still_blocked"] is True
    assert report["checks"]["paper_execution_still_blocked"] is True
    assert report["checks"]["paper_candidate_still_blocked"] is True
    assert report["checks"]["live_real_still_blocked"] is True
    assert report["exchange_submit_performed"] is False
    assert report["trading_action_performed"] is False


def test_30i_h2_overwrites_h1_test_with_cli_safe_variant() -> None:
    root = repo_root()
    text = (root / Path("tests/test_paper_sandbox_dry_run_internal_execution_harness_4B436630I_H1.py")).read_text(encoding="utf-8")
    assert "run_h1_checker_cli" in text
    assert "subprocess.run" in text
    assert "tools/check_4B436630I_H1_internal_execution_harness_acceptance_chain_hotfix.py" in text
