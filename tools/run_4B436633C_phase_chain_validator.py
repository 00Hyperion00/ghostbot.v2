from __future__ import annotations

import argparse
import json
from pathlib import Path

from tradebot.phase_chain_validator import build_phase_chain_validator_report, summarize_report, write_phase_chain_validator_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run 4B436633C phase chain validator report")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--reports-dir", default="reports/recovery")
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()

    report_path = write_phase_chain_validator_report(args.repo_root, reports_dir=args.reports_dir)
    report = build_phase_chain_validator_report(args.repo_root)
    summary = summarize_report(report)
    summary["report_path"] = str(Path(report_path))

    if args.once_json:
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    else:
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if summary.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
