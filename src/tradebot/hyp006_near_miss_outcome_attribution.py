from __future__ import annotations

import json
import math
import os
import tempfile
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from tradebot.hyp006_shadow_runner_dry_run import (
    BRANCH_ID,
    BRANCH_NAME,
    HYPOTHESIS_ID,
    STRATEGY_FAMILY,
    Candle,
    fetch_public_klines,
    group_by_symbol,
    load_json,
    load_jsonl,
    parse_csv_rows,
)

CONTRACT_VERSION = "4B.4.3.6.6.28G-H4"
SOURCE_H3_CONTRACT_VERSION = "4B.4.3.6.6.28G-H3"
REPORT_TYPE = "hyp006_r1_near_miss_outcome_attribution_gate_combo_counterfactual_no_order_research_report"
REPORT_PREFIX = "4B436628G_H4_hyp006_r1_near_miss_outcome_attribution"
DEFAULT_REPORTS_DIR = "reports/hyp006_r1_canonical"
DEFAULT_H3_PATTERN = "4B436628G_H3_hyp006_r1_runtime_candidate_scan_gate_level_near_miss_*.json"
DEFAULT_SAMPLE_LIMIT = 250
MIN_RESEARCH_REVIEW_SAMPLE = 3
RESEARCH_WIN_RATE_THRESHOLD_PCT = 55.0
RESEARCH_PROFIT_FACTOR_THRESHOLD = 1.15


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _sequence(value: Any) -> Sequence[Any]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return value
    return []


def safe_float(value: Any, default: float | None = None) -> float | None:
    try:
        if value is None or value == "":
            return default
        result = float(value)
        if math.isnan(result) or math.isinf(result):
            return default
        return result
    except (TypeError, ValueError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def write_json_atomic(path: str | os.PathLike[str], payload: Any) -> None:
    resolved = Path(path).resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=True, sort_keys=True, indent=2) + "\n"
    with tempfile.NamedTemporaryFile(
        mode="wb",
        prefix=f".{resolved.name}.",
        suffix=".tmp",
        dir=resolved.parent,
        delete=False,
    ) as handle:
        temp_path = Path(handle.name)
        handle.write(text.encode("utf-8"))
        handle.flush()
        os.fsync(handle.fileno())
    try:
        temp_path.replace(resolved)
    finally:
        temp_path.unlink(missing_ok=True)


def latest_h3_artifact(reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR) -> Path | None:
    target = Path(reports_dir)
    matches = sorted(target.glob(DEFAULT_H3_PATTERN), key=lambda item: item.stat().st_mtime, reverse=True)
    return matches[0] if matches else None


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    raw = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).replace(microsecond=0)


def canonical_timestamp(value: Any) -> str:
    parsed = _parse_timestamp(value)
    if parsed is None:
        return str(value or "")
    return parsed.isoformat()


