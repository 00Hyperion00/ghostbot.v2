from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tradebot.hyp005_shadow_observation_identity import (  # noqa: E402
    canonical_event_key,
    stable_observation_id,
)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _latest_two(reports_dir: Path) -> tuple[Path, Path]:
    matches = sorted(
        reports_dir.glob("4B436625V_hyp005_shadow_observation_ledger_*.jsonl"),
        key=lambda item: (item.stat().st_mtime_ns, item.name),
        reverse=True,
    )
    if len(matches) < 2:
        raise RuntimeError("HYP005_STABLE_IDENTITY_REQUIRES_TWO_25V_LEDGERS")
    return matches[0], matches[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only HYP-005 stable identity drift audit")
    parser.add_argument("--reports-dir", type=Path, required=True)
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    current_path, previous_path = _latest_two(args.reports_dir.resolve())
    current = _read_jsonl(current_path)
    previous = _read_jsonl(previous_path)
    current_map = {canonical_event_key(row): row for row in current}
    previous_map = {canonical_event_key(row): row for row in previous}
    current_keys = set(current_map)
    previous_keys = set(previous_map)
    stable_keys = current_keys & previous_keys
    raw_drift = sum(
        current_map[key].get("observation_id") != previous_map[key].get("observation_id")
        for key in stable_keys
    )
    projected_drift = sum(
        stable_observation_id(current_map[key]) != stable_observation_id(previous_map[key])
        for key in stable_keys
    )
    report = {
        "ok": True,
        "read_only": True,
        "previous_ledger": str(previous_path),
        "current_ledger": str(current_path),
        "previous_canonical_samples": len(previous_keys),
        "current_canonical_samples": len(current_keys),
        "newly_added_samples": len(current_keys - previous_keys),
        "removed_samples": len(previous_keys - current_keys),
        "stable_samples": len(stable_keys),
        "raw_observation_id_drift_count": raw_drift,
        "projected_stable_identity_drift_count": projected_drift,
        "stable_identity_ready": projected_drift == 0,
        "config_mutation_performed": False,
        "scheduler_mutation_performed": False,
        "trading_action_performed": False,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["stable_identity_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
