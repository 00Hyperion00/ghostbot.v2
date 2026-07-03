
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tradebot.archive_execution_approval_ledger import build_archive_execution_approval_ledger_report, summarize_report


def main() -> int:
    parser = argparse.ArgumentParser(description="4B.4.3.6.6.33H archive execution approval ledger check")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--reports-dir", default=None)
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    reports_dir = Path(args.reports_dir).resolve() if args.reports_dir else None
    report = build_archive_execution_approval_ledger_report(repo_root, reports_dir)
    summary = summarize_report(report)
    missing_files: list[str] = []
    required = [
        "src/tradebot/archive_execution_approval_ledger.py",
        "tools/check_4B436633H_archive_execution_approval_ledger.py",
        "tools/run_4B436633H_archive_execution_approval_ledger.py",
        "tests/test_archive_execution_approval_ledger_4B436633H.py",
        "docs/ARCHIVE_EXECUTION_APPROVAL_LEDGER_4B436633H.md",
        "README_APPLY_4B436633H.txt",
    ]
    for rel in required:
        if not (repo_root / rel).exists():
            missing_files.append(rel)
    summary.update({"required_files_present": not missing_files, "missing_files": missing_files})
    print(json.dumps(summary, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
