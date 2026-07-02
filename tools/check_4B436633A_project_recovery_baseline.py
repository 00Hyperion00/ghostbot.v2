from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REQUIRED_FILES = [
    "src/tradebot/project_recovery_baseline.py",
    "tools/run_4B436633A_project_recovery_baseline.py",
    "tools/check_4B436633A_project_recovery_baseline.py",
    "tests/test_project_recovery_baseline_4B436633A.py",
    "docs/PROJECT_RECOVERY_BASELINE_4B436633A.md",
    "README_APPLY_4B436633A.txt",
]


def _ensure_src_on_path(repo_root: Path) -> None:
    src = str((repo_root / "src").resolve())
    if src not in sys.path:
        sys.path.insert(0, src)


def main() -> int:
    parser = argparse.ArgumentParser(description="4B.4.3.6.6.33A recovery baseline checker")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    _ensure_src_on_path(repo_root)

    missing_files = [path for path in REQUIRED_FILES if not (repo_root / path).is_file()]

    import py_compile

    compile_targets = [
        repo_root / "src/tradebot/project_recovery_baseline.py",
        repo_root / "tools/run_4B436633A_project_recovery_baseline.py",
        repo_root / "tools/check_4B436633A_project_recovery_baseline.py",
    ]
    compile_errors: dict[str, str] = {}
    for target in compile_targets:
        if not target.is_file():
            continue
        try:
            py_compile.compile(str(target), doraise=True)
        except Exception as exc:  # pragma: no cover - diagnostic path
            compile_errors[str(target.relative_to(repo_root))] = str(exc)

    from tradebot.project_recovery_baseline import build_recovery_baseline

    report = build_recovery_baseline(repo_root)
    result = {
        "patch_id": "4B436633A",
        "patch_version": "4B.4.3.6.6.33A",
        "check_name": "project_recovery_baseline",
        "required_files_present": not missing_files,
        "missing_files": missing_files,
        "py_compile_ok": not compile_errors,
        "compile_errors": compile_errors,
        "baseline_status": report.status,
        "baseline_decision": report.decision,
        "repo_inventory_complete": report.repo_inventory.complete,
        "phase_inventory_complete": report.phase_inventory.complete,
        "evidence_inventory_complete": report.evidence_inventory.complete,
        "config_inventory_complete": report.config_inventory.complete,
        "safety_snapshot_complete": report.safety_snapshot.complete,
        "approved_for_live_real": report.approved_for_live_real,
        "approved_for_paper_transition": report.approved_for_paper_transition,
        "approved_for_exchange_submit": report.approved_for_exchange_submit,
        "approved_for_runtime_overlay": report.approved_for_runtime_overlay,
        "trading_action_performed": report.safety_snapshot.trading_action_performed,
        "training_performed": report.safety_snapshot.training_performed,
        "reload_performed": report.safety_snapshot.reload_performed,
        "ok": bool(
            not missing_files
            and not compile_errors
            and not report.approved_for_live_real
            and not report.approved_for_paper_transition
            and not report.approved_for_exchange_submit
            and not report.approved_for_runtime_overlay
            and not report.safety_snapshot.trading_action_performed
            and not report.safety_snapshot.training_performed
            and not report.safety_snapshot.reload_performed
        ),
    }

    if args.once_json:
        print(json.dumps(result, sort_keys=True, ensure_ascii=False))
    else:
        print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))

    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
