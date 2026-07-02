from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _bootstrap() -> Path:
    root = Path(__file__).resolve().parents[1]
    src = root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    return root


def main() -> int:
    parser = argparse.ArgumentParser(description="Run 4B436633G archive execution preflight and write ledgers.")
    parser.add_argument("--reports-dir", default=None)
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    root = _bootstrap()
    from tradebot.archive_execution_preflight import summarize_report, write_archive_execution_preflight_report

    report, paths = write_archive_execution_preflight_report(root, args.reports_dir)
    summary = summarize_report(report)
    summary.update(paths)
    if args.once_json:
        print(json.dumps(summary, sort_keys=True))
    else:
        print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary.get("ok") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
