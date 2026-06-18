from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

CONTRACT_VERSION = "4B.4.3.6.6.28G-H2"
REPORT_TYPE = "hyp006_r1_candidate_near_miss_scan_instrumentation_no_order_research_diagnostics"
REPORT_PREFIX = "4B436628G_H2_hyp006_r1_candidate_near_miss_scan_instrumentation"
BRANCH_ID = "HYP-006-R1"
HYPOTHESIS_ID = "HYP-006"
STRATEGY_FAMILY = "short_failed_liquidity_sweep_continuation"
LEDGER_GLOB = "4B436628D_hyp006_r1_shadow_ledger_*.jsonl"
TRACKING_GLOB = "4B436628G_hyp006_r1_shadow_sample_expansion_acceptance_tracking_*.json"
STAGNATION_GLOB = "4B436628G_H1_hyp006_r1_signal_frequency_stagnation_diagnostics_*.json"
CANDIDATE_FILE_KEYWORDS = (
    "candidate",
    "near_miss",
    "near-miss",
    "trigger",
    "gate",
    "reject",
    "rejection",
)
EXCLUDED_SCAN_NAME_PARTS = (
    "4B436628G_H1_",
    "4B436628G_H2_",
    "operator_cockpit",
    "acceptance_tracking",
    "continuity_delta",
    "dashboard_delta",
    "shadow_sample_expansion",
    "shadow_ledger",
    "shadow_observation_logger",
)
NO_MUTATION_FLAGS: dict[str, bool] = {
    "read_only": True,
    "network_request_performed": False,
    "config_mutation_performed": False,
    "scheduler_mutation_performed": False,
    "scheduler_task_created": False,
    "scheduler_task_modified": False,
    "strategy_parameter_mutation_performed": False,
    "training_performed": False,
    "reload_performed": False,
    "trading_action_performed": False,
    "order_actions_performed": False,
    "post_requests_allowed": False,
    "paper_live_order_enablement_present": False,
}
GATE_ALIASES: dict[str, str] = {
    "sweep": "SWEEP_CONDITION",
    "liquidity_sweep": "SWEEP_CONDITION",
    "failed_sweep": "FAILED_SWEEP_CONDITION",
    "continuation": "CONTINUATION_CONFIRMATION",
    "confirmation": "CONTINUATION_CONFIRMATION",
    "volume": "VOLUME_COMPRESSION_OR_EXPANSION",
    "volatility": "VOLATILITY_FILTER",
    "spread": "SPREAD_SLIPPAGE_FILTER",
    "slippage": "SPREAD_SLIPPAGE_FILTER",
    "quality": "DATA_QUALITY_FILTER",
    "sample": "SAMPLE_TARGET",
    "positive_rate": "WALK_FORWARD_POSITIVE_RATE",
    "walk_forward": "WALK_FORWARD_POSITIVE_RATE",
}


