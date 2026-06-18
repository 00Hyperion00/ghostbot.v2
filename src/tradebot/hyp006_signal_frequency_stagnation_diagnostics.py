from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

CONTRACT_VERSION = "4B.4.3.6.6.28G-H1"
REPORT_TYPE = "hyp006_r1_signal_frequency_candidate_trigger_stagnation_diagnostics_report"
BRANCH_ID = "HYP-006-R1"
HYPOTHESIS_ID = "HYP-006"
REPORT_PREFIX = "4B436628G_H1_hyp006_r1_signal_frequency_stagnation_diagnostics"
LEDGER_GLOB = "4B436628D_hyp006_r1_shadow_ledger_*.jsonl"
TRACKING_GLOB = "4B436628G_hyp006_r1_shadow_sample_expansion_acceptance_tracking_*.json"
CANDIDATE_SCAN_KEYWORDS = (
    "candidate",
    "near_miss",
    "near-miss",
    "trigger",
    "gate_count",
    "rejection",
    "reject",
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


@dataclass(frozen=True)
class LedgerSnapshot:
    path: Path
    sha256: str
    row_count: int
    unique_count: int
    observation_ids: frozenset[str]
    symbols: Counter[str]
    earliest_observation_utc: str | None
    latest_observation_utc: str | None
    modified_utc: str
    length_bytes: int


def utc_now_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Expected object JSON: {path}")
    return data


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def write_markdown(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# {CONTRACT_VERSION} HYP-006 Signal Frequency / Candidate Trigger Stagnation Diagnostics",
        "",
        f"- decision: `{payload.get('decision')}`",
        f"- branch: `{payload.get('branch_id')}`",
        f"- read_only: `{payload.get('read_only')}`",
        f"- current_unique_observation_ids: `{payload.get('current_unique_observation_ids')}`",
        f"- new_unique_observation_count_latest_delta: `{payload.get('new_unique_observation_count_latest_delta')}`",
        f"- stagnation_detected: `{payload.get('stagnation_detected')}`",
        f"- target_remaining_count: `{payload.get('target_remaining_count')}`",
        "",
        "## Blockers",
    ]
    for blocker in payload.get("blockers", []):
        lines.append(f"- `{blocker}`")
    lines.extend(["", "## Gate diagnostics"])
    for item in payload.get("gate_diagnostics", []):
        lines.append(
            f"- `{item.get('name')}` value=`{item.get('value')}` threshold=`{item.get('threshold')}` passed=`{item.get('passed')}`"
        )
    lines.extend(["", "## Recommendation", "", str(payload.get("recommendation", "")), ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for line_number, raw_line in enumerate(handle, 1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL row {line_number} in {path}: {exc}") from exc
            if isinstance(row, dict):
                rows.append(row)
    return rows


def _row_observation_id(row: Mapping[str, Any]) -> str | None:
    for key in ("observation_id", "id", "shadow_observation_id"):
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    symbol = row.get("symbol")
    timestamp = row.get("timestamp_utc") or row.get("event_time_utc") or row.get("open_time_utc")
    if isinstance(symbol, str) and isinstance(timestamp, str):
        return f"{BRANCH_ID}-{symbol}-{timestamp}"
    return None


def _row_timestamp(row: Mapping[str, Any]) -> str | None:
    for key in ("timestamp_utc", "event_time_utc", "open_time_utc", "generated_at_utc"):
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def build_ledger_snapshot(path: Path) -> LedgerSnapshot:
    rows = parse_jsonl(path)
    observation_ids = frozenset(
        obs_id for row in rows if (obs_id := _row_observation_id(row)) is not None
    )
    symbols: Counter[str] = Counter()
    timestamps: list[str] = []
    for row in rows:
        symbol = row.get("symbol")
        if isinstance(symbol, str) and symbol.strip():
            symbols[symbol.strip()] += 1
        timestamp = _row_timestamp(row)
        if timestamp:
            timestamps.append(timestamp)
    stat = path.stat()
    return LedgerSnapshot(
        path=path,
        sha256=sha256_file(path),
        row_count=len(rows),
        unique_count=len(observation_ids),
        observation_ids=observation_ids,
        symbols=symbols,
        earliest_observation_utc=min(timestamps) if timestamps else None,
        latest_observation_utc=max(timestamps) if timestamps else None,
        modified_utc=datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
        length_bytes=stat.st_size,
    )


def find_latest(paths: Sequence[Path]) -> Path | None:
    existing = [path for path in paths if path.exists()]
    if not existing:
        return None
    return max(existing, key=lambda item: item.stat().st_mtime)


def sorted_recent(paths: Iterable[Path], limit: int) -> list[Path]:
    return sorted((path for path in paths if path.exists()), key=lambda item: item.stat().st_mtime, reverse=True)[:limit]


def _safe_get(data: Mapping[str, Any], *keys: str) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current


def latest_tracking_report(reports_dir: Path) -> dict[str, Any] | None:
    latest = find_latest(list(reports_dir.glob(TRACKING_GLOB)))
    return read_json(latest) if latest else None


def summarize_tracking_metrics(tracking: Mapping[str, Any] | None) -> tuple[list[dict[str, Any]], list[str]]:
    if tracking is None:
        return [], ["LATEST_28G_TRACKING_REPORT_NOT_FOUND"]
    metrics = _safe_get(tracking, "acceptance_tracking_metrics", "metric_results")
    blockers = tracking.get("blockers", [])
    normalized_blockers = [str(item) for item in blockers] if isinstance(blockers, list) else []
    normalized_metrics: list[dict[str, Any]] = []
    if isinstance(metrics, list):
        for item in metrics:
            if isinstance(item, Mapping):
                normalized_metrics.append(
                    {
                        "name": item.get("name"),
                        "value": item.get("value"),
                        "threshold": item.get("threshold"),
                        "operator": item.get("operator"),
                        "passed": bool(item.get("passed")),
                        "delta": item.get("delta"),
                    }
                )
    return normalized_metrics, normalized_blockers


def extract_candidate_scan_evidence(reports_dir: Path) -> dict[str, Any]:
    candidate_files: list[Path] = []
    gate_counter: Counter[str] = Counter()
    symbol_counter: Counter[str] = Counter()
    near_miss_count = 0
    trigger_count = 0

    for path in sorted_recent(reports_dir.glob("*.json"), limit=80):
        name_lower = path.name.lower()
        if not any(keyword in name_lower for keyword in CANDIDATE_SCAN_KEYWORDS):
            # File names are the strongest signal. Skip broad JSON parsing unless the name indicates diagnostics.
            continue
        candidate_files.append(path)
        try:
            payload = read_json(path)
        except Exception:
            continue
        for key in ("gate_counts", "candidate_gate_counts", "failed_gate_counts", "rejection_counts"):
            value = payload.get(key)
            if isinstance(value, Mapping):
                for gate, count in value.items():
                    if isinstance(count, (int, float)):
                        gate_counter[str(gate)] += int(count)
        for key in ("symbol_counts", "candidate_symbol_counts", "near_miss_symbol_counts"):
            value = payload.get(key)
            if isinstance(value, Mapping):
                for symbol, count in value.items():
                    if isinstance(count, (int, float)):
                        symbol_counter[str(symbol)] += int(count)
        for key in ("near_miss_count", "near_misses", "candidate_near_miss_count"):
            value = payload.get(key)
            if isinstance(value, int):
                near_miss_count += value
            elif isinstance(value, list):
                near_miss_count += len(value)
        for key in ("trigger_count", "candidate_count", "signal_count"):
            value = payload.get(key)
            if isinstance(value, int):
                trigger_count += value

    return {
        "candidate_scan_files_found": len(candidate_files),
        "candidate_scan_files": [str(path) for path in candidate_files[:10]],
        "gate_block_counter": dict(gate_counter.most_common()),
        "symbol_candidate_counter": dict(symbol_counter.most_common()),
        "near_miss_count": near_miss_count,
        "trigger_count": trigger_count,
        "candidate_scan_data_available": bool(candidate_files),
        "candidate_scan_data_limitation": None
        if candidate_files
        else "No candidate/near-miss scan artifact was found; report uses ledger repetition and latest 28G acceptance blockers only.",
    }


def compute_stagnation(snapshots: Sequence[LedgerSnapshot]) -> dict[str, Any]:
    if not snapshots:
        return {
            "ledger_runs_observed": 0,
            "stagnation_detected": True,
            "stagnation_reason": "NO_HYP006_LEDGER_FOUND",
            "latest_delta_unique_count": 0,
            "unchanged_payload_run_count": 0,
        }
    latest = snapshots[0]
    previous = snapshots[1] if len(snapshots) > 1 else None
    latest_delta_unique = 0
    if previous is not None:
        latest_delta_unique = len(latest.observation_ids - previous.observation_ids)
    unchanged_payload_run_count = 1
    for snapshot in snapshots[1:]:
        if snapshot.sha256 == latest.sha256:
            unchanged_payload_run_count += 1
        else:
            break
    stagnation_detected = latest_delta_unique == 0 and unchanged_payload_run_count >= min(3, len(snapshots))
    return {
        "ledger_runs_observed": len(snapshots),
        "stagnation_detected": stagnation_detected,
        "stagnation_reason": "UNCHANGED_LEDGER_PAYLOAD_ACROSS_RECENT_RUNS"
        if stagnation_detected
        else "LATEST_LEDGER_CHANGED_OR_INSUFFICIENT_HISTORY",
        "latest_delta_unique_count": latest_delta_unique,
        "unchanged_payload_run_count": unchanged_payload_run_count,
        "latest_ledger_sha256": latest.sha256,
        "latest_ledger_length_bytes": latest.length_bytes,
        "latest_ledger_path": str(latest.path),
        "previous_ledger_path": str(previous.path) if previous else None,
    }


def build_diagnostics_report(
    reports_dir: Path,
    out_dir: Path | None = None,
    lookback_ledgers: int = 10,
    write_outputs: bool = True,
) -> dict[str, Any]:
    out_dir = out_dir or reports_dir
    ledger_paths = sorted_recent(reports_dir.glob(LEDGER_GLOB), limit=lookback_ledgers)
    snapshots = [build_ledger_snapshot(path) for path in ledger_paths]
    tracking = latest_tracking_report(reports_dir)
    gate_diagnostics, tracking_blockers = summarize_tracking_metrics(tracking)
    candidate_evidence = extract_candidate_scan_evidence(reports_dir)
    stagnation = compute_stagnation(snapshots)

    latest_snapshot = snapshots[0] if snapshots else None
    latest_unique_count = latest_snapshot.unique_count if latest_snapshot else 0
    target_remaining = max(30 - latest_unique_count, 0)
    blockers = list(dict.fromkeys(
        tracking_blockers
        + (["HYP006_SIGNAL_FREQUENCY_STAGNATION_DETECTED"] if stagnation.get("stagnation_detected") else [])
        + (["CANDIDATE_SCAN_ARTIFACT_NOT_FOUND"] if not candidate_evidence["candidate_scan_data_available"] else [])
    ))
    decision = (
        "HYP006_R1_SIGNAL_FREQUENCY_STAGNATION_DIAGNOSTICS_READY"
        if latest_snapshot
        else "HYP006_R1_SIGNAL_FREQUENCY_DIAGNOSTICS_BLOCKED_NO_LEDGER"
    )
    recommendation = (
        "Continue no-order monitoring and inspect trigger/gate frequency before changing any HYP-006 parameters. "
        "Do not train, reload, paper trade, live trade, or send orders."
    )
    if stagnation.get("stagnation_detected"):
        recommendation = (
            "No new unique HYP-006 observations were detected across recent scheduler ledgers. "
            "Run candidate/near-miss instrumentation before any parameter relaxation; keep all trading gates closed."
        )

    payload: dict[str, Any] = {
        "ok": latest_snapshot is not None,
        "contract_version": CONTRACT_VERSION,
        "report_type": REPORT_TYPE,
        "decision": decision,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "branch_id": BRANCH_ID,
        "hypothesis_id": HYPOTHESIS_ID,
        **NO_MUTATION_FLAGS,
        "reports_dir": str(reports_dir),
        "ledger_glob": LEDGER_GLOB,
        "ledger_runs_observed": stagnation.get("ledger_runs_observed", 0),
        "current_unique_observation_ids": latest_unique_count,
        "new_unique_observation_count_latest_delta": stagnation.get("latest_delta_unique_count", 0),
        "target_remaining_count": target_remaining,
        "stagnation_detected": bool(stagnation.get("stagnation_detected")),
        "stagnation": stagnation,
        "ledger_snapshots": [
            {
                "path": str(snapshot.path),
                "sha256": snapshot.sha256,
                "row_count": snapshot.row_count,
                "unique_count": snapshot.unique_count,
                "length_bytes": snapshot.length_bytes,
                "modified_utc": snapshot.modified_utc,
                "earliest_observation_utc": snapshot.earliest_observation_utc,
                "latest_observation_utc": snapshot.latest_observation_utc,
                "symbols": dict(snapshot.symbols.most_common()),
            }
            for snapshot in snapshots
        ],
        "gate_diagnostics": gate_diagnostics,
        "candidate_trigger_diagnostics": candidate_evidence,
        "blockers": blockers,
        "approved_for_signal_frequency_review": True,
        "approved_for_parameter_relaxation_candidate": False,
        "approved_for_acceptance_review_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "next_required_gate": "28G_H1_REVIEW_STAGNATION_DIAGNOSTICS_OR_CONTINUE_28G_REPEAT",
        "recommendation": recommendation,
        "risk_items": [
            {
                "level": "critical",
                "code": "NO_ORDER_DIAGNOSTIC_ONLY",
                "detail": "This report reads artifacts and writes diagnostic evidence only; it does not approve trading.",
            },
            {
                "level": "warning",
                "code": "SIGNAL_FREQUENCY_STAGNATION",
                "detail": "Recent scheduler ledgers have not added new unique HYP-006 observations.",
            },
            {
                "level": "warning",
                "code": "PARAMETER_RELAXATION_REQUIRES_SEPARATE_RESEARCH_GATE",
                "detail": "Any threshold change must be handled by a separate research-only patch with explicit risk approval.",
            },
        ],
    }

    if write_outputs:
        stamp = utc_now_compact()
        report_json = out_dir / f"{REPORT_PREFIX}_{stamp}.json"
        report_md = out_dir / f"{REPORT_PREFIX}_{stamp}.md"
        write_json(report_json, payload)
        write_markdown(report_md, payload)
        payload["report_json"] = str(report_json)
        payload["report_md"] = str(report_md)
        write_json(report_json, payload)
        write_markdown(report_md, payload)
    return payload


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build HYP-006 signal frequency stagnation diagnostics.")
    parser.add_argument("--reports-dir", default="reports/hyp006_r1_canonical")
    parser.add_argument("--out-dir", default=None)
    parser.add_argument("--lookback-ledgers", type=int, default=10)
    parser.add_argument("--once-json", action="store_true")
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args(argv)

    reports_dir = Path(args.reports_dir)
    out_dir = Path(args.out_dir) if args.out_dir else reports_dir
    payload = build_diagnostics_report(
        reports_dir=reports_dir,
        out_dir=out_dir,
        lookback_ledgers=max(args.lookback_ledgers, 1),
        write_outputs=not args.no_write,
    )
    if args.once_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"{CONTRACT_VERSION} HYP-006 signal frequency stagnation diagnostics {payload['decision']}")
        for key in (
            "read_only",
            "current_unique_observation_ids",
            "new_unique_observation_count_latest_delta",
            "target_remaining_count",
            "stagnation_detected",
            "approved_for_parameter_relaxation_candidate",
            "approved_for_paper_candidate",
            "approved_for_live_real",
            "training_performed",
            "reload_performed",
            "trading_action_performed",
        ):
            print(f" - {key}: {payload.get(key)}")
        for key in ("report_json", "report_md"):
            if payload.get(key):
                print(f"{key}: {payload[key]}")
    return 0 if payload.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
