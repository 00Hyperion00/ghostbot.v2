from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any, Iterable

HYP005_SHADOW_QUALITY_CONTRACT_VERSION = "4B.4.3.6.6.25AB-H2"
HYP005_SHADOW_QUALITY_HOTFIX_VERSION = "4B.4.3.6.6.25AB-H2"
HYP005_SHADOW_QUALITY_AUDIT_CONTINUE_COLLECTION = "HYP005_SHADOW_QUALITY_AUDIT_CONTINUE_COLLECTION"
HYP005_SHADOW_QUALITY_AUDIT_REVIEW_REQUIRED = "HYP005_SHADOW_QUALITY_AUDIT_REVIEW_REQUIRED"
HYP005_SHADOW_QUALITY_AUDIT_BLOCK = "HYP005_SHADOW_QUALITY_AUDIT_BLOCK"

OBSERVATION_CANONICAL_DEDUPLICATION_APPLIED = "OBSERVATION_CANONICAL_DEDUPLICATION_APPLIED"
OBSERVATION_DUPLICATES_REMOVED = "OBSERVATION_DUPLICATES_REMOVED"
MATURITY_PENDING_FIELD = "forward_return_bps_final"
RECOMMENDATION_MESSAGE_CONSISTENCY_APPLIED = "RECOMMENDATION_MESSAGE_CONSISTENCY_APPLIED"
BLOCK_WITH_UNIQUE_OBSERVATIONS_RECOMMENDATION = "BLOCK_WITH_UNIQUE_OBSERVATIONS_RECOMMENDATION"

HYP005_QUALITY_REQUIRED_FIELDS: tuple[str, ...] = (
    "observation_id",
    "hypothesis_id",
    "branch_name",
    "strategy_family",
    "symbol",
    "timeframe",
    "timestamp_utc",
    "entry_reference_price",
    "invalidation_level",
    "lookback_low",
    "swept_low",
    "sweep_depth_bps",
    "wick_pct",
    "compression_ratio",
    "spread_slippage_proxy_bps",
    "mae_bps",
    "mfe_bps",
    "data_quality_ok",
    "no_order_shadow_only",
    "order_action",
)

_OBSERVATION_LIST_KEYS: tuple[str, ...] = (
    "shadow_observations",
    "observations",
    "ledger",
    "records",
    "items",
    "rows",
)


@dataclass(frozen=True)
class Hyp005ShadowQualityLimits:
    min_shadow_sample_target: int = 30
    early_audit_min_observations: int = 10
    max_slippage_proxy_bps: float = 12.0
    max_symbol_dominance_pct: float = 50.0
    max_true_missing_fields_pct: float = 1.0
    max_maturity_pending_pct_for_ready: float = 35.0
    min_symbols_observed_for_10_symbol_set: int = 3
    min_matured_observations_for_edge_read: int = 5
    min_profit_factor_watch: float = 1.0
    min_mean_forward_edge_bps_watch: float = 0.0


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _safe_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def _safe_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "y"}:
            return True
        if lowered in {"false", "0", "no", "n"}:
            return False
    return None


def _mean(values: Iterable[float]) -> float | None:
    vals = [float(v) for v in values if _safe_float(v) is not None]
    if not vals:
        return None
    return round(sum(vals) / len(vals), 6)


def _median(values: Iterable[float]) -> float | None:
    vals = [float(v) for v in values if _safe_float(v) is not None]
    if not vals:
        return None
    return round(float(median(vals)), 6)


def _profit_factor(values: Iterable[float]) -> float | None:
    vals = [float(v) for v in values if _safe_float(v) is not None]
    if not vals:
        return None
    gains = sum(v for v in vals if v > 0)
    losses = abs(sum(v for v in vals if v < 0))
    if losses == 0:
        return 999.0 if gains > 0 else 0.0
    return round(gains / losses, 6)


