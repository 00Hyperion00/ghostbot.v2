from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradebot.recovery_closure_report import summarize_persisted, write_recovery_closure_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Write 4B436633I recovery closure report artifacts.")
    parser.add_argument("--reports-dir", default="reports/recovery", help="Output report directory.")
    parser.add_argument("--once-json", action="store_true", help="Emit one JSON object.")
    args = parser.parse_args()

    report, artifacts = write_recovery_closure_report(ROOT, args.reports_dir)
    summary = summarize_persisted(report, artifacts, ROOT)
    print(json.dumps(summary, sort_keys=True, ensure_ascii=False))
    return 0 if args.once_json else (0 if report.ok else 1)


if __name__ == "__main__":
    raise SystemExit(main())
