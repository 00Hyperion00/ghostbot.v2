
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from tradebot.runtime_readiness_planning_closure import evaluate


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def init_git_with_tags(repo: Path, tags: tuple[str, ...]) -> None:
    subprocess.run(["git", "init"], cwd=repo, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    (repo / "README.md").write_text("test\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "base"], cwd=repo, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    for tag in tags:
        subprocess.run(["git", "tag", tag], cwd=repo, check=True)


def base_safe_fields() -> dict:
    return {
        "approved_for_exchange_submit": False,
        "approved_for_live_real": False,
        "approved_for_paper_transition": False,
        "exchange_submit_allowed": False,
        "network_submit_allowed": False,
        "paper_submit_allowed": False,
        "order_submit_performed": False,
        "exchange_submit_performed": False,
        "runtime_evidence_collection_performed": False,
        "evidence_collection_started": False,
        "public_market_data_collection_performed": False,
        "runtime_probe_performed": False,
        "runtime_health_probe_performed": False,
        "private_api_access_allowed": False,
        "private_account_read_performed": False,
        "collection_preflight_executed": False,
        "collection_runbook_executed": False,
        "collection_authorization_unlocked": False,
        "dry_run_collector_executed": False,
        "collector_guard_relaxed": False,
        "collector_closure_executed": False,
        "paper_transition_blocked": True,
        "paper_transition_ready": False,
        "phase_34_closed": True,
    }


def ready_reports() -> dict[str, tuple[str, str]]:
    return {
        "35A": ("4B436635A_post_governance_runtime_readiness_planning_20260703T000001Z_ready.json", "POST_GOVERNANCE_RUNTIME_READINESS_PLANNING_READY_NO_SUBMIT_BOUNDARY_CARRIED_FORWARD"),
        "35B": ("4B436635B_runtime_readiness_evidence_expansion_20260703T000002Z_ready.json", "RUNTIME_READINESS_EVIDENCE_EXPANSION_READY_NO_SUBMIT_EVIDENCE_PACK_LOCKED"),
        "35C": ("4B436635C_runtime_evidence_collection_plan_20260703T000003Z_ready.json", "RUNTIME_EVIDENCE_COLLECTION_PLAN_READY_NO_SUBMIT_COLLECTION_BOUNDARY_LOCKED"),
        "35D": ("4B436635D_collection_preflight_gate_20260703T000004Z_ready.json", "COLLECTION_PREFLIGHT_GATE_READY_NO_SUBMIT_EXECUTION_GUARD_LOCKED"),
        "35E": ("4B436635E_dry_run_collection_authorization_20260703T000005Z_ready.json", "DRY_RUN_COLLECTION_AUTHORIZATION_READY_NO_SUBMIT_COLLECTION_SEAL_LOCKED"),
        "35F": ("4B436635F_public_data_collection_dry_run_20260703T000006Z_ready.json", "PUBLIC_DATA_COLLECTION_DRY_RUN_READY_NO_SUBMIT_COLLECTOR_GUARD_LOCKED"),
        "35G": ("4B436635G_dry_run_collector_closure_20260703T000007Z_ready.json", "DRY_RUN_COLLECTOR_CLOSURE_READY_NO_EXECUTION_PROOF_PAPER_BLOCKER_CARRIED_FORWARD"),
    }


def write_phase_reports(reports: Path) -> None:
    safe = base_safe_fields()
    for phase, (name, decision) in ready_reports().items():
        data = {"status": "READY", "decision": decision, **safe}
        if phase == "35G":
            data.update(
                {
                    "collector_scope_digest_ledger_complete": True,
                    "collector_scope_digest": "scope-digest",
                    "no_execution_proof_ledger_complete": True,
                    "no_execution_confirmed": True,
                    "no_execution_violation_count": 0,
                    "no_execution_proof_digest": "proof-digest",
                    "paper_blocker_carry_forward_complete": True,
                    "paper_blocker_carry_forward_count": 4,
                    "paper_blocker_carry_forward_digest": "blocker-digest",
                }
            )
        write_json(reports / name, data)


def test_ready_when_reports_and_tags_complete(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "recovery"
    write_phase_reports(reports)
    init_git_with_tags(tmp_path, tuple(f"4B.4.3.6.6.35{letter}" for letter in "ABCDEFG"))

    result = evaluate(repo_root=tmp_path, reports_dir=reports, write_reports=False)

    assert result["status"] == "READY"
    assert result["source_35g_complete"] is True
    assert result["phase_35_tag_audit_complete"] is True
    assert result["phase_35_missing_tag_count"] == 0
    assert result["planning_evidence_acceptance_complete"] is True
    assert result["planning_evidence_item_count"] == 7
    assert result["no_submit_phase_35_interim_seal_complete"] is True
    assert result["no_submit_phase_35_interim_seal_locked"] is True
    assert result["paper_transition_blocked"] is True
    assert result["order_submit_performed"] is False
    assert result["next_phase_unlock_allowed"] is False


def test_missing_tag_blocks_ready(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "recovery"
    write_phase_reports(reports)
    init_git_with_tags(tmp_path, tuple(f"4B.4.3.6.6.35{letter}" for letter in "ABCDEF"))

    result = evaluate(repo_root=tmp_path, reports_dir=reports, write_reports=False)

    assert result["status"] == "NOT_READY"
    assert result["phase_35_missing_tag_count"] == 1
    assert "4B.4.3.6.6.35G" in result["phase_35_missing_tags"]
    assert result["order_submit_performed"] is False


def test_execution_violation_blocks_ready(tmp_path: Path) -> None:
    reports = tmp_path / "reports" / "recovery"
    write_phase_reports(reports)
    g_name, _ = ready_reports()["35G"]
    data = json.loads((reports / g_name).read_text(encoding="utf-8"))
    data["public_market_data_collection_performed"] = True
    write_json(reports / g_name, data)
    init_git_with_tags(tmp_path, tuple(f"4B.4.3.6.6.35{letter}" for letter in "ABCDEFG"))

    result = evaluate(repo_root=tmp_path, reports_dir=reports, write_reports=False)

    assert result["status"] == "NOT_READY"
    assert result["source_35g_complete"] is False
    assert result["source_35g_execution_violation_count"] == 1
    assert "public_market_data_collection_performed" in result["source_35g_execution_violations"]
    assert result["public_market_data_collection_performed"] is False
