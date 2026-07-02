
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tradebot.canonical_evidence_phase_hygiene import check_canonical_evidence_phase_hygiene


def main() -> int:
    parser = argparse.ArgumentParser(description="Check 4B436633B canonical evidence and phase hygiene cleanup")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()

    payload = check_canonical_evidence_phase_hygiene(Path(args.repo_root).resolve())
    print(json.dumps(payload, indent=None if args.once_json else 2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
