from __future__ import annotations

import csv
import json
import math
import os
import tempfile
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import urlencode
from urllib.request import Request, urlopen

CONTRACT_VERSION = "4B.4.3.6.6.27G-H3"
HYPOTHESIS_ID = "HYP-005"
BRANCH_NAME = "liquidity_sweep_reversal_vol_compression"
STRATEGY_FAMILY = "long_liquidity_sweep_reversal"
REPORT_PREFIX = "4B436627GH3_hyp005_shadow_stagnation_diagnostics"


@dataclass(frozen=True)
class RuntimeSpec:
    hypothesis_id: str = HYPOTHESIS_ID
    branch_name: str = BRANCH_NAME
    strategy_family: str = STRATEGY_FAMILY
    timeframe: str = "4h"
    lookback_bars: int = 24
    hold_bars: int = 6
    min_sweep_bps: float = 18.0
    min_wick_pct: float = 42.0
    compression_window: int = 12
    compression_baseline_bars: int = 48
    max_compression_ratio: float = 1.05
    max_slippage_proxy_bps: float = 12.0
    min_shadow_sample_target: int = 30


@dataclass(frozen=True)
class Candle:
    timestamp_utc: str
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


@dataclass(frozen=True)
class CandidateAudit:
    symbol: str
    timestamp_utc: str
    identity_event_key: str
    observation_id: str
    exact_candidate: bool
    duplicate_existing_observation: bool
    new_unique_candidate: bool
    near_miss: bool
    failed_filters: list[str]
    passed_filters: list[str]
    sweep_depth_bps: float
    wick_pct: float
    compression_ratio: float
    spread_slippage_proxy_bps: float
    entry_reference_price: float
    lookback_low: float
    swept_low: float
    filter_distance: dict[str, float]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def safe_float(value: Any, default: float = 0.0) -> float:
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


def _candidate_spec_payload(payload: Mapping[str, Any] | None) -> Mapping[str, Any]:
    if not isinstance(payload, Mapping):
        return {}
    if payload.get("strategy_family") == STRATEGY_FAMILY or payload.get("branch_name") == BRANCH_NAME:
        return payload
    candidate = payload.get("candidate_spec")
    return candidate if isinstance(candidate, Mapping) else {}


def _nested_mapping(root: Mapping[str, Any], *keys: str) -> Mapping[str, Any]:
    node: Any = root
    for key in keys:
        if not isinstance(node, Mapping):
            return {}
        node = node.get(key)
    return node if isinstance(node, Mapping) else {}


def _threshold_from_acceptance_metrics(spec: Mapping[str, Any], name: str, default: float | int) -> float | int:
    metrics = spec.get("required_shadow_acceptance_metrics")
    if not isinstance(metrics, Sequence) or isinstance(metrics, (str, bytes)):
        return default
    for item in metrics:
        if isinstance(item, Mapping) and item.get("name") == name:
            threshold = item.get("threshold")
            if isinstance(default, int):
                return safe_int(threshold, default)
            return safe_float(threshold, float(default))
    return default


def parse_runtime_spec(candidate_spec: Mapping[str, Any] | None) -> RuntimeSpec:
    spec = _candidate_spec_payload(candidate_spec)
    entry = _nested_mapping(spec, "entry_signal_definition")
    params = _nested_mapping(spec, "entry_signal_definition", "parameters")
    return RuntimeSpec(
        hypothesis_id=str(spec.get("hypothesis_id") or HYPOTHESIS_ID),
        branch_name=str(spec.get("branch_name") or BRANCH_NAME),
        strategy_family=str(spec.get("strategy_family") or entry.get("strategy_family") or STRATEGY_FAMILY),
        timeframe=str(entry.get("timeframe") or "4h"),
        lookback_bars=max(2, safe_int(params.get("lookback_bars"), 24)),
        hold_bars=max(1, safe_int(params.get("hold_bars"), 6)),
        min_sweep_bps=safe_float(params.get("min_sweep_bps"), 18.0),
        min_wick_pct=safe_float(params.get("min_wick_pct"), 42.0),
        compression_window=max(2, safe_int(params.get("compression_window"), 12)),
        compression_baseline_bars=max(3, safe_int(params.get("compression_baseline_bars"), 48)),
        max_compression_ratio=safe_float(params.get("max_compression_ratio"), 1.05),
        max_slippage_proxy_bps=safe_float(
            _threshold_from_acceptance_metrics(spec, "max_slippage_proxy_bps", 12.0),
            12.0,
        ),
        min_shadow_sample_target=safe_int(
            _threshold_from_acceptance_metrics(spec, "min_shadow_sample_target", 30),
            30,
        ),
    )


