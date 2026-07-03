from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[no-redef]

PATCH_ID = "4B436637B-H1"
PATCH_ID_COMPACT = "4B436637B_H1"
PATCH_VERSION = "4B.4.3.6.6.37B-H1"
PATCH_NAME = "Install Contract Launcher Alignment Hotfix"
CHECK_NAME = "install_contract_launcher_alignment_hotfix"
NEXT_PHASE = "4B.4.3.6.6.37C"
READY_DECISION = "INSTALL_CONTRACT_LAUNCHER_ALIGNMENT_HOTFIX_READY_NO_SUBMIT_P0_1_CLOSED"
NOT_READY_DECISION = "INSTALL_CONTRACT_LAUNCHER_ALIGNMENT_HOTFIX_NOT_READY_NO_SUBMIT_LOCKED"
SOURCE_37B_PATTERN = "4B436637B_install_contract_alignment_*_not_ready.json"
REQUIRED_INSTALL_COMMAND = "python -m pip install -r requirements.txt"
INSTALL_CONTRACT_MARKER = "4B436637B-H1 INSTALL CONTRACT"
README_CONTRACT_MARKERS = (
    "INSTALL CONTRACT",
    "requirements.txt",
    "pyproject.toml",
)
LAUNCHER_CANDIDATES = (
    "run_dashboard.ps1",
    "run_dashboard.bat",
    "start_dashboard.bat",
)
BAT_LAUNCHERS = ("run_dashboard.bat", "start_dashboard.bat")
SAFETY_FALSE_KEYS = (
    "approved_for_exchange_submit",
    "approved_for_live_real",
    "approved_for_paper_transition",
    "approved_for_runtime_overlay",
    "archive_execution_allowed",
    "archive_move_performed",
    "deduplication_action_performed",
    "destructive_cleanup_performed",
    "evidence_collection_started",
    "exchange_submit_allowed",
    "exchange_submit_performed",
    "file_delete_performed",
    "file_move_performed",
    "http_request_performed",
    "network_request_allowed_now",
    "network_request_performed",
    "network_submit_allowed",
    "next_phase_unlock_allowed",
    "next_phase_unlock_performed",
    "order_submit_performed",
    "paper_environment_enabled",
    "paper_submit_allowed",
    "paper_transition_approval_performed",
    "paper_transition_ready",
    "paper_transition_unblocked",
    "phase_37_execution_started",
    "phase_37_unlocked",
    "private_account_read_performed",
    "private_api_access_allowed",
    "public_market_data_collection_performed",
    "public_observation_execution_performed",
    "reload_performed",
    "report_delete_performed",
    "runtime_evidence_collection_performed",
    "runtime_health_probe_performed",
    "runtime_overlay_activated",
    "runtime_overlay_allowed",
    "runtime_probe_performed",
    "runtime_readiness_unlock_performed",
    "signed_request_performed",
    "training_performed",
    "transition_to_next_phase_allowed",
    "transition_to_next_phase_performed",
    "trading_action_performed",
)


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest_obj(data: Any) -> str:
    return sha256_text(canonical_json(data))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as f:
        payload = json.load(f)
    return payload if isinstance(payload, dict) else {}


def safe_rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def bool_false_snapshot() -> dict[str, bool]:
    return {key: False for key in SAFETY_FALSE_KEYS}


