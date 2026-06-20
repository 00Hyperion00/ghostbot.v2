from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "4B.4.3.6.6.30I-H4"
PAYLOAD_DIRNAME = "_patch_payload"
PAYLOAD_SUBDIR = CONTRACT_VERSION
CHECKER = Path("tools/check_4B436630I_H4_internal_execution_harness_repo_hygiene_cleanup.py")
PATCH_BACKUP_DIRS = (
    Path("_patch_backup"),
    Path("tools/_patch_backup"),
    Path("tests/_patch_backup"),
    Path("docs/_patch_backup"),
)
PATCH_PAYLOAD_DIRS = (
    Path("_patch_payload"),
    Path("tools/_patch_payload"),
)
GITIGNORE_PATTERNS = (
    "_patch_payload/",
    "tools/_patch_payload/",
    "_patch_backup/",
    "tools/_patch_backup/",
    "tests/_patch_backup/",
    "docs/_patch_backup/",
    "*.pyc",
    "__pycache__/",
)


def _repo_root() -> Path:
    start = Path.cwd().resolve()
    for item in [start, *start.parents]:
        if (item / "src" / "tradebot").is_dir() and (item / "tools").is_dir():
            return item
    return start


def _payload_root(root: Path) -> Path:
    candidate = root / PAYLOAD_DIRNAME / PAYLOAD_SUBDIR
    if candidate.is_dir():
        return candidate
    script_dir = Path(__file__).resolve().parent
    fallback = script_dir.parent / PAYLOAD_DIRNAME / PAYLOAD_SUBDIR
    if fallback.is_dir():
        return fallback
    raise FileNotFoundError(f"patch payload not found: {candidate}")


def _copy_payload(root: Path, payload_root: Path) -> dict[str, bool]:
    copied: dict[str, bool] = {}
    for src in sorted(payload_root.rglob("*")):
        if src.is_dir():
            continue
        rel = src.relative_to(payload_root)
        dst = root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied[str(rel).replace("\\", "/")] = dst.exists()
    return copied


def _run_git_rm_cached(root: Path) -> dict[str, Any]:
    result: dict[str, Any] = {"attempted": False, "returncode": None, "stdout": "", "stderr": ""}
    if not (root / ".git").exists():
        result["skipped_reason"] = "not_a_git_worktree"
        return result
    cmd = [
        "git",
        "rm",
        "-r",
        "--cached",
        "-f",
        "--ignore-unmatch",
        "_patch_backup",
        "tools/_patch_backup",
        "tests/_patch_backup",
        "docs/_patch_backup",
    ]
    proc = subprocess.run(
        cmd,
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    result.update(
        {
            "attempted": True,
            "returncode": proc.returncode,
            "stdout": proc.stdout[-4000:],
            "stderr": proc.stderr[-4000:],
        }
    )
    return result


def _remove_dirs(root: Path, rel_dirs: tuple[Path, ...]) -> dict[str, bool]:
    removed: dict[str, bool] = {}
    for rel in rel_dirs:
        path = root / rel
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)
        removed[str(rel).replace("\\", "/")] = not path.exists()
    return removed


def _ensure_gitignore(root: Path) -> dict[str, bool]:
    gitignore = root / ".gitignore"
    existing = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
    lines = existing.splitlines()
    changed = False
    if "# 4B patch artifact hygiene" not in existing:
        if lines and lines[-1].strip():
            lines.append("")
        lines.append("# 4B patch artifact hygiene")
        changed = True
    present = set(line.strip() for line in lines)
    for pattern in GITIGNORE_PATTERNS:
        if pattern not in present:
            lines.append(pattern)
            present.add(pattern)
            changed = True
    if changed:
        gitignore.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    content = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
    return {pattern: pattern in content for pattern in GITIGNORE_PATTERNS}


def _run_checker(root: Path) -> dict[str, Any]:
    checker = root / CHECKER
    env = os.environ.copy()
    src_path = str(root / "src")
    env["PYTHONPATH"] = src_path if not env.get("PYTHONPATH") else f"{src_path}{os.pathsep}{env['PYTHONPATH']}"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    proc = subprocess.run(
        [sys.executable, "-B", str(checker), "--once-json"],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        check=False,
        timeout=600,
    )
    try:
        report = json.loads(proc.stdout)
    except Exception:
        report = {
            "ok": False,
            "returncode": proc.returncode,
            "stdout_tail": proc.stdout[-4000:],
            "stderr_tail": proc.stderr[-4000:],
        }
    report.setdefault("returncode", proc.returncode)
    return report


def main() -> int:
    root = _repo_root()
    payload_root = _payload_root(root)
    copied = _copy_payload(root, payload_root)
    git_rm_cached = _run_git_rm_cached(root)
    removed_backups = _remove_dirs(root, PATCH_BACKUP_DIRS)
    removed_payloads = _remove_dirs(root, PATCH_PAYLOAD_DIRS)
    gitignore = _ensure_gitignore(root)
    checker_report = _run_checker(root)
    result = {
        "contract_version": CONTRACT_VERSION,
        "copied": copied,
        "git_rm_cached": git_rm_cached,
        "removed_backups": removed_backups,
        "removed_payloads": removed_payloads,
        "gitignore": gitignore,
        "checker_report": checker_report,
        "ok": bool(checker_report.get("ok"))
        and all(copied.values())
        and all(removed_backups.values())
        and all(removed_payloads.values())
        and all(gitignore.values()),
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
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    print(f"{CONTRACT_VERSION} internal execution harness repo hygiene cleanup applied")
    checks = checker_report.get("checks", {}) if isinstance(checker_report, dict) else {}
    for key in (
        "tracked_patch_backup_absent",
        "filesystem_patch_backup_absent",
        "patch_payload_absent_after_apply",
        "h3_checker_ok",
        "h3_accepted_baseline_preserved",
        "exchange_submit_still_blocked",
        "paper_execution_still_blocked",
        "paper_candidate_still_blocked",
        "live_real_still_blocked",
    ):
        print(f" - {key}: {checks.get(key)}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
