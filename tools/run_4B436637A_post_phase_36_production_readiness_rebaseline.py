from __future__ import annotations

import argparse
import json
from pathlib import Path

from tradebot.post_phase_36_production_readiness_rebaseline import evaluate_post_phase_36_production_readiness_rebaseline


def main() -> int:
    parser = argparse.ArgumentParser(description="4B.4.3.6.6.37A Post-Phase-36 Production Readiness Re-Baseline runner")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--reports-dir", default="reports/recovery")
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    result = evaluate_post_phase_36_production_readiness_rebaseline(
        repo_root=Path(args.repo_root),
        reports_dir=Path(args.reports_dir),
        write_reports=True,
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
