
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tradebot.archive_execution_approval_ledger import write_archive_execution_approval_ledger_report


def main() -> int:
    parser = argparse.ArgumentParser(description="4B.4.3.6.6.33H archive execution approval ledger run")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--reports-dir", default=None)
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    reports_dir = Path(args.reports_dir).resolve() if args.reports_dir else None
    summary = write_archive_execution_approval_ledger_report(repo_root, reports_dir)
    print(json.dumps(summary, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
