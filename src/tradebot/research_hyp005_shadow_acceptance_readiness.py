from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any, Iterable, Mapping, Sequence
import json
import math

HYP005_SHADOW_ACCEPTANCE_CONTRACT_VERSION = "4B.4.3.6.6.25W"
HYPOTHESIS_ID = "HYP-005"
BRANCH_NAME = "liquidity_sweep_reversal_vol_compression"
STRATEGY_FAMILY = "long_liquidity_sweep_reversal"
REPORT_PREFIX = "4B436625W_hyp005_shadow_observation_acceptance"
SUMMARY_PREFIX = "4B436625W_hyp005_shadow_acceptance_summary"


@dataclass(frozen=True)
class Hyp005ShadowAcceptanceLimits:
    min_shadow_sample_count: int = 30
    min_shadow_days_observed: int = 30
    min_shadow_signal_capture_count: int = 25
    min_shadow_mean_forward_edge_bps: float = 50.0
    min_shadow_median_forward_edge_bps: float = 30.0
    min_shadow_profit_factor: float = 1.50
    min_shadow_oos_edge_bps: float = 25.0
    min_shadow_walk_forward_positive_rate_pct: float = 60.0
    max_shadow_top_win_dependency_pct: float = 45.0
    max_shadow_dominant_symbol_pct: float = 70.0
    max_shadow_wick_dependency_pct: float = 85.0
    max_shadow_slippage_proxy_bps: float = 12.0
    min_shadow_data_quality_pct: float = 98.0
    max_shadow_missing_fields_pct: float = 1.0
    min_manual_reviewers: int = 1
    walk_forward_segments: int = 4


@dataclass(frozen=True)
class ShadowAcceptanceSummary:
    shadow_observation_count: int
    shadow_days_observed: int
    shadow_signal_capture_count: int
    shadow_mean_forward_edge_bps: float | None
    shadow_median_forward_edge_bps: float | None
    shadow_profit_factor: float
    shadow_oos_edge_bps: float | None
    shadow_walk_forward_positive_rate_pct: float
    shadow_top_win_dependency_pct: float
    shadow_dominant_symbol_pct: float
    shadow_wick_dependency_pct: float
    shadow_slippage_proxy_bps: float
    shadow_data_quality_pct: float
    shadow_missing_fields_pct: float
    symbol_counts: dict[str, int]
    positive_count: int
    negative_count: int


REQUIRED_OBSERVATION_FIELDS = (
    "timestamp_utc",
    "symbol",
    "timeframe",
    "strategy_family",
    "sweep_direction",
    "lookback_low",
    "swept_low",
    "sweep_depth_bps",
    "wick_pct",
    "compression_ratio",
    "entry_reference_price",
    "invalidation_level",
    "forward_return_bps_final",
    "mae_bps",
    "mfe_bps",
    "spread_slippage_proxy_bps",
    "data_quality_ok",
    "operator_review_status",
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_json(path: str | Path | None) -> Any:
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


def load_jsonl(path: str | Path | None) -> list[Any]:
    if path is None:
        return []
    p = Path(path)
    if not p.exists():
        return []
    rows: list[Any] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


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


def safe_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "y", "ok"}:
        return True
    if text in {"false", "0", "no", "n"}:
        return False
    return default


