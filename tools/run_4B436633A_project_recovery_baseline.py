from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _ensure_src_on_path(repo_root: Path) -> None:
    src = str((repo_root / "src").resolve())
    if src not in sys.path:
        sys.path.insert(0, src)


def main() -> int:
    parser = argparse.ArgumentParser(description="4B.4.3.6.6.33A project recovery baseline runner")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--reports-dir", default="reports/recovery")
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    _ensure_src_on_path(repo_root)

    from tradebot.project_recovery_baseline import run_project_recovery_baseline

    reports_dir = Path(args.reports_dir)
    if not reports_dir.is_absolute():
        reports_dir = repo_root / reports_dir

    report, report_path = run_project_recovery_baseline(repo_root, reports_dir)
    payload = report.to_dict()
    payload["report_path"] = str(report_path)

    if args.once_json:
        print(json.dumps(payload, sort_keys=True, ensure_ascii=False))
    else:
        print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))

    return 0 if report.status == "READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
