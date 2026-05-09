from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence
import json

from tradebot.research_hyp005_liquidity_sweep_reversal_exploration import (
    BRANCH_NAME,
    HYPOTHESIS_ID,
    safe_float,
    safe_int,
    write_json,
)

HYP005_SHADOW_PLANNING_CONTRACT_VERSION = "4B.4.3.6.6.25U"
REPORT_PREFIX = "4B436625U_hyp005_no_order_shadow_planning"
SPEC_PREFIX = "4B436625U_hyp005_no_order_shadow_candidate_spec"


@dataclass(frozen=True)
class ShadowAcceptanceMetric:
    name: str
    operator: str
    threshold: float | int | str
    required: bool = True
    description: str = ""


@dataclass(frozen=True)
class Hyp005ShadowPlanningLimits:
    shadow_min_samples: int = 30
    shadow_min_days: int = 30
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


@dataclass(frozen=True)
class Hyp005NoOrderShadowCandidateSpec:
    contract_version: str
    hypothesis_id: str
    branch_name: str
    strategy_family: str
    status: str
    source_25s_decision: str
    source_25t_decision: str
    entry_signal_definition: dict[str, Any]
    invalidation_conditions: dict[str, Any]
    expected_hold_horizon: dict[str, Any]
    risk_observation_fields: list[str]
    required_shadow_acceptance_metrics: list[ShadowAcceptanceMetric]
    observed_robustness_metrics: dict[str, Any]
    required_source_reports: list[str]
    guardrails: dict[str, Any]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_json(path: str | Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    p = Path(path)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def _is_mapping(value: Any) -> bool:
    return isinstance(value, Mapping)


def _selected(report: Mapping[str, Any] | None) -> Mapping[str, Any]:
    if not isinstance(report, Mapping):
        return {}
    value = report.get("selected_candidate")
    return value if isinstance(value, Mapping) else {}


def _selected_metrics(report: Mapping[str, Any] | None) -> Mapping[str, Any]:
    selected = _selected(report)
    metrics = selected.get("metrics")
    return metrics if isinstance(metrics, Mapping) else {}


def _selected_spec(report: Mapping[str, Any] | None) -> Mapping[str, Any]:
    selected = _selected(report)
    spec = selected.get("spec")
    return spec if isinstance(spec, Mapping) else {}


def validate_hyp005_source_reports(
    exploration_report: Mapping[str, Any] | None,
    robustness_report: Mapping[str, Any] | None,
) -> tuple[bool, list[str], list[str]]:
    reasons: list[str] = []
    warnings: list[str] = []
    if not isinstance(exploration_report, Mapping):
        reasons.append("HYP005_EXPLORATION_REPORT_MISSING")
    elif exploration_report.get("hypothesis_id") != HYPOTHESIS_ID:
        reasons.append("HYP005_EXPLORATION_HYPOTHESIS_MISMATCH")
    elif exploration_report.get("decision") != "HYP005_EXPLORATION_PASS":
        reasons.append("HYP005_EXPLORATION_NOT_PASS")

    if not isinstance(robustness_report, Mapping):
        reasons.append("HYP005_ROBUSTNESS_REPORT_MISSING")
    elif robustness_report.get("hypothesis_id") != HYPOTHESIS_ID:
        reasons.append("HYP005_ROBUSTNESS_HYPOTHESIS_MISMATCH")
    elif robustness_report.get("decision") != "HYP005_ROBUSTNESS_PASS":
        reasons.append("HYP005_ROBUSTNESS_NOT_PASS")

    for label, report in (("25S", exploration_report), ("25T", robustness_report)):
        if not isinstance(report, Mapping):
            continue
        if bool(report.get("approved_for_training_candidate")):
            reasons.append(f"{label}_TRAINING_APPROVAL_GUARDRAIL_VIOLATION")
        if bool(report.get("approved_for_paper_candidate")):
            reasons.append(f"{label}_PAPER_APPROVAL_GUARDRAIL_VIOLATION")
        if bool(report.get("approved_for_live_real")) or bool(report.get("live_real_allowed")):
            reasons.append(f"{label}_LIVE_APPROVAL_GUARDRAIL_VIOLATION")
        if bool(report.get("order_actions_performed")) or bool(report.get("reload_performed")) or bool(report.get("config_mutation_performed")):
            reasons.append(f"{label}_SIDE_EFFECT_GUARDRAIL_VIOLATION")

    s_selected = _selected(exploration_report)
    t_selected = _selected(robustness_report)
    if isinstance(exploration_report, Mapping) and not s_selected:
        reasons.append("HYP005_25S_SELECTED_CANDIDATE_MISSING")
    if isinstance(robustness_report, Mapping) and not t_selected:
        reasons.append("HYP005_25T_SELECTED_CANDIDATE_MISSING")

    s_family = str(s_selected.get("strategy_family") or "")
    t_family = str(t_selected.get("strategy_family") or "")
    if s_family and t_family and s_family != t_family:
        reasons.append("HYP005_SELECTED_STRATEGY_MISMATCH")
    if t_family != "long_liquidity_sweep_reversal" and t_family:
        warnings.append("HYP005_SELECTED_STRATEGY_NOT_EXPECTED_LONG_SWEEP")
    if "ROBUST_SMALL_SAMPLE_PENALTY_APPLIED" in list(robustness_report.get("warnings") or []) if isinstance(robustness_report, Mapping) else False:
        warnings.append("SHADOW_SMALL_SAMPLE_CAUTION_REQUIRED")
    return not reasons, sorted(set(reasons)), sorted(set(warnings))


def build_entry_signal_definition(spec: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "strategy_family": "long_liquidity_sweep_reversal",
        "side": "LONG_ONLY",
        "timeframe": "4h",
        "setup": "Prior support/liquidity low is swept intrabar; candle reclaims above the swept level and closes with reversal structure after volatility compression filter remains acceptable.",
        "required_market_structure": [
            "lookback_low_reference_present",
            "downside_sweep_beyond_lookback_low",
            "close_reclaim_above_swept_low",
            "lower_wick_reversal_structure",
            "volatility_compression_filter_not_breached",
        ],
        "parameters": {
            "lookback_bars": safe_int(spec.get("lookback_bars"), 24),
            "hold_bars": safe_int(spec.get("hold_bars"), 6),
            "min_sweep_bps": safe_float(spec.get("min_sweep_bps"), 18.0),
            "min_wick_pct": safe_float(spec.get("min_wick_pct"), 42.0),
            "compression_window": safe_int(spec.get("compression_window"), 12),
            "compression_baseline_bars": safe_int(spec.get("compression_baseline_bars"), 48),
            "max_compression_ratio": safe_float(spec.get("max_compression_ratio"), 1.05),
        },
        "execution_mode": "NO_ORDER_SHADOW_ONLY",
    }


def build_invalidation_conditions(spec: Mapping[str, Any]) -> dict[str, Any]:
    hold_bars = safe_int(spec.get("hold_bars"), 6)
    return {
        "no_order_invalidation_only": True,
        "conditions": [
            "signal candle closes below swept liquidity low without reclaim",
            "forward path violates swept low by more than configured adverse excursion threshold",
            "spread/slippage proxy exceeds shadow max threshold",
            "data quality or required observation fields are missing",
            "market enters unsupported halt/outage/stale-data condition",
        ],
        "time_stop_bars": hold_bars,
        "mae_mfe_required": True,
        "manual_review_required": True,
    }


def build_expected_hold_horizon(spec: Mapping[str, Any]) -> dict[str, Any]:
    hold_bars = safe_int(spec.get("hold_bars"), 6)
    return {
        "timeframe": "4h",
        "hold_bars": hold_bars,
        "approx_hours": hold_bars * 4,
        "shadow_forward_return_bars": [1, 2, 3, hold_bars],
        "no_position_opened": True,
    }


def default_risk_observation_fields() -> list[str]:
    return [
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
        "hold_horizon_bars",
        "forward_return_bps_h1",
        "forward_return_bps_h2",
        "forward_return_bps_h3",
        "forward_return_bps_final",
        "mae_bps",
        "mfe_bps",
        "spread_slippage_proxy_bps",
        "volume_context",
        "regime_context",
        "data_quality_ok",
        "operator_review_status",
    ]


def required_shadow_acceptance_metrics(limits: Hyp005ShadowPlanningLimits) -> list[ShadowAcceptanceMetric]:
    return [
        ShadowAcceptanceMetric("shadow_sample_count", ">=", limits.shadow_min_samples, True, "Minimum no-order shadow observations before any paper-transition gate."),
        ShadowAcceptanceMetric("shadow_days_observed", ">=", limits.shadow_min_days, True, "Minimum calendar coverage for shadow monitoring."),
        ShadowAcceptanceMetric("shadow_signal_capture_count", ">=", limits.min_shadow_signal_capture_count, True, "Captured and reviewed candidate signals."),
        ShadowAcceptanceMetric("shadow_mean_forward_edge_bps", ">=", limits.min_shadow_mean_forward_edge_bps, True, "Mean forward edge after estimated costs/slippage."),
        ShadowAcceptanceMetric("shadow_median_forward_edge_bps", ">=", limits.min_shadow_median_forward_edge_bps, True, "Median forward edge after estimated costs/slippage."),
        ShadowAcceptanceMetric("shadow_profit_factor", ">=", limits.min_shadow_profit_factor, True, "Gross win/loss quality in no-order shadow data."),
        ShadowAcceptanceMetric("shadow_oos_edge_bps", ">=", limits.min_shadow_oos_edge_bps, True, "Most recent/out-of-sample shadow edge."),
        ShadowAcceptanceMetric("shadow_walk_forward_positive_rate_pct", ">=", limits.min_shadow_walk_forward_positive_rate_pct, True, "Segment stability requirement."),
        ShadowAcceptanceMetric("shadow_top_win_dependency_pct", "<=", limits.max_shadow_top_win_dependency_pct, True, "Avoids a result driven by a tiny number of wins."),
        ShadowAcceptanceMetric("shadow_dominant_symbol_pct", "<=", limits.max_shadow_dominant_symbol_pct, True, "Avoids one-symbol dependency."),
        ShadowAcceptanceMetric("shadow_wick_dependency_pct", "<=", limits.max_shadow_wick_dependency_pct, True, "Avoids extreme wick-only artifact dependency."),
        ShadowAcceptanceMetric("shadow_slippage_proxy_bps", "<=", limits.max_shadow_slippage_proxy_bps, True, "Ensures edge survives a realistic spread/slippage proxy."),
        ShadowAcceptanceMetric("shadow_data_quality_pct", ">=", limits.min_shadow_data_quality_pct, True, "Required field completeness and freshness."),
        ShadowAcceptanceMetric("shadow_missing_fields_pct", "<=", limits.max_shadow_missing_fields_pct, True, "Missing observation-field ceiling."),
        ShadowAcceptanceMetric("manual_reviewers", ">=", limits.min_manual_reviewers, True, "Manual review remains mandatory before any further gate."),
    ]


def _metrics_copy(metrics: Mapping[str, Any]) -> dict[str, Any]:
    keys = [
        "signal_count",
        "mean_net_edge_bps",
        "penalized_mean_net_edge_bps",
        "median_net_edge_bps",
        "profit_factor",
        "win_rate_pct",
        "oos_mean_net_edge_bps",
        "walk_forward_positive_rate_pct",
        "top_win_dependency_pct",
        "dominant_symbol_pct",
        "wick_dependency_pct",
        "symbols_traded",
        "recent_30d_signal_count",
        "recent_30d_mean_edge_bps",
        "recent_60d_mean_edge_bps",
        "small_sample_penalty_bps",
    ]
    return {key: metrics.get(key) for key in keys if key in metrics}


def _source_path(report: Mapping[str, Any] | None, fallback: str) -> str:
    if not isinstance(report, Mapping):
        return fallback
    value = report.get("source_report") or report.get("report_json") or report.get("source")
    return str(value or fallback)


def build_candidate_spec(
    *,
    exploration_report: Mapping[str, Any],
    robustness_report: Mapping[str, Any],
    limits: Hyp005ShadowPlanningLimits,
) -> Hyp005NoOrderShadowCandidateSpec:
    spec = _selected_spec(robustness_report) or _selected_spec(exploration_report)
    metrics = _metrics_copy(_selected_metrics(robustness_report))
    acceptance = required_shadow_acceptance_metrics(limits)
    guardrails = {
        "observation_only": True,
        "no_order_shadow_only": True,
        "orders_allowed": False,
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "training_allowed": False,
        "model_reload_allowed": False,
        "config_mutation_allowed": False,
        "post_requests_allowed": False,
        "manual_review_required": True,
        "paper_transition_requires_new_gate": True,
        "live_transition_requires_separate_gate": True,
        "candidate_spec_is_not_trading_permission": True,
    }
    return Hyp005NoOrderShadowCandidateSpec(
        contract_version=HYP005_SHADOW_PLANNING_CONTRACT_VERSION,
        hypothesis_id=HYPOTHESIS_ID,
        branch_name=BRANCH_NAME,
        strategy_family=str(_selected(robustness_report).get("strategy_family") or _selected(exploration_report).get("strategy_family") or "long_liquidity_sweep_reversal"),
        status="NO_ORDER_SHADOW_PLAN_READY",
        source_25s_decision=str(exploration_report.get("decision")),
        source_25t_decision=str(robustness_report.get("decision")),
        entry_signal_definition=build_entry_signal_definition(spec),
        invalidation_conditions=build_invalidation_conditions(spec),
        expected_hold_horizon=build_expected_hold_horizon(spec),
        risk_observation_fields=default_risk_observation_fields(),
        required_shadow_acceptance_metrics=acceptance,
        observed_robustness_metrics=metrics,
        required_source_reports=[
            _source_path(exploration_report, "25S exploration PASS report"),
            _source_path(robustness_report, "25T robustness PASS report"),
        ],
        guardrails=guardrails,
    )


def _spec_to_dict(spec: Hyp005NoOrderShadowCandidateSpec | None) -> dict[str, Any] | None:
    if spec is None:
        return None
    data = asdict(spec)
    data["required_shadow_acceptance_metrics"] = [asdict(item) for item in spec.required_shadow_acceptance_metrics]
    return data


def build_hyp005_no_order_shadow_planning_report(
    *,
    exploration_report: Mapping[str, Any] | None,
    robustness_report: Mapping[str, Any] | None,
    limits: Hyp005ShadowPlanningLimits | None = None,
) -> dict[str, Any]:
    limits = limits or Hyp005ShadowPlanningLimits()
    valid, reasons, warnings = validate_hyp005_source_reports(exploration_report, robustness_report)
    spec = None
    if valid and isinstance(exploration_report, Mapping) and isinstance(robustness_report, Mapping):
        spec = build_candidate_spec(exploration_report=exploration_report, robustness_report=robustness_report, limits=limits)
    decision = "HYP005_SHADOW_PLAN_READY" if valid and spec is not None else "HYP005_SHADOW_PLAN_BLOCK"
    approved_research = decision == "HYP005_SHADOW_PLAN_READY"
    reason_codes = list(reasons)
    if approved_research:
        reason_codes.extend([
            "HYP005_EXPLORATION_PASS_CONFIRMED",
            "HYP005_ROBUSTNESS_PASS_CONFIRMED",
            "NO_ORDER_SHADOW_PLAN_READY",
            "NO_TRAINING_PAPER_LIVE_APPROVALS_DETECTED",
        ])
    else:
        reason_codes.append("NO_ORDER_SHADOW_PLAN_NOT_READY")
    candidate_spec = _spec_to_dict(spec)
    selected_metrics = _metrics_copy(_selected_metrics(robustness_report))
    report = {
        "contract_version": HYP005_SHADOW_PLANNING_CONTRACT_VERSION,
        "phase": "25U",
        "report_type": "hyp005_no_order_shadow_planning_candidate_spec_gate",
        "generated_at": utc_now_iso(),
        "hypothesis_id": HYPOTHESIS_ID,
        "branch_name": BRANCH_NAME,
        "decision": decision,
        "ok": approved_research,
        "selected_strategy_family": (candidate_spec or {}).get("strategy_family"),
        "candidate_spec": candidate_spec,
        "observed_robustness_metrics": selected_metrics,
        "shadow_min_samples": limits.shadow_min_samples,
        "shadow_plan_ready": approved_research,
        "no_order_shadow_only": True,
        "reason_codes": sorted(set(reason_codes)),
        "warnings": sorted(set(warnings)),
        "recommendation": (
            "HYP-005 no-order shadow plan is ready. Do not train, reload, paper trade, or enable live trading; collect shadow observations and require a separate paper-transition gate."
            if approved_research
            else "HYP-005 no-order shadow plan is blocked. Fix missing/invalid 25S/25T source reports; do not train, reload, paper trade, or enable live trading."
        ),
        "limits": asdict(limits),
        "guardrails": {
            "observation_only": True,
            "no_order_shadow_only": True,
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
            "manual_review_required": True,
            "paper_transition_requires_new_gate": True,
            "live_transition_requires_separate_gate": True,
            "candidate_spec_is_not_trading_permission": True,
        },
        "approved_for_research_candidate": approved_research,
        "approved_for_shadow_candidate": approved_research,
        "approved_for_training_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "live_real_allowed": False,
        "post_requests_allowed": False,
        "config_mutation_performed": False,
        "order_actions_performed": False,
        "reload_performed": False,
    }
    return report


def report_to_markdown(report: Mapping[str, Any]) -> str:
    spec = report.get("candidate_spec") if isinstance(report.get("candidate_spec"), Mapping) else {}
    metrics = report.get("observed_robustness_metrics") if isinstance(report.get("observed_robustness_metrics"), Mapping) else {}
    acceptance = spec.get("required_shadow_acceptance_metrics", []) if isinstance(spec, Mapping) else []
    lines = [
        "# 4B.4.3.6.6.25U HYP-005 No-Order Shadow Planning / Candidate Spec Gate",
        "",
        f"- contract_version: `{report.get('contract_version')}`",
        f"- decision: **{report.get('decision')}**",
        f"- hypothesis_id: `{report.get('hypothesis_id')}`",
        f"- branch_name: `{report.get('branch_name')}`",
        f"- selected_strategy_family: `{report.get('selected_strategy_family')}`",
        f"- shadow_plan_ready: `{report.get('shadow_plan_ready')}`",
        f"- no_order_shadow_only: `{report.get('no_order_shadow_only')}`",
        f"- shadow_min_samples: `{report.get('shadow_min_samples')}`",
        f"- signal_count: `{metrics.get('signal_count')}`",
        f"- penalized_mean_net_edge_bps: `{metrics.get('penalized_mean_net_edge_bps')}`",
        f"- median_net_edge_bps: `{metrics.get('median_net_edge_bps')}`",
        f"- profit_factor: `{metrics.get('profit_factor')}`",
        f"- oos_mean_net_edge_bps: `{metrics.get('oos_mean_net_edge_bps')}`",
        f"- approved_for_research_candidate: `{report.get('approved_for_research_candidate')}`",
        f"- approved_for_training_candidate: `{report.get('approved_for_training_candidate')}`",
        f"- approved_for_paper_candidate: `{report.get('approved_for_paper_candidate')}`",
        f"- approved_for_live_real: `{report.get('approved_for_live_real')}`",
        f"- reason_codes: `{report.get('reason_codes')}`",
        f"- warnings: `{report.get('warnings')}`",
        f"- recommendation: {report.get('recommendation')}",
        "",
        "## Candidate Spec Summary",
        "",
        f"- status: `{spec.get('status') if isinstance(spec, Mapping) else None}`",
        f"- execution_mode: `{((spec.get('entry_signal_definition') or {}) if isinstance(spec, Mapping) else {}).get('execution_mode')}`",
        f"- paper_transition_requires_new_gate: `{((spec.get('guardrails') or {}) if isinstance(spec, Mapping) else {}).get('paper_transition_requires_new_gate')}`",
        f"- live_transition_requires_separate_gate: `{((spec.get('guardrails') or {}) if isinstance(spec, Mapping) else {}).get('live_transition_requires_separate_gate')}`",
        "",
        "## Required Shadow Acceptance Metrics",
        "",
        "| metric | operator | threshold | required |",
        "|---|---:|---:|---:|",
    ]
    for item in acceptance:
        if isinstance(item, Mapping):
            lines.append(f"| `{item.get('name')}` | `{item.get('operator')}` | `{item.get('threshold')}` | `{item.get('required')}` |")
    lines.extend([
        "",
        "## Guardrails",
        "",
        "- observation_only: `True`",
        "- no_order_shadow_only: `True`",
        "- orders_allowed: `False`",
        "- training_allowed: `False`",
        "- paper_trading_allowed: `False`",
        "- live_trading_allowed: `False`",
        "- model_reload_allowed: `False`",
        "- config_mutation_allowed: `False`",
        "- post_requests_allowed: `False`",
        "- Training remains blocked.",
        "- Paper/live remain blocked.",
    ])
    return "\n".join(lines) + "\n"
