from __future__ import annotations

import argparse
import json
import py_compile
from pathlib import Path

from tradebot.phase_chain_validator import build_phase_chain_validator_report, summarize_report

PATCH_ID = "4B436633C"
PATCH_VERSION = "4B.4.3.6.6.33C"
REQUIRED_FILES = [
    "src/tradebot/phase_chain_validator.py",
    "tools/run_4B436633C_phase_chain_validator.py",
    "tools/check_4B436633C_phase_chain_validator.py",
    "tests/test_phase_chain_validator_4B436633C.py",
    "docs/PHASE_CHAIN_VALIDATOR_4B436633C.md",
    "README_APPLY_4B436633C.txt",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Check 4B436633C phase chain validator")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()

    root = Path(args.repo_root).resolve()
    missing = [path for path in REQUIRED_FILES if not (root / path).exists()]
    compile_errors: dict[str, str] = {}
    for rel in REQUIRED_FILES:
        if not rel.endswith(".py"):
            continue
        path = root / rel
        if not path.exists():
            continue
        try:
            py_compile.compile(str(path), doraise=True)
        except Exception as exc:  # noqa: BLE001
            compile_errors[rel] = f"{type(exc).__name__}: {exc}"

    report = build_phase_chain_validator_report(root)
    summary = summarize_report(report)
    summary.update(
        {
            "required_files_present": not missing,
            "missing_files": missing,
            "py_compile_ok": not compile_errors,
            "compile_errors": compile_errors,
        }
    )
    summary["ok"] = bool(summary["ok"] and not missing and not compile_errors)

    if args.once_json:
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    else:
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if summary.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
