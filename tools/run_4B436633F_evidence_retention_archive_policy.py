from __future__ import annotations

import argparse
import json
from pathlib import Path

from tradebot.evidence_retention_archive_policy import summarize_report, write_evidence_retention_archive_policy_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run 4B436633F evidence retention archive policy")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--reports-dir", default="reports/recovery")
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    repo_root = Path(args.repo_root).resolve()
    reports_dir = (repo_root / args.reports_dir).resolve() if not Path(args.reports_dir).is_absolute() else Path(args.reports_dir).resolve()
    report, paths = write_evidence_retention_archive_policy_report(repo_root, reports_dir)
    summary = summarize_report(report)
    summary.update(paths)
    print(json.dumps(summary, sort_keys=True, ensure_ascii=False) if args.once_json else json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
