from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

def _root() -> Path:
    return Path(__file__).resolve().parents[1]

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    root = _root()
    src = str(root / "src")
    if src not in sys.path:
        sys.path.insert(0, src)
    from tradebot.release_audit_legacy_api_drift_compatibility_v2 import build_legacy_api_drift_compatibility_v2_snapshot

    snapshot = build_legacy_api_drift_compatibility_v2_snapshot(root)
    if args.once_json:
        print(json.dumps(snapshot, sort_keys=True))
    else:
        print(json.dumps(snapshot, indent=2, sort_keys=True))
    return 0 if snapshot["ok"] else 2

if __name__ == "__main__":
    raise SystemExit(main())
