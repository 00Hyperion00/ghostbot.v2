from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tradebot.hyp005_shadow_observation_identity import (  # noqa: E402
    HYP005_SHADOW_OBSERVATION_END_TO_END_IDENTITY_VERSION,
    assert_artifact_equivalence,
    canonical_event_key,
    stable_observation_id,
)


def _latest(directory: Path, pattern: str) -> Path | None:
    matches = sorted(directory.glob(pattern), key=lambda item: (item.stat().st_mtime_ns, item.name), reverse=True)
    return matches[0] if matches else None


def _read_json(path: Path | None) -> Any:
    return None if path is None else json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path | None) -> list[dict[str, Any]]:
    if path is None:
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _rows_from_report(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, Mapping):
        return []
    rows = payload.get("shadow_observations")
    return list(rows) if isinstance(rows, list) else []


def _all_canonical(rows: list[dict[str, Any]]) -> bool:
    return all(row.get("observation_id") == stable_observation_id(row) for row in rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only HYP-005 end-to-end canonical identity chain audit")
    parser.add_argument("--reports-dir", type=Path, required=True)
    parser.add_argument("--require-runtime-chain", action="store_true")
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    reports_dir = args.reports_dir.resolve()

    ledger_jsonl = _latest(reports_dir, "4B436625V_hyp005_shadow_observation_ledger_*.jsonl")
    ledger_json = _latest(reports_dir, "4B436625V_hyp005_shadow_observation_ledger_*.json")
    logger_report = _latest(reports_dir, "4B436625V_hyp005_shadow_observation_logger_*.json")
    merged_jsonl = _latest(reports_dir, "4B436625X_hyp005_shadow_merged_ledger_*.jsonl")

    jsonl_rows = _read_jsonl(ledger_jsonl)
    json_payload = _read_json(ledger_json)
    json_rows = list(json_payload) if isinstance(json_payload, list) else []
    report_payload = _read_json(logger_report)
    report_rows = _rows_from_report(report_payload)
    merged_rows = _read_jsonl(merged_jsonl)

    artifact_equivalent = False
    try:
        assert_artifact_equivalence(json_rows, jsonl_rows, report_rows)
        artifact_equivalent = bool(ledger_json and ledger_jsonl and logger_report)
    except ValueError:
        artifact_equivalent = False

    latest_bundle_canonical = bool(jsonl_rows or json_rows or report_rows) and all(
        _all_canonical(rows) for rows in (json_rows, jsonl_rows, report_rows)
    )
    merged_ledger_canonical = bool(merged_jsonl) and _all_canonical(merged_rows)
    report_declares_h2 = isinstance(report_payload, Mapping) and (
        report_payload.get("identity_chain_contract_version") == HYP005_SHADOW_OBSERVATION_END_TO_END_IDENTITY_VERSION
        and report_payload.get("canonical_identity_end_to_end") is True
        and report_payload.get("identity_artifact_equivalence_verified") is True
    )
    active_runtime_chain_ready = artifact_equivalent and latest_bundle_canonical and merged_ledger_canonical and report_declares_h2
    report = {
        "ok": active_runtime_chain_ready if args.require_runtime_chain else artifact_equivalent,
        "read_only": True,
        "identity_contract_version": HYP005_SHADOW_OBSERVATION_END_TO_END_IDENTITY_VERSION,
        "ledger_json": str(ledger_json) if ledger_json else None,
        "ledger_jsonl": str(ledger_jsonl) if ledger_jsonl else None,
        "logger_report": str(logger_report) if logger_report else None,
        "merged_ledger_jsonl": str(merged_jsonl) if merged_jsonl else None,
        "logger_bundle_rows": len(jsonl_rows),
        "merged_ledger_rows": len(merged_rows),
        "json_jsonl_report_equivalent": artifact_equivalent,
        "latest_logger_bundle_canonical": latest_bundle_canonical,
        "logger_report_declares_h2": report_declares_h2,
        "merged_ledger_canonical": merged_ledger_canonical,
        "active_runtime_chain_ready": active_runtime_chain_ready,
        "config_mutation_performed": False,
        "scheduler_mutation_performed": False,
        "trading_action_performed": False,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
