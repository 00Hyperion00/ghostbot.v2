from __future__ import annotations

import argparse
import json
from pathlib import Path

from tradebot.release_audit_legacy_api_drift_compatibility_h5 import PATCH_NAME, build_phase61_h5_report


def main() -> int:
    parser = argparse.ArgumentParser(description=PATCH_NAME)
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    report = build_phase61_h5_report(Path(args.project_root))
    print(json.dumps(report, sort_keys=True) if args.once_json else json.dumps(report, indent=2, sort_keys=True))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
