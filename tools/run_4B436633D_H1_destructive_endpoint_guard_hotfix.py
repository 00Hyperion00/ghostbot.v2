from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from check_4B436633D_H1_destructive_endpoint_guard_hotfix import build_report

PATCH_ID = "4B436633D_H1"
PATCH_VERSION = "4B.4.3.6.6.33D-H1"


def _timestamp() -> str:
    return time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())


def main() -> int:
    parser = argparse.ArgumentParser(description="Run 4B436633D-H1 destructive endpoint guard hotfix report.")
    parser.add_argument("--reports-dir", default="reports/recovery")
    parser.add_argument("--once-json", action="store_true")
    parser.add_argument("--skip-33d-check", action="store_true")
    args = parser.parse_args()
    root = Path.cwd()
    report = build_report(root, include_33d_check=not args.skip_33d_check)
    reports_dir = root / args.reports_dir
    reports_dir.mkdir(parents=True, exist_ok=True)
    suffix = "ready" if report.get("status") == "READY" else "not_ready"
    path = reports_dir / f"4B436633D_H1_destructive_endpoint_guard_hotfix_{_timestamp()}_{suffix}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report["report_path"] = str(path)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
