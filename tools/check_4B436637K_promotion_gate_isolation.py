from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradebot.promotion_gate_isolation import build_report  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Check 4B436637K promotion gate isolation")
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    report = build_report(ROOT, None, write_reports=False)
    print(json.dumps(report, sort_keys=True, ensure_ascii=False))
    return 0 if report.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
