from __future__ import annotations

import argparse
import json
import py_compile
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "4B.4.3.6.6.30D-H2"
BASE_CONTRACT_VERSION = "4B.4.3.6.6.30D"
EXPECTED_FILES = [
    "README_APPLY_4B436630D_H2.txt",
    "docs/OPERATOR_APPROVAL_EVIDENCE_CAPTURE_4B436630D_H2.md",
    "tests/test_paper_transition_approval_evidence_capture_4B436630D_H2.py",
    "tools/apply_4B436630D_H2_operator_approval_evidence_repo_hygiene.py",
    "tools/check_4B436630D_H2_operator_approval_evidence_repo_hygiene.py",
    "tools/rollback_4B436630D_H2_operator_approval_evidence_repo_hygiene.py",
]
BASE_FILES = [
    "src/tradebot/paper_transition_approval_evidence_capture.py",
    "tests/test_paper_transition_approval_evidence_capture_4B436630D.py",
    "tests/test_paper_transition_approval_evidence_capture_4B436630D_H1.py",
    "tools/check_4B436630D_operator_approval_evidence_capture.py",
    "tools/run_4B436630D_operator_approval_evidence_capture.py",
]
PY_FILES = [item for item in [*EXPECTED_FILES, *BASE_FILES] if item.endswith(".py")]
NOW_MS = 1_800_000_000_000


def repo_root() -> Path:
    start = Path.cwd().resolve()
    for item in [start, *start.parents]:
        if (item / "src" / "tradebot").is_dir() and (item / "tools").is_dir():
            return item
    return start


def compile_py(root: Path) -> dict[str, bool]:
    out: dict[str, bool] = {}
    for rel in PY_FILES:
        path = root / rel
        if not path.exists():
            out[rel] = False
            continue
        try:
            py_compile.compile(str(path), doraise=True)
            out[rel] = True
        except Exception:
            out[rel] = False
    return out


def run_base_checker(root: Path) -> dict[str, Any]:
    checker = root / "tools" / "check_4B436630D_operator_approval_evidence_capture.py"
    if not checker.exists():
        return {"ok": False, "reason": "BASE_30D_CHECKER_MISSING"}
    proc = subprocess.run(
        [sys.executable, str(checker), "--once-json"],
        cwd=root,
        text=True,
        capture_output=True,
        timeout=30,
    )
    if proc.returncode != 0:
        return {"ok": False, "returncode": proc.returncode, "stdout": proc.stdout[-1000:], "stderr": proc.stderr[-1000:]}
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        return {"ok": False, "reason": f"BASE_30D_CHECKER_JSON_PARSE_FAILED:{exc}", "stdout": proc.stdout[-1000:]}
    payload["returncode"] = proc.returncode
    return payload


def module_probe(root: Path) -> dict[str, Any]:
    if str(root / "src") not in sys.path:
        sys.path.insert(0, str(root / "src"))
    import tradebot.paper_transition_approval_evidence_capture as module

    default_payload = module.build_from_operator_inputs(now_ms=NOW_MS)
    ready_payload = module.build_from_operator_inputs(
        operator_id="operator-30d",
        confirmation_token="CONFIRM_PAPER_TRANSITION_CANDIDATE",
        freeze_token="FREEZE_PAPER_TRANSITION_SANDBOX_ENVELOPE",
        issue_approval=True,
        freeze_runtime_envelope=True,
        verify_final_risk_cap=True,
        now_ms=NOW_MS,
    )
    original_stamp = module.utc_stamp
    with tempfile.TemporaryDirectory() as tmpdir:
        module.utc_stamp = lambda: "20300101T000000Z"  # type: ignore[assignment]
        try:
            default_json, default_md = module.write_report_bundle(default_payload, tmpdir)
            ready_json, ready_md = module.write_report_bundle(ready_payload, tmpdir)
        finally:
            module.utc_stamp = original_stamp  # type: ignore[assignment]
        collision_guard_ok = (
            default_json != ready_json
            and default_md != ready_md
            and default_json.exists()
            and ready_json.exists()
            and default_md.exists()
            and ready_md.exists()
            and "input_required" in default_json.name
            and "ready" in ready_json.name
        )
    return {
        "ok": bool(collision_guard_ok and ready_payload.get("approved_for_operator_approval_evidence_capture") is True),
        "default_decision": default_payload.get("decision"),
        "ready_decision": ready_payload.get("decision"),
        "collision_guard_ok": collision_guard_ok,
        "ready_review_only": ready_payload.get("approved_for_paper_transition_candidate_review") is True,
        "paper_transition_candidate_still_blocked": ready_payload.get("approved_for_paper_transition_candidate") is False,
        "paper_candidate_still_blocked": ready_payload.get("approved_for_paper_candidate") is False,
        "live_real_still_blocked": ready_payload.get("approved_for_live_real") is False,
        "order_actions_blocked": ready_payload.get("order_actions_performed") is False and ready_payload.get("trading_action_performed") is False,
    }


