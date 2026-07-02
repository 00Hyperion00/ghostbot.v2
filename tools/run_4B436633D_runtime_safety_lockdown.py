from __future__ import annotations

import argparse
import json
from pathlib import Path

from tradebot.runtime_safety_lockdown import build_runtime_safety_lockdown, summarize, write_report


def main() -> int:
    parser = argparse.ArgumentParser(description="4B.4.3.6.6.33D runtime safety lockdown report runner")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--reports-dir", default="reports/recovery")
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    report = build_runtime_safety_lockdown(repo_root)
    report_path = write_report(report, repo_root / args.reports_dir)
    payload = summarize(report, report_path)
    print(json.dumps(payload if args.once_json else report.to_dict(), indent=None if args.once_json else 2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
