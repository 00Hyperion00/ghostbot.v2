from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradebot.paper_sandbox_dry_run_runtime_harness import build_report  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=str(ROOT))
    parser.add_argument("--reports-dir", default=None)
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    report = build_report(Path(args.repo_root), Path(args.reports_dir) if args.reports_dir else None, write_reports=False)
    print(json.dumps(report, sort_keys=True, ensure_ascii=False))
    return 0 if report.get("status") == "READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
