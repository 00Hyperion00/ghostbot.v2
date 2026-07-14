
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path.cwd() / "src"))
from tradebot.release_audit_legacy_api_drift_compatibility_h3 import build_phase61_h3_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Check 4B436661_H3 compatibility hotfix")
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    report = build_phase61_h3_report(Path.cwd())
    print(json.dumps(report, sort_keys=True) if args.once_json else json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
