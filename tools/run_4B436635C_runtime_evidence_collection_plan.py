from __future__ import annotations

import argparse
import json
from pathlib import Path

from tradebot.runtime_evidence_collection_plan import evaluate


def main() -> int:
    parser = argparse.ArgumentParser(description="4B.4.3.6.6.35C runtime evidence collection plan runner")
    parser.add_argument("--root", default=".")
    parser.add_argument("--reports-dir", default="reports/recovery")
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    result = evaluate(Path(args.root), Path(args.reports_dir), write_reports=True)
    print(json.dumps(result, sort_keys=True, ensure_ascii=False))
    return 0 if result.get("ok") else 2

if __name__ == "__main__":
    raise SystemExit(main())
