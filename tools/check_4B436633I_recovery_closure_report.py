from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradebot.recovery_closure_report import build_recovery_closure_report, summarize_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Check 4B436633I recovery closure report readiness.")
    parser.add_argument("--once-json", action="store_true", help="Emit one JSON object.")
    args = parser.parse_args()

    report = build_recovery_closure_report(ROOT)
    summary = summarize_report(report)
    print(json.dumps(summary, sort_keys=True, ensure_ascii=False))
    return 0 if args.once_json else (0 if report.ok else 1)


if __name__ == "__main__":
    raise SystemExit(main())
