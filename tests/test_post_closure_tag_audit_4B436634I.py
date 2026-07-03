from __future__ import annotations

import json
import subprocess
from pathlib import Path

from tradebot.post_closure_tag_audit import (
    READY_DECISION,
    evaluate_post_closure_tag_audit,
)


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, text=True, capture_output=True)


def _write_34h_report(root: Path, *, unsafe: bool = False) -> None:
    reports = root / "reports" / "recovery"
    reports.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": "READY",
        "decision": "SIGNATURE_PACKAGE_CLOSURE_READY_NO_SUBMIT_CHAIN_CLOSED",
        "source_34g_complete": True,
        "accepted_for_governance_closure": True,
        "final_governance_acceptance_complete": True,
        "no_submit_chain_closure_complete": True,
        "no_submit_chain_closed": True,
        "phase_34_tag_audit_complete": True,
        "governance_locked": True,
        "approved_for_exchange_submit": unsafe,
        "exchange_submit_allowed": False,
        "order_submit_performed": False,
        "baseline_digest": "baseline",
        "manifest_sha256": "manifest",
        "immutable_plan_digest": "plan",
    }
    (reports / "4B436634H_signature_package_closure_20260703T101605Z_ready.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )


def _make_repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init")
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "config", "user.name", "Test User")
    (root / "seed.txt").write_text("seed\n", encoding="utf-8")
    _git(root, "add", "seed.txt")
    _git(root, "commit", "-m", "seed")
    return root


def _tag_34(root: Path, *, include_h: bool = True) -> None:
    _git(root, "add", "reports/recovery/4B436634H_signature_package_closure_20260703T101605Z_ready.json")
    _git(root, "commit", "-m", "34H source report")
    suffixes = "ABCDEFGH" if include_h else "ABCDEFG"
    for suffix in suffixes:
        _git(root, "tag", f"4B.4.3.6.6.34{suffix}")


def test_ready_when_34h_tag_present_and_only_34i_self_artifacts_dirty(tmp_path: Path) -> None:
    root = _make_repo(tmp_path)
    _write_34h_report(root)
    _tag_34(root, include_h=True)
    # Expected pre-34I-commit self artifact should not block clean-worktree confirmation.
    target = root / "src" / "tradebot" / "post_closure_tag_audit.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("# generated\n", encoding="utf-8")

    result = evaluate_post_closure_tag_audit(repo_root=root, reports_dir="reports/recovery")

    assert result["status"] == "READY"
    assert result["decision"] == READY_DECISION
    assert result["source_34h_complete"] is True
    assert result["phase_34h_tag_verification_complete"] is True
    assert result["missing_tag_count"] == 0
    assert result["normalized_dirty_worktree_count"] == 0
    assert result["no_submit_phase_34_final_sealed"] is True
    assert result["exchange_submit_allowed"] is False
    assert result["next_phase_unlock_allowed"] is False


def test_not_ready_when_34h_tag_missing(tmp_path: Path) -> None:
    root = _make_repo(tmp_path)
    _write_34h_report(root)
    _tag_34(root, include_h=False)

    result = evaluate_post_closure_tag_audit(repo_root=root, reports_dir="reports/recovery")

    assert result["status"] == "NOT_READY"
    assert result["phase_34h_tag_verification_complete"] is False
    assert result["missing_tags"] == ["4B.4.3.6.6.34H"]
    assert result["next_phase_unlock_allowed"] is False


def test_not_ready_when_source_34h_has_submit_approval(tmp_path: Path) -> None:
    root = _make_repo(tmp_path)
    _write_34h_report(root, unsafe=True)
    _tag_34(root, include_h=True)

    result = evaluate_post_closure_tag_audit(repo_root=root, reports_dir="reports/recovery")

    assert result["status"] == "NOT_READY"
    assert result["source_34h_complete"] is False
    assert "approved_for_exchange_submit" in result["source_34h_safety_violations"]
    assert result["order_submit_performed"] is False
