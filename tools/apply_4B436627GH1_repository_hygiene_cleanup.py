from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Iterable

CONTRACT_VERSION = "4B.4.3.6.6.27G-H1"
BACKUP_DIRNAME = "_patch_backup_4B436627GH1"
MANAGED_BEGIN = "# BEGIN 4B.4.3.6.6.27G-H1 REPOSITORY HYGIENE"
MANAGED_END = "# END 4B.4.3.6.6.27G-H1 REPOSITORY HYGIENE"
IGNORE_LINES = (
    "reports/hyp005_r1_canonical/",
    "tools/_patch_backup_*/",
    "tools/_patch_payload_*/",
)


def _run(root: Path, args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=root,
        check=check,
        encoding="utf-8",
        errors="strict",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return _run(root, ["git", *args], check=check)


def _chunks(items: list[str], size: int = 100) -> Iterable[list[str]]:
    for index in range(0, len(items), size):
        yield items[index : index + size]


def _is_hygiene_target(path: str) -> bool:
    normalized = path.replace("\\", "/")
    return (
        normalized.startswith("reports/hyp005_r1_canonical/")
        or normalized.startswith("tools/_patch_backup_")
        or normalized.startswith("tools/_patch_payload_")
    )


def _tracked_targets(root: Path) -> list[str]:
    result = _git(root, "ls-files", "-z")
    return sorted(path for path in result.stdout.split("\0") if path and _is_hygiene_target(path))


def _ensure_git_root(root: Path) -> None:
    result = _git(root, "rev-parse", "--show-toplevel")
    actual = Path(result.stdout.strip()).resolve()
    if actual != root.resolve():
        raise RuntimeError(f"GIT_ROOT_MISMATCH:{actual}")


def _append_managed_gitignore(original: str) -> str:
    if MANAGED_BEGIN in original and MANAGED_END in original:
        return original
    prefix = original
    if prefix and not prefix.endswith("\n"):
        prefix += "\n"
    if prefix and not prefix.endswith("\n\n"):
        prefix += "\n"
    managed = "\n".join((MANAGED_BEGIN, *IGNORE_LINES, MANAGED_END, ""))
    return prefix + managed


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    backup_dir = root / "tools" / BACKUP_DIRNAME
    gitignore_path = root / ".gitignore"
    backup_gitignore_path = backup_dir / "gitignore.before.txt"
    manifest_path = backup_dir / "tracked_paths_before.json"

    _ensure_git_root(root)
    backup_dir.mkdir(parents=True, exist_ok=True)

    original = gitignore_path.read_text(encoding="utf-8") if gitignore_path.exists() else ""
    if not backup_gitignore_path.exists():
        backup_gitignore_path.write_text(original, encoding="utf-8")

    tracked_before = _tracked_targets(root)
    if not manifest_path.exists():
        manifest_path.write_text(
            json.dumps({"contract_version": CONTRACT_VERSION, "tracked_paths_before": tracked_before}, indent=2) + "\n",
            encoding="utf-8",
        )

    updated = _append_managed_gitignore(original)
    if updated != original:
        gitignore_path.write_text(updated, encoding="utf-8")

    local_paths_before = [path for path in tracked_before if (root / path).exists()]
    for chunk in _chunks(tracked_before):
        _git(root, "rm", "-r", "--cached", "--ignore-unmatch", "--", *chunk)

    tracked_after = _tracked_targets(root)
    local_paths_preserved = all((root / path).exists() for path in local_paths_before)
    checks = {
        "gitignore_policy_present": all(line in gitignore_path.read_text(encoding="utf-8") for line in IGNORE_LINES),
        "canonical_runtime_reports_untracked": not any(path.startswith("reports/hyp005_r1_canonical/") for path in tracked_after),
        "patch_backup_payload_untracked": not any(path.startswith("tools/_patch_backup_") or path.startswith("tools/_patch_payload_") for path in tracked_after),
        "local_runtime_artifacts_preserved": local_paths_preserved,
        "accepted_baseline_source_mutation_performed": False,
        "config_mutation_performed": False,
        "scheduler_mutation_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "paper_live_order_enablement_present": False,
    }
    ok = (
        checks["gitignore_policy_present"]
        and checks["canonical_runtime_reports_untracked"]
        and checks["patch_backup_payload_untracked"]
        and checks["local_runtime_artifacts_preserved"]
        and not checks["accepted_baseline_source_mutation_performed"]
        and not checks["config_mutation_performed"]
        and not checks["scheduler_mutation_performed"]
        and not checks["training_performed"]
        and not checks["reload_performed"]
        and not checks["trading_action_performed"]
        and not checks["paper_live_order_enablement_present"]
    )
    print(f"{CONTRACT_VERSION} Repository hygiene cleanup / runtime report artifact ignore policy / patch backup-payload exclusion / accepted baseline preservation hotfix applied")
    for key, value in checks.items():
        print(f" - {key}: {value}")
    print(f" - tracked_hygiene_paths_removed_from_index: {len(tracked_before)}")
    print(f" - local_hygiene_paths_preserved: {len(local_paths_before)}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