def run_check(root: Path | None = None) -> dict[str, Any]:
    root = (root or repo_root()).resolve()
    expected = {rel: (root / rel).exists() for rel in EXPECTED_FILES}
    base = {rel: (root / rel).exists() for rel in BASE_FILES}
    compiled = compile_py(root)
    module_path = root / "src" / "tradebot" / "paper_transition_approval_evidence_capture.py"
    module_text = module_path.read_text(encoding="utf-8") if module_path.exists() else ""
    gitignore_path = root / ".gitignore"
    gitignore = gitignore_path.read_text(encoding="utf-8") if gitignore_path.exists() else ""
    base_report = run_base_checker(root)
    probe = module_probe(root) if module_path.exists() else {"ok": False, "reason": "MODULE_MISSING"}
    root_payload_absent = not (root / "_patch_payload").exists()
    tools_payload_absent = not (root / "tools" / "_patch_payload").exists()
    checks = {
        "all_expected_files_present": all(expected.values()),
        "all_base_files_present": all(base.values()),
        "all_py_compile_ok": all(compiled.values()),
        "root_patch_payload_worktree_removed": root_payload_absent,
        "tools_patch_payload_worktree_removed": tools_payload_absent,
        "gitignore_blocks_root_patch_payload": "_patch_payload/" in gitignore,
        "gitignore_blocks_tools_patch_payload": "tools/_patch_payload/" in gitignore,
        "report_collision_guard_present": "def _unique_report_paths(" in module_text and "def _report_decision_suffix(" in module_text,
        "report_collision_guard_probe_ok": bool(probe.get("collision_guard_ok")),
        "base_30d_checker_ok": bool(base_report.get("ok")),
        "module_probe_ok": bool(probe.get("ok")),
        "explicit_evidence_capture_ready": probe.get("ready_decision") == "PAPER_TRANSITION_APPROVAL_EVIDENCE_CAPTURE_READY_FOR_30C_REVIEW_NO_ORDER_ENABLEMENT_LIVE_REAL_BLOCKED",
        "paper_transition_candidate_still_blocked": bool(probe.get("paper_transition_candidate_still_blocked")),
        "paper_candidate_still_blocked": bool(probe.get("paper_candidate_still_blocked")),
        "live_real_still_blocked": bool(probe.get("live_real_still_blocked")),
        "order_actions_blocked": bool(probe.get("order_actions_blocked")),
    }
    return {
        "contract_version": CONTRACT_VERSION,
        "base_contract_version": BASE_CONTRACT_VERSION,
        "ok": all(checks.values()),
        "checks": checks,
        "expected_files": expected,
        "base_files": base,
        "compiled": compiled,
        "base_30d_report": base_report,
        "module_probe": probe,
        "read_only": True,
        "paper_live_order_enablement_present": False,
        "order_actions_performed": False,
        "trading_action_performed": False,
        "runtime_overlay_activation_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "scheduler_mutation_performed": False,
        "strategy_parameter_mutation_performed": False,
        "hyp006_strategy_threshold_mutation_performed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    report = run_check()
    if args.once_json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"{CONTRACT_VERSION} operator approval evidence repo hygiene {'READY' if report.get('ok') else 'NOT_READY'}")
        for key, value in report.get("checks", {}).items():
            print(f" - {key}: {value}")
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
