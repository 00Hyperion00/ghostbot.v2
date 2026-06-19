from __future__ import annotations

import argparse
import json
import py_compile
import subprocess
from pathlib import Path

CONTRACT_VERSION = "4B.4.3.6.6.29A-H1"
BAD_REPORT_DIR = "reports/production_hardeninsrc=src"
EXPECTED_FILES = [
    "tools/apply_4B436629A_H1_production_report_path_hygiene.py",
    "tools/check_4B436629A_H1_production_report_path_hygiene.py",
    "tools/run_4B436629A_H1_production_report_path_hygiene.py",
    "tools/rollback_4B436629A_H1_production_report_path_hygiene.py",
    "tests/test_production_report_path_hygiene_4B436629A_H1.py",
    "docs/PRODUCTION_REPORT_PATH_HYGIENE_4B436629A_H1.md",
]
COMPILE_FILES = [
    *EXPECTED_FILES[:4],
    "tools/run_4B436629A_production_hardening_p0.py",
    "tests/test_production_report_path_hygiene_4B436629A_H1.py",
]


def _read(root: Path, rel: str) -> str:
    path = root / rel
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _compile_ok(path: Path) -> bool:
    try:
        py_compile.compile(str(path), doraise=True)
        return True
    except Exception:
        return False


def _git_ls_files(root: Path, pattern: str) -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", pattern],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def build_report(root: Path) -> dict[str, object]:
    expected = {name: (root / name).exists() for name in EXPECTED_FILES}
    compiled = {name: _compile_ok(root / name) for name in COMPILE_FILES if (root / name).exists() and name.endswith(".py")}
    run_tool = _read(root, "tools/run_4B436629A_production_hardening_p0.py")
    gitignore = _read(root, ".gitignore")
    bad_tracked = _git_ls_files(root, BAD_REPORT_DIR + "/*")
    canonical_tracked = _git_ls_files(root, "reports/production_hardening/*")
    bad_dir_exists = (root / BAD_REPORT_DIR).exists()
    checks = {
        "all_expected_files_present": all(expected.values()),
        "all_py_compile_ok": all(compiled.values()) if compiled else False,
        "bad_report_path_not_tracked": len(bad_tracked) == 0,
        "bad_report_path_removed_from_worktree": not bad_dir_exists,
        "canonical_production_hardening_report_preserved": len(canonical_tracked) >= 1 or (root / "reports" / "production_hardening").exists(),
        "gitignore_bad_path_policy_present": "BEGIN 4B.4.3.6.6.29A-H1 REPORT PATH HYGIENE" in gitignore and "reports/production_hardeninsrc=src/" in gitignore,
        "run_tool_canonical_guard_present": "_resolve_canonical_reports_dir" in run_tool and "REPORTS_DIR_NOT_CANONICAL_PRODUCTION_HARDENING" in run_tool,
        "run_tool_bad_fragment_guard_present": "production_hardeninsrc" in run_tool and "src=src" in run_tool,
        "runtime_activation_blocked": "runtime_overlay_activation_performed" in run_tool and '"runtime_overlay_activation_performed": False' in _read(root, "src/tradebot/production_hardening.py"),
        "paper_live_order_blocked": '"paper_live_order_enablement_performed": False' in _read(root, "src/tradebot/production_hardening.py"),
        "training_reload_blocked": '"training_performed": False' in _read(root, "src/tradebot/production_hardening.py") and '"reload_performed": False' in _read(root, "src/tradebot/production_hardening.py"),
    }
    return {
        "contract_version": CONTRACT_VERSION,
        "ok": all(checks.values()),
        "read_only": True,
        "checks": checks,
        "expected_files": expected,
        "compiled": compiled,
        "bad_report_tracked_files": bad_tracked,
        "canonical_report_tracked_files": canonical_tracked,
        "config_mutation_performed": False,
        "scheduler_mutation_performed": False,
        "strategy_parameter_mutation_performed": False,
        "runtime_overlay_activation_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "paper_live_order_enablement_present": False,
        "hyp006_strategy_threshold_mutation_performed": False,
        "production_hardening_report_path_hygiene": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check 4B.4.3.6.6.29A-H1 production report path hygiene hotfix")
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    report = build_report(Path.cwd())
    if args.once_json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"{CONTRACT_VERSION} production report path hygiene check")
        for key, value in report["checks"].items():
            print(f" - {key}: {value}")
    return 0 if report.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
