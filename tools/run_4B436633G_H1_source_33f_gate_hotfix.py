from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_4B436633G_H1_source_33f_gate_hotfix import build_summary

PATCH_ID = "4B436633G_H1"


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run 4B436633G-H1 source 33F gate hotfix")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--reports-dir", default="reports/recovery")
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    repo_root = Path(args.repo_root).resolve()
    reports_dir = Path(args.reports_dir)
    if not reports_dir.is_absolute():
        reports_dir = repo_root / reports_dir
    summary = build_summary(repo_root)
    ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    suffix = "ready" if summary.get("ok") else "not_ready"
    report_path = reports_dir / f"{PATCH_ID}_source_33f_gate_hotfix_{ts}_{suffix}.json"
    _write_json(report_path, summary)
    summary = dict(summary)
    summary["report_path"] = str(report_path)
    print(json.dumps(summary, sort_keys=True, ensure_ascii=False) if args.once_json else json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
