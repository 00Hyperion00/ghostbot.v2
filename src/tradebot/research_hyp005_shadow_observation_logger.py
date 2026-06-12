from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import csv
import json
import math

from .hyp005_shadow_observation_identity import (
    HYP005_SHADOW_OBSERVATION_END_TO_END_IDENTITY_VERSION,
    normalize_observation_identity,
)

HYP005_SHADOW_OBSERVATION_CONTRACT_VERSION = "4B.4.3.6.6.25V"
HYPOTHESIS_ID = "HYP-005"
BRANCH_NAME = "liquidity_sweep_reversal_vol_compression"
STRATEGY_FAMILY = "long_liquidity_sweep_reversal"
REPORT_PREFIX = "4B436625V_hyp005_shadow_observation_logger"
LEDGER_PREFIX = "4B436625V_hyp005_shadow_observation_ledger"


@dataclass(frozen=True)
class Hyp005ShadowRuntimeLimits:
    min_shadow_sample_target: int = 30
    min_required_fields: int = 18
    max_missing_fields_pct: float = 1.0
    max_slippage_proxy_bps: float = 12.0
    max_stale_source_age_sec: int = 900
    min_rows_per_symbol: int = 30
    max_public_fetch_limit: int = 1000


@dataclass(frozen=True)
class Hyp005ShadowCandidateRuntimeSpec:
    hypothesis_id: str
    branch_name: str
    strategy_family: str
    timeframe: str
    lookback_bars: int
    hold_bars: int
    min_sweep_bps: float
    min_wick_pct: float
    compression_window: int
    compression_baseline_bars: int
    max_compression_ratio: float
    risk_observation_fields: list[str]
    no_order_shadow_only: bool
    orders_allowed: bool
    paper_trading_allowed: bool
    live_trading_allowed: bool
    training_allowed: bool
    model_reload_allowed: bool
    post_requests_allowed: bool
    paper_transition_requires_new_gate: bool
    live_transition_requires_separate_gate: bool


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
class ShadowObservation:
    contract_version: str
    hypothesis_id: str
    branch_name: str
    observation_id: str
    timestamp_utc: str
    symbol: str
    timeframe: str
    strategy_family: str
    sweep_direction: str
    lookback_low: float
    swept_low: float
    sweep_depth_bps: float
    wick_pct: float
    compression_ratio: float
    entry_reference_price: float
    invalidation_level: float
    hold_horizon_bars: int
    forward_return_bps_h1: float | None
    forward_return_bps_h2: float | None
    forward_return_bps_h3: float | None
    forward_return_bps_final: float | None
    mae_bps: float | None
    mfe_bps: float | None
    spread_slippage_proxy_bps: float
    volume_context: dict[str, Any]
    regime_context: dict[str, Any]
    data_quality_ok: bool
    operator_review_status: str
    no_order_shadow_only: bool = True
    order_action: str = "NONE"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_json(path: str | Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    p = Path(path)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def write_json(path: str | Path, payload: Any) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")


def write_jsonl(path: str | Path, rows: Sequence[Mapping[str, Any]]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(dict(row), sort_keys=True, ensure_ascii=False) + "\n")


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


def _is_mapping(value: Any) -> bool:
    return isinstance(value, Mapping)


def _nested_mapping(root: Mapping[str, Any], *keys: str) -> Mapping[str, Any]:
    node: Any = root
    for key in keys:
        if not isinstance(node, Mapping):
            return {}
        node = node.get(key)
    return node if isinstance(node, Mapping) else {}


def _candidate_spec_payload(payload: Mapping[str, Any] | None) -> Mapping[str, Any]:
    if not isinstance(payload, Mapping):
        return {}
    if payload.get("status") == "NO_ORDER_SHADOW_PLAN_READY" or payload.get("strategy_family") == STRATEGY_FAMILY:
        return payload
    candidate = payload.get("candidate_spec")
    return candidate if isinstance(candidate, Mapping) else {}


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


def parse_runtime_spec(candidate_spec: Mapping[str, Any] | None) -> Hyp005ShadowCandidateRuntimeSpec | None:
    spec = _candidate_spec_payload(candidate_spec)
    if not spec:
        return None
    entry = _nested_mapping(spec, "entry_signal_definition")
    params = _nested_mapping(spec, "entry_signal_definition", "parameters")
    guardrails = _nested_mapping(spec, "guardrails")
    fields = spec.get("risk_observation_fields")
    risk_fields = [str(item) for item in fields] if isinstance(fields, Sequence) and not isinstance(fields, (str, bytes)) else []
    return Hyp005ShadowCandidateRuntimeSpec(
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
        risk_observation_fields=risk_fields,
        no_order_shadow_only=bool(guardrails.get("no_order_shadow_only", True)),
        orders_allowed=bool(guardrails.get("orders_allowed", False)),
        paper_trading_allowed=bool(guardrails.get("paper_trading_allowed", False)),
        live_trading_allowed=bool(guardrails.get("live_trading_allowed", False)),
        training_allowed=bool(guardrails.get("training_allowed", False)),
        model_reload_allowed=bool(guardrails.get("model_reload_allowed", False)),
        post_requests_allowed=bool(guardrails.get("post_requests_allowed", False)),
        paper_transition_requires_new_gate=bool(guardrails.get("paper_transition_requires_new_gate", True)),
        live_transition_requires_separate_gate=bool(guardrails.get("live_transition_requires_separate_gate", True)),
    )


def validate_candidate_spec(
    candidate_spec: Mapping[str, Any] | None,
    limits: Hyp005ShadowRuntimeLimits | None = None,
) -> tuple[Hyp005ShadowCandidateRuntimeSpec | None, list[str], list[str]]:
    limits = limits or Hyp005ShadowRuntimeLimits()
    runtime_spec = parse_runtime_spec(candidate_spec)
    reasons: list[str] = []
    warnings: list[str] = []
    if runtime_spec is None:
        return None, ["HYP005_SHADOW_CANDIDATE_SPEC_MISSING"], warnings
    if runtime_spec.hypothesis_id != HYPOTHESIS_ID:
        reasons.append("HYP005_SPEC_HYPOTHESIS_MISMATCH")
    if runtime_spec.branch_name != BRANCH_NAME:
        reasons.append("HYP005_SPEC_BRANCH_MISMATCH")
    if runtime_spec.strategy_family != STRATEGY_FAMILY:
        reasons.append("HYP005_SPEC_STRATEGY_MISMATCH")
    if not runtime_spec.no_order_shadow_only:
        reasons.append("SPEC_NOT_NO_ORDER_SHADOW_ONLY")
    if runtime_spec.orders_allowed:
        reasons.append("SPEC_ORDERS_ALLOWED_GUARDRAIL_VIOLATION")
    if runtime_spec.paper_trading_allowed:
        reasons.append("SPEC_PAPER_ALLOWED_GUARDRAIL_VIOLATION")
    if runtime_spec.live_trading_allowed:
        reasons.append("SPEC_LIVE_ALLOWED_GUARDRAIL_VIOLATION")
    if runtime_spec.training_allowed or runtime_spec.model_reload_allowed or runtime_spec.post_requests_allowed:
        reasons.append("SPEC_SIDE_EFFECT_PERMISSION_GUARDRAIL_VIOLATION")
    if not runtime_spec.paper_transition_requires_new_gate:
        reasons.append("SPEC_PAPER_TRANSITION_GATE_MISSING")
    if not runtime_spec.live_transition_requires_separate_gate:
        reasons.append("SPEC_LIVE_TRANSITION_GATE_MISSING")
    if len(runtime_spec.risk_observation_fields) < limits.min_required_fields:
        warnings.append("SPEC_RISK_OBSERVATION_FIELDS_LOW")
    for required_field in (
        "timestamp_utc",
        "symbol",
        "strategy_family",
        "sweep_direction",
        "entry_reference_price",
        "invalidation_level",
        "forward_return_bps_final",
        "mae_bps",
        "mfe_bps",
        "spread_slippage_proxy_bps",
        "data_quality_ok",
    ):
        if runtime_spec.risk_observation_fields and required_field not in runtime_spec.risk_observation_fields:
            warnings.append(f"SPEC_FIELD_{required_field.upper()}_MISSING")
    return runtime_spec, sorted(set(reasons)), sorted(set(warnings))


def parse_csv_rows(path: str | Path, default_symbol: str = "TESTUSDT") -> list[Candle]:
    candles: list[Candle] = []
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for raw in reader:
            timestamp = raw.get("timestamp_utc") or raw.get("timestamp") or raw.get("open_time") or raw.get("time") or ""
            symbol = str(raw.get("symbol") or default_symbol)
            candle = Candle(
                timestamp_utc=str(timestamp),
                symbol=symbol,
                open=safe_float(raw.get("open")),
                high=safe_float(raw.get("high")),
                low=safe_float(raw.get("low")),
                close=safe_float(raw.get("close")),
                volume=safe_float(raw.get("volume"), 0.0),
            )
            if candle.high > 0 and candle.low > 0 and candle.close > 0 and candle.open > 0:
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


def fetch_binance_klines(
    *,
    symbol: str,
    interval: str,
    days: int,
    base_url: str,
    limit_ceiling: int = 1000,
    timeout_sec: int = 15,
) -> list[Candle]:
    # method="GET" public_market_data_GET_only
    bars_needed = int(math.ceil(max(1, days) * 24 / _interval_hours(interval))) + 80
    limit = max(1, min(limit_ceiling, bars_needed))
    endpoint = base_url.rstrip("/") + "/api/v3/klines?" + urlencode({"symbol": symbol, "interval": interval, "limit": limit})
    req = Request(endpoint, method="GET", headers={"User-Agent": "tradebot-hyp005-shadow-probe/4B436625V"})
    with urlopen(req, timeout=timeout_sec) as response:  # noqa: S310 - public market-data GET only; no credentials or POST.
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
        grouped.setdefault(candle.symbol, []).append(candle)
    for items in grouped.values():
        items.sort(key=lambda item: item.timestamp_utc)
    return grouped


def _mean(values: Sequence[float]) -> float | None:
    clean = [value for value in values if value is not None and not math.isnan(value)]
    if not clean:
        return None
    return sum(clean) / len(clean)


def _range(candle: Candle) -> float:
    return max(0.0, candle.high - candle.low)


def _basis_bps(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator * 10000.0


def _forward_return(entry: float, future_close: float | None) -> float | None:
    if entry <= 0 or future_close is None or future_close <= 0:
        return None
    return (future_close - entry) / entry * 10000.0


def _mae_mfe(candles: Sequence[Candle], start: int, hold_bars: int, entry: float) -> tuple[float | None, float | None]:
    if entry <= 0:
        return None, None
    future = candles[start + 1 : start + 1 + hold_bars]
    if not future:
        return None, None
    min_low = min(item.low for item in future)
    max_high = max(item.high for item in future)
    mae = (min_low - entry) / entry * 10000.0
    mfe = (max_high - entry) / entry * 10000.0
    return round(mae, 6), round(mfe, 6)


def scan_liquidity_sweep_observations(
    candles: Sequence[Candle],
    *,
    runtime_spec: Hyp005ShadowCandidateRuntimeSpec,
    timeframe: str,
) -> list[ShadowObservation]:
    observations: list[ShadowObservation] = []
    lookback = runtime_spec.lookback_bars
    hold = runtime_spec.hold_bars
    compression_window = runtime_spec.compression_window
    compression_baseline = runtime_spec.compression_baseline_bars
    min_index = max(lookback, compression_baseline, compression_window) + 1
    ranges = [_range(item) for item in candles]
    for idx in range(min_index, len(candles)):
        candle = candles[idx]
        prior = candles[idx - lookback : idx]
        if len(prior) < lookback:
            continue
        lookback_low = min(item.low for item in prior)
        if lookback_low <= 0:
            continue
        swept_low = candle.low
        sweep_depth_bps = _basis_bps(lookback_low - swept_low, lookback_low)
        candle_range = max(candle.high - candle.low, 1e-12)
        wick_pct = max(0.0, min(candle.open, candle.close) - candle.low) / candle_range * 100.0
        reclaim = candle.close > lookback_low
        short_ranges = ranges[max(0, idx - compression_window) : idx]
        base_ranges = ranges[max(0, idx - compression_baseline) : idx]
        short_mean = _mean(short_ranges) or 0.0
        base_mean = _mean(base_ranges) or 0.0
        compression_ratio = short_mean / base_mean if base_mean > 0 else 1.0
        if not (
            swept_low < lookback_low
            and sweep_depth_bps >= runtime_spec.min_sweep_bps
            and reclaim
            and wick_pct >= runtime_spec.min_wick_pct
            and compression_ratio <= runtime_spec.max_compression_ratio
        ):
            continue
        entry = candle.close
        h1_close = candles[idx + 1].close if idx + 1 < len(candles) else None
        h2_close = candles[idx + 2].close if idx + 2 < len(candles) else None
        h3_close = candles[idx + 3].close if idx + 3 < len(candles) else None
        final_close = candles[idx + hold].close if idx + hold < len(candles) else None
        mae, mfe = _mae_mfe(candles, idx, hold, entry)
        spread_slippage_proxy = min(99.0, max(0.0, _basis_bps(candle.high - candle.low, candle.close) * 0.03))
        data_quality_ok = all(value > 0 for value in (candle.open, candle.high, candle.low, candle.close))
        observation_id = f"{HYPOTHESIS_ID}-{candle.symbol}-{timeframe}-{idx}-{candle.timestamp_utc}".replace(":", "").replace("+", "Z")
        observations.append(
            ShadowObservation(
                contract_version=HYP005_SHADOW_OBSERVATION_CONTRACT_VERSION,
                hypothesis_id=HYPOTHESIS_ID,
                branch_name=BRANCH_NAME,
                observation_id=observation_id,
                timestamp_utc=candle.timestamp_utc,
                symbol=candle.symbol,
                timeframe=timeframe,
                strategy_family=runtime_spec.strategy_family,
                sweep_direction="DOWNSIDE_SWEEP_LONG_REVERSAL",
                lookback_low=round(lookback_low, 8),
                swept_low=round(swept_low, 8),
                sweep_depth_bps=round(sweep_depth_bps, 6),
                wick_pct=round(wick_pct, 6),
                compression_ratio=round(compression_ratio, 6),
                entry_reference_price=round(entry, 8),
                invalidation_level=round(swept_low, 8),
                hold_horizon_bars=hold,
                forward_return_bps_h1=None if h1_close is None else round(_forward_return(entry, h1_close) or 0.0, 6),
                forward_return_bps_h2=None if h2_close is None else round(_forward_return(entry, h2_close) or 0.0, 6),
                forward_return_bps_h3=None if h3_close is None else round(_forward_return(entry, h3_close) or 0.0, 6),
                forward_return_bps_final=None if final_close is None else round(_forward_return(entry, final_close) or 0.0, 6),
                mae_bps=mae,
                mfe_bps=mfe,
                spread_slippage_proxy_bps=round(spread_slippage_proxy, 6),
                volume_context={"signal_volume": round(candle.volume, 8)},
                regime_context={"compression_ratio": round(compression_ratio, 6), "lookback_bars": lookback},
                data_quality_ok=data_quality_ok,
                operator_review_status="PENDING_REVIEW",
            )
        )
    return observations


def _observation_dicts(observations: Sequence[ShadowObservation]) -> list[dict[str, Any]]:
    return [normalize_observation_identity(asdict(item)) for item in observations]


def summarize_observations(
    observations: Sequence[ShadowObservation],
    *,
    runtime_spec: Hyp005ShadowCandidateRuntimeSpec | None,
    limits: Hyp005ShadowRuntimeLimits,
) -> dict[str, Any]:
    count = len(observations)
    symbols = sorted({item.symbol for item in observations})
    final_returns = [item.forward_return_bps_final for item in observations if item.forward_return_bps_final is not None]
    wins = [value for value in final_returns if value > 0]
    losses = [abs(value) for value in final_returns if value < 0]
    profit_factor = (sum(wins) / sum(losses)) if losses else (999.0 if wins else 0.0)
    missing_count = 0
    total_fields = 0
    required_fields = runtime_spec.risk_observation_fields if runtime_spec else []
    for item in _observation_dicts(observations):
        for field_name in required_fields:
            total_fields += 1
            if field_name not in item or item.get(field_name) is None:
                missing_count += 1
    missing_pct = (missing_count / total_fields * 100.0) if total_fields else 0.0
    data_quality_ok_count = sum(1 for item in observations if item.data_quality_ok)
    data_quality_pct = (data_quality_ok_count / count * 100.0) if count else 100.0
    slippage_values = [item.spread_slippage_proxy_bps for item in observations]
    symbol_counts = {symbol: sum(1 for item in observations if item.symbol == symbol) for symbol in symbols}
    dominant_symbol_pct = max(symbol_counts.values()) / count * 100.0 if count and symbol_counts else 0.0
    return {
        "shadow_observation_count": count,
        "symbols_observed": symbols,
        "symbols_observed_count": len(symbols),
        "shadow_signal_capture_count": count,
        "shadow_mean_forward_edge_bps": None if not final_returns else round(sum(final_returns) / len(final_returns), 6),
        "shadow_median_forward_edge_bps": None if not final_returns else round(sorted(final_returns)[len(final_returns) // 2], 6),
        "shadow_profit_factor": round(profit_factor, 6),
        "shadow_win_rate_pct": round(len(wins) / len(final_returns) * 100.0, 6) if final_returns else 0.0,
        "shadow_missing_fields_pct": round(missing_pct, 6),
        "shadow_data_quality_pct": round(data_quality_pct, 6),
        "shadow_slippage_proxy_bps": round(max(slippage_values), 6) if slippage_values else 0.0,
        "shadow_dominant_symbol_pct": round(dominant_symbol_pct, 6),
        "shadow_sample_target": limits.min_shadow_sample_target,
        "shadow_sample_target_met": count >= limits.min_shadow_sample_target,
        "forward_returns_available_count": len(final_returns),
    }


def build_hyp005_shadow_observation_logger_report(
    *,
    candidate_spec: Mapping[str, Any] | None,
    candles: Sequence[Candle],
    symbols: Sequence[str] | None = None,
    timeframe: str = "4h",
    limits: Hyp005ShadowRuntimeLimits | None = None,
) -> dict[str, Any]:
    limits = limits or Hyp005ShadowRuntimeLimits()
    runtime_spec, reasons, warnings = validate_candidate_spec(candidate_spec, limits)
    grouped = group_by_symbol(candles)
    requested_symbols = sorted(set(symbols or grouped.keys()))
    observations: list[ShadowObservation] = []
    rows_by_symbol = {symbol: len(grouped.get(symbol, [])) for symbol in requested_symbols}
    if runtime_spec is not None and not reasons:
        for symbol in requested_symbols:
            rows = grouped.get(symbol, [])
            if len(rows) < limits.min_rows_per_symbol:
                warnings.append(f"SHADOW_ROWS_LOW_{symbol}")
                continue
            observations.extend(scan_liquidity_sweep_observations(rows, runtime_spec=runtime_spec, timeframe=timeframe))
    else:
        warnings.append("SHADOW_SCAN_SKIPPED_INVALID_SPEC")
    observation_rows = _observation_dicts(observations)
    summary = summarize_observations(observations, runtime_spec=runtime_spec, limits=limits)
    if summary["shadow_observation_count"] < limits.min_shadow_sample_target:
        warnings.append("SHADOW_SAMPLE_COUNT_BELOW_ACCEPTANCE_TARGET")
    if summary["shadow_slippage_proxy_bps"] > limits.max_slippage_proxy_bps:
        warnings.append("SHADOW_SLIPPAGE_PROXY_HIGH")
    if summary["shadow_missing_fields_pct"] > limits.max_missing_fields_pct:
        reasons.append("SHADOW_MISSING_FIELDS_HIGH")
    decision = "HYP005_SHADOW_OBSERVATION_LOGGER_READY" if runtime_spec is not None and not reasons else "HYP005_SHADOW_OBSERVATION_LOGGER_BLOCK"
    approved_shadow = decision == "HYP005_SHADOW_OBSERVATION_LOGGER_READY"
    reason_codes = list(reasons)
    if approved_shadow:
        reason_codes.extend([
            "HYP005_SHADOW_CANDIDATE_SPEC_CONFIRMED",
            "NO_ORDER_SHADOW_LEDGER_READY",
            "NO_TRAINING_PAPER_LIVE_APPROVALS_DETECTED",
        ])
    else:
        reason_codes.append("NO_ORDER_SHADOW_LEDGER_NOT_READY")
    return {
        "contract_version": HYP005_SHADOW_OBSERVATION_CONTRACT_VERSION,
        "phase": "25V",
        "report_type": "hyp005_shadow_observation_logger_no_order_runtime_probe",
        "generated_at": utc_now_iso(),
        "hypothesis_id": HYPOTHESIS_ID,
        "branch_name": BRANCH_NAME,
        "decision": decision,
        "ok": approved_shadow,
        "selected_strategy_family": runtime_spec.strategy_family if runtime_spec else None,
        "timeframe": timeframe,
        "symbols_requested": requested_symbols,
        "rows_by_symbol": rows_by_symbol,
        "shadow_observation_count": summary["shadow_observation_count"],
        "shadow_sample_target": limits.min_shadow_sample_target,
        "shadow_sample_target_met": summary["shadow_sample_target_met"],
        "shadow_summary": summary,
        "shadow_observations": observation_rows,
        "identity_contract_version": HYP005_SHADOW_OBSERVATION_END_TO_END_IDENTITY_VERSION,
        "canonical_identity_end_to_end": True,
        "no_order_shadow_only": True,
        "runtime_probe_only": True,
        "reason_codes": sorted(set(reason_codes)),
        "warnings": sorted(set(warnings)),
        "recommendation": (
            "HYP-005 no-order shadow observation logger is ready. Keep collecting shadow observations; do not train, reload, paper trade, or enable live trading."
            if approved_shadow
            else "HYP-005 shadow observation logger is blocked. Fix candidate spec/data quality before collecting shadow observations; do not train, reload, paper trade, or enable live trading."
        ),
        "limits": asdict(limits),
        "guardrails": {
            "observation_only": True,
            "no_order_shadow_only": True,
            "runtime_probe_only": True,
            "orders_allowed": False,
            "paper_trading_allowed": False,
            "live_trading_allowed": False,
            "training_allowed": False,
            "model_reload_allowed": False,
            "config_mutation_allowed": False,
            "post_requests_allowed": False,
            "order_actions_performed": False,
            "reload_performed": False,
            "config_mutation_performed": False,
            "paper_transition_requires_new_gate": True,
            "live_transition_requires_separate_gate": True,
        },
        "approved_for_research_candidate": approved_shadow,
        "approved_for_shadow_candidate": approved_shadow,
        "approved_for_training_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "live_real_allowed": False,
        "post_requests_allowed": False,
        "config_mutation_performed": False,
        "order_actions_performed": False,
        "reload_performed": False,
    }


def report_to_markdown(report: Mapping[str, Any]) -> str:
    summary = report.get("shadow_summary") if isinstance(report.get("shadow_summary"), Mapping) else {}
    guardrails = report.get("guardrails") if isinstance(report.get("guardrails"), Mapping) else {}
    lines = [
        "# 4B.4.3.6.6.25V HYP-005 Shadow Observation Logger / No-Order Runtime Probe Gate",
        "",
        f"- contract_version: `{report.get('contract_version')}`",
        f"- decision: **{report.get('decision')}**",
        f"- hypothesis_id: `{report.get('hypothesis_id')}`",
        f"- branch_name: `{report.get('branch_name')}`",
        f"- selected_strategy_family: `{report.get('selected_strategy_family')}`",
        f"- timeframe: `{report.get('timeframe')}`",
        f"- shadow_observation_count: `{report.get('shadow_observation_count')}`",
        f"- shadow_sample_target: `{report.get('shadow_sample_target')}`",
        f"- shadow_sample_target_met: `{report.get('shadow_sample_target_met')}`",
        f"- approved_for_shadow_candidate: `{report.get('approved_for_shadow_candidate')}`",
        f"- approved_for_training_candidate: `{report.get('approved_for_training_candidate')}`",
        f"- approved_for_paper_candidate: `{report.get('approved_for_paper_candidate')}`",
        f"- approved_for_live_real: `{report.get('approved_for_live_real')}`",
        f"- reason_codes: `{report.get('reason_codes')}`",
        f"- warnings: `{report.get('warnings')}`",
        f"- recommendation: {report.get('recommendation')}",
        "",
        "## Shadow Summary",
        "",
        f"- shadow_mean_forward_edge_bps: `{summary.get('shadow_mean_forward_edge_bps')}`",
        f"- shadow_median_forward_edge_bps: `{summary.get('shadow_median_forward_edge_bps')}`",
        f"- shadow_profit_factor: `{summary.get('shadow_profit_factor')}`",
        f"- shadow_data_quality_pct: `{summary.get('shadow_data_quality_pct')}`",
        f"- shadow_missing_fields_pct: `{summary.get('shadow_missing_fields_pct')}`",
        f"- shadow_slippage_proxy_bps: `{summary.get('shadow_slippage_proxy_bps')}`",
        "",
        "## Guardrails",
        "",
        f"- no_order_shadow_only: `{guardrails.get('no_order_shadow_only')}`",
        f"- runtime_probe_only: `{guardrails.get('runtime_probe_only')}`",
        f"- orders_allowed: `{guardrails.get('orders_allowed')}`",
        f"- training_allowed: `{guardrails.get('training_allowed')}`",
        f"- paper_trading_allowed: `{guardrails.get('paper_trading_allowed')}`",
        f"- live_trading_allowed: `{guardrails.get('live_trading_allowed')}`",
        f"- post_requests_allowed: `{guardrails.get('post_requests_allowed')}`",
        "- Candidate observations are not trading permission.",
        "- Training remains blocked.",
        "- Paper/live remain blocked.",
    ]
    return "\n".join(lines) + "\n"
