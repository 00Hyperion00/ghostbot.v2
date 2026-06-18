from __future__ import annotations

import csv
import json
import math
import os
import tempfile
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import urlencode
from urllib.request import Request, urlopen

CONTRACT_VERSION = "4B.4.3.6.6.28C"
SOURCE_REGISTRATION_CONTRACT_VERSION = "4B.4.3.6.6.28B"
HYPOTHESIS_ID = "HYP-006"
BRANCH_ID = "HYP-006-R1"
BRANCH_NAME = "failed_downside_sweep_reversal_continuation_short"
STRATEGY_FAMILY = "short_failed_liquidity_sweep_continuation"
REPORT_PREFIX = "4B436628C_hyp006_r1_no_order_shadow_runner_dry_run"
DRY_RUN_LEDGER_PREFIX = "4B436628C_hyp006_r1_shadow_dry_run_ledger"
NEXT_REQUIRED_GATE = "28D_CANONICAL_NO_ORDER_SHADOW_COLLECTION_SCHEDULER_REGISTRATION_OPERATOR_APPROVAL"
PROPOSED_SCHEDULER_TASK_NAME = "TradeBot_HYP006_R1_Canonical_NoOrderShadowCollection"
PUBLIC_BINANCE_BASE_URL = "https://api.binance.com"
CANDIDATE_SCAN_HOOK_CONTRACT_VERSION = "4B.4.3.6.6.28G-H3"
CANDIDATE_SCAN_ARTIFACT_PREFIX = "4B436628G_H3_hyp006_r1_runtime_candidate_scan_gate_level_near_miss"
NEAR_MISS_MAX_FAILED_GATES = 2


@dataclass(frozen=True)
class RuntimeSpec:
    lookback_bars: int = 24
    hold_bars: int = 6
    min_sweep_bps: float = 18.0
    min_wick_pct_reference: float = 42.0
    compression_window: int = 12
    compression_baseline_bars: int = 48
    max_compression_ratio_reference: float = 1.05
    max_slippage_proxy_bps: float = 12.0
    timeframe: str = "4h"


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
class Hyp006DryRunObservation:
    contract_version: str
    hypothesis_id: str
    branch_id: str
    branch_name: str
    observation_id: str
    timestamp_utc: str
    symbol: str
    timeframe: str
    strategy_family: str
    side: str
    lookback_low: float
    swept_low: float
    sweep_depth_bps: float
    reclaim_reference: bool
    wick_pct_reference: float
    compression_ratio_reference: float
    entry_reference_price: float
    hold_horizon_bars: int
    forward_return_bps_h1_short_probe: float | None
    forward_return_bps_h2_short_probe: float | None
    forward_return_bps_h3_short_probe: float | None
    forward_return_bps_final_short_probe: float | None
    mae_bps_short_probe: float | None
    mfe_bps_short_probe: float | None
    spread_slippage_proxy_bps: float
    data_quality_ok: bool
    duplicate_existing_observation: bool
    no_order_measurement_only: bool
    operator_review_status: str


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


def load_json(path: str | os.PathLike[str] | None) -> Any:
    if path is None:
        return None
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_jsonl(path: str | os.PathLike[str] | None) -> list[dict[str, Any]]:
    if path is None:
        return []
    rows: list[dict[str, Any]] = []
    target = Path(path)
    if not target.exists():
        return rows
    for line in target.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        if isinstance(item, Mapping):
            rows.append(dict(item))
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


def write_jsonl_atomic(path: str | os.PathLike[str], rows: Sequence[Mapping[str, Any]]) -> None:
    resolved = Path(path).resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(dict(row), ensure_ascii=True, sort_keys=True) + "\n" for row in rows)
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


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _sequence(value: Any) -> Sequence[Any]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return value
    return []


def extract_candidate_spec(source: Mapping[str, Any] | None) -> Mapping[str, Any]:
    payload = _mapping(source)
    nested = payload.get("candidate_spec_draft")
    if isinstance(nested, Mapping):
        return nested
    return payload