def load_json(path: str | os.PathLike[str] | None) -> Any:
    if path is None:
        return None
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_jsonl(path: str | os.PathLike[str] | None) -> list[dict[str, Any]]:
    if path is None:
        return []
    rows: list[dict[str, Any]] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        if isinstance(payload, Mapping):
            rows.append(dict(payload))
    return rows


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


def write_markdown(path: str | os.PathLike[str], payload: Mapping[str, Any]) -> None:
    lines = [
        "# 4B.4.3.6.6.27G-H3 Shadow Observation Stagnation Diagnostics",
        "",
        f"- decision: `{payload.get('decision')}`",
        f"- shadow_observation_count: `{payload.get('ledger_summary', {}).get('shadow_observation_count')}`",
        f"- latest_observation_utc: `{payload.get('ledger_summary', {}).get('latest_observation_utc')}`",
        f"- stagnation_status: `{payload.get('stagnation', {}).get('status')}`",
        f"- exact_candidate_count: `{payload.get('candidate_diagnostics', {}).get('exact_candidate_count')}`",
        f"- new_unique_candidate_count: `{payload.get('candidate_diagnostics', {}).get('new_unique_candidate_count')}`",
        f"- near_miss_count: `{payload.get('candidate_diagnostics', {}).get('near_miss_count')}`",
        f"- top_bottleneck_filter: `{payload.get('candidate_diagnostics', {}).get('top_bottleneck_filter')}`",
        "",
        "## Recommendation",
        "",
        str(payload.get("recommendation", "")),
    ]
    resolved = Path(path).resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_csv_rows(path: str | os.PathLike[str], default_symbol: str = "TESTUSDT") -> list[Candle]:
    candles: list[Candle] = []
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for raw in reader:
            timestamp = raw.get("timestamp_utc") or raw.get("timestamp") or raw.get("open_time") or raw.get("time") or ""
            symbol = str(raw.get("symbol") or default_symbol).upper().strip()
            candle = Candle(
                timestamp_utc=str(timestamp),
                symbol=symbol,
                open=safe_float(raw.get("open")),
                high=safe_float(raw.get("high")),
                low=safe_float(raw.get("low")),
                close=safe_float(raw.get("close")),
                volume=safe_float(raw.get("volume"), 0.0),
            )
            if candle.timestamp_utc and candle.symbol:
                candles.append(candle)
    return candles


def _interval_hours(interval: str) -> float:
    value = interval.strip().lower()
    if value.endswith("m"):
        return max(1.0 / 60.0, safe_float(value[:-1], 1.0) / 60.0)
    if value.endswith("h"):
        return max(1.0, safe_float(value[:-1], 4.0))
    if value.endswith("d"):
        return max(24.0, safe_float(value[:-1], 1.0) * 24.0)
    return 4.0


def fetch_public_klines(
    *,
    symbol: str,
    interval: str,
    days: int,
    base_url: str,
    timeout_sec: int = 15,
    limit_ceiling: int = 1000,
) -> list[Candle]:
    bars_needed = int(math.ceil(max(1, days) * 24 / _interval_hours(interval))) + 80
    limit = max(1, min(limit_ceiling, bars_needed))
    endpoint = base_url.rstrip("/") + "/api/v3/klines?" + urlencode({"symbol": symbol, "interval": interval, "limit": limit})
    req = Request(endpoint, method="GET", headers={"User-Agent": "tradebot-hyp005-stagnation-diagnostics/4B436627GH3"})
    with urlopen(req, timeout=timeout_sec) as response:  # noqa: S310 - explicit public market-data GET only.
        payload = json.loads(response.read().decode("utf-8"))
    candles: list[Candle] = []
    for row in payload if isinstance(payload, list) else []:
        if not isinstance(row, Sequence) or len(row) < 6:
            continue
        open_time_ms = safe_int(row[0], 0)
        timestamp = datetime.fromtimestamp(open_time_ms / 1000, tz=timezone.utc).replace(microsecond=0).isoformat()
        candles.append(
            Candle(
                timestamp_utc=timestamp,
                symbol=symbol,
                open=safe_float(row[1]),
                high=safe_float(row[2]),
                low=safe_float(row[3]),
                close=safe_float(row[4]),
                volume=safe_float(row[5], 0.0),
            )
        )
    return candles


def group_by_symbol(candles: Iterable[Candle]) -> dict[str, list[Candle]]:
    grouped: dict[str, list[Candle]] = {}
    for candle in candles:
        grouped.setdefault(candle.symbol.upper(), []).append(candle)
    for rows in grouped.values():
        rows.sort(key=lambda item: item.timestamp_utc)
    return grouped


