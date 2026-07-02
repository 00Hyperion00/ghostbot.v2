
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tradebot.canonical_evidence_phase_hygiene import run_canonical_evidence_phase_hygiene


def main() -> int:
    parser = argparse.ArgumentParser(description="Run 4B436633B canonical evidence and phase hygiene cleanup")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--reports-dir", default="reports/recovery")
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()

    root = Path(args.repo_root).resolve()
    report, paths = run_canonical_evidence_phase_hygiene(root, Path(args.reports_dir))
    payload = report.to_dict()
    payload["written_reports"] = {key: str(path) for key, path in paths.items()}
    print(json.dumps(payload, indent=None if args.once_json else 2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