def _win_rate(values: Iterable[float]) -> float | None:
    vals = [float(v) for v in values if _safe_float(v) is not None]
    if not vals:
        return None
    wins = sum(1 for v in vals if v > 0)
    return round((wins / len(vals)) * 100.0, 6)


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _load_jsonl(path: Path) -> list[Any]:
    rows: list[Any] = []
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def _latest_file(directory: Path, pattern: str) -> Path | None:
    matches = sorted(directory.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return matches[0] if matches else None


def _looks_like_observation(item: dict[str, Any]) -> bool:
    return bool(
        item.get("observation_id")
        or (item.get("symbol") and item.get("timeframe") and item.get("timestamp_utc"))
    )


def _extract_observations(payload: Any) -> list[dict[str, Any]]:
    """Extract observations from ledger snapshots, nested report objects, or JSONL wrapper rows.

    25AB-H1 intentionally does not treat every JSONL wrapper row as an observation.
    It recurses into known observation list keys first and only accepts dicts that look
    like actual observation rows.
    """
    if isinstance(payload, list):
        extracted: list[dict[str, Any]] = []
        for item in payload:
            if isinstance(item, dict):
                nested_found = False
                for key in _OBSERVATION_LIST_KEYS:
                    value = item.get(key)
                    if isinstance(value, list):
                        extracted.extend(_extract_observations(value))
                        nested_found = True
                if not nested_found and _looks_like_observation(item):
                    extracted.append(dict(item))
        return extracted

    if not isinstance(payload, dict):
        return []

    for key in _OBSERVATION_LIST_KEYS:
        value = payload.get(key)
        if isinstance(value, list):
            return _extract_observations(value)

    # Some ledgers are a mapping from observation_id to object.
    candidate_values = [item for item in payload.values() if isinstance(item, dict)]
    if candidate_values and any(_looks_like_observation(item) for item in candidate_values):
        return [dict(item) for item in candidate_values if _looks_like_observation(item)]

    if _looks_like_observation(payload):
        return [dict(payload)]
    return []


def _normalize_timestamp(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    candidate = raw.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(candidate)
    except ValueError:
        return raw
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _safe_key_part(value: Any, default: str = "UNKNOWN") -> str:
    text = str(value or "").strip()
    return text.upper() if text else default


def _compact_timestamp_for_observation_id(normalized_timestamp: str) -> str:
    # Real 25V IDs keep the date dashes but remove the time colons, e.g.
    # 2026-05-18T04:00:00Z -> 2026-05-18T040000Z.
    return normalized_timestamp.replace(":", "").replace("+0000", "Z")


def _observation_id_looks_like_rolling_25v_id(observation: dict[str, Any], normalized_timestamp: str) -> bool:
    obs_id = str(observation.get("observation_id") or "").upper()
    if not obs_id.startswith("HYP-005-"):
        return False
    symbol = _safe_key_part(observation.get("symbol"))
    timeframe = str(observation.get("timeframe") or "").lower()
    compact_timestamp = _compact_timestamp_for_observation_id(normalized_timestamp).upper()
    return bool(symbol in obs_id and timeframe.upper() in obs_id and compact_timestamp in obs_id)


def _canonical_observation_key(observation: dict[str, Any]) -> tuple[str, str, str, str, str]:
    """Stable dedupe key independent of rolling-window row index in observation_id.

    25V observation_id may embed a rolling row index. The same symbol/timeframe/candle
    can therefore receive different IDs across scheduler cycles. The canonical key
    dedupes real 25V IDs by hypothesis, strategy family, symbol, timeframe, and candle timestamp.

    Non-standard/test IDs are kept distinct by appending the ID to the timestamp component.
    This preserves backwards compatibility for callers that intentionally create multiple
    synthetic observations on the same timestamp with short IDs such as ``a`` and ``c``.
    """
    normalized_timestamp = _normalize_timestamp(observation.get("timestamp_utc"))
    obs_id = str(observation.get("observation_id") or "").strip()
    timestamp_key = normalized_timestamp
    if obs_id and not _observation_id_looks_like_rolling_25v_id(observation, normalized_timestamp):
        timestamp_key = f"{normalized_timestamp}|id={obs_id}"
    return (
        _safe_key_part(observation.get("hypothesis_id"), "HYP-005"),
        str(observation.get("strategy_family") or observation.get("branch_name") or "UNKNOWN").strip().lower(),
        _safe_key_part(observation.get("symbol")),
        str(observation.get("timeframe") or "UNKNOWN").strip().lower(),
        timestamp_key,
    )


def _missing_required_fields(observation: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    for field in HYP005_QUALITY_REQUIRED_FIELDS:
        value = observation.get(field)
        if value is None or value == "":
            missing.append(field)
    return missing


def _observation_rank(observation: dict[str, Any]) -> tuple[int, int, int, int, int, str]:
    """Higher rank wins when duplicate observations are present."""
    matured = 1 if _safe_float(observation.get(MATURITY_PENDING_FIELD)) is not None else 0
    data_quality = 1 if _safe_bool(observation.get("data_quality_ok")) is True else 0
    true_missing_penalty = -len(_missing_required_fields(observation))
    obs_id_present = 1 if str(observation.get("observation_id") or "").strip() else 0
    numeric_field_score = sum(
        1
        for field in (
            "entry_reference_price",
            "invalidation_level",
            "sweep_depth_bps",
            "wick_pct",
            "compression_ratio",
            "spread_slippage_proxy_bps",
            "mae_bps",
            "mfe_bps",
            "forward_return_bps_h1",
            "forward_return_bps_h2",
            "forward_return_bps_h3",
        )
        if _safe_float(observation.get(field)) is not None
    )
    return (
        matured,
        data_quality,
        true_missing_penalty,
        obs_id_present,
        numeric_field_score,
        str(observation.get("observation_id") or ""),
    )


def _dedupe_observations_with_stats(observations: Iterable[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    by_key: dict[tuple[str, str, str, str, str], dict[str, Any]] = {}
    by_key_rank: dict[tuple[str, str, str, str, str], tuple[int, int, int, int, int, str]] = {}
    raw_count = 0
    canonical_missing_count = 0
    duplicate_keys: dict[str, int] = {}

    for obs in observations:
        if not isinstance(obs, dict):
            continue
        raw_count += 1
        key = _canonical_observation_key(obs)
        if not key[-1]:
            # Timestamp-less rows cannot be safely canonicalized; fall back to observation_id.
            canonical_missing_count += 1
            obs_id = str(obs.get("observation_id") or f"__no_canonical_{raw_count:06d}")
            key = ("FALLBACK", "fallback", "UNKNOWN", "unknown", obs_id)
        rank = _observation_rank(obs)
        key_text = "|".join(key)
        if key in by_key:
            duplicate_keys[key_text] = duplicate_keys.get(key_text, 1) + 1
            if rank > by_key_rank[key]:
                by_key[key] = dict(obs)
                by_key_rank[key] = rank
        else:
            by_key[key] = dict(obs)
            by_key_rank[key] = rank

    deduped = sorted(
        by_key.values(),
        key=lambda item: (
            _normalize_timestamp(item.get("timestamp_utc")),
            str(item.get("symbol") or ""),
            str(item.get("timeframe") or ""),
            str(item.get("observation_id") or ""),
        ),
    )
    duplicate_removed = raw_count - len(deduped)
    stats = {
        "dedupe_enabled": True,
        "dedupe_key_strategy": "hypothesis_id|strategy_family|symbol|timeframe|timestamp_utc",
        "raw_observation_count": raw_count,
        "unique_observation_count": len(deduped),
        "duplicate_removed_count": duplicate_removed,
        "canonical_key_missing_count": canonical_missing_count,
        "duplicate_key_count": len(duplicate_keys),
        "duplicate_key_examples": sorted(duplicate_keys.keys())[:20],
        "preferred_duplicate_policy": "prefer_matured_forward_return_then_data_quality_then_fewer_missing_fields",
    }
    return deduped, stats


def _dedupe_observations(observations: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped, _stats = _dedupe_observations_with_stats(observations)
    return deduped


def _read_observation_sources(reports_dir: Path, include_all: bool) -> tuple[list[dict[str, Any]], list[str]]:
    source_paths: list[Path] = []
    observations: list[dict[str, Any]] = []

    json_ledgers = sorted(
        reports_dir.glob("4B436625V_hyp005_shadow_observation_ledger_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    jsonl_ledgers = sorted(
        reports_dir.glob("4B436625V_hyp005_shadow_observation_ledger_*.jsonl"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    if not include_all:
        json_ledgers = json_ledgers[:1]
        jsonl_ledgers = jsonl_ledgers[:1]

    for path in json_ledgers:
        try:
            payload = _read_json(path)
        except (OSError, json.JSONDecodeError):
            continue
        extracted = _extract_observations(payload)
        if extracted:
            observations.extend(extracted)
            source_paths.append(path)

    for path in jsonl_ledgers:
        rows = _load_jsonl(path)
        extracted = _extract_observations(rows)
        if extracted:
            observations.extend(extracted)
            source_paths.append(path)

    # Fallback: use latest 25V report if ledger files are absent or empty.
    if not observations:
        latest_25v = _latest_file(reports_dir, "4B436625V_hyp005_shadow_observation_logger_*.json")
        if latest_25v is not None:
            try:
                payload = _read_json(latest_25v)
            except (OSError, json.JSONDecodeError):
                payload = None
            extracted = _extract_observations(payload)
            if extracted:
                observations.extend(extracted)
                source_paths.append(latest_25v)

    return observations, [str(path) for path in source_paths]


def load_hyp005_shadow_observations(reports_dir: Path, include_all: bool = True) -> tuple[list[dict[str, Any]], list[str]]:
    """Load and canonical-deduplicate HYP-005 shadow observations from 25V ledgers and reports."""
    observations, source_paths, _stats = load_hyp005_shadow_observations_with_dedupe_stats(
        reports_dir, include_all=include_all
    )
    return observations, source_paths


def load_hyp005_shadow_observations_with_dedupe_stats(
    reports_dir: Path | str,
    include_all: bool = True,
) -> tuple[list[dict[str, Any]], list[str], dict[str, Any]]:
    reports_path = Path(reports_dir)
    raw_observations, source_paths = _read_observation_sources(reports_path, include_all=include_all)
    observations, dedupe_stats = _dedupe_observations_with_stats(raw_observations)
    dedupe_stats["source_path_count"] = len(source_paths)
    return observations, source_paths, dedupe_stats


def _symbol_quality_summary(symbol: str, rows: list[dict[str, Any]], limits: Hyp005ShadowQualityLimits) -> dict[str, Any]:
    returns = [_safe_float(row.get(MATURITY_PENDING_FIELD)) for row in rows]
    matured_returns = [ret for ret in returns if ret is not None]
    slippages = [_safe_float(row.get("spread_slippage_proxy_bps")) for row in rows]
    slippage_values = [value for value in slippages if value is not None]
    maes = [_safe_float(row.get("mae_bps")) for row in rows]
    mfes = [_safe_float(row.get("mfe_bps")) for row in rows]
    high_slippage_count = sum(1 for value in slippage_values if value > limits.max_slippage_proxy_bps)
    symbol_flags: list[str] = []
    if high_slippage_count > 0:
        symbol_flags.append("SYMBOL_SLIPPAGE_PROXY_HIGH")
    mean_edge = _mean(matured_returns)
    pf = _profit_factor(matured_returns)
    if mean_edge is not None and mean_edge < limits.min_mean_forward_edge_bps_watch:
        symbol_flags.append("SYMBOL_MEAN_FORWARD_EDGE_NEGATIVE")
    if pf is not None and pf < limits.min_profit_factor_watch:
        symbol_flags.append("SYMBOL_PROFIT_FACTOR_LOW")
    pending_count = len(rows) - len(matured_returns)
    if pending_count > 0:
        symbol_flags.append("SYMBOL_MATURITY_PENDING_PRESENT")
    return {
        "symbol": symbol,
        "observation_count": len(rows),
        "matured_observation_count": len(matured_returns),
        "maturity_pending_count": pending_count,
        "mean_forward_edge_bps": mean_edge,
        "median_forward_edge_bps": _median(matured_returns),
        "win_rate_pct": _win_rate(matured_returns),
        "profit_factor": pf,
        "mean_slippage_proxy_bps": _mean(slippage_values),
        "max_slippage_proxy_bps": max(slippage_values) if slippage_values else None,
        "high_slippage_count": high_slippage_count,
        "mean_mae_bps": _mean([value for value in maes if value is not None]),
        "mean_mfe_bps": _mean([value for value in mfes if value is not None]),
        "flags": symbol_flags,
    }




def _format_reason_list(values: Iterable[str]) -> str:
    unique = [str(value) for value in dict.fromkeys(values) if str(value).strip()]
    return ", ".join(unique) if unique else "none"


def _build_quality_audit_recommendation(
    *,
    decision: str,
    observation_count: int,
    blockers: list[str],
    warnings: list[str],
) -> tuple[str, str]:
    """Build a recommendation that matches the actual deduped observation count.

    25AB-H1 used the generic BLOCK message for every blocker, including true missing
    fields, and therefore could claim there were no unique observations while the
    report contained valid deduped observations. 25AB-H2 makes the message consistent
    with the canonical deduplication result.
    """
    blocker_text = _format_reason_list(blockers)
    warning_text = _format_reason_list(warnings)
    if decision == HYP005_SHADOW_QUALITY_AUDIT_BLOCK:
        if observation_count <= 0:
            return (
                "HYP-005 shadow quality audit found no unique shadow observations after canonical deduplication. "
                "Keep paper/live/order disabled and verify 25V/25X collection.",
                "NO_UNIQUE_OBSERVATIONS_RECOMMENDATION",
            )
        return (
            f"HYP-005 shadow quality audit is blocked with {observation_count} unique shadow observations after "
            f"canonical deduplication. Keep paper/live/order disabled. Resolve blockers before any transition gate: "
            f"{blocker_text}. Review warnings: {warning_text}.",
            BLOCK_WITH_UNIQUE_OBSERVATIONS_RECOMMENDATION,
        )
    if decision == HYP005_SHADOW_QUALITY_AUDIT_REVIEW_REQUIRED:
        return (
            f"HYP-005 shadow quality audit is deduped and review-required/collection-only with {observation_count} "
            "unique shadow observations. Continue no-order shadow collection; do not train, reload, paper trade, "
            "live trade, or send orders. Review maturity-pending and slippage flags before any future transition gate.",
            "REVIEW_REQUIRED_COLLECTION_ONLY_RECOMMENDATION",
        )
    return (
        f"HYP-005 shadow quality audit is deduped and allows continued no-order collection only with {observation_count} "
        "unique shadow observations. Do not train, reload, paper trade, live trade, or send orders.",
        "CONTINUE_COLLECTION_ONLY_RECOMMENDATION",
    )

def build_hyp005_shadow_quality_audit_report(
    reports_dir: Path | str,
    *,
    include_all: bool = True,
    limits: Hyp005ShadowQualityLimits | None = None,
    review_ok: bool = False,
) -> dict[str, Any]:
    limits = limits or Hyp005ShadowQualityLimits()
    reports_dir = Path(reports_dir)
    observations, observation_source_paths, dedupe_stats = load_hyp005_shadow_observations_with_dedupe_stats(
        reports_dir, include_all=include_all
    )

    latest_25v_path = _latest_file(reports_dir, "4B436625V_hyp005_shadow_observation_logger_*.json")
    latest_25w_path = _latest_file(reports_dir, "4B436625W_hyp005_shadow_observation_acceptance_*.json")
    latest_25y_path = _latest_file(reports_dir, "4B436625Y_hyp005_shadow_operator_daily_audit_*.json")

    latest_25v: dict[str, Any] = {}
    latest_25w: dict[str, Any] = {}
    latest_25y: dict[str, Any] = {}
    for target, path in (("25v", latest_25v_path), ("25w", latest_25w_path), ("25y", latest_25y_path)):
        if path is None:
            continue
        try:
            payload = _read_json(path)
        except (OSError, json.JSONDecodeError):
            payload = {}
        if isinstance(payload, dict):
            if target == "25v":
                latest_25v = payload
            elif target == "25w":
                latest_25w = payload
            else:
                latest_25y = payload

    observation_count = len(observations)
    matured_returns = [_safe_float(obs.get(MATURITY_PENDING_FIELD)) for obs in observations]
    matured_values = [ret for ret in matured_returns if ret is not None]
    maturity_pending_count = observation_count - len(matured_values)
    maturity_pending_pct = round((maturity_pending_count / observation_count) * 100.0, 6) if observation_count else 0.0

    missing_by_observation: list[dict[str, Any]] = []
    true_missing_fields_count = 0
    for obs in observations:
        missing = _missing_required_fields(obs)
        if missing:
            missing_by_observation.append(
                {
                    "observation_id": obs.get("observation_id"),
                    "canonical_key": "|".join(_canonical_observation_key(obs)),
                    "symbol": obs.get("symbol"),
                    "timestamp_utc": obs.get("timestamp_utc"),
                    "missing_fields": missing,
                }
            )
            true_missing_fields_count += len(missing)
    total_required_field_slots = observation_count * len(HYP005_QUALITY_REQUIRED_FIELDS)
    true_missing_fields_pct = (
        round((true_missing_fields_count / total_required_field_slots) * 100.0, 6)
        if total_required_field_slots
        else 0.0
    )

    by_symbol: dict[str, list[dict[str, Any]]] = {}
    for obs in observations:
        symbol = str(obs.get("symbol") or "UNKNOWN")
        by_symbol.setdefault(symbol, []).append(obs)
    per_symbol_quality = [_symbol_quality_summary(symbol, rows, limits) for symbol, rows in sorted(by_symbol.items())]
    dominant_symbol_count = max((len(rows) for rows in by_symbol.values()), default=0)
    dominant_symbol = max(by_symbol.items(), key=lambda item: len(item[1]))[0] if by_symbol else None
    dominant_symbol_pct = round((dominant_symbol_count / observation_count) * 100.0, 6) if observation_count else 0.0

    slippage_values = [
        slip
        for obs in observations
        if (slip := _safe_float(obs.get("spread_slippage_proxy_bps"))) is not None
    ]
    high_slippage_observations = [
        {
            "observation_id": obs.get("observation_id"),
            "canonical_key": "|".join(_canonical_observation_key(obs)),
            "symbol": obs.get("symbol"),
            "timestamp_utc": obs.get("timestamp_utc"),
            "spread_slippage_proxy_bps": _safe_float(obs.get("spread_slippage_proxy_bps")),
        }
        for obs in observations
        if (_safe_float(obs.get("spread_slippage_proxy_bps")) or 0.0) > limits.max_slippage_proxy_bps
    ]

    reason_codes: list[str] = ["NO_TRAINING_PAPER_LIVE_APPROVALS_DETECTED", OBSERVATION_CANONICAL_DEDUPLICATION_APPLIED]
    warnings: list[str] = []
    blockers: list[str] = []

    latest_25v_decision = latest_25v.get("decision")
    latest_25v_reason_codes = latest_25v.get("reason_codes") if isinstance(latest_25v.get("reason_codes"), list) else []

    if dedupe_stats.get("duplicate_removed_count", 0) > 0:
        reason_codes.append(OBSERVATION_DUPLICATES_REMOVED)
        warnings.append("OBSERVATION_DUPLICATES_REMOVED_FROM_QUALITY_METRICS")

    if observation_count == 0:
        blockers.append("NO_HYP005_SHADOW_OBSERVATIONS_FOUND")
        reason_codes.append("NO_HYP005_SHADOW_OBSERVATIONS_FOUND")
    if observation_count < limits.early_audit_min_observations:
        warnings.append("QUALITY_AUDIT_SAMPLE_COUNT_LOW")
        reason_codes.append("QUALITY_AUDIT_SAMPLE_COUNT_LOW")
    if observation_count < limits.min_shadow_sample_target:
        warnings.append("SHADOW_SAMPLE_COUNT_BELOW_ACCEPTANCE_TARGET")
        reason_codes.append("SHADOW_SAMPLE_COUNT_BELOW_ACCEPTANCE_TARGET")

    if true_missing_fields_pct > limits.max_true_missing_fields_pct:
        blockers.append("TRUE_REQUIRED_FIELDS_MISSING_HIGH")
        reason_codes.append("TRUE_REQUIRED_FIELDS_MISSING_HIGH")
    elif maturity_pending_count > 0:
        reason_codes.append("MISSING_FINAL_RETURN_CLASSIFIED_AS_MATURITY_PENDING")
        warnings.append("MATURITY_PENDING_FORWARD_RETURNS_PRESENT")

    if maturity_pending_pct > limits.max_maturity_pending_pct_for_ready:
        warnings.append("MATURITY_PENDING_RATE_HIGH")
        reason_codes.append("MATURITY_PENDING_RATE_HIGH")

    if len(by_symbol) < limits.min_symbols_observed_for_10_symbol_set and observation_count > 0:
        warnings.append("SYMBOL_DIVERSITY_LOW")
        reason_codes.append("SYMBOL_DIVERSITY_LOW")
    if dominant_symbol_pct > limits.max_symbol_dominance_pct:
        warnings.append("SYMBOL_DOMINANCE_HIGH")
        reason_codes.append("SYMBOL_DOMINANCE_HIGH")

    high_slippage_count = len(high_slippage_observations)
    if high_slippage_count > 0:
        warnings.append("SHADOW_SLIPPAGE_PROXY_HIGH")
        reason_codes.append("SHADOW_SLIPPAGE_PROXY_HIGH")

    mean_edge = _mean(matured_values)
    median_edge = _median(matured_values)
    win_rate = _win_rate(matured_values)
    pf = _profit_factor(matured_values)
    if len(matured_values) < limits.min_matured_observations_for_edge_read:
        warnings.append("MATURED_EDGE_SAMPLE_COUNT_LOW")
        reason_codes.append("MATURED_EDGE_SAMPLE_COUNT_LOW")
    if mean_edge is not None and mean_edge < limits.min_mean_forward_edge_bps_watch:
        warnings.append("MATURED_MEAN_FORWARD_EDGE_NEGATIVE")
        reason_codes.append("MATURED_MEAN_FORWARD_EDGE_NEGATIVE")
    if pf is not None and pf < limits.min_profit_factor_watch:
        warnings.append("MATURED_PROFIT_FACTOR_LOW")
        reason_codes.append("MATURED_PROFIT_FACTOR_LOW")

    if (
        latest_25v_decision == "HYP005_SHADOW_OBSERVATION_LOGGER_BLOCK"
        and "SHADOW_MISSING_FIELDS_HIGH" in latest_25v_reason_codes
        and maturity_pending_count > 0
        and true_missing_fields_pct <= limits.max_true_missing_fields_pct
    ):
        reason_codes.append("LOGGER_BLOCK_EXPLAINED_BY_MATURITY_PENDING_FINAL_RETURNS")
        warnings.append("LOGGER_BLOCK_IS_MATURITY_AWARE_REVIEW_ITEM")

    decision = HYP005_SHADOW_QUALITY_AUDIT_CONTINUE_COLLECTION
    if blockers:
        decision = HYP005_SHADOW_QUALITY_AUDIT_BLOCK
    elif warnings:
        decision = HYP005_SHADOW_QUALITY_AUDIT_REVIEW_REQUIRED

    quality_summary = {
        "shadow_observation_count": observation_count,
        "shadow_sample_target": limits.min_shadow_sample_target,
        "progress_pct": round((observation_count / limits.min_shadow_sample_target) * 100.0, 6)
        if limits.min_shadow_sample_target
        else None,
        "matured_forward_return_count": len(matured_values),
        "maturity_pending_count": maturity_pending_count,
        "maturity_pending_pct": maturity_pending_pct,
        "true_missing_required_fields_count": true_missing_fields_count,
        "true_missing_required_fields_pct": true_missing_fields_pct,
        "symbols_observed": sorted(by_symbol.keys()),
        "symbols_observed_count": len(by_symbol),
        "dominant_symbol": dominant_symbol,
        "dominant_symbol_pct": dominant_symbol_pct,
        "mean_forward_edge_bps": mean_edge,
        "median_forward_edge_bps": median_edge,
        "win_rate_pct": win_rate,
        "profit_factor": pf,
        "mean_slippage_proxy_bps": _mean(slippage_values),
        "max_slippage_proxy_bps": max(slippage_values) if slippage_values else None,
        "high_slippage_count": high_slippage_count,
        "high_slippage_symbols": sorted({str(item.get("symbol")) for item in high_slippage_observations}),
    }

    latest_25y_count = _safe_float(latest_25y.get("shadow_observation_count"))
    if latest_25y_count is not None and abs(float(latest_25y_count) - float(observation_count)) > max(2.0, float(observation_count) * 0.25):
        warnings.append("QUALITY_COUNT_DIFFERS_FROM_LATEST_25Y")
        reason_codes.append("QUALITY_COUNT_DIFFERS_FROM_LATEST_25Y")

    recommendation, recommendation_type = _build_quality_audit_recommendation(
        decision=decision,
        observation_count=observation_count,
        blockers=sorted(dict.fromkeys(blockers)),
        warnings=sorted(dict.fromkeys(warnings)),
    )
    reason_codes.append(RECOMMENDATION_MESSAGE_CONSISTENCY_APPLIED)
    if recommendation_type == BLOCK_WITH_UNIQUE_OBSERVATIONS_RECOMMENDATION:
        reason_codes.append(BLOCK_WITH_UNIQUE_OBSERVATIONS_RECOMMENDATION)

    return {
        "ok": decision != HYP005_SHADOW_QUALITY_AUDIT_BLOCK,
        "contract_version": HYP005_SHADOW_QUALITY_CONTRACT_VERSION,
        "hotfix_version": HYP005_SHADOW_QUALITY_HOTFIX_VERSION,
        "phase": "25AB-H2",
        "report_type": "hyp005_shadow_observation_quality_slippage_risk_audit_deduped_message_consistent",
        "generated_at_utc": _utc_now_iso(),
        "decision": decision,
        "hypothesis_id": "HYP-005",
        "branch_name": "liquidity_sweep_reversal_vol_compression",
        "selected_strategy_family": "long_liquidity_sweep_reversal",
        "review_ok": bool(review_ok),
        "runtime_probe_only": True,
        "no_order_quality_audit_only": True,
        "approved_for_shadow_collection": decision != HYP005_SHADOW_QUALITY_AUDIT_BLOCK,
        "approved_for_training_candidate": False,
        "approved_for_research_candidate": False,
        "approved_for_paper_transition_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "live_real_allowed": False,
        "paper_trading_started": False,
        "order_actions_performed": False,
        "post_requests_allowed": False,
        "reload_performed": False,
        "training_performed": False,
        "config_mutation_performed": False,
        "limits": asdict(limits),
        "deduplication": dedupe_stats,
        "source_paths": {
            "latest_25v_json": str(latest_25v_path) if latest_25v_path else None,
            "latest_25w_json": str(latest_25w_path) if latest_25w_path else None,
            "latest_25y_json": str(latest_25y_path) if latest_25y_path else None,
            "observation_source_paths": observation_source_paths,
        },
        "latest_inputs": {
            "latest_25v_decision": latest_25v.get("decision"),
            "latest_25v_reason_codes": latest_25v_reason_codes,
            "latest_25w_decision": latest_25w.get("decision"),
            "latest_25y_decision": latest_25y.get("decision"),
            "latest_25y_logger_decision": latest_25y.get("latest_logger_decision"),
            "latest_25y_acceptance_decision": latest_25y.get("latest_acceptance_decision"),
            "latest_25y_shadow_observation_count": latest_25y.get("shadow_observation_count"),
        },
        "quality_summary": quality_summary,
        "per_symbol_quality": per_symbol_quality,
        "high_slippage_observations": high_slippage_observations,
        "missing_required_fields": missing_by_observation[:50],
        "maturity_pending_observations": [
            {
                "observation_id": obs.get("observation_id"),
                "canonical_key": "|".join(_canonical_observation_key(obs)),
                "symbol": obs.get("symbol"),
                "timestamp_utc": obs.get("timestamp_utc"),
                "reason": "FORWARD_RETURN_FINAL_PENDING",
            }
            for obs in observations
            if _safe_float(obs.get(MATURITY_PENDING_FIELD)) is None
        ][:100],
        "reason_codes": sorted(dict.fromkeys(reason_codes)),
        "warnings": sorted(dict.fromkeys(warnings)),
        "blockers": sorted(dict.fromkeys(blockers)),
        "recommendation_consistency": {
            "hotfix_applied": True,
            "recommendation_type": recommendation_type,
            "unique_observation_count_at_message_build": observation_count,
            "no_unique_observation_claim_allowed": observation_count <= 0,
        },
        "recommendation": recommendation,
    }


def write_hyp005_shadow_quality_audit_report(report: dict[str, Any], out_dir: Path | str) -> tuple[Path, Path]:
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    json_path = out_path / f"4B436625AB_H2_hyp005_shadow_quality_slippage_audit_{stamp}.json"
    md_path = out_path / f"4B436625AB_H2_hyp005_shadow_quality_slippage_audit_{stamp}.md"
    json_text = json.dumps(report, indent=2, sort_keys=True)
    md_text = render_hyp005_shadow_quality_audit_markdown(report)
    json_path.write_text(json_text, encoding="utf-8")
    md_path.write_text(md_text, encoding="utf-8")

    # Backward-compatible copies keep prior 25AB-H1 and original 25AB globs usable for older tests and operator scripts.
    h1_json_path = out_path / f"4B436625AB_H1_hyp005_shadow_quality_slippage_audit_{stamp}.json"
    h1_md_path = out_path / f"4B436625AB_H1_hyp005_shadow_quality_slippage_audit_{stamp}.md"
    h1_json_path.write_text(json_text, encoding="utf-8")
    h1_md_path.write_text(md_text, encoding="utf-8")

    legacy_json_path = out_path / f"4B436625AB_hyp005_shadow_quality_slippage_audit_{stamp}.json"
    legacy_md_path = out_path / f"4B436625AB_hyp005_shadow_quality_slippage_audit_{stamp}.md"
    legacy_json_path.write_text(json_text, encoding="utf-8")
    legacy_md_path.write_text(md_text, encoding="utf-8")
    return json_path, md_path


def render_hyp005_shadow_quality_audit_markdown(report: dict[str, Any]) -> str:
    qs = report.get("quality_summary", {}) if isinstance(report.get("quality_summary"), dict) else {}
    dd = report.get("deduplication", {}) if isinstance(report.get("deduplication"), dict) else {}
    lines = [
        "# HYP-005 Shadow Observation Quality / Slippage Risk Audit Deduplication + Recommendation Message Consistency Hotfix",
        "",
        f"- contract_version: `{report.get('contract_version')}`",
        f"- hotfix_version: `{report.get('hotfix_version')}`",
        f"- decision: `{report.get('decision')}`",
        f"- generated_at_utc: `{report.get('generated_at_utc')}`",
        f"- raw_observation_count: `{dd.get('raw_observation_count')}`",
        f"- unique_observation_count: `{dd.get('unique_observation_count')}`",
        f"- duplicate_removed_count: `{dd.get('duplicate_removed_count')}`",
        f"- shadow_observation_count: `{qs.get('shadow_observation_count')}`",
        f"- shadow_sample_target: `{qs.get('shadow_sample_target')}`",
        f"- progress_pct: `{qs.get('progress_pct')}`",
        f"- matured_forward_return_count: `{qs.get('matured_forward_return_count')}`",
        f"- maturity_pending_count: `{qs.get('maturity_pending_count')}`",
        f"- true_missing_required_fields_pct: `{qs.get('true_missing_required_fields_pct')}`",
        f"- mean_forward_edge_bps: `{qs.get('mean_forward_edge_bps')}`",
        f"- median_forward_edge_bps: `{qs.get('median_forward_edge_bps')}`",
        f"- profit_factor: `{qs.get('profit_factor')}`",
        f"- win_rate_pct: `{qs.get('win_rate_pct')}`",
        f"- max_slippage_proxy_bps: `{qs.get('max_slippage_proxy_bps')}`",
        f"- high_slippage_count: `{qs.get('high_slippage_count')}`",
        "",
        "## Guardrail Decision",
        "",
        "No training, reload, paper trading, live trading, POST requests, or order actions are approved by this audit.",
        "",
        "## Reason Codes",
        "",
    ]
    for code in report.get("reason_codes", []):
        lines.append(f"- `{code}`")
    lines.extend(["", "## Warnings", ""])
    for warning in report.get("warnings", []):
        lines.append(f"- `{warning}`")
    lines.extend(["", "## Per-Symbol Quality", ""])
    for row in report.get("per_symbol_quality", []):
        if not isinstance(row, dict):
            continue
        lines.append(
            "- "
            f"{row.get('symbol')}: count={row.get('observation_count')}, matured={row.get('matured_observation_count')}, "
            f"pending={row.get('maturity_pending_count')}, mean_edge={row.get('mean_forward_edge_bps')}, "
            f"pf={row.get('profit_factor')}, max_slip={row.get('max_slippage_proxy_bps')}, flags={','.join(row.get('flags', []))}"
        )
    lines.extend(["", "## Recommendation", "", str(report.get("recommendation") or "")])
    return "\n".join(lines) + "\n"