@dataclass(frozen=True)
class LedgerSnapshot:
    path: Path
    row_count: int
    unique_count: int
    symbols: Counter[str]
    earliest_observation_utc: str | None
    latest_observation_utc: str | None
    length_bytes: int
    modified_utc: str


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def utc_now_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object at {path}")
    return data


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for line_no, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            value = json.loads(stripped)
            if not isinstance(value, dict):
                raise ValueError(f"Expected JSON object at {path}:{line_no}")
            rows.append(value)
    return rows


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def write_markdown(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    candidate = payload.get("candidate_trigger_instrumentation", {})
    gate_counter = candidate.get("gate_block_counter", {}) if isinstance(candidate, Mapping) else {}
    symbol_counter = candidate.get("symbol_candidate_counter", {}) if isinstance(candidate, Mapping) else {}
    lines = [
        f"# {CONTRACT_VERSION} HYP-006 Candidate / Near-Miss Scan Instrumentation",
        "",
        f"- decision: `{payload.get('decision')}`",
        f"- branch_id: `{payload.get('branch_id')}`",
        f"- read_only: `{payload.get('read_only')}`",
        f"- raw_candidate_scan_artifact_found: `{candidate.get('raw_candidate_scan_artifact_found') if isinstance(candidate, Mapping) else None}`",
        f"- candidate_count: `{candidate.get('candidate_count') if isinstance(candidate, Mapping) else None}`",
        f"- near_miss_count: `{candidate.get('near_miss_count') if isinstance(candidate, Mapping) else None}`",
        f"- trigger_count: `{candidate.get('trigger_count') if isinstance(candidate, Mapping) else None}`",
        f"- current_unique_observation_ids: `{payload.get('current_unique_observation_ids')}`",
        f"- new_unique_observation_count_latest_delta: `{payload.get('new_unique_observation_count_latest_delta')}`",
        f"- target_remaining_count: `{payload.get('target_remaining_count')}`",
        "",
        "## Gate block counter",
        "",
    ]
    if isinstance(gate_counter, Mapping) and gate_counter:
        for gate, count in sorted(gate_counter.items(), key=lambda item: (-int(item[1]), str(item[0]))):
            lines.append(f"- `{gate}`: `{count}`")
    else:
        lines.append("- No raw candidate gate block data was available.")
    lines.extend(["", "## Symbol candidate counter", ""])
    if isinstance(symbol_counter, Mapping) and symbol_counter:
        for symbol, count in sorted(symbol_counter.items(), key=lambda item: (-int(item[1]), str(item[0]))):
            lines.append(f"- `{symbol}`: `{count}`")
    else:
        lines.append("- No raw symbol candidate data was available.")
    lines.extend([
        "",
        "## Recommendation",
        "",
        str(payload.get("recommendation", "")),
        "",
        "## Safety",
        "",
        "This report is read-only and does not approve parameter relaxation, paper trading, live trading, model reload, training, or order placement.",
        "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def stable_json_dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def normalize_gate_name(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return "UNKNOWN_GATE"
    upper = text.upper().replace(" ", "_").replace("-", "_")
    lower = upper.lower()
    for token, alias in GATE_ALIASES.items():
        if token in lower:
            return alias
    return upper


def as_sequence(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def first_string(record: Mapping[str, Any], keys: Sequence[str]) -> str | None:
    for key in keys:
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "1", "y", "triggered", "pass", "passed"}
    return False


def is_near_miss_record(record: Mapping[str, Any], source_hint: str) -> bool:
    if "near" in source_hint.lower() and "miss" in source_hint.lower():
        return True
    for key in ("near_miss", "is_near_miss", "nearMiss", "near_miss_candidate"):
        if boolish(record.get(key)):
            return True
    status = str(record.get("status") or record.get("decision") or record.get("classification") or "").lower()
    return "near" in status and "miss" in status


def is_trigger_record(record: Mapping[str, Any], source_hint: str) -> bool:
    if "trigger" in source_hint.lower():
        return True
    for key in ("triggered", "is_trigger", "trigger", "signal_triggered"):
        if boolish(record.get(key)):
            return True
    status = str(record.get("status") or record.get("decision") or record.get("classification") or "").lower()
    return "trigger" in status or "candidate" in status and "rejected" not in status


def collect_gate_values(record: Mapping[str, Any]) -> list[str]:
    values: list[str] = []
    for key in (
        "gate",
        "blocked_gate",
        "failed_gate",
        "rejected_gate",
        "rejection_gate",
        "reject_gate",
        "reason_code",
        "reject_reason",
        "rejection_reason",
        "blocker",
    ):
        if key in record:
            values.extend(str(item) for item in as_sequence(record.get(key)) if item is not None)
    for key in ("reason_codes", "blockers", "failed_gates", "failed_metric_codes", "rejection_reasons"):
        value = record.get(key)
        if isinstance(value, list):
            values.extend(str(item) for item in value if item is not None)
    return [normalize_gate_name(value) for value in values if str(value).strip()]


def flatten_event_records(value: Any, key_path: str = "") -> list[tuple[str, Mapping[str, Any]]]:
    records: list[tuple[str, Mapping[str, Any]]] = []
    if isinstance(value, dict):
        lower_path = key_path.lower()
        if any(token in lower_path for token in ("candidate", "near_miss", "near-miss", "trigger", "rejection", "reject")):
            if any(field in value for field in ("symbol", "status", "decision", "gate", "blockers", "reason_codes", "triggered", "near_miss")):
                records.append((key_path, value))
        for key, child in value.items():
            child_path = f"{key_path}.{key}" if key_path else str(key)
            records.extend(flatten_event_records(child, child_path))
    elif isinstance(value, list):
        lower_path = key_path.lower()
        for idx, item in enumerate(value):
            child_path = f"{key_path}[{idx}]"
            if isinstance(item, dict) and any(token in lower_path for token in ("candidate", "near_miss", "near-miss", "trigger", "rejection", "reject", "rows", "events")):
                records.append((key_path, item))
            records.extend(flatten_event_records(item, child_path))
    return records


def find_candidate_scan_files(reports_dir: Path) -> list[Path]:
    files: list[Path] = []
    for path in reports_dir.rglob("*.json"):
        name = path.name.lower()
        if any(excluded.lower() in name for excluded in EXCLUDED_SCAN_NAME_PARTS):
            continue
        if any(keyword in name for keyword in CANDIDATE_FILE_KEYWORDS):
            files.append(path)
    return sorted(files, key=lambda item: item.stat().st_mtime, reverse=True)


def summarize_ledger(path: Path) -> LedgerSnapshot:
    rows = read_jsonl(path)
    observation_ids: set[str] = set()
    symbols: Counter[str] = Counter()
    timestamps: list[str] = []
    for row in rows:
        observation_id = row.get("observation_id") or row.get("id")
        if observation_id is not None:
            observation_ids.add(str(observation_id))
        symbol = row.get("symbol")
        if symbol is not None:
            symbols[str(symbol)] += 1
        timestamp = row.get("timestamp_utc") or row.get("event_time_utc") or row.get("open_time_utc")
        if timestamp is not None:
            timestamps.append(str(timestamp))
    stat = path.stat()
    modified_utc = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
    return LedgerSnapshot(
        path=path,
        row_count=len(rows),
        unique_count=len(observation_ids) if observation_ids else len(rows),
        symbols=symbols,
        earliest_observation_utc=min(timestamps) if timestamps else None,
        latest_observation_utc=max(timestamps) if timestamps else None,
        length_bytes=stat.st_size,
        modified_utc=modified_utc,
    )


def latest_json(reports_dir: Path, pattern: str) -> dict[str, Any] | None:
    files = sorted(reports_dir.glob(pattern), key=lambda item: item.stat().st_mtime, reverse=True)
    if not files:
        return None
    return read_json(files[0])


def count_candidate_records(files: Sequence[Path]) -> dict[str, Any]:
    gate_block_counter: Counter[str] = Counter()
    symbol_candidate_counter: Counter[str] = Counter()
    symbol_near_miss_counter: Counter[str] = Counter()
    source_file_counter: Counter[str] = Counter()
    candidate_count = 0
    near_miss_count = 0
    trigger_count = 0
    sample_records: list[dict[str, Any]] = []
    parse_errors: list[dict[str, str]] = []

    for path in files:
        try:
            payload = read_json(path)
        except Exception as exc:  # pragma: no cover - defensive diagnostic path
            parse_errors.append({"path": str(path), "error": str(exc)})
            continue
        records = flatten_event_records(payload, path.name)
        source_file_counter[str(path)] += len(records)
        for source_hint, record in records:
            candidate_count += 1
            symbol = first_string(record, ("symbol", "asset", "pair", "market")) or "UNKNOWN"
            symbol_candidate_counter[symbol] += 1
            if is_near_miss_record(record, source_hint):
                near_miss_count += 1
                symbol_near_miss_counter[symbol] += 1
            if is_trigger_record(record, source_hint):
                trigger_count += 1
            gate_values = collect_gate_values(record)
            if gate_values:
                gate_block_counter.update(gate_values)
            elif not is_trigger_record(record, source_hint):
                gate_block_counter["UNCLASSIFIED_CANDIDATE_REJECTION"] += 1
            if len(sample_records) < 25:
                sample_records.append(
                    {
                        "source": str(path),
                        "source_hint": source_hint,
                        "symbol": symbol,
                        "near_miss": is_near_miss_record(record, source_hint),
                        "trigger": is_trigger_record(record, source_hint),
                        "gates": gate_values,
                    }
                )

    return {
        "raw_candidate_scan_artifact_found": bool(files),
        "candidate_scan_files": [str(path) for path in files[:25]],
        "candidate_scan_files_found": len(files),
        "candidate_count": candidate_count,
        "near_miss_count": near_miss_count,
        "trigger_count": trigger_count,
        "gate_block_counter": dict(gate_block_counter),
        "symbol_candidate_counter": dict(symbol_candidate_counter),
        "symbol_near_miss_counter": dict(symbol_near_miss_counter),
        "source_file_record_counter": dict(source_file_counter),
        "sample_candidate_records": sample_records,
        "parse_errors": parse_errors,
    }


def collect_blockers_from_latest_reports(reports_dir: Path) -> Counter[str]:
    blockers: Counter[str] = Counter()
    for pattern in (TRACKING_GLOB, STAGNATION_GLOB):
        payload = latest_json(reports_dir, pattern)
        if not payload:
            continue
        for blocker in payload.get("blockers", []) if isinstance(payload.get("blockers"), list) else []:
            blockers[normalize_gate_name(blocker)] += 1
        metrics: Any = payload.get("gate_diagnostics")
        if metrics is None and isinstance(payload.get("acceptance_tracking_metrics"), dict):
            metrics = payload["acceptance_tracking_metrics"].get("metric_results")
        if isinstance(metrics, list):
            for metric in metrics:
                if isinstance(metric, dict) and not bool(metric.get("passed")):
                    blockers[normalize_gate_name(metric.get("name"))] += 1
    return blockers


def build_instrumentation_report(reports_dir: Path, *, max_candidate_files: int = 50) -> dict[str, Any]:
    ledgers = sorted(reports_dir.glob(LEDGER_GLOB), key=lambda item: item.stat().st_mtime, reverse=True)
    ledger_snapshots = [summarize_ledger(path) for path in ledgers[:5]]
    latest = ledger_snapshots[0] if ledger_snapshots else None
    previous = ledger_snapshots[1] if len(ledger_snapshots) > 1 else None
    new_unique_delta = 0
    if latest and previous:
        new_unique_delta = latest.unique_count - previous.unique_count

    candidate_files = find_candidate_scan_files(reports_dir)[:max_candidate_files]
    candidate_summary = count_candidate_records(candidate_files)
    existing_blockers = collect_blockers_from_latest_reports(reports_dir)
    merged_gate_counter = Counter(candidate_summary["gate_block_counter"])
    if not merged_gate_counter:
        merged_gate_counter.update(existing_blockers)
    candidate_summary["gate_block_counter"] = dict(merged_gate_counter)
    candidate_summary["fallback_acceptance_block_counter_used"] = bool(existing_blockers and not candidate_summary["raw_candidate_scan_artifact_found"])
    candidate_summary["instrumentation_limitation"] = (
        "No raw candidate/near-miss scan artifact found; gate counters fall back to latest 28G/28G-H1 blockers."
        if not candidate_summary["raw_candidate_scan_artifact_found"]
        else "Raw candidate/near-miss artifacts found and summarized."
    )

    current_unique = latest.unique_count if latest else 0
    target_remaining = max(0, 30 - current_unique)
    no_new_observations = new_unique_delta <= 0
    raw_scan_missing = not candidate_summary["raw_candidate_scan_artifact_found"]
    blockers = [
        "NO_NEW_SHADOW_OBSERVATIONS_SINCE_28F_BASELINE" if no_new_observations else "NEW_SHADOW_OBSERVATIONS_DETECTED",
        "SHADOW_SAMPLE_COUNT_BELOW_TARGET" if target_remaining else "SHADOW_SAMPLE_TARGET_REACHED",
    ]
    if raw_scan_missing:
        blockers.append("RAW_CANDIDATE_NEAR_MISS_SCAN_ARTIFACT_NOT_FOUND")
    if candidate_summary["near_miss_count"] == 0:
        blockers.append("NEAR_MISS_EVENTS_NOT_OBSERVED_OR_NOT_INSTRUMENTED")
    blockers.extend([key for key in existing_blockers if key not in blockers and not key.startswith("NEW_")])

    return {
        **NO_MUTATION_FLAGS,
        "ok": True,
        "contract_version": CONTRACT_VERSION,
        "report_type": REPORT_TYPE,
        "decision": "HYP006_R1_CANDIDATE_NEAR_MISS_SCAN_INSTRUMENTATION_READY",
        "generated_at_utc": utc_now(),
        "branch_id": BRANCH_ID,
        "hypothesis_id": HYPOTHESIS_ID,
        "strategy_family": STRATEGY_FAMILY,
        "approved_for_signal_frequency_review": True,
        "approved_for_candidate_near_miss_diagnostics": True,
        "approved_for_parameter_relaxation_candidate": False,
        "approved_for_acceptance_review_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "current_unique_observation_ids": current_unique,
        "new_unique_observation_count_latest_delta": new_unique_delta,
        "target_remaining_count": target_remaining,
        "ledger_runs_observed": len(ledger_snapshots),
        "ledger_snapshots": [
            {
                "path": str(snapshot.path),
                "row_count": snapshot.row_count,
                "unique_count": snapshot.unique_count,
                "length_bytes": snapshot.length_bytes,
                "modified_utc": snapshot.modified_utc,
                "earliest_observation_utc": snapshot.earliest_observation_utc,
                "latest_observation_utc": snapshot.latest_observation_utc,
                "symbols": dict(snapshot.symbols),
            }
            for snapshot in ledger_snapshots
        ],
        "candidate_trigger_instrumentation": candidate_summary,
        "blockers": blockers,
        "risk_items": [
            {
                "level": "critical",
                "code": "NO_ORDER_RESEARCH_DIAGNOSTIC_ONLY",
                "detail": "This instrumentation reads/writes diagnostic artifacts only and does not approve trading.",
            },
            {
                "level": "warning",
                "code": "RAW_CANDIDATE_SCAN_REQUIRED_BEFORE_PARAMETER_RELAXATION",
                "detail": "Threshold or parameter relaxation is not permitted without raw candidate/near-miss evidence.",
            },
            {
                "level": "warning",
                "code": "HYP006_SAMPLE_EXPANSION_STALLED",
                "detail": "HYP-006 still needs additional unique observations before acceptance review.",
            },
        ],
        "next_required_gate": "28G_H2_REVIEW_CANDIDATE_NEAR_MISS_INSTRUMENTATION_OR_ADD_RAW_SCAN_HOOK",
        "recommendation": (
            "Raw HYP-006 candidate/near-miss scan artifacts are still required before any parameter relaxation. "
            "Keep no-order collection running and add integrated raw scan hooks only through a separate read-only research gate if missing."
            if raw_scan_missing
            else "Review candidate/near-miss gate counters before any separate research-only parameter sensitivity analysis."
        ),
    }


def run_report(reports_dir: Path, out_dir: Path) -> dict[str, Any]:
    payload = build_instrumentation_report(reports_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = utc_now_compact()
    report_json = out_dir / f"{REPORT_PREFIX}_{stamp}.json"
    report_md = out_dir / f"{REPORT_PREFIX}_{stamp}.md"
    payload["report_json"] = str(report_json)
    payload["report_md"] = str(report_md)
    write_json(report_json, payload)
    write_markdown(report_md, payload)
    return payload


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run 28G-H2 HYP-006 candidate/near-miss instrumentation diagnostics.")
    parser.add_argument("--reports-dir", type=Path, default=Path("reports/hyp006_r1_canonical"))
    parser.add_argument("--out-dir", type=Path, default=Path("reports/hyp006_r1_canonical"))
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args(argv)
    payload = run_report(args.reports_dir, args.out_dir)
    if args.once_json:
        print(stable_json_dump(payload))
    else:
        summary = payload["candidate_trigger_instrumentation"]
        print(f"{CONTRACT_VERSION} HYP-006 candidate/near-miss instrumentation {payload['decision']}")
        print(f" - read_only: {payload['read_only']}")
        print(f" - raw_candidate_scan_artifact_found: {summary['raw_candidate_scan_artifact_found']}")
        print(f" - candidate_scan_files_found: {summary['candidate_scan_files_found']}")
        print(f" - candidate_count: {summary['candidate_count']}")
        print(f" - near_miss_count: {summary['near_miss_count']}")
        print(f" - trigger_count: {summary['trigger_count']}")
        print(f" - fallback_acceptance_block_counter_used: {summary['fallback_acceptance_block_counter_used']}")
        print(f" - current_unique_observation_ids: {payload['current_unique_observation_ids']}")
        print(f" - target_remaining_count: {payload['target_remaining_count']}")
        print(f" - approved_for_parameter_relaxation_candidate: {payload['approved_for_parameter_relaxation_candidate']}")
        print(f" - approved_for_paper_candidate: {payload['approved_for_paper_candidate']}")
        print(f" - approved_for_live_real: {payload['approved_for_live_real']}")
        print(f" - training_performed: {payload['training_performed']}")
        print(f" - reload_performed: {payload['reload_performed']}")
        print(f" - trading_action_performed: {payload['trading_action_performed']}")
        print(f"report_json: {payload['report_json']}")
        print(f"report_md: {payload['report_md']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
