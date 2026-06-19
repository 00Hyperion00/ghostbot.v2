from __future__ import annotations

import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_VERSION = "4B.4.3.6.6.29A-H1"
BACKUP_DIR = ROOT / "tools" / f"_patch_backup_4B436629A_H1_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
BAD_REPORT_DIR_REL = Path("reports") / "production_hardeninsrc=src"
CANONICAL_REPORT_DIR_REL = Path("reports") / "production_hardening"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def _backup(path: Path) -> None:
    if path.exists():
        target = BACKUP_DIR / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        if path.is_dir():
            shutil.copytree(path, target, dirs_exist_ok=True)
        else:
            shutil.copy2(path, target)


def _run_git(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def patch_gitignore() -> bool:
    path = ROOT / ".gitignore"
    text = _read(path)
    marker = "BEGIN 4B.4.3.6.6.29A-H1 REPORT PATH HYGIENE"
    if marker in text:
        return False
    _backup(path)
    block = """
# BEGIN 4B.4.3.6.6.29A-H1 REPORT PATH HYGIENE
reports/production_hardeninsrc=*/
reports/production_hardeninsrc=src/
# END 4B.4.3.6.6.29A-H1 REPORT PATH HYGIENE
""".strip()
    _write(path, text.rstrip() + "\n" + block + "\n")
    return True


def patch_run_tool() -> bool:
    path = ROOT / "tools" / "run_4B436629A_production_hardening_p0.py"
    text = _read(path)
    if "REPORTS_DIR_NOT_CANONICAL_PRODUCTION_HARDENING" in text and "_resolve_canonical_reports_dir" in text:
        return False
    _backup(path)
    if "from check_4B436629A_production_hardening_p0 import CONTRACT_VERSION, build_report" not in text:
        raise RuntimeError("29A run tool import marker not found")
    if "    reports_dir = Path(args.reports_dir)\n    reports_dir.mkdir(parents=True, exist_ok=True)" not in text:
        raise RuntimeError("29A run tool reports_dir marker not found")
    helper = '''
CANONICAL_REPORTS_DIR = Path("reports") / "production_hardening"
BAD_REPORTS_DIR_FRAGMENTS = (
    "production_hardeninsrc",
    "hardeninsrc",
    "src=src",
    "$env:",
    "%pythonpath%",
)


def _resolve_canonical_reports_dir(root: Path, raw_reports_dir: str) -> Path:
    raw = str(raw_reports_dir or "").strip()
    if not raw:
        raw = CANONICAL_REPORTS_DIR.as_posix()
    lowered = raw.replace("\\\\", "/").lower()
    if any(fragment in lowered for fragment in BAD_REPORTS_DIR_FRAGMENTS):
        raise ValueError(
            "REPORTS_DIR_NOT_CANONICAL_PRODUCTION_HARDENING: "
            "refusing suspicious production hardening reports-dir path"
        )
    candidate = Path(raw)
    resolved = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
    canonical = (root / CANONICAL_REPORTS_DIR).resolve()
    if resolved != canonical:
        raise ValueError(
            "REPORTS_DIR_NOT_CANONICAL_PRODUCTION_HARDENING: "
            f"expected {CANONICAL_REPORTS_DIR.as_posix()}, got {raw!r}"
        )
    return canonical

'''
    text = text.replace("from check_4B436629A_production_hardening_p0 import CONTRACT_VERSION, build_report\n\n\n", "from check_4B436629A_production_hardening_p0 import CONTRACT_VERSION, build_report\n\n\n" + helper, 1)
    old = "    reports_dir = Path(args.reports_dir)\n    reports_dir.mkdir(parents=True, exist_ok=True)"
    new = "    reports_dir = _resolve_canonical_reports_dir(root, args.reports_dir)\n    reports_dir.mkdir(parents=True, exist_ok=True)"
    text = text.replace(old, new, 1)
    _write(path, text)
    return True


def remove_bad_report_path() -> dict[str, object]:
    bad_dir = ROOT / BAD_REPORT_DIR_REL
    before_exists = bad_dir.exists()
    tracked_before = _run_git(["ls-files", BAD_REPORT_DIR_REL.as_posix() + "/*"])
    tracked_paths = [line.strip() for line in tracked_before.stdout.splitlines() if line.strip()]
    git_rm_performed = False
    if tracked_paths:
        _backup(bad_dir)
        result = _run_git(["rm", "-r", "--ignore-unmatch", BAD_REPORT_DIR_REL.as_posix()])
        git_rm_performed = result.returncode == 0
        if result.returncode != 0:
            raise RuntimeError(f"git rm failed for {BAD_REPORT_DIR_REL.as_posix()}: {result.stderr.strip()}")
    elif bad_dir.exists():
        _backup(bad_dir)
        shutil.rmtree(bad_dir)
    # If git rm removed the tracked files, this is already gone. Remove any leftover empty dir.
    if bad_dir.exists():
        shutil.rmtree(bad_dir)
    tracked_after = _run_git(["ls-files", BAD_REPORT_DIR_REL.as_posix() + "/*"])
    return {
        "bad_report_dir_before_exists": before_exists,
        "bad_report_dir_removed": not bad_dir.exists(),
        "bad_report_tracked_before_count": len(tracked_paths),
        "bad_report_tracked_after_count": len([line for line in tracked_after.stdout.splitlines() if line.strip()]),
        "git_rm_performed": git_rm_performed,
    }


def main() -> int:
    patched = {
        "gitignore_bad_path_policy": patch_gitignore(),
        "run_tool_canonical_reports_dir_guard": patch_run_tool(),
    }
    cleanup = remove_bad_report_path()
    if str(ROOT / "tools") not in sys.path:
        sys.path.insert(0, str(ROOT / "tools"))
    from check_4B436629A_H1_production_report_path_hygiene import build_report  # noqa: E402

    report = build_report(ROOT)
    print(f"{CONTRACT_VERSION} Production Hardening report path hygiene hotfix applied")
    for key, value in patched.items():
        print(f" - patched_{key}: {value}")
    for key, value in cleanup.items():
        print(f" - {key}: {value}")
    for key, value in report["checks"].items():
        print(f" - {key}: {value}")
    for key in (
        "config_mutation_performed",
        "scheduler_mutation_performed",
        "strategy_parameter_mutation_performed",
        "runtime_overlay_activation_performed",
        "training_performed",
        "reload_performed",
        "trading_action_performed",
        "paper_live_order_enablement_present",
    ):
        print(f" - {key}: {report.get(key)}")
    return 0 if report.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