def validate_candidate_spec_source(source: Mapping[str, Any] | None) -> tuple[bool, list[str], Mapping[str, Any]]:
    spec = extract_candidate_spec(source)
    reasons: list[str] = []
    if not spec:
        reasons.append("CANDIDATE_SPEC_MISSING")
        return False, reasons, spec
    if spec.get("contract_version") != SOURCE_REGISTRATION_CONTRACT_VERSION:
        reasons.append("SOURCE_CONTRACT_VERSION_MISMATCH")
    if spec.get("hypothesis_id") != HYPOTHESIS_ID:
        reasons.append("HYPOTHESIS_ID_MISMATCH")
    if spec.get("branch_id") != BRANCH_ID:
        reasons.append("BRANCH_ID_MISMATCH")
    if spec.get("branch_name") != BRANCH_NAME:
        reasons.append("BRANCH_NAME_MISMATCH")
    if spec.get("strategy_family") != STRATEGY_FAMILY:
        reasons.append("STRATEGY_FAMILY_MISMATCH")
    if spec.get("no_order_shadow_only") is not True:
        reasons.append("NO_ORDER_SHADOW_ONLY_MISSING")
    approvals = _mapping(spec.get("approvals"))
    for flag in (
        "approved_for_shadow_collection",
        "approved_for_training_candidate",
        "approved_for_paper_candidate",
        "approved_for_live_real",
        "order_actions_allowed",
    ):
        if approvals.get(flag) is not False:
            reasons.append(f"UNSAFE_APPROVAL_{flag.upper()}")
    gate = _mapping(spec.get("registration_gate"))
    if gate.get("registration_requires_28c_runner") is not True:
        reasons.append("REGISTRATION_28C_GATE_MISSING")
    if gate.get("next_required_gate") != "28C_NO_ORDER_SHADOW_RUNNER_DRY_RUN_AND_OPERATOR_REGISTRATION_APPROVAL":
        reasons.append("SOURCE_NEXT_GATE_MISMATCH")
    return not reasons, reasons, spec


def runtime_spec_from_candidate_spec(source: Mapping[str, Any] | None) -> RuntimeSpec:
    spec = extract_candidate_spec(source)
    entry = _mapping(spec.get("entry_signal_definition"))
    params = _mapping(entry.get("parameters"))
    acceptance_metrics = _sequence(spec.get("required_shadow_acceptance_metrics"))
    max_slippage = 12.0
    for metric in acceptance_metrics:
        item = _mapping(metric)
        if item.get("name") == "max_slippage_proxy_bps":
            max_slippage = safe_float(item.get("threshold"), 12.0)
            break
    return RuntimeSpec(
        lookback_bars=max(2, safe_int(params.get("lookback_bars"), 24)),
        hold_bars=max(1, safe_int(params.get("hold_bars"), 6)),
        min_sweep_bps=safe_float(params.get("min_sweep_bps"), 18.0),
        min_wick_pct_reference=safe_float(params.get("min_wick_pct_reference"), 42.0),
        compression_window=max(2, safe_int(params.get("compression_window"), 12)),
        compression_baseline_bars=max(3, safe_int(params.get("compression_baseline_bars"), 48)),
        max_compression_ratio_reference=safe_float(params.get("max_compression_ratio_reference"), 1.05),
        max_slippage_proxy_bps=max_slippage,
        timeframe=str(entry.get("timeframe") or "4h"),
    )


