from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradebot.status_conflict_resolver import check_status_conflict_resolver


def main() -> int:
    parser = argparse.ArgumentParser(description="4B.4.3.6.6.33E status conflict resolver check")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--reports-root", default="reports")
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    payload = check_status_conflict_resolver(project_root=args.project_root, reports_root=args.reports_root)
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