def _mean(values: Sequence[float]) -> float | None:
    clean = [value for value in values if value is not None and not math.isnan(value)]
    return None if not clean else sum(clean) / len(clean)


def _range(candle: Candle) -> float:
    return max(0.0, candle.high - candle.low)


def _basis_bps(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator * 10000.0


def _parse_timestamp(value: object) -> datetime:
    text = str(value or "").strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def canonical_timestamp_token(value: object) -> str:
    return _parse_timestamp(value).strftime("%Y-%m-%dT%H%M%SZ")


def canonical_event_key(symbol: str, timeframe: str, timestamp_utc: str) -> str:
    return "|".join((HYPOTHESIS_ID, symbol.upper(), timeframe, canonical_timestamp_token(timestamp_utc)))


def stable_observation_id(symbol: str, timeframe: str, timestamp_utc: str) -> str:
    return f"{HYPOTHESIS_ID}-{symbol.upper()}-{timeframe}-{canonical_timestamp_token(timestamp_utc)}"


def ledger_identity_set(rows: Sequence[Mapping[str, Any]]) -> set[str]:
    identities: set[str] = set()
    for row in rows:
        observation_id = str(row.get("observation_id") or "").strip()
        if observation_id:
            identities.add(observation_id)
        symbol = str(row.get("symbol") or "").strip().upper()
        timestamp = str(row.get("timestamp_utc") or row.get("timestamp") or "").strip()
        timeframe = str(row.get("timeframe") or "4h")
        if symbol and timestamp:
            identities.add(stable_observation_id(symbol, timeframe, timestamp))
    return identities


def _evaluate_candle(candles: Sequence[Candle], idx: int, spec: RuntimeSpec, existing_ids: set[str]) -> CandidateAudit:
    candle = candles[idx]
    ranges = [_range(item) for item in candles]
    prior = candles[idx - spec.lookback_bars : idx]
    lookback_low = min(item.low for item in prior) if prior else 0.0
    swept_low = candle.low
    sweep_depth_bps = _basis_bps(lookback_low - swept_low, lookback_low) if lookback_low > 0 else 0.0
    candle_range = max(candle.high - candle.low, 1e-12)
    wick_pct = max(0.0, min(candle.open, candle.close) - candle.low) / candle_range * 100.0
    reclaim = candle.close > lookback_low
    short_ranges = ranges[max(0, idx - spec.compression_window) : idx]
    base_ranges = ranges[max(0, idx - spec.compression_baseline_bars) : idx]
    short_mean = _mean(short_ranges) or 0.0
    base_mean = _mean(base_ranges) or 0.0
    compression_ratio = short_mean / base_mean if base_mean > 0 else 1.0
    spread_slippage_proxy = min(99.0, max(0.0, _basis_bps(candle.high - candle.low, candle.close) * 0.03))
    data_quality_ok = all(value > 0 for value in (candle.open, candle.high, candle.low, candle.close))
    hold_horizon_available = idx + spec.hold_bars < len(candles)
    filters = {
        "swept_low": swept_low < lookback_low,
        "min_sweep_bps": sweep_depth_bps >= spec.min_sweep_bps,
        "reclaim": reclaim,
        "min_wick_pct": wick_pct >= spec.min_wick_pct,
        "max_compression_ratio": compression_ratio <= spec.max_compression_ratio,
        "data_quality": data_quality_ok,
        "hold_horizon_available": hold_horizon_available,
        "max_slippage_proxy_bps": spread_slippage_proxy <= spec.max_slippage_proxy_bps,
    }
    scanner_filter_names = ["swept_low", "min_sweep_bps", "reclaim", "min_wick_pct", "max_compression_ratio"]
    exact_candidate = all(filters[name] for name in scanner_filter_names)
    failed_filters = [name for name, passed in filters.items() if not passed]
    passed_filters = [name for name, passed in filters.items() if passed]
    observation_id = stable_observation_id(candle.symbol, spec.timeframe, candle.timestamp_utc)
    duplicate = observation_id in existing_ids
    scanner_failures = [name for name in scanner_filter_names if name in failed_filters]
    near_miss = (not exact_candidate) and filters["swept_low"] and filters["reclaim"] and len(scanner_failures) <= 2
    return CandidateAudit(
        symbol=candle.symbol.upper(),
        timestamp_utc=candle.timestamp_utc,
        identity_event_key=canonical_event_key(candle.symbol, spec.timeframe, candle.timestamp_utc),
        observation_id=observation_id,
        exact_candidate=exact_candidate,
        duplicate_existing_observation=duplicate,
        new_unique_candidate=exact_candidate and not duplicate,
        near_miss=near_miss,
        failed_filters=failed_filters,
        passed_filters=passed_filters,
        sweep_depth_bps=round(sweep_depth_bps, 6),
        wick_pct=round(wick_pct, 6),
        compression_ratio=round(compression_ratio, 6),
        spread_slippage_proxy_bps=round(spread_slippage_proxy, 6),
        entry_reference_price=round(candle.close, 8),
        lookback_low=round(lookback_low, 8),
        swept_low=round(swept_low, 8),
        filter_distance={
            "min_sweep_bps_gap": round(spec.min_sweep_bps - sweep_depth_bps, 6),
            "min_wick_pct_gap": round(spec.min_wick_pct - wick_pct, 6),
            "max_compression_ratio_gap": round(compression_ratio - spec.max_compression_ratio, 6),
            "max_slippage_proxy_bps_gap": round(spread_slippage_proxy - spec.max_slippage_proxy_bps, 6),
        },
    )


def scan_candidate_audit(candles: Sequence[Candle], spec: RuntimeSpec, existing_ids: set[str]) -> list[CandidateAudit]:
    audits: list[CandidateAudit] = []
    grouped = group_by_symbol(candles)
    min_index = max(spec.lookback_bars, spec.compression_baseline_bars, spec.compression_window) + 1
    for rows in grouped.values():
        if len(rows) <= min_index:
            continue
        for idx in range(min_index, len(rows)):
            audits.append(_evaluate_candle(rows, idx, spec, existing_ids))
    return audits


def _ledger_summary(rows: Sequence[Mapping[str, Any]], spec: RuntimeSpec) -> dict[str, Any]:
    timestamps = [str(row.get("timestamp_utc") or "") for row in rows if row.get("timestamp_utc")]
    latest = max(timestamps) if timestamps else None
    symbols = sorted({str(row.get("symbol") or "").upper() for row in rows if row.get("symbol")})
    return {
        "shadow_observation_count": len(rows),
        "shadow_sample_target": spec.min_shadow_sample_target,
        "shadow_sample_target_met": len(rows) >= spec.min_shadow_sample_target,
        "latest_observation_utc": latest,
        "symbols_observed": symbols,
        "symbols_observed_count": len(symbols),
    }


def _candidate_summary(audits: Sequence[CandidateAudit], grouped: Mapping[str, Sequence[Candle]]) -> dict[str, Any]:
    filter_rejections: Counter[str] = Counter()
    for audit in audits:
        for name in audit.failed_filters:
            filter_rejections[name] += 1
    exact = [item for item in audits if item.exact_candidate]
    near_misses = [item for item in audits if item.near_miss]
    new_unique = [item for item in audits if item.new_unique_candidate]
    duplicates = [item for item in audits if item.exact_candidate and item.duplicate_existing_observation]
    top_filter = filter_rejections.most_common(1)[0][0] if filter_rejections else None
    rows_by_symbol = {symbol: len(rows) for symbol, rows in sorted(grouped.items())}
    exact_by_symbol = Counter(item.symbol for item in exact)
    near_by_symbol = Counter(item.symbol for item in near_misses)
    top_near_misses = sorted(
        near_misses,
        key=lambda item: (len(item.failed_filters), -item.sweep_depth_bps, item.timestamp_utc),
    )[:20]
    return {
        "symbols_scanned": sorted(grouped.keys()),
        "rows_by_symbol": rows_by_symbol,
        "evaluated_candle_count": len(audits),
        "exact_candidate_count": len(exact),
        "new_unique_candidate_count": len(new_unique),
        "duplicate_candidate_count": len(duplicates),
        "near_miss_count": len(near_misses),
        "filter_rejection_counts": dict(sorted(filter_rejections.items())),
        "top_bottleneck_filter": top_filter,
        "exact_candidates_by_symbol": dict(sorted(exact_by_symbol.items())),
        "near_misses_by_symbol": dict(sorted(near_by_symbol.items())),
        "top_near_misses": [asdict(item) for item in top_near_misses],
    }


def _stagnation_summary(ledger_summary: Mapping[str, Any], candidate_summary: Mapping[str, Any], generated_at: str) -> dict[str, Any]:
    latest_text = ledger_summary.get("latest_observation_utc")
    days_since_latest: float | None = None
    if latest_text:
        days_since_latest = round((_parse_timestamp(generated_at) - _parse_timestamp(latest_text)).total_seconds() / 86400.0, 4)
    new_count = safe_int(candidate_summary.get("new_unique_candidate_count"), 0)
    exact_count = safe_int(candidate_summary.get("exact_candidate_count"), 0)
    near_count = safe_int(candidate_summary.get("near_miss_count"), 0)
    if days_since_latest is not None and days_since_latest >= 7 and new_count == 0:
        status = "STAGNATED"
    elif new_count > 0:
        status = "NEW_UNIQUE_CANDIDATES_AVAILABLE"
    elif exact_count > 0 and new_count == 0:
        status = "DUPLICATE_ONLY"
    elif near_count > 0:
        status = "NEAR_MISS_BOTTLENECK"
    else:
        status = "NO_CURRENT_CANDIDATE_REGIME"
    return {
        "status": status,
        "days_since_latest_observation": days_since_latest,
        "new_unique_observation_available": new_count > 0,
        "duplicate_only_current_candidates": exact_count > 0 and new_count == 0,
        "near_miss_bottleneck_detected": near_count > 0,
    }


def _recommendation(stagnation: Mapping[str, Any], candidate_summary: Mapping[str, Any]) -> str:
    status = stagnation.get("status")
    top_filter = candidate_summary.get("top_bottleneck_filter") or "unknown"
    if status == "NEW_UNIQUE_CANDIDATES_AVAILABLE":
        return "New unique candidates are visible in diagnostics. Keep no-order collection running and let the canonical logger confirm them; do not enable paper/live trading."
    if status == "DUPLICATE_ONLY":
        return "Current exact candidates are duplicates of existing ledger observations. Keep collecting; do not lower thresholds to inflate the sample count."
    if status == "NEAR_MISS_BOTTLENECK":
        return f"Near-miss candidates exist and the leading bottleneck is {top_filter}. Review thresholds after more evidence; do not mutate strategy parameters in this patch."
    if status == "STAGNATED":
        return f"Observation stream is stagnant and no new unique candidates are detected. Investigate bottleneck filter {top_filter}; keep paper/live gates closed."
    return "No current HYP-005-R1 candidate regime is detected. Keep no-order diagnostics and scheduler active; do not train, reload, paper trade, live trade, or send orders."


def build_stagnation_diagnostics_report(
    *,
    candidate_spec: Mapping[str, Any] | None,
    ledger_rows: Sequence[Mapping[str, Any]],
    candles: Sequence[Candle],
    generated_at: str | None = None,
) -> dict[str, Any]:
    generated = generated_at or utc_now_iso()
    spec = parse_runtime_spec(candidate_spec)
    existing_ids = ledger_identity_set(ledger_rows)
    grouped = group_by_symbol(candles)
    audits = scan_candidate_audit(candles, spec, existing_ids)
    ledger = _ledger_summary(ledger_rows, spec)
    candidates = _candidate_summary(audits, grouped)
    stagnation = _stagnation_summary(ledger, candidates, generated)
    decision = "HYP005_SHADOW_STAGNATION_DIAGNOSTICS_READY" if candles else "HYP005_SHADOW_STAGNATION_DIAGNOSTICS_BLOCK"
    ok = bool(candles)
    return {
        "contract_version": CONTRACT_VERSION,
        "report_type": "hyp005_shadow_observation_stagnation_diagnostics_no_order_research_bottleneck_report",
        "generated_at_utc": generated,
        "ok": ok,
        "decision": decision,
        "hypothesis_id": HYPOTHESIS_ID,
        "branch_name": BRANCH_NAME,
        "selected_strategy_family": spec.strategy_family,
        "timeframe": spec.timeframe,
        "read_only": True,
        "no_order_research_diagnostics_only": True,
        "network_request_performed": False,
        "config_mutation_performed": False,
        "scheduler_mutation_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "post_requests_allowed": False,
        "order_actions_performed": False,
        "approved_for_training_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "runtime_spec": asdict(spec),
        "ledger_summary": ledger,
        "candidate_diagnostics": candidates,
        "stagnation": stagnation,
        "reason_codes": [
            "NO_ORDER_RESEARCH_DIAGNOSTICS_ONLY",
            "PAPER_LIVE_GATES_REMAIN_CLOSED",
            "STRATEGY_PARAMETER_MUTATION_NOT_PERFORMED",
        ],
        "warnings": ["SHADOW_OBSERVATION_STAGNATION_DETECTED"] if stagnation.get("status") == "STAGNATED" else [],
        "recommendation": _recommendation(stagnation, candidates),
    }
