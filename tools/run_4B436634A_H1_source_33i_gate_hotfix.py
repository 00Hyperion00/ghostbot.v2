
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tools.check_4B436634A_H1_source_33i_gate_hotfix import check

PATCH_ID = "4B436634A_H1"


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run 34A-H1 source 33I gate hotfix evidence.")
    parser.add_argument("--reports-dir", default="reports/recovery")
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    summary = check()
    reports_dir = (ROOT / args.reports_dir).resolve() if not Path(args.reports_dir).is_absolute() else Path(args.reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    suffix = "ready" if summary["ok"] else "not_ready"
    report_path = reports_dir / f"{PATCH_ID}_source_33i_gate_hotfix_{utc_timestamp()}_{suffix}.json"
    payload = dict(summary)
    payload["report_path"] = str(report_path)
    report_path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(payload, sort_keys=True, ensure_ascii=False))
    return 0 if summary["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