def parse_csv_rows(path: str | os.PathLike[str], default_symbol: str = "TESTUSDT") -> list[Candle]:
    candles: list[Candle] = []
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            timestamp = row.get("timestamp_utc") or row.get("timestamp") or row.get("open_time") or row.get("time") or ""
            symbol = str(row.get("symbol") or default_symbol).strip().upper()
            if not timestamp or not symbol:
                continue
            candles.append(
                Candle(
                    timestamp_utc=str(timestamp),
                    symbol=symbol,
                    open=safe_float(row.get("open")),
                    high=safe_float(row.get("high")),
                    low=safe_float(row.get("low")),
                    close=safe_float(row.get("close")),
                    volume=safe_float(row.get("volume"), 0.0),
                )
            )
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
    base_url: str = PUBLIC_BINANCE_BASE_URL,
    timeout_sec: int = 15,
    limit_ceiling: int = 1000,
) -> list[Candle]:
    bars_needed = int(math.ceil(max(1, days) * 24 / _interval_hours(interval))) + 96
    limit = max(1, min(limit_ceiling, bars_needed))
    endpoint = base_url.rstrip("/") + "/api/v3/klines?" + urlencode({"symbol": symbol.upper(), "interval": interval, "limit": limit})
    req = Request(endpoint, method="GET", headers={"User-Agent": "tradebot-hyp006-dry-run/4B436628C"})
    with urlopen(req, timeout=timeout_sec) as response:  # noqa: S310 - explicit public market-data GET only.
        payload = json.loads(response.read().decode("utf-8"))
    candles: list[Candle] = []
    for raw in payload if isinstance(payload, list) else []:
        if not isinstance(raw, Sequence) or len(raw) < 6:
            continue
        open_time_ms = safe_int(raw[0], 0)
        timestamp = datetime.fromtimestamp(open_time_ms / 1000, tz=timezone.utc).replace(microsecond=0).isoformat()
        candles.append(
            Candle(
                timestamp_utc=timestamp,
                symbol=symbol.upper(),
                open=safe_float(raw[1]),
                high=safe_float(raw[2]),
                low=safe_float(raw[3]),
                close=safe_float(raw[4]),
                volume=safe_float(raw[5], 0.0),
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


def stable_observation_id(symbol: str, timeframe: str, timestamp_utc: str) -> str:
    return f"{HYPOTHESIS_ID}-{symbol.upper()}-{timeframe}-{canonical_timestamp_token(timestamp_utc)}"


def _range(candle: Candle) -> float:
    return max(0.0, candle.high - candle.low)


def _mean(values: Sequence[float]) -> float | None:
    clean = [value for value in values if value is not None and not math.isnan(value)]
    return None if not clean else sum(clean) / len(clean)


def _basis_bps(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator * 10000.0


def _short_return(entry: float, future_close: float | None) -> float | None:
    if entry <= 0 or future_close is None or future_close <= 0:
        return None
    return (entry - future_close) / entry * 10000.0


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


def existing_observation_ids(rows: Sequence[Mapping[str, Any]]) -> set[str]:
    values: set[str] = set()
    for row in rows:
        observation_id = row.get("observation_id")
        if observation_id:
            values.add(str(observation_id))
    return values


def _gate_counter_from_events(events: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for event in events:
        for gate in event.get("failed_gates", []) if isinstance(event.get("failed_gates"), list) else []:
            counter[str(gate)] += 1
    return dict(sorted(counter.items(), key=lambda item: (-item[1], item[0])))


def _empty_candidate_scan_diagnostics(
    *,
    runtime_spec: RuntimeSpec,
    scanned_candle_count: int = 0,
    skipped_insufficient_history_count: int = 0,
) -> dict[str, Any]:
    return {
        "contract_version": CANDIDATE_SCAN_HOOK_CONTRACT_VERSION,
        "report_type": "hyp006_r1_runtime_candidate_scan_gate_level_near_miss_emission",
        "hypothesis_id": HYPOTHESIS_ID,
        "branch_id": BRANCH_ID,
        "branch_name": BRANCH_NAME,
        "strategy_family": STRATEGY_FAMILY,
        "timeframe": runtime_spec.timeframe,
        "read_only": True,
        "runtime_hook_enabled": True,
        "raw_candidate_scan_artifact_found": True,
        "no_order_measurement_only": True,
        "strategy_parameter_mutation_performed": False,
        "config_mutation_performed": False,
        "scheduler_mutation_performed": False,
        "scheduler_task_created": False,
        "scheduler_task_modified": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "order_actions_performed": False,
        "approved_for_parameter_relaxation_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "scanned_candle_count": scanned_candle_count,
        "skipped_insufficient_history_count": skipped_insufficient_history_count,
        "candidate_count": 0,
        "near_miss_count": 0,
        "trigger_count": 0,
        "duplicate_existing_trigger_count": 0,
        "symbol_candidate_counter": {},
        "symbol_near_miss_counter": {},
        "symbol_trigger_counter": {},
        "gate_block_counter": {},
        "sample_near_miss_events": [],
        "sample_rejection_events": [],
        "sample_trigger_events": [],
    }


def _build_gate_evaluation(
    *,
    candle: Candle,
    lookback_low: float,
    sweep_depth_bps: float,
    wick_pct: float,
    reclaim_reference: bool,
    compression_ratio: float,
    spread_slippage_proxy: float,
    data_quality_ok: bool,
    runtime_spec: RuntimeSpec,
) -> dict[str, Any]:
    swept_low = candle.low
    gate_checks: dict[str, bool] = {
        "DATA_QUALITY_FILTER": bool(data_quality_ok),
        "DOWNSIDE_SWEEP_OCCURRED": swept_low < lookback_low,
        "MIN_SWEEP_DEPTH_BPS": sweep_depth_bps >= runtime_spec.min_sweep_bps,
        "RECLAIM_REFERENCE_CLOSE": bool(reclaim_reference),
        "MIN_WICK_PCT_REFERENCE": wick_pct >= runtime_spec.min_wick_pct_reference,
        "MAX_COMPRESSION_RATIO_REFERENCE": compression_ratio <= runtime_spec.max_compression_ratio_reference,
        "MAX_SPREAD_SLIPPAGE_PROXY_BPS": spread_slippage_proxy <= runtime_spec.max_slippage_proxy_bps,
    }
    failed_gates = [gate for gate, passed in gate_checks.items() if not passed]
    passed_gate_count = len(gate_checks) - len(failed_gates)
    candidate_probe = bool(gate_checks["DOWNSIDE_SWEEP_OCCURRED"] and data_quality_ok)
    trigger = not failed_gates
    near_miss = bool(candidate_probe and not trigger and len(failed_gates) <= NEAR_MISS_MAX_FAILED_GATES)
    return {
        "timestamp_utc": candle.timestamp_utc,
        "symbol": candle.symbol.upper(),
        "timeframe": runtime_spec.timeframe,
        "candidate_probe": candidate_probe,
        "trigger": trigger,
        "near_miss": near_miss,
        "gate_checks": gate_checks,
        "failed_gates": failed_gates,
        "passed_gate_count": passed_gate_count,
        "failed_gate_count": len(failed_gates),
        "lookback_low": round(lookback_low, 8),
        "swept_low": round(swept_low, 8),
        "sweep_depth_bps": round(sweep_depth_bps, 6),
        "min_sweep_bps": runtime_spec.min_sweep_bps,
        "reclaim_reference": bool(reclaim_reference),
        "wick_pct_reference": round(wick_pct, 6),
        "min_wick_pct_reference": runtime_spec.min_wick_pct_reference,
        "compression_ratio_reference": round(compression_ratio, 6),
        "max_compression_ratio_reference": runtime_spec.max_compression_ratio_reference,
        "spread_slippage_proxy_bps": round(spread_slippage_proxy, 6),
        "max_slippage_proxy_bps": runtime_spec.max_slippage_proxy_bps,
        "data_quality_ok": bool(data_quality_ok),
    }


def merge_candidate_scan_diagnostics(diagnostics: Sequence[Mapping[str, Any]], *, sample_limit: int = 100) -> dict[str, Any]:
    candidate_count = 0
    near_miss_count = 0
    trigger_count = 0
    duplicate_existing_trigger_count = 0
    scanned_candle_count = 0
    skipped_insufficient_history_count = 0
    symbol_candidate_counter: Counter[str] = Counter()
    symbol_near_miss_counter: Counter[str] = Counter()
    symbol_trigger_counter: Counter[str] = Counter()
    gate_block_counter: Counter[str] = Counter()
    sample_near_miss_events: list[Mapping[str, Any]] = []
    sample_rejection_events: list[Mapping[str, Any]] = []
    sample_trigger_events: list[Mapping[str, Any]] = []
    timeframe = "4h"

    for item in diagnostics:
        timeframe = str(item.get("timeframe") or timeframe)
        candidate_count += int(item.get("candidate_count") or 0)
        near_miss_count += int(item.get("near_miss_count") or 0)
        trigger_count += int(item.get("trigger_count") or 0)
        duplicate_existing_trigger_count += int(item.get("duplicate_existing_trigger_count") or 0)
        scanned_candle_count += int(item.get("scanned_candle_count") or 0)
        skipped_insufficient_history_count += int(item.get("skipped_insufficient_history_count") or 0)
        symbol_candidate_counter.update({str(key): int(value) for key, value in dict(item.get("symbol_candidate_counter") or {}).items()})
        symbol_near_miss_counter.update({str(key): int(value) for key, value in dict(item.get("symbol_near_miss_counter") or {}).items()})
        symbol_trigger_counter.update({str(key): int(value) for key, value in dict(item.get("symbol_trigger_counter") or {}).items()})
        gate_block_counter.update({str(key): int(value) for key, value in dict(item.get("gate_block_counter") or {}).items()})
        sample_near_miss_events.extend([event for event in item.get("sample_near_miss_events", []) if isinstance(event, Mapping)])
        sample_rejection_events.extend([event for event in item.get("sample_rejection_events", []) if isinstance(event, Mapping)])
        sample_trigger_events.extend([event for event in item.get("sample_trigger_events", []) if isinstance(event, Mapping)])

    return {
        "contract_version": CANDIDATE_SCAN_HOOK_CONTRACT_VERSION,
        "report_type": "hyp006_r1_runtime_candidate_scan_gate_level_near_miss_emission",
        "hypothesis_id": HYPOTHESIS_ID,
        "branch_id": BRANCH_ID,
        "branch_name": BRANCH_NAME,
        "strategy_family": STRATEGY_FAMILY,
        "timeframe": timeframe,
        "read_only": True,
        "runtime_hook_enabled": True,
        "raw_candidate_scan_artifact_found": True,
        "no_order_measurement_only": True,
        "strategy_parameter_mutation_performed": False,
        "config_mutation_performed": False,
        "scheduler_mutation_performed": False,
        "scheduler_task_created": False,
        "scheduler_task_modified": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "order_actions_performed": False,
        "approved_for_parameter_relaxation_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "scanned_candle_count": scanned_candle_count,
        "skipped_insufficient_history_count": skipped_insufficient_history_count,
        "candidate_count": candidate_count,
        "near_miss_count": near_miss_count,
        "trigger_count": trigger_count,
        "duplicate_existing_trigger_count": duplicate_existing_trigger_count,
        "symbol_candidate_counter": dict(sorted(symbol_candidate_counter.items())),
        "symbol_near_miss_counter": dict(sorted(symbol_near_miss_counter.items())),
        "symbol_trigger_counter": dict(sorted(symbol_trigger_counter.items())),
        "gate_block_counter": dict(sorted(gate_block_counter.items(), key=lambda pair: (-pair[1], pair[0]))),
        "sample_near_miss_events": list(sample_near_miss_events[:sample_limit]),
        "sample_rejection_events": list(sample_rejection_events[:sample_limit]),
        "sample_trigger_events": list(sample_trigger_events[:sample_limit]),
        "recommendation": "Review gate-level near-miss evidence before any separate research-only parameter sensitivity proposal. Trading gates remain closed.",
    }


def scan_hyp006_short_probe_observations_with_diagnostics(
    candles: Sequence[Candle],
    *,
    runtime_spec: RuntimeSpec,
    existing_ids: set[str] | None = None,
    sample_limit: int = 100,
) -> tuple[list[Hyp006DryRunObservation], dict[str, Any]]:
    existing_ids = set(existing_ids or set())
    observations: list[Hyp006DryRunObservation] = []
    lookback = runtime_spec.lookback_bars
    hold = runtime_spec.hold_bars
    compression_window = runtime_spec.compression_window
    compression_baseline = runtime_spec.compression_baseline_bars
    min_index = max(lookback, compression_window, compression_baseline) + 1
    ranges = [_range(item) for item in candles]
    diagnostics = _empty_candidate_scan_diagnostics(
        runtime_spec=runtime_spec,
        scanned_candle_count=0,
        skipped_insufficient_history_count=min(len(candles), min_index),
    )
    symbol_candidate_counter: Counter[str] = Counter()
    symbol_near_miss_counter: Counter[str] = Counter()
    symbol_trigger_counter: Counter[str] = Counter()
    gate_block_counter: Counter[str] = Counter()
    sample_near_miss_events: list[dict[str, Any]] = []
    sample_rejection_events: list[dict[str, Any]] = []
    sample_trigger_events: list[dict[str, Any]] = []

    candidate_count = 0
    near_miss_count = 0
    trigger_count = 0
    duplicate_existing_trigger_count = 0
    scanned_candle_count = 0

    for idx in range(min_index, len(candles)):
        if idx + hold >= len(candles):
            continue
        candle = candles[idx]
        prior = candles[idx - lookback : idx]
        if len(prior) < lookback:
            continue
        lookback_low = min(item.low for item in prior)
        if lookback_low <= 0:
            continue
        scanned_candle_count += 1
        swept_low = candle.low
        sweep_depth_bps = _basis_bps(lookback_low - swept_low, lookback_low)
        candle_range = max(candle.high - candle.low, 1e-12)
        wick_pct = max(0.0, min(candle.open, candle.close) - candle.low) / candle_range * 100.0
        reclaim_reference = candle.close > lookback_low
        short_ranges = ranges[max(0, idx - compression_window) : idx]
        base_ranges = ranges[max(0, idx - compression_baseline) : idx]
        short_mean = _mean(short_ranges) or 0.0
        base_mean = _mean(base_ranges) or 0.0
        compression_ratio = short_mean / base_mean if base_mean > 0 else 1.0
        spread_slippage_proxy = min(99.0, max(0.0, _basis_bps(candle.high - candle.low, candle.close) * 0.03))
        data_quality_ok = all(value > 0 for value in (candle.open, candle.high, candle.low, candle.close))
        event = _build_gate_evaluation(
            candle=candle,
            lookback_low=lookback_low,
            sweep_depth_bps=sweep_depth_bps,
            wick_pct=wick_pct,
            reclaim_reference=reclaim_reference,
            compression_ratio=compression_ratio,
            spread_slippage_proxy=spread_slippage_proxy,
            data_quality_ok=data_quality_ok,
            runtime_spec=runtime_spec,
        )
        if event["candidate_probe"]:
            candidate_count += 1
            symbol_candidate_counter[event["symbol"]] += 1
        if event["near_miss"]:
            near_miss_count += 1
            symbol_near_miss_counter[event["symbol"]] += 1
            if len(sample_near_miss_events) < sample_limit:
                sample_near_miss_events.append(event)
        if event["failed_gates"]:
            gate_block_counter.update(str(gate) for gate in event["failed_gates"])
            if event["candidate_probe"] and not event["near_miss"] and len(sample_rejection_events) < sample_limit:
                sample_rejection_events.append(event)

        if not event["trigger"]:
            continue

        entry = candle.close
        h1_close = candles[idx + 1].close if idx + 1 < len(candles) else None
        h2_close = candles[idx + 2].close if idx + 2 < len(candles) else None
        h3_close = candles[idx + 3].close if idx + 3 < len(candles) else None
        final_close = candles[idx + hold].close if idx + hold < len(candles) else None
        mae, mfe = _short_mae_mfe(candles, idx, hold, entry)
        observation_id = stable_observation_id(candle.symbol, runtime_spec.timeframe, candle.timestamp_utc)
        trigger_count += 1
        symbol_trigger_counter[candle.symbol.upper()] += 1
        if observation_id in existing_ids:
            duplicate_existing_trigger_count += 1
        trigger_event = dict(event)
        trigger_event["observation_id"] = observation_id
        trigger_event["duplicate_existing_observation"] = observation_id in existing_ids
        if len(sample_trigger_events) < sample_limit:
            sample_trigger_events.append(trigger_event)
        observations.append(
            Hyp006DryRunObservation(
                contract_version=CONTRACT_VERSION,
                hypothesis_id=HYPOTHESIS_ID,
                branch_id=BRANCH_ID,
                branch_name=BRANCH_NAME,
                observation_id=observation_id,
                timestamp_utc=candle.timestamp_utc,
                symbol=candle.symbol.upper(),
                timeframe=runtime_spec.timeframe,
                strategy_family=STRATEGY_FAMILY,
                side="SHORT_RESEARCH_PROBE_ONLY",
                lookback_low=round(lookback_low, 8),
                swept_low=round(swept_low, 8),
                sweep_depth_bps=round(sweep_depth_bps, 6),
                reclaim_reference=bool(reclaim_reference),
                wick_pct_reference=round(wick_pct, 6),
                compression_ratio_reference=round(compression_ratio, 6),
                entry_reference_price=round(entry, 8),
                hold_horizon_bars=hold,
                forward_return_bps_h1_short_probe=None if h1_close is None else round(_short_return(entry, h1_close) or 0.0, 6),
                forward_return_bps_h2_short_probe=None if h2_close is None else round(_short_return(entry, h2_close) or 0.0, 6),
                forward_return_bps_h3_short_probe=None if h3_close is None else round(_short_return(entry, h3_close) or 0.0, 6),
                forward_return_bps_final_short_probe=None if final_close is None else round(_short_return(entry, final_close) or 0.0, 6),
                mae_bps_short_probe=mae,
                mfe_bps_short_probe=mfe,
                spread_slippage_proxy_bps=round(spread_slippage_proxy, 6),
                data_quality_ok=data_quality_ok,
                duplicate_existing_observation=observation_id in existing_ids,
                no_order_measurement_only=True,
                operator_review_status="PENDING_28D_OPERATOR_REGISTRATION_REVIEW",
            )
        )

    diagnostics.update(
        {
            "scanned_candle_count": scanned_candle_count,
            "candidate_count": candidate_count,
            "near_miss_count": near_miss_count,
            "trigger_count": trigger_count,
            "duplicate_existing_trigger_count": duplicate_existing_trigger_count,
            "symbol_candidate_counter": dict(sorted(symbol_candidate_counter.items())),
            "symbol_near_miss_counter": dict(sorted(symbol_near_miss_counter.items())),
            "symbol_trigger_counter": dict(sorted(symbol_trigger_counter.items())),
            "gate_block_counter": dict(sorted(gate_block_counter.items(), key=lambda pair: (-pair[1], pair[0]))),
            "sample_near_miss_events": sample_near_miss_events,
            "sample_rejection_events": sample_rejection_events,
            "sample_trigger_events": sample_trigger_events,
        }
    )
    return observations, diagnostics


def scan_hyp006_short_probe_observations(
    candles: Sequence[Candle],
    *,
    runtime_spec: RuntimeSpec,
    existing_ids: set[str] | None = None,
) -> list[Hyp006DryRunObservation]:
    observations, _diagnostics = scan_hyp006_short_probe_observations_with_diagnostics(
        candles,
        runtime_spec=runtime_spec,
        existing_ids=existing_ids,
    )
    return observations


def summarize_observations(observations: Sequence[Hyp006DryRunObservation]) -> dict[str, Any]:
    rows = [asdict(item) for item in observations]
    final_returns = [item.forward_return_bps_final_short_probe for item in observations if item.forward_return_bps_final_short_probe is not None]
    wins = [value for value in final_returns if value > 0]
    losses = [abs(value) for value in final_returns if value < 0]
    profit_factor = (sum(wins) / sum(losses)) if losses else (999.0 if wins else 0.0)
    symbols = sorted({item.symbol for item in observations})
    duplicate_count = sum(1 for item in observations if item.duplicate_existing_observation)
    unique_new = len({item.observation_id for item in observations if not item.duplicate_existing_observation})
    return {
        "dry_run_observation_count": len(observations),
        "new_unique_dry_run_observation_count": unique_new,
        "duplicate_existing_observation_count": duplicate_count,
        "matured_count": len(final_returns),
        "symbols_observed": symbols,
        "symbols_observed_count": len(symbols),
        "symbol_counts": dict(sorted(Counter(item.symbol for item in observations).items())),
        "win_count": len(wins),
        "loss_count": len(losses),
        "win_rate_pct": round(len(wins) / len(final_returns) * 100.0, 6) if final_returns else 0.0,
        "net_return_bps": round(sum(final_returns), 6) if final_returns else 0.0,
        "mean_return_bps": round(sum(final_returns) / len(final_returns), 6) if final_returns else None,
        "median_return_bps": round(sorted(final_returns)[len(final_returns) // 2], 6) if final_returns else None,
        "profit_factor": round(profit_factor, 6),
        "best_return_bps": round(max(final_returns), 6) if final_returns else None,
        "worst_return_bps": round(min(final_returns), 6) if final_returns else None,
        "sample_observation_ids": [str(row.get("observation_id")) for row in rows[:20]],
    }


def build_scheduler_registration_preflight(*, out_dir: str | os.PathLike[str] | None = None) -> dict[str, Any]:
    report_dir = Path(out_dir or "reports/hyp006_r1_canonical")
    return {
        "preflight_status": "READY_FOR_OPERATOR_REVIEW_NOT_REGISTERED",
        "proposed_task_name": PROPOSED_SCHEDULER_TASK_NAME,
        "proposed_reports_dir": str(report_dir),
        "proposed_frequency": "4h candle close / operator approved canonical schedule",
        "requires_operator_registration_approval": True,
        "requires_separate_scheduler_patch": True,
        "scheduler_task_created": False,
        "scheduler_task_modified": False,
        "scheduler_mutation_performed": False,
        "canonical_runner_dry_run_required": False,
        "registration_blockers": [
            "NO_28D_OPERATOR_REGISTRATION_APPROVAL",
            "NO_CANONICAL_SCHEDULER_MUTATION_PATCH",
            "NO_HYP006_ACCEPTANCE_LEDGER_YET",
            "NO_PAPER_LIVE_TRAINING_RELOAD_ORDER_ENABLEMENT",
        ],
    }


def build_hyp006_shadow_runner_dry_run_report(
    *,
    candidate_spec_source: Mapping[str, Any] | None,
    candles: Sequence[Candle],
    symbols: Sequence[str] | None = None,
    existing_ledger_rows: Sequence[Mapping[str, Any]] | None = None,
    source_paths: Mapping[str, Any] | None = None,
    network_request_performed: bool = False,
    out_dir: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    source_paths = dict(source_paths or {})
    spec_ok, spec_reasons, spec = validate_candidate_spec_source(candidate_spec_source)
    runtime_spec = runtime_spec_from_candidate_spec(spec)
    grouped = group_by_symbol(candles)
    requested_symbols = sorted({item.upper() for item in (symbols or grouped.keys())})
    existing_ids = existing_observation_ids(list(existing_ledger_rows or []))
    observations: list[Hyp006DryRunObservation] = []
    scan_diagnostics: list[Mapping[str, Any]] = []
    rows_by_symbol: dict[str, int] = {}
    for symbol in requested_symbols:
        rows = grouped.get(symbol, [])
        rows_by_symbol[symbol] = len(rows)
        if spec_ok:
            symbol_observations, symbol_diagnostics = scan_hyp006_short_probe_observations_with_diagnostics(
                rows,
                runtime_spec=runtime_spec,
                existing_ids=existing_ids,
            )
            observations.extend(symbol_observations)
            scan_diagnostics.append(symbol_diagnostics)
    candidate_scan_diagnostics = merge_candidate_scan_diagnostics(scan_diagnostics)
    summary = summarize_observations(observations)
    dry_run_ok = bool(spec_ok and rows_by_symbol and all(count > 0 for count in rows_by_symbol.values()))
    decision = "HYP006_R1_NO_ORDER_SHADOW_RUNNER_DRY_RUN_READY" if dry_run_ok else "HYP006_R1_NO_ORDER_SHADOW_RUNNER_DRY_RUN_BLOCKED"
    blockers: list[str] = []
    if not spec_ok:
        blockers.extend(spec_reasons)
    if not rows_by_symbol or any(count == 0 for count in rows_by_symbol.values()):
        blockers.append("DRY_RUN_MARKET_DATA_MISSING")
    blockers.extend([
        "NO_28D_OPERATOR_REGISTRATION_APPROVAL",
        "NO_CANONICAL_SCHEDULER_REGISTRATION_PATCH",
        "NO_HYP006_SHADOW_ACCEPTANCE_METRICS",
        "NO_PAPER_LIVE_TRAINING_RELOAD_ORDER_ENABLEMENT",
    ])
    observations_payload = [asdict(item) for item in observations]
    scheduler_preflight = build_scheduler_registration_preflight(out_dir=out_dir)
    return {
        "contract_version": CONTRACT_VERSION,
        "source_registration_contract_version": _mapping(spec).get("contract_version"),
        "report_type": "hyp006_r1_no_order_shadow_runner_dry_run_operator_registration_preflight_pack",
        "decision": decision,
        "ok": dry_run_ok,
        "generated_at_utc": utc_now_iso(),
        "hypothesis_id": HYPOTHESIS_ID,
        "branch_id": BRANCH_ID,
        "branch_name": BRANCH_NAME,
        "strategy_family": STRATEGY_FAMILY,
        "runtime_spec": asdict(runtime_spec),
        "rows_by_symbol": rows_by_symbol,
        "symbols_requested": requested_symbols,
        "dry_run_summary": summary,
        "dry_run_observations": observations_payload,
        "candidate_scan_diagnostics": candidate_scan_diagnostics,
        "runtime_candidate_scan_hook_contract_version": CANDIDATE_SCAN_HOOK_CONTRACT_VERSION,
        "candidate_spec_validation": {"ok": spec_ok, "reasons": sorted(set(spec_reasons))},
        "runner_dry_run_ready": dry_run_ok,
        "operator_registration_approval_gate_ready": dry_run_ok,
        "canonical_scheduler_registration_preflight_ready": dry_run_ok,
        "scheduler_registration_preflight": scheduler_preflight,
        "approved_for_operator_registration_review_candidate": dry_run_ok,
        "approved_for_no_order_shadow_collection_registration_candidate": dry_run_ok,
        "approved_for_shadow_collection": False,
        "approved_for_training_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "paper_transition_candidate_found": False,
        "blockers": sorted(set(blockers)),
        "reason_codes": [
            "NO_ORDER_SHADOW_RUNNER_DRY_RUN_ONLY",
            "OPERATOR_REGISTRATION_APPROVAL_REQUIRED",
            "CANONICAL_SCHEDULER_REGISTRATION_PREFLIGHT_ONLY",
            "PAPER_LIVE_GATES_REMAIN_CLOSED",
            "NO_TRAINING_RELOAD_ORDER_ENABLEMENT",
        ],
        "risk_items": [
            {"level": "critical", "code": "DRY_RUN_NOT_EXECUTION_EDGE", "detail": "HYP-006-R1 dry-run validates runner mechanics only."},
            {"level": "warning", "code": "SHORT_SIDE_COSTS_STILL_UNMODELED", "detail": "Funding, borrow, liquidation, and execution costs remain outside acceptance."},
            {"level": "warning", "code": "28D_REQUIRED", "detail": NEXT_REQUIRED_GATE},
        ],
        "next_required_gate": NEXT_REQUIRED_GATE,
        "recommendation": "Proceed to 28D operator-approved canonical scheduler registration only if the dry-run evidence is accepted. Do not train, reload, paper trade, live trade, or send orders.",
        "source_paths": source_paths,
        "read_only": True,
        "no_order_shadow_runner_dry_run_only": True,
        "post_requests_allowed": False,
        "network_request_performed": bool(network_request_performed),
        "config_mutation_performed": False,
        "scheduler_mutation_performed": False,
        "scheduler_task_created": False,
        "scheduler_task_modified": False,
        "strategy_parameter_mutation_performed": False,
        "branch_state_mutation_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "order_actions_performed": False,
        "warnings": ["28D_REQUIRED_BEFORE_CANONICAL_SHADOW_COLLECTION_REGISTRATION"],
    }


def write_markdown(path: str | os.PathLike[str], payload: Mapping[str, Any]) -> None:
    summary = _mapping(payload.get("dry_run_summary"))
    preflight = _mapping(payload.get("scheduler_registration_preflight"))
    lines = [
        "# 4B.4.3.6.6.28C HYP-006-R1 No-Order Shadow Runner Dry-Run",
        "",
        f"- decision: `{payload.get('decision')}`",
        f"- branch_id: `{payload.get('branch_id')}`",
        f"- dry_run_observation_count: `{summary.get('dry_run_observation_count')}`",
        f"- new_unique_dry_run_observation_count: `{summary.get('new_unique_dry_run_observation_count')}`",
        f"- operator_registration_approval_gate_ready: `{payload.get('operator_registration_approval_gate_ready')}`",
        f"- proposed_task_name: `{preflight.get('proposed_task_name')}`",
        f"- scheduler_mutation_performed: `{payload.get('scheduler_mutation_performed')}`",
        f"- approved_for_shadow_collection: `{payload.get('approved_for_shadow_collection')}`",
        f"- approved_for_paper_candidate: `{payload.get('approved_for_paper_candidate')}`",
        f"- approved_for_live_real: `{payload.get('approved_for_live_real')}`",
        f"- next_required_gate: `{payload.get('next_required_gate')}`",
        "",
        "## Recommendation",
        "",
        str(payload.get("recommendation", "")),
    ]
    resolved = Path(path).resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_report_bundle(payload: Mapping[str, Any], out_dir: str | os.PathLike[str]) -> tuple[Path, Path, Path]:
    target_dir = Path(out_dir)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_json = target_dir / f"{REPORT_PREFIX}_{stamp}.json"
    ledger_jsonl = target_dir / f"{DRY_RUN_LEDGER_PREFIX}_{stamp}.jsonl"
    report_md = target_dir / f"{REPORT_PREFIX}_{stamp}.md"
    write_json_atomic(report_json, payload)
    write_jsonl_atomic(ledger_jsonl, [dict(row) for row in _sequence(payload.get("dry_run_observations")) if isinstance(row, Mapping)])
    write_markdown(report_md, payload)
    return report_json, ledger_jsonl, report_md