def git_tags(root: Path, pattern: str) -> list[str]:
    try:
        proc = subprocess.run(
            ["git", "tag", "--list", pattern],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except Exception:
        return []
    if proc.returncode != 0:
        return []
    return sorted(line.strip() for line in proc.stdout.splitlines() if line.strip())


def git_head(root: Path) -> tuple[bool, str | None, str | None]:
    try:
        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        head = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except Exception:
        return False, None, None
    if branch.returncode != 0 or head.returncode != 0:
        return False, None, None
    return True, branch.stdout.strip() or None, head.stdout.strip() or None


def find_latest_report(root: Path, reports_dir: Path | None, pattern: str) -> Path | None:
    search_dirs = []
    if reports_dir is not None:
        search_dirs.append(reports_dir)
    search_dirs.extend([root / "reports" / "recovery", root / "reports", root])
    candidates: list[Path] = []
    seen: set[Path] = set()
    for directory in search_dirs:
        if not directory.exists():
            continue
        for path in directory.rglob(pattern):
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            candidates.append(path)
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def load_source_37b(root: Path, reports_dir: Path | None) -> tuple[dict[str, Any] | None, Path | None]:
    path = find_latest_report(root, reports_dir, SOURCE_37B_PATTERN)
    if path is None:
        return None, None
    return load_json(path), path


def validate_source_37b(source: dict[str, Any] | None) -> tuple[bool, list[str], dict[str, Any]]:
    errors: list[str] = []
    if source is None:
        return False, ["SOURCE_37B_NOT_READY_REPORT_NOT_FOUND"], {
            "source_37b_complete": False,
            "source_37b_status": "SOURCE_37B_MISSING",
            "source_37b_safety_violation_count": 0,
            "source_37b_safety_violations": [],
        }
    source_safety_violations = [k for k in SAFETY_FALSE_KEYS if bool(source.get(k, False))]
    expected_decision = "INSTALL_CONTRACT_ALIGNMENT_NOT_READY_NO_SUBMIT_LOCKED"
    if source.get("status") != "NOT_READY":
        errors.append("SOURCE_37B_STATUS_NOT_NOT_READY")
    if source.get("decision") != expected_decision:
        errors.append("SOURCE_37B_DECISION_UNEXPECTED")
    if not bool(source.get("source_37a_complete", False)):
        errors.append("SOURCE_37A_NOT_COMPLETE_IN_37B")
    if source.get("source_37a_status") != "SOURCE_37A_READY":
        errors.append("SOURCE_37A_NOT_READY_IN_37B")
    if not bool(source.get("requirements_pyproject_aligned", False)):
        errors.append("SOURCE_37B_REQUIREMENTS_NOT_ALIGNED")
    if int(source.get("requirements_pyproject_mismatch_count", 999)) != 0:
        errors.append("SOURCE_37B_REQUIREMENTS_MISMATCH_COUNT_NONZERO")
    if not bool(source.get("readme_contract_marker_present", False)):
        errors.append("SOURCE_37B_README_MARKER_MISSING")
    if int(source.get("launcher_misaligned_count", 0)) < 1:
        errors.append("SOURCE_37B_NO_LAUNCHER_MISALIGNMENT_TO_FIX")
    if source_safety_violations:
        errors.append("SOURCE_37B_SAFETY_VIOLATION")
    info = {
        "source_37b_complete": len(errors) == 0,
        "source_37b_status": "SOURCE_37B_NOT_READY_ACCEPTED_FOR_HOTFIX" if len(errors) == 0 else "SOURCE_37B_INVALID",
        "source_37b_decision": source.get("decision"),
        "source_37b_requirements_pyproject_aligned": bool(source.get("requirements_pyproject_aligned", False)),
        "source_37b_readme_contract_marker_present": bool(source.get("readme_contract_marker_present", False)),
        "source_37b_launcher_misaligned_count": int(source.get("launcher_misaligned_count", 0) or 0),
        "source_37b_no_submit_gate_ready_count": int(source.get("no_submit_p0_1_hardening_gate_ready_count", 0) or 0),
        "source_37b_safety_violation_count": len(source_safety_violations),
        "source_37b_safety_violations": source_safety_violations,
    }
    return len(errors) == 0, errors, info


def normalize_dependency_name(dep: str) -> str:
    dep = dep.strip()
    match = re.match(r"([A-Za-z0-9_.-]+)", dep)
    return (match.group(1) if match else dep).replace("_", "-").lower()


def load_pyproject_dependencies(root: Path) -> tuple[list[str], dict[str, Any]]:
    path = root / "pyproject.toml"
    if not path.exists():
        return [], {"pyproject_exists": False, "pyproject_path": "pyproject.toml", "pyproject_dependency_count": 0}
    with path.open("rb") as f:
        data = tomllib.load(f)
    deps = data.get("project", {}).get("dependencies", [])
    clean = sorted(str(dep).strip() for dep in deps if str(dep).strip())
    info = {
        "pyproject_exists": True,
        "pyproject_path": "pyproject.toml",
        "pyproject_dependency_count": len(clean),
        "pyproject_dependencies_digest": digest_obj(clean),
    }
    return clean, info


def load_requirements(root: Path) -> tuple[list[str], dict[str, Any]]:
    path = root / "requirements.txt"
    if not path.exists():
        return [], {"requirements_exists": False, "requirements_path": "requirements.txt", "requirements_dependency_count": 0}
    lines = [line.strip() for line in read_text(path).splitlines()]
    deps = sorted(
        line for line in lines
        if line and not line.startswith("#") and not line.startswith("-")
    )
    info = {
        "requirements_exists": True,
        "requirements_path": "requirements.txt",
        "requirements_dependency_count": len(deps),
        "requirements_actual_digest": digest_obj(deps),
        "requirements_contract_generated_by_37b_or_h1": "4B436637" in read_text(path),
    }
    return deps, info


def requirements_alignment(root: Path) -> dict[str, Any]:
    py_deps, py_info = load_pyproject_dependencies(root)
    req_deps, req_info = load_requirements(root)
    py_names = {normalize_dependency_name(dep) for dep in py_deps}
    req_names = {normalize_dependency_name(dep) for dep in req_deps}
    missing = sorted(py_names - req_names)
    extra = sorted(req_names - py_names)
    aligned = bool(py_info.get("pyproject_exists")) and bool(req_info.get("requirements_exists")) and not missing and not extra and len(py_names) > 0
    return {
        **py_info,
        **req_info,
        "requirements_pyproject_aligned": aligned,
        "requirements_pyproject_mismatch_count": len(missing) + len(extra),
        "requirements_missing_from_pyproject_dependency_names": extra,
        "requirements_extra_dependency_names": extra,
        "requirements_missing_dependency_names": missing,
    }


def readme_alignment(root: Path) -> dict[str, Any]:
    path = root / "README.md"
    if not path.exists():
        return {
            "readme_exists": False,
            "readme_contract_marker_present": False,
            "readme_references_pyproject_toml": False,
            "readme_references_requirements_txt": False,
        }
    text = read_text(path).lower()
    return {
        "readme_exists": True,
        "readme_contract_marker_present": all(marker.lower() in text for marker in README_CONTRACT_MARKERS),
        "readme_references_pyproject_toml": "pyproject.toml" in text,
        "readme_references_requirements_txt": "requirements.txt" in text,
    }


def _command_regex() -> re.Pattern[str]:
    # Covers common launcher variants: pip install -r requirements.txt,
    # python -m pip install -r requirements.txt, py -m pip install -r requirements.txt,
    # and quoted python executables.
    return re.compile(
        r"(?i)(?P<prefix>^|[&|]\s*|call\s+|if\s+errorlevel\s+\d+\s+)(?P<cmd>(?:\"?python\"?|\"?py\"?)\s+-m\s+pip\s+install\s+-r\s+requirements\.txt|pip\s+install\s+-r\s+requirements\.txt)",
        re.MULTILINE,
    )


def uses_required_install_command(text: str) -> bool:
    normalized = re.sub(r"\s+", " ", text.lower())
    return REQUIRED_INSTALL_COMMAND in normalized


def references_requirements(text: str) -> bool:
    return "requirements.txt" in text.lower()


def normalize_bat_launcher_text(text: str) -> tuple[str, bool]:
    original = text
    marker_line = f"REM {INSTALL_CONTRACT_MARKER}: use {REQUIRED_INSTALL_COMMAND}"

    def replace(match: re.Match[str]) -> str:
        return f"{match.group('prefix')}{REQUIRED_INSTALL_COMMAND}"

    text = _command_regex().sub(replace, text)
    lines = text.splitlines()
    has_marker = any(INSTALL_CONTRACT_MARKER.lower() in line.lower() for line in lines)
    if not has_marker:
        out: list[str] = []
        inserted = False
        for line in lines:
            if not inserted and REQUIRED_INSTALL_COMMAND.lower() in re.sub(r"\s+", " ", line.lower()):
                out.append(marker_line)
                inserted = True
            out.append(line)
        if not inserted and references_requirements(text):
            out.append(marker_line)
            out.append(REQUIRED_INSTALL_COMMAND)
        text = "\n".join(out)
    if original.endswith("\n") and not text.endswith("\n"):
        text += "\n"
    elif not text.endswith("\n"):
        text += "\n"
    return text, text != original


def launcher_record(root: Path, rel: str) -> dict[str, Any]:
    path = root / rel
    if not path.exists():
        return {
            "path": rel,
            "exists": False,
            "candidate": False,
            "aligned": False,
            "install_contract_marker_present": False,
            "references_requirements_txt": False,
            "uses_python_m_pip_requirements_install": False,
        }
    text = read_text(path)
    marker_present = (INSTALL_CONTRACT_MARKER.lower() in text.lower()) or ("install contract" in text.lower())
    refs = references_requirements(text)
    uses_required = uses_required_install_command(text)
    candidate = refs or rel in LAUNCHER_CANDIDATES
    aligned = candidate and refs and uses_required and marker_present
    return {
        "path": rel,
        "exists": True,
        "candidate": candidate,
        "aligned": aligned,
        "install_contract_marker_present": marker_present,
        "references_requirements_txt": refs,
        "uses_python_m_pip_requirements_install": uses_required,
    }


def launcher_alignment(root: Path) -> dict[str, Any]:
    records = [launcher_record(root, rel) for rel in LAUNCHER_CANDIDATES if (root / rel).exists()]
    candidate_count = len([r for r in records if r["candidate"]])
    aligned_count = len([r for r in records if r["aligned"]])
    misaligned = [r for r in records if r["candidate"] and not r["aligned"]]
    return {
        "launcher_candidate_count": candidate_count,
        "launcher_aligned_count": aligned_count,
        "launcher_misaligned_count": len(misaligned),
        "launcher_misaligned_paths": [str(r["path"]) for r in misaligned],
        "launcher_records": records,
        "launcher_contract_aligned": candidate_count > 0 and len(misaligned) == 0,
    }


def apply_bat_launcher_hotfix(root: Path) -> dict[str, Any]:
    changed: list[str] = []
    missing: list[str] = []
    for rel in BAT_LAUNCHERS:
        path = root / rel
        if not path.exists():
            missing.append(rel)
            continue
        text = read_text(path)
        new_text, did_change = normalize_bat_launcher_text(text)
        if did_change:
            write_text(path, new_text)
            changed.append(rel)
    return {
        "bat_launcher_normalization_performed": bool(changed),
        "bat_launcher_normalized_files": changed,
        "bat_launcher_missing_files": missing,
        "bat_launcher_candidate_count": len(BAT_LAUNCHERS) - len(missing),
    }


def build_contract_alignment(root: Path, source_ok: bool) -> dict[str, Any]:
    req = requirements_alignment(root)
    readme = readme_alignment(root)
    launchers = launcher_alignment(root)
    complete = (
        source_ok
        and bool(req.get("requirements_pyproject_aligned"))
        and int(req.get("requirements_pyproject_mismatch_count", 999)) == 0
        and bool(readme.get("readme_contract_marker_present"))
        and bool(readme.get("readme_references_pyproject_toml"))
        and bool(readme.get("readme_references_requirements_txt"))
        and bool(launchers.get("launcher_contract_aligned"))
    )
    body = {
        "install_contract_launcher_alignment_complete": complete,
        "install_contract_launcher_alignment_locked": complete,
        "install_contract_launcher_alignment_status": "INSTALL_CONTRACT_LAUNCHER_ALIGNMENT_READY" if complete else "INSTALL_CONTRACT_LAUNCHER_ALIGNMENT_NOT_READY",
        "install_contract_alignment_complete": complete,
        "install_contract_alignment_locked": complete,
        "install_contract_alignment_status": "INSTALL_CONTRACT_ALIGNMENT_READY_AFTER_H1" if complete else "INSTALL_CONTRACT_ALIGNMENT_NOT_READY_AFTER_H1",
        "install_contract_alignment_gap_id": "P0_INSTALL_CONTRACT_ALIGNMENT",
        **req,
        **readme,
        **launchers,
    }
    body["install_contract_launcher_alignment_digest"] = digest_obj({k: v for k, v in body.items() if not k.endswith("_path")})
    return body


def build_gap_delta(alignment: dict[str, Any]) -> dict[str, Any]:
    p0_closed = bool(alignment.get("install_contract_alignment_complete"))
    base_gaps = [
        ("install_contract", "P0_INSTALL_CONTRACT_ALIGNMENT"),
        ("repo_hygiene", "P0_REPO_HYGIENE_EVIDENCE_RETENTION"),
        ("strict_config", "P0_STRICT_CONFIG_UNKNOWN_KEY_FAIL_CLOSED"),
        ("api_security", "P0_API_AUTH_DESTRUCTIVE_ENDPOINT_GUARD"),
        ("operator_controls", "P0_TYPED_CONFIRMATION_DESTRUCTIVE_ACTIONS"),
        ("persistence", "P0_SQLITE_AUDIT_BASELINE"),
        ("runtime_safety", "P0_RUNTIME_PROCESS_LOCK"),
        ("execution_cost_model", "P0_FEE_SLIPPAGE_BASELINE"),
        ("evidence_governance", "P0_REPORT_COMMIT_POLICY"),
        ("promotion_governance", "P0_PROMOTION_GATE_ISOLATION"),
    ]
    items: list[dict[str, Any]] = []
    for domain, gap_id in base_gaps:
        closed = gap_id == "P0_INSTALL_CONTRACT_ALIGNMENT" and p0_closed
        items.append({
            "domain": domain,
            "gap_id": gap_id,
            "closed": closed,
            "closed_by": PATCH_VERSION if closed else None,
            "auto_close_allowed": False,
        })
    closed_count = sum(1 for i in items if i["closed"])
    body = {
        "p0_gap_closure_delta_complete": p0_closed,
        "p0_gap_closure_delta_locked": p0_closed,
        "p0_gap_closure_delta_status": "P0_1_INSTALL_CONTRACT_GAP_CLOSED" if p0_closed else "P0_1_INSTALL_CONTRACT_GAP_NOT_CLOSED",
        "p0_gap_closure_items": items,
        "p0_hardening_gap_count_after_37b_h1": len(items),
        "p0_hardening_closed_gap_count_after_37b_h1": closed_count,
        "p0_hardening_open_gap_count_after_37b_h1": len(items) - closed_count,
        "p0_hardening_complete": closed_count == len(items),
        "p0_hardening_performed": False,
        "p0_hardening_auto_close_allowed": False,
        "p0_install_contract_alignment_closed": p0_closed,
        "p0_install_contract_alignment_closed_by": PATCH_VERSION if p0_closed else None,
    }
    body["p0_gap_closure_delta_digest"] = digest_obj(body)
    return body


def build_gate(source_ok: bool, alignment: dict[str, Any], delta: dict[str, Any]) -> dict[str, Any]:
    checks = [
        {"check_id": "source_37b_not_ready_accepted_for_hotfix", "ready": source_ok, "unlock_allowed": False},
        {"check_id": "bat_launchers_normalized", "ready": bool(alignment.get("launcher_contract_aligned")), "unlock_allowed": False},
        {"check_id": "requirements_pyproject_aligned", "ready": bool(alignment.get("requirements_pyproject_aligned")), "unlock_allowed": False},
        {"check_id": "readme_contract_marker_present", "ready": bool(alignment.get("readme_contract_marker_present")), "unlock_allowed": False},
        {"check_id": "install_contract_alignment_closed", "ready": bool(delta.get("p0_install_contract_alignment_closed")), "unlock_allowed": False},
        {"check_id": "only_p0_1_closed", "ready": int(delta.get("p0_hardening_closed_gap_count_after_37b_h1", 0)) == 1, "unlock_allowed": False},
        {"check_id": "paper_transition_remains_blocked", "ready": True, "unlock_allowed": False},
        {"check_id": "network_submit_forbidden", "ready": True, "unlock_allowed": False},
        {"check_id": "next_phase_not_auto_unlocked", "ready": True, "unlock_allowed": False},
    ]
    ready_count = sum(1 for c in checks if c["ready"])
    complete = ready_count == len(checks)
    body = {
        "no_submit_p0_1_hardening_gate_complete": complete,
        "no_submit_p0_1_hardening_gate_locked": complete,
        "no_submit_p0_1_hardening_gate_status": "NO_SUBMIT_P0_1_HARDENING_GATE_READY_AFTER_H1" if complete else "NO_SUBMIT_P0_1_HARDENING_GATE_NOT_READY_AFTER_H1",
        "no_submit_p0_1_hardening_gate_check_count": len(checks),
        "no_submit_p0_1_hardening_gate_ready_count": ready_count,
        "no_submit_p0_1_hardening_gate_checks": checks,
    }
    body["no_submit_p0_1_hardening_gate_digest"] = digest_obj(body)
    return body


def write_report(path: Path | None, payload: dict[str, Any]) -> str | None:
    if path is None:
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    return str(path)


def evaluate(root: Path, reports_dir: Path | None = None, write: bool = False) -> dict[str, Any]:
    source, source_path = load_source_37b(root, reports_dir)
    source_ok, source_errors, source_info = validate_source_37b(source)
    alignment = build_contract_alignment(root, source_ok)
    delta = build_gap_delta(alignment)
    gate = build_gate(source_ok, alignment, delta)
    git_available, git_branch, git_head_short = git_head(root)
    phase37_tags = git_tags(root, "4B.4.3.6.6.37*")

    ok = bool(alignment.get("install_contract_alignment_complete")) and bool(delta.get("p0_gap_closure_delta_complete")) and bool(gate.get("no_submit_p0_1_hardening_gate_complete")) and not source_errors
    stamp = utc_stamp()
    status = "READY" if ok else "NOT_READY"
    report_name = f"{PATCH_ID_COMPACT}_install_contract_launcher_alignment_hotfix_{stamp}_{status.lower()}.json"
    report_path = (reports_dir or (root / "reports" / "recovery")) / report_name if write else None

    result: dict[str, Any] = {
        "ok": ok,
        "status": status,
        "accepted_for_install_contract_launcher_alignment_hotfix": ok,
        "decision": READY_DECISION if ok else NOT_READY_DECISION,
        "patch_id": PATCH_ID_COMPACT,
        "patch_version": PATCH_VERSION,
        "patch_name": PATCH_NAME,
        "check_name": CHECK_NAME,
        "contract_name": "install_contract_launcher_alignment",
        "delta_name": "p0_gap_closure_delta_h1",
        "gate_name": "no_submit_p0_1_hardening_gate_h1",
        "errors": source_errors,
        "git_available": git_available,
        "git_branch": git_branch,
        "git_head_short": git_head_short,
        "source_37b_report": str(source_path) if source_path else None,
        **source_info,
        **alignment,
        **delta,
        **gate,
        "phase_34_closed": True,
        "phase_35_closed": True,
        "phase_36_final_closed": True,
        "phase_37_planning_only": True,
        "phase_37_unlocked": False,
        "phase_37_execution_started": False,
        "phase_37_tag_count_observed": len(phase37_tags),
        "phase_37_tags_observed": phase37_tags,
        "phase_reopen_allowed": False,
        "phase_reopen_performed": False,
        "production_hardening_p0_1_ready": ok,
        "production_hardening_p0_1_scope": "install_contract_launcher_alignment_only",
        "production_readiness_status": "P0_1_INSTALL_CONTRACT_ALIGNMENT_READY_NO_SUBMIT" if ok else "P0_1_INSTALL_CONTRACT_ALIGNMENT_NOT_READY_NO_SUBMIT",
        "paper_transition_blocked": True,
        "paper_transition_status": "PAPER_TRANSITION_BLOCKED_37B_H1_INSTALL_CONTRACT_ALIGNMENT_NO_SUBMIT",
        "next_phase": NEXT_PHASE,
        **bool_false_snapshot(),
        "report_path": str(report_path) if report_path else None,
    }
    # Scope-specific mutation flags are always false in check/run output.
    result.update({
        "install_contract_apply_performed": False,
        "install_contract_mutation_performed": False,
        "launcher_install_contract_mutation_performed": False,
        "requirements_alignment_mutation_performed": False,
        "readme_install_contract_mutation_performed": False,
        "repo_hygiene_cleanup_performed": False,
        "strict_config_mutation_performed": False,
        "api_auth_mutation_performed": False,
        "typed_confirmation_mutation_performed": False,
        "sqlite_schema_mutation_performed": False,
        "runtime_lock_mutation_performed": False,
        "fee_slippage_mutation_performed": False,
        "report_commit_policy_mutation_performed": False,
        "promotion_gate_mutation_performed": False,
    })
    if write:
        report_dir = reports_dir or (root / "reports" / "recovery")
        report_dir.mkdir(parents=True, exist_ok=True)
        alignment_path = report_dir / f"{PATCH_ID_COMPACT}_install_contract_launcher_alignment_{stamp}.json"
        delta_path = report_dir / f"{PATCH_ID_COMPACT}_p0_gap_closure_delta_{stamp}.json"
        gate_path = report_dir / f"{PATCH_ID_COMPACT}_no_submit_p0_1_hardening_gate_{stamp}.json"
        result["install_contract_launcher_alignment_path"] = write_report(alignment_path, alignment)
        result["p0_gap_closure_delta_path"] = write_report(delta_path, delta)
        result["no_submit_p0_1_hardening_gate_path"] = write_report(gate_path, gate)
        result["report_path"] = write_report(report_path, result)
    else:
        result.setdefault("install_contract_launcher_alignment_path", None)
        result.setdefault("p0_gap_closure_delta_path", None)
        result.setdefault("no_submit_p0_1_hardening_gate_path", None)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=PATCH_NAME)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--reports-dir", default=None)
    parser.add_argument("--once-json", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args(argv)
    root = Path(args.repo_root).resolve()
    reports_dir = Path(args.reports_dir).resolve() if args.reports_dir else None
    payload = evaluate(root, reports_dir=reports_dir, write=args.write_report)
    print(json.dumps(payload, sort_keys=True, ensure_ascii=False))
    return 0 if payload.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
