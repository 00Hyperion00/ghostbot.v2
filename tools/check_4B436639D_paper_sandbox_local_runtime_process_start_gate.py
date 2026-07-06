from __future__ import annotations

import argparse
import json
from pathlib import Path

from tradebot.paper_sandbox_local_runtime_process_start_gate import build_report


def main() -> int:
    parser = argparse.ArgumentParser(description="4B.4.3.6.6.39D local runtime process start gate check")
    parser.add_argument("--reports-dir", default="reports/recovery")
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    report = build_report(Path(args.reports_dir), write_artifacts=False)
    if args.once_json:
        print(json.dumps(report, sort_keys=True, ensure_ascii=False))
    else:
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if report.get("status") == "READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
