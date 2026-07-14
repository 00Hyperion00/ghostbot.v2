from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Check 4B436661 release audit pytest collection hygiene")
    parser.add_argument("--once-json", action="store_true", help="emit one JSON result")
    args = parser.parse_args()

    root = _project_root()
    sys.path.insert(0, str(root / "src"))

    from tradebot.release_audit_pytest_collection_hygiene import build_release_audit_snapshot

    result = build_release_audit_snapshot(root)
    if args.once_json:
        print(json.dumps(result, sort_keys=True))
    else:
        print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("ok") is True else 2


if __name__ == "__main__":
    raise SystemExit(main())
