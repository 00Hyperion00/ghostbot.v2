from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradebot.paper_transition_readiness_review import build_report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports-dir", type=Path, default=Path("reports/recovery"))
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    report = build_report(ROOT, args.reports_dir, write_reports=False)
    print(json.dumps(report, sort_keys=True, ensure_ascii=False))
    return 0 if report.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
