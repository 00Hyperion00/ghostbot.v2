from __future__ import annotations

import argparse
import json
import os
import py_compile
import subprocess
import sys
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "4B.4.3.6.6.30I-H4"
EXPECTED_FILES = (
    "README_APPLY_4B436630I_H4.txt",
    "docs/INTERNAL_EXECUTION_HARNESS_REPO_HYGIENE_CLEANUP_4B436630I_H4.md",
    "tests/test_paper_sandbox_dry_run_internal_execution_harness_4B436630I_H4.py",
    "tools/check_4B436630I_H4_internal_execution_harness_repo_hygiene_cleanup.py",
    "tools/rollback_4B436630I_H4_internal_execution_harness_repo_hygiene_cleanup.py",
)
PY_COMPILE_FILES = (
    "tests/test_paper_sandbox_dry_run_internal_execution_harness_4B436630I_H4.py",
    "tools/check_4B436630I_H4_internal_execution_harness_repo_hygiene_cleanup.py",
    "tools/rollback_4B436630I_H4_internal_execution_harness_repo_hygiene_cleanup.py",
)
PATCH_BACKUP_DIRS = (
    "_patch_backup",
    "tools/_patch_backup",
    "tests/_patch_backup",
    "docs/_patch_backup",
)
PATCH_PAYLOAD_DIRS = (
    "_patch_payload",
    "tools/_patch_payload",
)
GITIGNORE_PATTERNS = (
    "_patch_payload/",
    "tools/_patch_payload/",
    "_patch_backup/",
    "tools/_patch_backup/",
    "tests/_patch_backup/",
    "docs/_patch_backup/",
)
H3_CHECKER = Path("tools/check_4B436630I_H3_internal_execution_harness_deterministic_acceptance_hotfix.py")


def repo_root() -> Path:
    start = Path.cwd().resolve()
    for item in [start, *start.parents]:
        if (item / "src" / "tradebot").is_dir() and (item / "tools").is_dir():
            return item
    return start


def compile_file(path: Path) -> dict[str, Any]:
    try:
        py_compile.compile(str(path), doraise=True)
        return {"ok": True, "error": ""}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def run_json_checker(root: Path, rel_path: Path) -> dict[str, Any]:
    if not (root / rel_path).exists():
        return {"ok": False, "returncode": None, "missing": str(rel_path)}
    env = os.environ.copy()
    src_path = str(root / "src")
    env["PYTHONPATH"] = src_path if not env.get("PYTHONPATH") else f"{src_path}{os.pathsep}{env['PYTHONPATH']}"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    proc = subprocess.run(
        [sys.executable, "-B", str(root / rel_path), "--once-json"],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        check=False,
        timeout=600,
    )
    try:
        payload = json.loads(proc.stdout)
    except Exception:
        return {
            "ok": False,
            "returncode": proc.returncode,
            "stdout_tail": proc.stdout[-4000:],
            "stderr_tail": proc.stderr[-4000:],
        }
    payload.setdefault("returncode", proc.returncode)
    return payload


def git_ls_files(root: Path, paths: tuple[str, ...]) -> dict[str, Any]:
    if not (root / ".git").exists():
        return {"git_available": False, "tracked": [], "ok": True}
    proc = subprocess.run(
        ["git", "ls-files", "--", *paths],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    tracked = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    return {
        "git_available": True,
        "returncode": proc.returncode,
        "tracked": tracked,
        "stderr": proc.stderr[-4000:],
        "ok": proc.returncode == 0 and not tracked,
    }


def gitignore_status(root: Path) -> dict[str, bool]:
    path = root / ".gitignore"
    content = path.read_text(encoding="utf-8") if path.exists() else ""
    return {pattern: pattern in content for pattern in GITIGNORE_PATTERNS}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    root = repo_root()
    expected = {path: (root / path).exists() for path in EXPECTED_FILES}
    compiled = {path: compile_file(root / path) for path in PY_COMPILE_FILES}
    h3_report = run_json_checker(root, H3_CHECKER)
    h3_checks = h3_report.get("checks", {}) if isinstance(h3_report, dict) else {}
    git_tracked = git_ls_files(root, PATCH_BACKUP_DIRS)
    backup_absent = {path: not (root / path).exists() for path in PATCH_BACKUP_DIRS}
    payload_absent = {path: not (root / path).exists() for path in PATCH_PAYLOAD_DIRS}
    gitignore = gitignore_status(root)

    checks = {
        "contract_version_ok": CONTRACT_VERSION == "4B.4.3.6.6.30I-H4",
        "all_expected_files_present": all(expected.values()),
        "all_py_compile_ok": all(item["ok"] for item in compiled.values()),
        "tracked_patch_backup_absent": bool(git_tracked.get("ok")),
        "filesystem_patch_backup_absent": all(backup_absent.values()),
        "patch_payload_absent_after_apply": all(payload_absent.values()),
        "gitignore_hygiene_patterns_present": all(gitignore.values()),
        "h3_checker_ok": bool(h3_report.get("ok")),
        "h3_accepted_baseline_preserved": bool(h3_checks.get("checker_30d_ok"))
        and bool(h3_checks.get("checker_30i_ok"))
        and bool(h3_checks.get("checker_h1_ok")),
        "exchange_submit_still_blocked": bool(h3_checks.get("exchange_submit_still_blocked"))
        and h3_report.get("exchange_submit_performed") is False,
        "order_actions_blocked": bool(h3_checks.get("order_actions_blocked"))
        and h3_report.get("order_actions_performed") is False,
        "paper_execution_still_blocked": bool(h3_checks.get("paper_execution_still_blocked")),
        "paper_candidate_still_blocked": bool(h3_checks.get("paper_candidate_still_blocked")),
        "live_real_still_blocked": bool(h3_checks.get("live_real_still_blocked")),
        "runtime_training_reload_mutation_blocked": h3_report.get("runtime_overlay_activation_performed") is False
        and h3_report.get("training_performed") is False
        and h3_report.get("reload_performed") is False
        and h3_report.get("strategy_parameter_mutation_performed") is False,
    }
    result = {
        "contract_version": CONTRACT_VERSION,
        "ok": all(checks.values()),
        "checks": checks,
        "expected_files": expected,
        "compiled": compiled,
        "git_tracked_patch_backup": git_tracked,
        "filesystem_patch_backup_absent": backup_absent,
        "patch_payload_absent": payload_absent,
        "gitignore": gitignore,
        "h3_report_summary": {
            "ok": h3_report.get("ok"),
            "contract_version": h3_report.get("contract_version"),
            "checks": h3_checks,
            "exchange_submit_performed": h3_report.get("exchange_submit_performed"),
            "order_actions_performed": h3_report.get("order_actions_performed"),
            "trading_action_performed": h3_report.get("trading_action_performed"),
        },
        "read_only": True,
        "exchange_submit_performed": False,
        "order_actions_performed": False,
        "trading_action_performed": False,
        "runtime_overlay_activation_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "strategy_parameter_mutation_performed": False,
        "hyp006_strategy_threshold_mutation_performed": False,
    }
    if args.once_json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"{CONTRACT_VERSION} internal execution harness repo hygiene cleanup checker")
        for key, value in checks.items():
            print(f" - {key}: {value}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