def normalize_observation(row: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(row)
    result.setdefault("hypothesis_id", HYPOTHESIS_ID)
    result.setdefault("branch_name", BRANCH_NAME)
    result.setdefault("strategy_family", STRATEGY_FAMILY)
    result.setdefault("no_order_shadow_only", True)
    result.setdefault("order_action", "NONE")
    result.setdefault("operator_review_status", "PENDING")
    return result


def extract_observations_from_payload(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [normalize_observation(item) for item in payload if isinstance(item, Mapping)]
    if not isinstance(payload, Mapping):
        return []
    observations = payload.get("shadow_observations")
    if isinstance(observations, list):
        return [normalize_observation(item) for item in observations if isinstance(item, Mapping)]
    ledger = payload.get("observations")
    if isinstance(ledger, list):
        return [normalize_observation(item) for item in ledger if isinstance(item, Mapping)]
    return []


def load_observations_from_paths(paths: Iterable[str | Path]) -> tuple[list[dict[str, Any]], list[str]]:
    observations: list[dict[str, Any]] = []
    source_paths: list[str] = []
    for raw_path in paths:
        path = Path(raw_path)
        if not path.exists():
            continue
        source_paths.append(str(path))
        if path.suffix.lower() == ".jsonl":
            observations.extend(normalize_observation(item) for item in load_jsonl(path) if isinstance(item, Mapping))
            continue
        payload = load_json(path)
        observations.extend(extract_observations_from_payload(payload))
        if isinstance(payload, Mapping):
            # Accept direct 25V logger reports that point to external ledger files.
            parent = path.parent
            for key in ("ledger_json", "ledger_jsonl"):
                ledger_path = payload.get(key)
                if isinstance(ledger_path, str) and ledger_path:
                    lp = Path(ledger_path)
                    if not lp.is_absolute() and not lp.exists():
                        lp = parent / ledger_path
                    if lp.exists() and str(lp) not in source_paths:
                        source_paths.append(str(lp))
                        if lp.suffix.lower() == ".jsonl":
                            observations.extend(normalize_observation(item) for item in load_jsonl(lp) if isinstance(item, Mapping))
                        else:
                            observations.extend(extract_observations_from_payload(load_json(lp)))
    return observations, source_paths


def _final_return_bps(row: Mapping[str, Any]) -> float | None:
    for key in ("forward_return_bps_final", "forward_return_bps_h3", "forward_return_bps_h2", "forward_return_bps_h1"):
        if key in row and row.get(key) not in (None, ""):
            return safe_float(row.get(key), 0.0)
    return None


def _timestamp_date(text: Any) -> str | None:
    if text is None:
        return None
    raw = str(text).strip()
    if not raw:
        return None
    # ISO strings from the project are enough; keep parsing deliberately forgiving.
    if "T" in raw:
        return raw.split("T", 1)[0]
    if " " in raw:
        return raw.split(" ", 1)[0]
    return raw[:10] if len(raw) >= 10 else None


def _profit_factor(edges: Sequence[float]) -> float:
    gains = sum(value for value in edges if value > 0)
    losses = abs(sum(value for value in edges if value < 0))
    if gains <= 0:
        return 0.0
    if losses <= 0:
        return 999.0
    return gains / losses


def _walk_forward_positive_rate(edges: Sequence[float], segments: int) -> float:
    if not edges:
        return 0.0
    n = max(1, min(segments, len(edges)))
    positives = 0
    for index in range(n):
        start = round(index * len(edges) / n)
        end = round((index + 1) * len(edges) / n)
        chunk = list(edges[start:end])
        if chunk and sum(chunk) / len(chunk) > 0:
            positives += 1
    return round((positives / n) * 100.0, 6)


def _top_win_dependency_pct(edges: Sequence[float]) -> float:
    positives = [value for value in edges if value > 0]
    total = sum(positives)
    if total <= 0:
        return 100.0
    return round((max(positives) / total) * 100.0, 6)


def _dominant_symbol_pct(rows: Sequence[Mapping[str, Any]]) -> tuple[float, dict[str, int]]:
    counts: dict[str, int] = {}
    for row in rows:
        symbol = str(row.get("symbol") or "UNKNOWN").upper()
        counts[symbol] = counts.get(symbol, 0) + 1
    if not counts:
        return 0.0, counts
    return round((max(counts.values()) / sum(counts.values())) * 100.0, 6), counts


def _missing_fields_pct(rows: Sequence[Mapping[str, Any]]) -> float:
    if not rows:
        return 100.0
    total = len(rows) * len(REQUIRED_OBSERVATION_FIELDS)
    missing = 0
    for row in rows:
        for field in REQUIRED_OBSERVATION_FIELDS:
            if row.get(field) in (None, ""):
                missing += 1
    return round((missing / total) * 100.0, 6)


def summarize_shadow_observations(
    observations: Sequence[Mapping[str, Any]],
    limits: Hyp005ShadowAcceptanceLimits | None = None,
) -> ShadowAcceptanceSummary:
    limits = limits or Hyp005ShadowAcceptanceLimits()
    rows = [normalize_observation(row) for row in observations]
    edges = [value for row in rows if (value := _final_return_bps(row)) is not None]
    dates = sorted({date for row in rows if (date := _timestamp_date(row.get("timestamp_utc")))})
    positive_count = sum(1 for value in edges if value > 0)
    negative_count = sum(1 for value in edges if value < 0)
    dominant_symbol_pct, symbol_counts = _dominant_symbol_pct(rows)
    oos_edges = edges[int(len(edges) * 0.70):] if edges else []
    data_quality_ok = sum(1 for row in rows if safe_bool(row.get("data_quality_ok"), True))
    wick_values = [safe_float(row.get("wick_pct"), 0.0) for row in rows]
    slippage_values = [safe_float(row.get("spread_slippage_proxy_bps"), 0.0) for row in rows]
    return ShadowAcceptanceSummary(
        shadow_observation_count=len(rows),
        shadow_days_observed=len(dates),
        shadow_signal_capture_count=len(edges),
        shadow_mean_forward_edge_bps=round(sum(edges) / len(edges), 6) if edges else None,
        shadow_median_forward_edge_bps=round(float(median(edges)), 6) if edges else None,
        shadow_profit_factor=round(_profit_factor(edges), 6),
        shadow_oos_edge_bps=round(sum(oos_edges) / len(oos_edges), 6) if oos_edges else None,
        shadow_walk_forward_positive_rate_pct=_walk_forward_positive_rate(edges, limits.walk_forward_segments),
        shadow_top_win_dependency_pct=_top_win_dependency_pct(edges),
        shadow_dominant_symbol_pct=dominant_symbol_pct,
        shadow_wick_dependency_pct=round(sum(wick_values) / len(wick_values), 6) if wick_values else 0.0,
        shadow_slippage_proxy_bps=round(sum(slippage_values) / len(slippage_values), 6) if slippage_values else 0.0,
        shadow_data_quality_pct=round((data_quality_ok / len(rows)) * 100.0, 6) if rows else 0.0,
        shadow_missing_fields_pct=_missing_fields_pct(rows),
        symbol_counts=symbol_counts,
        positive_count=positive_count,
        negative_count=negative_count,
    )


def evaluate_shadow_acceptance(
    summary: ShadowAcceptanceSummary,
    limits: Hyp005ShadowAcceptanceLimits | None = None,
    *,
    manual_reviewers: int = 1,
) -> tuple[bool, list[str], list[str]]:
    limits = limits or Hyp005ShadowAcceptanceLimits()
    reasons: list[str] = []
    warnings: list[str] = []
    if summary.shadow_observation_count < limits.min_shadow_sample_count:
        reasons.append("SHADOW_SAMPLE_COUNT_LOW")
        warnings.append("SHADOW_SAMPLE_COUNT_BELOW_ACCEPTANCE_TARGET")
    if summary.shadow_days_observed < limits.min_shadow_days_observed:
        reasons.append("SHADOW_DAYS_OBSERVED_LOW")
    if summary.shadow_signal_capture_count < limits.min_shadow_signal_capture_count:
        reasons.append("SHADOW_SIGNAL_CAPTURE_COUNT_LOW")
    if summary.shadow_mean_forward_edge_bps is None or summary.shadow_mean_forward_edge_bps < limits.min_shadow_mean_forward_edge_bps:
        reasons.append("SHADOW_MEAN_FORWARD_EDGE_LOW")
    if summary.shadow_median_forward_edge_bps is None or summary.shadow_median_forward_edge_bps < limits.min_shadow_median_forward_edge_bps:
        reasons.append("SHADOW_MEDIAN_FORWARD_EDGE_LOW")
    if summary.shadow_profit_factor < limits.min_shadow_profit_factor:
        reasons.append("SHADOW_PROFIT_FACTOR_LOW")
    if summary.shadow_oos_edge_bps is None or summary.shadow_oos_edge_bps < limits.min_shadow_oos_edge_bps:
        reasons.append("SHADOW_OOS_EDGE_LOW")
    if summary.shadow_walk_forward_positive_rate_pct < limits.min_shadow_walk_forward_positive_rate_pct:
        reasons.append("SHADOW_WALK_FORWARD_STABILITY_LOW")
    if summary.shadow_top_win_dependency_pct > limits.max_shadow_top_win_dependency_pct:
        reasons.append("SHADOW_TOP_WIN_DEPENDENCY_HIGH")
    if summary.shadow_dominant_symbol_pct > limits.max_shadow_dominant_symbol_pct:
        reasons.append("SHADOW_DOMINANT_SYMBOL_DEPENDENCY_HIGH")
    if summary.shadow_wick_dependency_pct > limits.max_shadow_wick_dependency_pct:
        reasons.append("SHADOW_WICK_DEPENDENCY_HIGH")
    if summary.shadow_slippage_proxy_bps > limits.max_shadow_slippage_proxy_bps:
        reasons.append("SHADOW_SLIPPAGE_PROXY_HIGH")
    if summary.shadow_data_quality_pct < limits.min_shadow_data_quality_pct:
        reasons.append("SHADOW_DATA_QUALITY_LOW")
    if summary.shadow_missing_fields_pct > limits.max_shadow_missing_fields_pct:
        reasons.append("SHADOW_MISSING_FIELDS_HIGH")
    if manual_reviewers < limits.min_manual_reviewers:
        reasons.append("SHADOW_MANUAL_REVIEW_MISSING")
    return not reasons, sorted(set(reasons)), sorted(set(warnings))


def build_hyp005_shadow_acceptance_report(
    *,
    observations: Sequence[Mapping[str, Any]],
    source_ledgers: Sequence[str] | None = None,
    limits: Hyp005ShadowAcceptanceLimits | None = None,
    manual_reviewers: int = 1,
) -> dict[str, Any]:
    limits = limits or Hyp005ShadowAcceptanceLimits()
    normalized = [normalize_observation(row) for row in observations]
    summary = summarize_shadow_observations(normalized, limits=limits)
    approved, reasons, warnings = evaluate_shadow_acceptance(summary, limits=limits, manual_reviewers=manual_reviewers)
    decision = "HYP005_SHADOW_PAPER_TRANSITION_READY" if approved else "HYP005_SHADOW_PAPER_TRANSITION_BLOCK"
    reason_codes = list(reasons)
    if approved:
        reason_codes.extend([
            "HYP005_SHADOW_LEDGER_ACCEPTANCE_CONFIRMED",
            "PAPER_TRANSITION_READY_REQUIRES_SEPARATE_ENABLEMENT",
            "NO_TRAINING_PAPER_LIVE_APPROVALS_DETECTED",
        ])
    else:
        reason_codes.append("HYP005_SHADOW_LEDGER_ACCEPTANCE_NOT_MET")
    return {
        "contract_version": HYP005_SHADOW_ACCEPTANCE_CONTRACT_VERSION,
        "phase": "25W",
        "report_type": "hyp005_shadow_observation_acceptance_paper_transition_readiness_gate",
        "generated_at": utc_now_iso(),
        "hypothesis_id": HYPOTHESIS_ID,
        "branch_name": BRANCH_NAME,
        "selected_strategy_family": STRATEGY_FAMILY,
        "decision": decision,
        "ok": approved,
        "paper_transition_ready": approved,
        "paper_transition_readiness_only": True,
        "shadow_acceptance_summary": asdict(summary),
        "source_ledgers": list(source_ledgers or []),
        "shadow_observations_preview": normalized[:5],
        "reason_codes": sorted(set(reason_codes)),
        "warnings": sorted(set(warnings)),
        "recommendation": (
            "HYP-005 shadow observations met the paper-transition readiness gate. Do not start paper trading here; require a separate paper enablement gate and manual review."
            if approved
            else "HYP-005 shadow observations did not meet paper-transition readiness. Keep collecting no-order shadow observations; do not train, reload, paper trade, or enable live trading."
        ),
        "limits": asdict(limits),
        "guardrails": {
            "observation_only": True,
            "paper_transition_readiness_only": True,
            "no_order_shadow_only": True,
            "orders_allowed": False,
            "paper_trading_allowed": False,
            "live_trading_allowed": False,
            "training_allowed": False,
            "model_reload_allowed": False,
            "config_mutation_allowed": False,
            "post_requests_allowed": False,
            "order_actions_performed": False,
            "paper_trading_started": False,
            "live_trading_started": False,
            "reload_performed": False,
            "config_mutation_performed": False,
            "paper_transition_requires_new_gate": True,
            "live_transition_requires_separate_gate": True,
            "manual_review_required": True,
        },
        "approved_for_research_candidate": approved,
        "approved_for_shadow_candidate": True,
        "approved_for_paper_transition_candidate": approved,
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
    summary = report.get("shadow_acceptance_summary") if isinstance(report.get("shadow_acceptance_summary"), Mapping) else {}
    guardrails = report.get("guardrails") if isinstance(report.get("guardrails"), Mapping) else {}
    lines = [
        "# 4B.4.3.6.6.25W HYP-005 Shadow Observation Acceptance / Paper-Transition Readiness Gate",
        "",
        f"- contract_version: `{report.get('contract_version')}`",
        f"- decision: **{report.get('decision')}**",
        f"- hypothesis_id: `{report.get('hypothesis_id')}`",
        f"- branch_name: `{report.get('branch_name')}`",
        f"- selected_strategy_family: `{report.get('selected_strategy_family')}`",
        f"- paper_transition_ready: `{report.get('paper_transition_ready')}`",
        f"- approved_for_paper_transition_candidate: `{report.get('approved_for_paper_transition_candidate')}`",
        f"- approved_for_paper_candidate: `{report.get('approved_for_paper_candidate')}`",
        f"- approved_for_live_real: `{report.get('approved_for_live_real')}`",
        f"- reason_codes: `{report.get('reason_codes')}`",
        f"- warnings: `{report.get('warnings')}`",
        f"- recommendation: {report.get('recommendation')}",
        "",
        "## Shadow Acceptance Summary",
        "",
        f"- shadow_observation_count: `{summary.get('shadow_observation_count')}`",
        f"- shadow_days_observed: `{summary.get('shadow_days_observed')}`",
        f"- shadow_signal_capture_count: `{summary.get('shadow_signal_capture_count')}`",
        f"- shadow_mean_forward_edge_bps: `{summary.get('shadow_mean_forward_edge_bps')}`",
        f"- shadow_median_forward_edge_bps: `{summary.get('shadow_median_forward_edge_bps')}`",
        f"- shadow_profit_factor: `{summary.get('shadow_profit_factor')}`",
        f"- shadow_oos_edge_bps: `{summary.get('shadow_oos_edge_bps')}`",
        f"- shadow_walk_forward_positive_rate_pct: `{summary.get('shadow_walk_forward_positive_rate_pct')}`",
        f"- shadow_top_win_dependency_pct: `{summary.get('shadow_top_win_dependency_pct')}`",
        f"- shadow_dominant_symbol_pct: `{summary.get('shadow_dominant_symbol_pct')}`",
        f"- shadow_wick_dependency_pct: `{summary.get('shadow_wick_dependency_pct')}`",
        f"- shadow_slippage_proxy_bps: `{summary.get('shadow_slippage_proxy_bps')}`",
        f"- shadow_data_quality_pct: `{summary.get('shadow_data_quality_pct')}`",
        f"- shadow_missing_fields_pct: `{summary.get('shadow_missing_fields_pct')}`",
        "",
        "## Guardrails",
        "",
        f"- no_order_shadow_only: `{guardrails.get('no_order_shadow_only')}`",
        f"- paper_transition_readiness_only: `{guardrails.get('paper_transition_readiness_only')}`",
        f"- orders_allowed: `{guardrails.get('orders_allowed')}`",
        f"- paper_trading_allowed: `{guardrails.get('paper_trading_allowed')}`",
        f"- live_trading_allowed: `{guardrails.get('live_trading_allowed')}`",
        f"- post_requests_allowed: `{guardrails.get('post_requests_allowed')}`",
        "- Paper-transition readiness is not paper-trading permission.",
        "- Paper trading remains blocked until a separate gate explicitly enables it.",
        "- Live trading remains blocked.",
    ]
    return "\n".join(lines) + "\n"
