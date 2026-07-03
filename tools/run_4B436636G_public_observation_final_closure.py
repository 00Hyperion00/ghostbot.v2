from __future__ import annotations

import argparse
import json
from pathlib import Path

from tradebot.public_observation_final_closure import evaluate_public_observation_final_closure


def main() -> int:
    parser = argparse.ArgumentParser(description="4B.4.3.6.6.36G Public Observation Final Closure runner")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--reports-dir", default="reports/recovery")
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    result = evaluate_public_observation_final_closure(
        repo_root=Path(args.repo_root),
        reports_dir=Path(args.reports_dir),
        write_reports=True,
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