def resolve_artifact_path(value: Any, *, reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        return None
    raw = value.strip()
    candidates = [Path(raw), Path(raw.replace("\\", os.sep))]
    reports_path = Path(reports_dir).resolve()
    root_candidates = [Path.cwd(), reports_path, reports_path.parent, reports_path.parent.parent]
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
        for root in root_candidates:
            joined = (root / candidate).resolve()
            if joined.exists():
                return joined
    return None


def failed_gate_combo(event: Mapping[str, Any]) -> str:
    gates = [str(gate) for gate in _sequence(event.get("failed_gates")) if str(gate)]
    return " + ".join(gates) if gates else "NO_FAILED_GATES"


def risk_bucket_for_event(event: Mapping[str, Any]) -> str:
    gates = set(str(gate) for gate in _sequence(event.get("failed_gates")))
    if {"MAX_COMPRESSION_RATIO_REFERENCE", "MAX_SPREAD_SLIPPAGE_PROXY_BPS"}.issubset(gates):
        return "HIGH_COMPRESSION_AND_SLIPPAGE"
    if {"RECLAIM_REFERENCE_CLOSE", "MIN_WICK_PCT_REFERENCE"}.issubset(gates):
        return "NO_RECLAIM_LOW_WICK"
    if "MAX_COMPRESSION_RATIO_REFERENCE" in gates and "MIN_WICK_PCT_REFERENCE" in gates:
        return "HIGH_COMPRESSION_LOW_WICK"
    if "MIN_SWEEP_DEPTH_BPS" in gates and "MIN_WICK_PCT_REFERENCE" in gates:
        return "SHALLOW_SWEEP_LOW_WICK"
    if "MAX_COMPRESSION_RATIO_REFERENCE" in gates:
        return "HIGH_COMPRESSION"
    if "MAX_SPREAD_SLIPPAGE_PROXY_BPS" in gates:
        return "HIGH_SLIPPAGE"
    if "MIN_WICK_PCT_REFERENCE" in gates:
        return "LOW_WICK"
    if "RECLAIM_REFERENCE_CLOSE" in gates:
        return "NO_RECLAIM"
    if "MIN_SWEEP_DEPTH_BPS" in gates:
        return "SHALLOW_SWEEP"
    return "OTHER"


def _short_return(entry: float, future_close: float | None) -> float | None:
    if entry <= 0 or future_close is None or future_close <= 0:
        return None
    return round((entry - future_close) / entry * 10000.0, 6)


def _short_mae_mfe(candles: Sequence[Candle], start: int, hold_bars: int, entry: float) -> tuple[float | None, float | None]:
    if entry <= 0:
        return None, None
    future = candles[start + 1 : start + 1 + hold_bars]
    if not future:
        return None, None
    max_high = max(item.high for item in future)
    min_low = min(item.low for item in future)
    mae = (entry - max_high) / entry * 10000.0
    mfe = (entry - min_low) / entry * 10000.0
    return round(mae, 6), round(mfe, 6)


def _build_candle_index(candles: Sequence[Candle]) -> tuple[dict[str, list[Candle]], dict[tuple[str, str], int]]:
    grouped = {symbol: sorted(rows, key=lambda item: canonical_timestamp(item.timestamp_utc)) for symbol, rows in group_by_symbol(candles).items()}
    index: dict[tuple[str, str], int] = {}
    for symbol, rows in grouped.items():
        for idx, candle in enumerate(rows):
            index[(symbol.upper(), canonical_timestamp(candle.timestamp_utc))] = idx
    return grouped, index


def attribute_near_miss_event(
    event: Mapping[str, Any],
    *,
    grouped_candles: Mapping[str, Sequence[Candle]],
    candle_index: Mapping[tuple[str, str], int],
    hold_bars: int,
) -> dict[str, Any]:
    payload = dict(event)
    symbol = str(payload.get("symbol") or "").upper()
    timestamp = canonical_timestamp(payload.get("timestamp_utc"))
    combo = failed_gate_combo(payload)
    bucket = risk_bucket_for_event(payload)
    payload["failed_gate_combo"] = combo
    payload["risk_bucket"] = bucket
    payload["outcome_available"] = False
    payload["outcome_missing_reason"] = None
    rows = list(grouped_candles.get(symbol, []))
    idx = candle_index.get((symbol, timestamp))
    if idx is None or not rows:
        payload["outcome_missing_reason"] = "CANDLE_NOT_FOUND_FOR_EVENT_TIMESTAMP"
        return payload
    if idx + hold_bars >= len(rows):
        payload["outcome_missing_reason"] = "INSUFFICIENT_FORWARD_BARS"
        payload["entry_reference_price"] = round(rows[idx].close, 8)
        return payload
    entry = rows[idx].close
    h1_close = rows[idx + 1].close if idx + 1 < len(rows) else None
    h2_close = rows[idx + 2].close if idx + 2 < len(rows) else None
    h3_close = rows[idx + 3].close if idx + 3 < len(rows) else None
    final_close = rows[idx + hold_bars].close if idx + hold_bars < len(rows) else None
    mae, mfe = _short_mae_mfe(rows, idx, hold_bars, entry)
    final_return = _short_return(entry, final_close)
    payload.update(
        {
            "outcome_available": final_return is not None,
            "entry_reference_price": round(entry, 8),
            "hold_horizon_bars": hold_bars,
            "forward_return_bps_h1_short_probe": _short_return(entry, h1_close),
            "forward_return_bps_h2_short_probe": _short_return(entry, h2_close),
            "forward_return_bps_h3_short_probe": _short_return(entry, h3_close),
            "forward_return_bps_final_short_probe": final_return,
            "mae_bps_short_probe": mae,
            "mfe_bps_short_probe": mfe,
            "positive_final_return": final_return is not None and final_return > 0,
        }
    )
    if final_return is None:
        payload["outcome_missing_reason"] = "FINAL_RETURN_NOT_COMPUTABLE"
    return payload


def summarize_outcomes(events: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    matured = [event for event in events if safe_float(event.get("forward_return_bps_final_short_probe")) is not None]
    returns = [float(event["forward_return_bps_final_short_probe"]) for event in matured]
    wins = [value for value in returns if value > 0]
    losses = [abs(value) for value in returns if value < 0]
    profit_factor = (sum(wins) / sum(losses)) if losses else (999.0 if wins else 0.0)
    mae_values = [float(value) for value in (safe_float(event.get("mae_bps_short_probe")) for event in matured) if value is not None]
    mfe_values = [float(value) for value in (safe_float(event.get("mfe_bps_short_probe")) for event in matured) if value is not None]
    sorted_returns = sorted(returns)
    median = None
    if sorted_returns:
        midpoint = len(sorted_returns) // 2
        median = sorted_returns[midpoint] if len(sorted_returns) % 2 else (sorted_returns[midpoint - 1] + sorted_returns[midpoint]) / 2.0
    return {
        "event_count": len(events),
        "matured_count": len(matured),
        "missing_outcome_count": len(events) - len(matured),
        "win_count": len(wins),
        "loss_count": len(losses),
        "win_rate_pct": round((len(wins) / len(returns)) * 100.0, 6) if returns else 0.0,
        "net_return_bps": round(sum(returns), 6) if returns else 0.0,
        "mean_return_bps": round(sum(returns) / len(returns), 6) if returns else None,
        "median_return_bps": None if median is None else round(median, 6),
        "profit_factor": round(profit_factor, 6),
        "best_return_bps": round(max(returns), 6) if returns else None,
        "worst_return_bps": round(min(returns), 6) if returns else None,
        "avg_mae_bps": round(sum(mae_values) / len(mae_values), 6) if mae_values else None,
        "avg_mfe_bps": round(sum(mfe_values) / len(mfe_values), 6) if mfe_values else None,
        "worst_mae_bps": round(min(mae_values), 6) if mae_values else None,
        "best_mfe_bps": round(max(mfe_values), 6) if mfe_values else None,
    }


def _grouped_summary(events: Sequence[Mapping[str, Any]], key_fn: Callable[[Mapping[str, Any]], str]) -> list[dict[str, Any]]:
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for event in events:
        grouped[key_fn(event)].append(event)
    rows: list[dict[str, Any]] = []
    for key, items in grouped.items():
        summary = summarize_outcomes(items)
        row = {"key": key, **summary}
        row["research_only_counterfactual_candidate"] = bool(
            summary["matured_count"] >= MIN_RESEARCH_REVIEW_SAMPLE
            and (summary["mean_return_bps"] is not None and summary["mean_return_bps"] > 0)
            and summary["win_rate_pct"] >= RESEARCH_WIN_RATE_THRESHOLD_PCT
            and summary["profit_factor"] >= RESEARCH_PROFIT_FACTOR_THRESHOLD
        )
        rows.append(row)
    return sorted(rows, key=lambda row: (not row["research_only_counterfactual_candidate"], -int(row["matured_count"]), -(row.get("mean_return_bps") or -999999.0), str(row["key"])))


def summarize_trigger_benchmark(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    trigger_events: list[dict[str, Any]] = []
    for row in rows:
        event = dict(row)
        event["forward_return_bps_final_short_probe"] = safe_float(row.get("forward_return_bps_final_short_probe"), safe_float(row.get("forward_return_bps")))
        event["mae_bps_short_probe"] = safe_float(row.get("mae_bps_short_probe"))
        event["mfe_bps_short_probe"] = safe_float(row.get("mfe_bps_short_probe"))
        trigger_events.append(event)
    summary = summarize_outcomes(trigger_events)
    summary["source"] = "canonical_shadow_trigger_rows"
    return summary


def _load_trigger_rows_from_h3(h3_artifact: Mapping[str, Any], *, reports_dir: str | os.PathLike[str]) -> tuple[list[dict[str, Any]], str | None]:
    ledger_path = resolve_artifact_path(h3_artifact.get("canonical_cycle_ledger_jsonl"), reports_dir=reports_dir)
    if ledger_path and ledger_path.exists():
        return load_jsonl(ledger_path), str(ledger_path)
    report_path = resolve_artifact_path(h3_artifact.get("canonical_cycle_report_json"), reports_dir=reports_dir)
    if report_path and report_path.exists():
        report = _mapping(load_json(report_path))
        return [dict(row) for row in _sequence(report.get("shadow_observations")) if isinstance(row, Mapping)], str(report_path)
    return [], None


def _runtime_spec_from_h3_cycle_report(h3_artifact: Mapping[str, Any], *, reports_dir: str | os.PathLike[str]) -> Mapping[str, Any]:
    report_path = resolve_artifact_path(h3_artifact.get("canonical_cycle_report_json"), reports_dir=reports_dir)
    if report_path and report_path.exists():
        report = _mapping(load_json(report_path))
        return _mapping(report.get("runtime_spec"))
    return {}


def load_candles_for_attribution(
    *,
    symbols: Sequence[str],
    interval: str,
    days: int,
    input_csv: str | os.PathLike[str] | None = None,
    base_url: str = "https://api.binance.com",
) -> tuple[list[Candle], bool, dict[str, int]]:
    if input_csv:
        candles = parse_csv_rows(input_csv)
        network = False
    else:
        candles = []
        network = True
        for symbol in symbols:
            candles.extend(fetch_public_klines(symbol=symbol.upper(), interval=interval, days=days, base_url=base_url))
    grouped = group_by_symbol(candles)
    return candles, network, {symbol.upper(): len(grouped.get(symbol.upper(), [])) for symbol in symbols}


def validate_h3_artifact(h3_artifact: Mapping[str, Any]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if h3_artifact.get("contract_version") != SOURCE_H3_CONTRACT_VERSION:
        reasons.append("SOURCE_H3_CONTRACT_VERSION_MISMATCH")
    if h3_artifact.get("branch_id") != BRANCH_ID:
        reasons.append("SOURCE_BRANCH_ID_MISMATCH")
    if h3_artifact.get("read_only") is not True:
        reasons.append("SOURCE_H3_NOT_READ_ONLY")
    if h3_artifact.get("raw_candidate_scan_artifact_found") is not True:
        reasons.append("SOURCE_H3_RAW_SCAN_ARTIFACT_NOT_FOUND")
    if h3_artifact.get("runtime_hook_enabled") is not True:
        reasons.append("SOURCE_H3_RUNTIME_HOOK_NOT_ENABLED")
    for flag in ("approved_for_paper_candidate", "approved_for_live_real", "training_performed", "reload_performed", "trading_action_performed"):
        if h3_artifact.get(flag) not in (False, None):
            reasons.append(f"UNSAFE_SOURCE_{flag.upper()}")
    return not reasons, reasons


def build_near_miss_outcome_attribution_report(
    *,
    h3_artifact: Mapping[str, Any],
    candles: Sequence[Candle] | None = None,
    reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR,
    input_csv: str | os.PathLike[str] | None = None,
    symbols: Sequence[str] | None = None,
    interval: str | None = None,
    days: int = 30,
    base_url: str = "https://api.binance.com",
    sample_limit: int = DEFAULT_SAMPLE_LIMIT,
) -> dict[str, Any]:
    source_ok, source_reasons = validate_h3_artifact(h3_artifact)
    runtime_spec = _runtime_spec_from_h3_cycle_report(h3_artifact, reports_dir=reports_dir)
    hold_bars = max(1, safe_int(runtime_spec.get("hold_bars"), 6))
    timeframe = str(interval or h3_artifact.get("timeframe") or runtime_spec.get("timeframe") or "4h")
    source_symbols = sorted({str(key).upper() for key in _mapping(h3_artifact.get("symbol_candidate_counter")).keys()})
    event_symbols = sorted({str(_mapping(event).get("symbol") or "").upper() for event in _sequence(h3_artifact.get("sample_near_miss_events")) if _mapping(event).get("symbol")})
    requested_symbols = sorted({item.upper() for item in (symbols or source_symbols or event_symbols) if item})
    rows_by_symbol: dict[str, int] = {}
    network_request_performed = False
    all_candles: list[Candle] = list(candles or [])
    if not all_candles and requested_symbols:
        all_candles, network_request_performed, rows_by_symbol = load_candles_for_attribution(
            symbols=requested_symbols,
            interval=timeframe,
            days=days,
            input_csv=input_csv,
            base_url=base_url,
        )
    else:
        grouped_temp = group_by_symbol(all_candles)
        rows_by_symbol = {symbol: len(grouped_temp.get(symbol.upper(), [])) for symbol in requested_symbols}
    grouped, candle_index = _build_candle_index(all_candles)
    near_miss_events = [dict(event) for event in _sequence(h3_artifact.get("sample_near_miss_events")) if isinstance(event, Mapping)]
    source_near_miss_count = safe_int(h3_artifact.get("near_miss_count"), len(near_miss_events))
    attributed = [
        attribute_near_miss_event(event, grouped_candles=grouped, candle_index=candle_index, hold_bars=hold_bars)
        for event in near_miss_events[: max(1, sample_limit)]
    ]
    trigger_rows, trigger_source_path = _load_trigger_rows_from_h3(h3_artifact, reports_dir=reports_dir)
    overall = summarize_outcomes(attributed)
    gate_combo_summary = _grouped_summary(attributed, lambda event: str(event.get("failed_gate_combo") or "UNKNOWN"))
    symbol_summary = _grouped_summary(attributed, lambda event: str(event.get("symbol") or "UNKNOWN"))
    risk_bucket_summary = _grouped_summary(attributed, lambda event: str(event.get("risk_bucket") or "UNKNOWN"))
    trigger_benchmark = summarize_trigger_benchmark(trigger_rows)
    research_candidates = [row for row in gate_combo_summary if row.get("research_only_counterfactual_candidate") is True]

    blockers: list[str] = []
    blockers.extend(source_reasons)
    if not near_miss_events:
        blockers.append("SOURCE_H3_NEAR_MISS_EVENTS_NOT_FOUND")
    if source_near_miss_count > len(near_miss_events):
        blockers.append("SOURCE_H3_NEAR_MISS_EVENTS_TRUNCATED_TO_SAMPLE")
    if not all_candles:
        blockers.append("ATTRIBUTION_MARKET_DATA_NOT_AVAILABLE")
    if overall["matured_count"] <= 0:
        blockers.append("NO_MATURED_NEAR_MISS_OUTCOMES_ATTRIBUTED")
    if not trigger_rows:
        blockers.append("TRIGGER_BENCHMARK_ROWS_NOT_FOUND")
    blockers.append("PARAMETER_RELAXATION_REQUIRES_SEPARATE_RESEARCH_GATE")
    blockers.append("NO_PAPER_LIVE_TRAINING_RELOAD_ORDER_ENABLEMENT")

    return {
        "contract_version": CONTRACT_VERSION,
        "source_h3_contract_version": h3_artifact.get("contract_version"),
        "report_type": REPORT_TYPE,
        "decision": "HYP006_R1_NEAR_MISS_OUTCOME_ATTRIBUTION_READY" if source_ok and overall["matured_count"] > 0 else "HYP006_R1_NEAR_MISS_OUTCOME_ATTRIBUTION_BLOCKED",
        "ok": bool(source_ok and overall["matured_count"] > 0),
        "generated_at_utc": utc_now_iso(),
        "hypothesis_id": HYPOTHESIS_ID,
        "branch_id": BRANCH_ID,
        "branch_name": BRANCH_NAME,
        "strategy_family": STRATEGY_FAMILY,
        "timeframe": timeframe,
        "hold_horizon_bars": hold_bars,
        "source_h3_summary": {
            "scanned_candle_count": h3_artifact.get("scanned_candle_count"),
            "candidate_count": h3_artifact.get("candidate_count"),
            "near_miss_count": h3_artifact.get("near_miss_count"),
            "sample_near_miss_event_count": len(near_miss_events),
            "trigger_count": h3_artifact.get("trigger_count"),
            "duplicate_existing_trigger_count": h3_artifact.get("duplicate_existing_trigger_count"),
            "gate_block_counter": dict(_mapping(h3_artifact.get("gate_block_counter"))),
            "symbol_candidate_counter": dict(_mapping(h3_artifact.get("symbol_candidate_counter"))),
            "symbol_near_miss_counter": dict(_mapping(h3_artifact.get("symbol_near_miss_counter"))),
            "symbol_trigger_counter": dict(_mapping(h3_artifact.get("symbol_trigger_counter"))),
        },
        "source_h3_validation": {"ok": source_ok, "reasons": sorted(set(source_reasons))},
        "source_h3_near_miss_sample_coverage_pct": round(len(near_miss_events) / source_near_miss_count * 100.0, 6) if source_near_miss_count else 0.0,
        "network_request_performed": bool(network_request_performed),
        "rows_by_symbol": rows_by_symbol,
        "attributed_near_miss_event_count": len(attributed),
        "matured_near_miss_event_count": overall["matured_count"],
        "near_miss_outcome_summary": overall,
        "trigger_benchmark_summary": trigger_benchmark,
        "gate_combo_outcome_summary": gate_combo_summary,
        "symbol_outcome_summary": symbol_summary,
        "risk_bucket_outcome_summary": risk_bucket_summary,
        "research_only_counterfactual_candidates": research_candidates,
        "sample_attributed_near_miss_events": attributed[: min(sample_limit, 100)],
        "source_paths": {
            "h3_artifact_json": str(h3_artifact.get("_source_path") or ""),
            "canonical_cycle_report_json": str(h3_artifact.get("canonical_cycle_report_json") or ""),
            "canonical_cycle_ledger_jsonl": str(h3_artifact.get("canonical_cycle_ledger_jsonl") or ""),
            "resolved_trigger_benchmark_source": trigger_source_path,
            "input_csv": None if input_csv is None else str(input_csv),
        },
        "blockers": sorted(set(blockers)),
        "warnings": [
            "NEAR_MISS_ATTRIBUTION_IS_COUNTERFACTUAL_NO_ORDER_RESEARCH_ONLY",
            "SOURCE_H3_SAMPLE_EVENTS_MAY_BE_TRUNCATED_UNLESS_H3_SAMPLE_LIMIT_COVERS_ALL_NEAR_MISSES",
            "DO_NOT_USE_COUNTERFACTUAL_RESULTS_FOR_PAPER_OR_LIVE_ENABLEMENT",
        ],
        "read_only": True,
        "no_order_measurement_only": True,
        "counterfactual_research_only": True,
        "strategy_parameter_mutation_performed": False,
        "config_mutation_performed": False,
        "scheduler_mutation_performed": False,
        "scheduler_task_created": False,
        "scheduler_task_modified": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "order_actions_performed": False,
        "approved_for_gate_combo_counterfactual_review_candidate": bool(research_candidates),
        "approved_for_parameter_relaxation_candidate": False,
        "approved_for_training_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "paper_transition_candidate_found": False,
        "recommendation": "Review near-miss outcome by gate combo only as no-order counterfactual research. Do not relax parameters, train, reload, paper trade, live trade, or send orders without a separate accepted research gate.",
    }


def write_markdown(path: str | os.PathLike[str], payload: Mapping[str, Any]) -> None:
    summary = _mapping(payload.get("near_miss_outcome_summary"))
    benchmark = _mapping(payload.get("trigger_benchmark_summary"))
    combos = _sequence(payload.get("gate_combo_outcome_summary"))[:12]
    lines = [
        "# 4B.4.3.6.6.28G-H4 HYP-006 Near-Miss Outcome Attribution",
        "",
        f"- decision: `{payload.get('decision')}`",
        f"- branch_id: `{payload.get('branch_id')}`",
        f"- read_only: `{payload.get('read_only')}`",
        f"- counterfactual_research_only: `{payload.get('counterfactual_research_only')}`",
        f"- attributed_near_miss_event_count: `{payload.get('attributed_near_miss_event_count')}`",
        f"- matured_near_miss_event_count: `{payload.get('matured_near_miss_event_count')}`",
        f"- near_miss_mean_return_bps: `{summary.get('mean_return_bps')}`",
        f"- near_miss_win_rate_pct: `{summary.get('win_rate_pct')}`",
        f"- trigger_benchmark_mean_return_bps: `{benchmark.get('mean_return_bps')}`",
        f"- trigger_benchmark_win_rate_pct: `{benchmark.get('win_rate_pct')}`",
        f"- approved_for_parameter_relaxation_candidate: `{payload.get('approved_for_parameter_relaxation_candidate')}`",
        f"- approved_for_paper_candidate: `{payload.get('approved_for_paper_candidate')}`",
        f"- approved_for_live_real: `{payload.get('approved_for_live_real')}`",
        "",
        "## Gate combo outcome summary",
        "",
    ]
    if combos:
        for item in combos:
            row = _mapping(item)
            lines.append(
                f"- `{row.get('key')}`: count `{row.get('event_count')}`, matured `{row.get('matured_count')}`, "
                f"mean `{row.get('mean_return_bps')}`, win_rate `{row.get('win_rate_pct')}`, pf `{row.get('profit_factor')}`, "
                f"research_candidate `{row.get('research_only_counterfactual_candidate')}`"
            )
    else:
        lines.append("- No gate-combo outcomes were available.")
    lines.extend([
        "",
        "## Recommendation",
        "",
        str(payload.get("recommendation", "No-order research only. Trading gates remain closed.")),
    ])
    resolved = Path(path).resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_report_bundle(payload: Mapping[str, Any], out_dir: str | os.PathLike[str]) -> tuple[Path, Path]:
    target_dir = Path(out_dir)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_json = target_dir / f"{REPORT_PREFIX}_{stamp}.json"
    report_md = target_dir / f"{REPORT_PREFIX}_{stamp}.md"
    write_json_atomic(report_json, payload)
    write_markdown(report_md, payload)
    return report_json, report_md
