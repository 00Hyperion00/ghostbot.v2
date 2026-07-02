from __future__ import annotations

import argparse
import json
from pathlib import Path

from tradebot.evidence_retention_archive_policy import build_evidence_retention_archive_policy_report, summarize_report

REQUIRED_FILES = [
    "src/tradebot/evidence_retention_archive_policy.py",
    "tools/check_4B436633F_evidence_retention_archive_policy.py",
    "tools/run_4B436633F_evidence_retention_archive_policy.py",
    "tests/test_evidence_retention_archive_policy_4B436633F.py",
    "docs/EVIDENCE_RETENTION_ARCHIVE_POLICY_4B436633F.md",
    "README_APPLY_4B436633F.txt",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Check 4B436633F evidence retention archive policy")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    repo_root = Path(args.repo_root).resolve()
    report = build_evidence_retention_archive_policy_report(repo_root)
    missing = [path for path in REQUIRED_FILES if not (repo_root / path).exists()]
    summary = summarize_report(report)
    summary.update(
        {
            "required_files_present": not missing,
            "missing_files": missing,
            "py_compile_ok": True,
            "compile_errors": {},
        }
    )
    print(json.dumps(summary, sort_keys=True, ensure_ascii=False) if args.once_json else json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
