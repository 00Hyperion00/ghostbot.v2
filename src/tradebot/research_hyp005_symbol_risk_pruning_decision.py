from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any, Iterable, Sequence

from tradebot.research_hyp005_shadow_quality_audit import (
    HYP005_QUALITY_REQUIRED_FIELDS,
    load_hyp005_shadow_observations_with_dedupe_stats,
)

HYP005_SYMBOL_RISK_PRUNING_CONTRACT_VERSION = "4B.4.3.6.6.25AC"
HYP005_CONTINUE_WITH_BASELINE_SYMBOLS = "HYP005_CONTINUE_WITH_BASELINE_SYMBOLS"
HYP005_CONTINUE_WITH_PRUNED_SYMBOL_SET = "HYP005_CONTINUE_WITH_PRUNED_SYMBOL_SET"
HYP005_BRANCH_REFINEMENT_REQUIRED = "HYP005_BRANCH_REFINEMENT_REQUIRED"
HYP005_BRANCH_CLOSURE_RECOMMENDED = "HYP005_BRANCH_CLOSURE_RECOMMENDED"

NO_TRAINING_PAPER_LIVE_APPROVALS_DETECTED = "NO_TRAINING_PAPER_LIVE_APPROVALS_DETECTED"
NO_AUTOMATIC_SYMBOL_CONFIG_MUTATION = "NO_AUTOMATIC_SYMBOL_CONFIG_MUTATION"
SYMBOL_PRUNING_SCENARIO_ANALYSIS_COMPLETED = "SYMBOL_PRUNING_SCENARIO_ANALYSIS_COMPLETED"
CANONICAL_DEDUPLICATION_REUSED_FROM_25AB_H2 = "CANONICAL_DEDUPLICATION_REUSED_FROM_25AB_H2"

DEFAULT_HYP005_SYMBOLS_10: tuple[str, ...] = (
    "BTCUSDT",
    "ETHUSDT",
    "SOLUSDT",
    "BNBUSDT",
    "XRPUSDT",
    "DOGEUSDT",
    "ADAUSDT",
    "AVAXUSDT",
    "LINKUSDT",
    "LTCUSDT",
)

DEFAULT_PRIORITY_RISK_SYMBOLS: tuple[str, ...] = ("AVAXUSDT", "DOGEUSDT")


@dataclass(frozen=True)
class Hyp005SymbolRiskPruningLimits:
    min_unique_observations: int = 30
    min_matured_observations: int = 20
    min_remaining_symbols: int = 6
    max_pruned_symbols: int = 3
    max_slippage_proxy_bps: float = 12.0
    max_true_missing_fields_pct: float = 1.0
    min_mean_forward_edge_bps: float = 0.0
    min_median_forward_edge_bps: float = 0.0
    min_profit_factor: float = 1.0
    min_win_rate_pct: float = 45.0
    tail_loss_threshold_bps: float = -100.0
    closure_min_matured_observations: int = 30
    closure_max_mean_forward_edge_bps: float = -25.0
    closure_max_profit_factor: float = 0.65


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


def _mean(values: Iterable[float]) -> float | None:
    vals = [float(value) for value in values if _safe_float(value) is not None]
    return round(sum(vals) / len(vals), 6) if vals else None


def _median(values: Iterable[float]) -> float | None:
    vals = [float(value) for value in values if _safe_float(value) is not None]
    return round(float(median(vals)), 6) if vals else None


def _profit_factor(values: Iterable[float]) -> float | None:
    vals = [float(value) for value in values if _safe_float(value) is not None]
    if not vals:
        return None
    gains = sum(value for value in vals if value > 0)
    losses = abs(sum(value for value in vals if value < 0))
    if losses == 0:
        return 999.0 if gains > 0 else 0.0
    return round(gains / losses, 6)


def _win_rate(values: Iterable[float]) -> float | None:
    vals = [float(value) for value in values if _safe_float(value) is not None]
    if not vals:
        return None
    return round((sum(1 for value in vals if value > 0) / len(vals)) * 100.0, 6)


def _missing_required_fields(observation: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    for field in HYP005_QUALITY_REQUIRED_FIELDS:
        value = observation.get(field)
        if value is None or value == "":
            missing.append(field)
    return missing


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return payload if isinstance(payload, dict) else {}


def _latest_file(directory: Path, pattern: str) -> Path | None:
    matches = sorted(directory.glob(pattern), key=lambda path: path.stat().st_mtime, reverse=True)
    return matches[0] if matches else None


def _normalize_symbol(value: Any) -> str:
    return str(value or "UNKNOWN").strip().upper()


def _sorted_unique(values: Iterable[str]) -> list[str]:
    return sorted({str(value).strip().upper() for value in values if str(value).strip()})


def _scenario_id(excluded_symbols: Sequence[str]) -> str:
    if not excluded_symbols:
        return "BASELINE_ALL_SYMBOLS"
    return "PRUNE_" + "_".join(_sorted_unique(excluded_symbols))


def _scenario_metrics(
    observations: Sequence[dict[str, Any]],
    *,
    excluded_symbols: Sequence[str],
    limits: Hyp005SymbolRiskPruningLimits,
) -> dict[str, Any]:
    excluded = set(_sorted_unique(excluded_symbols))
    rows = [row for row in observations if _normalize_symbol(row.get("symbol")) not in excluded]
    symbols = _sorted_unique(_normalize_symbol(row.get("symbol")) for row in rows)
    matured_values = [
        value
        for row in rows
        if (value := _safe_float(row.get("forward_return_bps_final"))) is not None
    ]
    maturity_pending_count = len(rows) - len(matured_values)
    slippages = [
        value
        for row in rows
        if (value := _safe_float(row.get("spread_slippage_proxy_bps"))) is not None
    ]
    high_slippage_rows = [
        row
        for row in rows
        if (_safe_float(row.get("spread_slippage_proxy_bps")) or 0.0) > limits.max_slippage_proxy_bps
    ]
    high_slippage_symbols = _sorted_unique(_normalize_symbol(row.get("symbol")) for row in high_slippage_rows)
    tail_loss_rows = [
        row
        for row in rows
        if (_safe_float(row.get("forward_return_bps_final")) is not None)
        and float(row["forward_return_bps_final"]) <= limits.tail_loss_threshold_bps
    ]
    missing_required_fields_count = sum(len(_missing_required_fields(row)) for row in rows)
    total_required_slots = len(rows) * len(HYP005_QUALITY_REQUIRED_FIELDS)
    missing_required_fields_pct = (
        round((missing_required_fields_count / total_required_slots) * 100.0, 6)
        if total_required_slots
        else 0.0
    )
    mean_edge = _mean(matured_values)
    median_edge = _median(matured_values)
    pf = _profit_factor(matured_values)
    win_rate = _win_rate(matured_values)
    checks = {
        "unique_observation_target_met": len(observations) >= limits.min_unique_observations,
        "matured_observation_target_met": len(matured_values) >= limits.min_matured_observations,
        "remaining_symbol_count_ok": len(symbols) >= limits.min_remaining_symbols,
        "pruned_symbol_count_ok": len(excluded) <= limits.max_pruned_symbols,
        "mean_forward_edge_ok": mean_edge is not None and mean_edge >= limits.min_mean_forward_edge_bps,
        "median_forward_edge_ok": median_edge is not None and median_edge >= limits.min_median_forward_edge_bps,
        "profit_factor_ok": pf is not None and pf >= limits.min_profit_factor,
        "win_rate_ok": win_rate is not None and win_rate >= limits.min_win_rate_pct,
        "slippage_risk_removed": not high_slippage_rows,
        "true_missing_fields_ok": missing_required_fields_pct <= limits.max_true_missing_fields_pct,
    }
    return {
        "scenario_id": _scenario_id(tuple(excluded)),
        "excluded_symbols": sorted(excluded),
        "included_symbols": symbols,
        "included_symbol_count": len(symbols),
        "observation_count": len(rows),
        "matured_forward_return_count": len(matured_values),
        "maturity_pending_count": maturity_pending_count,
        "mean_forward_edge_bps": mean_edge,
        "median_forward_edge_bps": median_edge,
        "profit_factor": pf,
        "win_rate_pct": win_rate,
        "mean_slippage_proxy_bps": _mean(slippages),
        "max_slippage_proxy_bps": max(slippages) if slippages else None,
        "high_slippage_count": len(high_slippage_rows),
        "high_slippage_symbols": high_slippage_symbols,
        "tail_loss_count": len(tail_loss_rows),
        "tail_loss_symbols": _sorted_unique(_normalize_symbol(row.get("symbol")) for row in tail_loss_rows),
        "true_missing_required_fields_count": missing_required_fields_count,
        "true_missing_required_fields_pct": missing_required_fields_pct,
        "checks": checks,
        "passes_continuation_gate": all(checks.values()),
    }


def _symbol_risk_summary(
    observations: Sequence[dict[str, Any]],
    *,
    limits: Hyp005SymbolRiskPruningLimits,
) -> list[dict[str, Any]]:
    by_symbol: dict[str, list[dict[str, Any]]] = {}
    for row in observations:
        by_symbol.setdefault(_normalize_symbol(row.get("symbol")), []).append(row)

    summaries: list[dict[str, Any]] = []
    for symbol, rows in sorted(by_symbol.items()):
        matured_values = [
            value
            for row in rows
            if (value := _safe_float(row.get("forward_return_bps_final"))) is not None
        ]
        slippages = [
            value
            for row in rows
            if (value := _safe_float(row.get("spread_slippage_proxy_bps"))) is not None
        ]
        high_slippage_count = sum(value > limits.max_slippage_proxy_bps for value in slippages)
        tail_loss_count = sum(value <= limits.tail_loss_threshold_bps for value in matured_values)
        missing_count = sum(len(_missing_required_fields(row)) for row in rows)
        total_slots = len(rows) * len(HYP005_QUALITY_REQUIRED_FIELDS)
        missing_pct = round((missing_count / total_slots) * 100.0, 6) if total_slots else 0.0
        flags: list[str] = []
        mean_edge = _mean(matured_values)
        pf = _profit_factor(matured_values)
        if high_slippage_count:
            flags.append("SYMBOL_SLIPPAGE_PROXY_HIGH")
        if tail_loss_count:
            flags.append("SYMBOL_TAIL_LOSS_PRESENT")
        if mean_edge is not None and mean_edge < limits.min_mean_forward_edge_bps:
            flags.append("SYMBOL_MEAN_FORWARD_EDGE_NEGATIVE")
        if pf is not None and pf < limits.min_profit_factor:
            flags.append("SYMBOL_PROFIT_FACTOR_LOW")
        if missing_pct > limits.max_true_missing_fields_pct:
            flags.append("SYMBOL_TRUE_REQUIRED_FIELDS_MISSING_HIGH")
        summaries.append(
            {
                "symbol": symbol,
                "observation_count": len(rows),
                "matured_forward_return_count": len(matured_values),
                "maturity_pending_count": len(rows) - len(matured_values),
                "mean_forward_edge_bps": mean_edge,
                "median_forward_edge_bps": _median(matured_values),
                "profit_factor": pf,
                "win_rate_pct": _win_rate(matured_values),
                "mean_slippage_proxy_bps": _mean(slippages),
                "max_slippage_proxy_bps": max(slippages) if slippages else None,
                "high_slippage_count": high_slippage_count,
                "tail_loss_count": tail_loss_count,
                "true_missing_required_fields_count": missing_count,
                "true_missing_required_fields_pct": missing_pct,
                "flags": flags,
            }
        )
    return summaries


def _candidate_scenarios(
    observations: Sequence[dict[str, Any]],
    *,
    limits: Hyp005SymbolRiskPruningLimits,
) -> list[dict[str, Any]]:
    observed_symbols = set(_sorted_unique(_normalize_symbol(row.get("symbol")) for row in observations))
    high_slippage_symbols = _sorted_unique(
        _normalize_symbol(row.get("symbol"))
        for row in observations
        if (_safe_float(row.get("spread_slippage_proxy_bps")) or 0.0) > limits.max_slippage_proxy_bps
    )
    priority_symbols = [symbol for symbol in DEFAULT_PRIORITY_RISK_SYMBOLS if symbol in observed_symbols]
    risk_symbols = _sorted_unique([*priority_symbols, *high_slippage_symbols])[: limits.max_pruned_symbols]

    scenario_exclusions: list[tuple[str, ...]] = [tuple()]
    for symbol in risk_symbols:
        scenario_exclusions.append((symbol,))
    if risk_symbols:
        scenario_exclusions.append(tuple(risk_symbols))
    if set(DEFAULT_PRIORITY_RISK_SYMBOLS).issubset(observed_symbols):
        scenario_exclusions.append(tuple(DEFAULT_PRIORITY_RISK_SYMBOLS))

    unique_exclusions: list[tuple[str, ...]] = []
    seen: set[tuple[str, ...]] = set()
    for exclusions in scenario_exclusions:
        key = tuple(_sorted_unique(exclusions))
        if key not in seen:
            unique_exclusions.append(key)
            seen.add(key)
    return [
        _scenario_metrics(observations, excluded_symbols=exclusions, limits=limits)
        for exclusions in unique_exclusions
    ]


def _scenario_sort_key(scenario: dict[str, Any]) -> tuple[int, float, float, float, int, int]:
    return (
        1 if scenario.get("passes_continuation_gate") else 0,
        float(scenario.get("profit_factor") or -999.0),
        float(scenario.get("mean_forward_edge_bps") or -999.0),
        float(scenario.get("median_forward_edge_bps") or -999.0),
        int(scenario.get("matured_forward_return_count") or 0),
        -len(scenario.get("excluded_symbols") or []),
    )


def _scenario_by_id(scenarios: Sequence[dict[str, Any]], scenario_id: str) -> dict[str, Any]:
    for scenario in scenarios:
        if scenario.get("scenario_id") == scenario_id:
            return scenario
    raise ValueError(f"scenario not found: {scenario_id}")


def _latest_quality_report(reports_dir: Path, input_json: Path | None) -> tuple[dict[str, Any], str | None]:
    if input_json is not None:
        return _read_json(input_json), str(input_json)
    latest = _latest_file(reports_dir, "4B436625AB_H2_hyp005_shadow_quality_slippage_audit_*.json")
    if latest is None:
        return {}, None
    return _read_json(latest), str(latest)


def build_hyp005_symbol_risk_pruning_decision_report(
    reports_dir: Path | str,
    *,
    input_json: Path | str | None = None,
    include_all: bool = True,
    review_ok: bool = False,
    limits: Hyp005SymbolRiskPruningLimits | None = None,
) -> dict[str, Any]:
    active_limits = limits or Hyp005SymbolRiskPruningLimits()
    reports_path = Path(reports_dir)
    input_path = Path(input_json) if input_json is not None else None
    source_quality_report, source_quality_path = _latest_quality_report(reports_path, input_path)
    observations, source_paths, dedupe_stats = load_hyp005_shadow_observations_with_dedupe_stats(
        reports_path,
        include_all=include_all,
    )
    scenarios = _candidate_scenarios(observations, limits=active_limits)
    baseline = _scenario_by_id(scenarios, "BASELINE_ALL_SYMBOLS")
    passing_scenarios = [scenario for scenario in scenarios if scenario.get("passes_continuation_gate")]
    best_passing = max(passing_scenarios, key=_scenario_sort_key) if passing_scenarios else None
    best_available = max(scenarios, key=_scenario_sort_key) if scenarios else baseline

    reason_codes: list[str] = [
        NO_TRAINING_PAPER_LIVE_APPROVALS_DETECTED,
        NO_AUTOMATIC_SYMBOL_CONFIG_MUTATION,
        SYMBOL_PRUNING_SCENARIO_ANALYSIS_COMPLETED,
        CANONICAL_DEDUPLICATION_REUSED_FROM_25AB_H2,
    ]
    warnings: list[str] = []
    blockers: list[str] = []

    if not review_ok:
        blockers.append("REVIEW_OK_REQUIRED")
    if len(observations) < active_limits.min_unique_observations:
        blockers.append("UNIQUE_SHADOW_SAMPLE_TARGET_NOT_MET")
    if int(baseline.get("matured_forward_return_count") or 0) < active_limits.min_matured_observations:
        blockers.append("MATURED_SHADOW_SAMPLE_TARGET_NOT_MET")
    if float(baseline.get("true_missing_required_fields_pct") or 0.0) > active_limits.max_true_missing_fields_pct:
        warnings.append("BASELINE_TRUE_REQUIRED_FIELDS_MISSING_HIGH")
    if int(baseline.get("high_slippage_count") or 0) > 0:
        warnings.append("BASELINE_SHADOW_SLIPPAGE_PROXY_HIGH")
    if (baseline.get("mean_forward_edge_bps") is not None) and float(baseline["mean_forward_edge_bps"]) < 0:
        warnings.append("BASELINE_MEAN_FORWARD_EDGE_NEGATIVE")
    if (baseline.get("profit_factor") is not None) and float(baseline["profit_factor"]) < active_limits.min_profit_factor:
        warnings.append("BASELINE_PROFIT_FACTOR_LOW")

    decision = HYP005_BRANCH_REFINEMENT_REQUIRED
    selected_scenario = best_available

    baseline_passes = bool(baseline.get("passes_continuation_gate"))
    if not blockers and baseline_passes:
        decision = HYP005_CONTINUE_WITH_BASELINE_SYMBOLS
        selected_scenario = baseline
        reason_codes.append("BASELINE_SYMBOL_SET_PASSES_CONTINUATION_GATE")
    elif not blockers and best_passing is not None:
        decision = HYP005_CONTINUE_WITH_PRUNED_SYMBOL_SET
        selected_scenario = best_passing
        reason_codes.append("PRUNED_SYMBOL_SET_PASSES_CONTINUATION_GATE")
        if selected_scenario.get("excluded_symbols"):
            reason_codes.append("SYMBOL_RISK_PRUNING_RECOMMENDED")
    else:
        reason_codes.append("NO_SYMBOL_SCENARIO_PASSES_CONTINUATION_GATE")
        if blockers:
            reason_codes.extend(blockers)
        closure_ready = (
            len(observations) >= active_limits.min_unique_observations
            and int(best_available.get("matured_forward_return_count") or 0)
            >= active_limits.closure_min_matured_observations
            and (best_available.get("mean_forward_edge_bps") is not None)
            and float(best_available["mean_forward_edge_bps"]) <= active_limits.closure_max_mean_forward_edge_bps
            and (best_available.get("profit_factor") is not None)
            and float(best_available["profit_factor"]) <= active_limits.closure_max_profit_factor
        )
        if not blockers and closure_ready:
            decision = HYP005_BRANCH_CLOSURE_RECOMMENDED
            reason_codes.append("ALL_CONTROLLED_SYMBOL_SCENARIOS_REMAIN_ECONOMICALLY_WEAK")
        else:
            decision = HYP005_BRANCH_REFINEMENT_REQUIRED
            reason_codes.append("CANDIDATE_REFINEMENT_REQUIRED_BEFORE_TRANSITION")

    recommended_symbols = list(selected_scenario.get("included_symbols") or [])
    recommended_pruned_symbols = list(selected_scenario.get("excluded_symbols") or [])
    if decision == HYP005_CONTINUE_WITH_BASELINE_SYMBOLS:
        recommendation = (
            "HYP-005 baseline symbol set passes the no-order continuation decision gate. Continue observation only; "
            "do not train, reload, start paper trading, enable live trading, mutate scheduler config, or send orders."
        )
    elif decision == HYP005_CONTINUE_WITH_PRUNED_SYMBOL_SET:
        recommendation = (
            "HYP-005 controlled risk-pruning scenario passes the no-order continuation decision gate. Review the "
            f"recommended removal list ({','.join(recommended_pruned_symbols) or 'none'}) and use a separate operator "
            "patch before changing the scheduler. Do not train, reload, paper trade, live trade, or send orders."
        )
    elif decision == HYP005_BRANCH_CLOSURE_RECOMMENDED:
        recommendation = (
            "HYP-005 remains economically weak after controlled symbol-risk pruning scenarios. Recommend branch "
            "closure review. Do not train, reload, paper trade, live trade, mutate scheduler config, or send orders."
        )
    else:
        recommendation = (
            "HYP-005 requires branch refinement. No controlled symbol scenario currently passes the continuation "
            "gate. Continue no-order analysis only; do not train, reload, paper trade, live trade, mutate scheduler "
            "config, or send orders."
        )

    return {
        "ok": decision in {HYP005_CONTINUE_WITH_BASELINE_SYMBOLS, HYP005_CONTINUE_WITH_PRUNED_SYMBOL_SET},
        "contract_version": HYP005_SYMBOL_RISK_PRUNING_CONTRACT_VERSION,
        "phase": "25AC",
        "report_type": "hyp005_symbol_risk_pruning_candidate_continuation_decision_gate",
        "generated_at_utc": _utc_now_iso(),
        "decision": decision,
        "hypothesis_id": "HYP-005",
        "branch_name": "liquidity_sweep_reversal_vol_compression",
        "selected_strategy_family": "long_liquidity_sweep_reversal",
        "review_ok": bool(review_ok),
        "no_order_decision_gate_only": True,
        "runtime_probe_only": True,
        "source_quality_report_json": source_quality_path,
        "source_quality_report_decision": source_quality_report.get("decision"),
        "source_quality_report_unique_observation_count": (
            (source_quality_report.get("deduplication") or {}).get("unique_observation_count")
            if isinstance(source_quality_report.get("deduplication"), dict)
            else None
        ),
        "source_observation_paths": source_paths,
        "deduplication": dedupe_stats,
        "limits": asdict(active_limits),
        "baseline_scenario": baseline,
        "scenario_comparisons": scenarios,
        "selected_scenario": selected_scenario,
        "recommended_symbols": recommended_symbols,
        "recommended_symbols_arg": ",".join(recommended_symbols),
        "recommended_pruned_symbols": recommended_pruned_symbols,
        "per_symbol_risk": _symbol_risk_summary(observations, limits=active_limits),
        "approved_for_continued_no_order_shadow_collection": decision != HYP005_BRANCH_CLOSURE_RECOMMENDED,
        "approved_for_symbol_set_candidate": decision in {
            HYP005_CONTINUE_WITH_BASELINE_SYMBOLS,
            HYP005_CONTINUE_WITH_PRUNED_SYMBOL_SET,
        },
        "approved_for_scheduler_regeneration": False,
        "scheduler_regeneration_requires_separate_operator_patch": True,
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
        "reason_codes": sorted(dict.fromkeys(reason_codes)),
        "warnings": sorted(dict.fromkeys(warnings)),
        "blockers": sorted(dict.fromkeys(blockers)),
        "recommendation": recommendation,
    }


def render_hyp005_symbol_risk_pruning_decision_markdown(report: dict[str, Any]) -> str:
    baseline = report.get("baseline_scenario", {}) if isinstance(report.get("baseline_scenario"), dict) else {}
    selected = report.get("selected_scenario", {}) if isinstance(report.get("selected_scenario"), dict) else {}
    lines = [
        "# HYP-005 Symbol Risk Pruning / Candidate Continuation Decision Gate",
        "",
        f"- contract_version: `{report.get('contract_version')}`",
        f"- decision: `{report.get('decision')}`",
        f"- generated_at_utc: `{report.get('generated_at_utc')}`",
        f"- canonical_unique_observation_count: `{(report.get('deduplication') or {}).get('unique_observation_count')}`",
        f"- baseline_mean_forward_edge_bps: `{baseline.get('mean_forward_edge_bps')}`",
        f"- baseline_profit_factor: `{baseline.get('profit_factor')}`",
        f"- selected_scenario: `{selected.get('scenario_id')}`",
        f"- recommended_pruned_symbols: `{','.join(report.get('recommended_pruned_symbols') or [])}`",
        f"- recommended_symbols_arg: `{report.get('recommended_symbols_arg')}`",
        "",
        "## Safety",
        "",
        "This gate does not mutate scheduler config, train models, reload models, start paper trading, enable live trading, send POST requests, or send orders.",
        "",
        "## Scenario Comparisons",
        "",
    ]
    for scenario in report.get("scenario_comparisons", []):
        if not isinstance(scenario, dict):
            continue
        lines.append(
            "- "
            f"{scenario.get('scenario_id')}: excluded={','.join(scenario.get('excluded_symbols') or []) or 'none'}, "
            f"matured={scenario.get('matured_forward_return_count')}, mean_edge={scenario.get('mean_forward_edge_bps')}, "
            f"median_edge={scenario.get('median_forward_edge_bps')}, pf={scenario.get('profit_factor')}, "
            f"win_rate={scenario.get('win_rate_pct')}, high_slip={scenario.get('high_slippage_count')}, "
            f"tail_losses={scenario.get('tail_loss_count')}, passes={scenario.get('passes_continuation_gate')}"
        )
    lines.extend(["", "## Per-Symbol Risk", ""])
    for row in report.get("per_symbol_risk", []):
        if not isinstance(row, dict):
            continue
        lines.append(
            "- "
            f"{row.get('symbol')}: count={row.get('observation_count')}, matured={row.get('matured_forward_return_count')}, "
            f"mean_edge={row.get('mean_forward_edge_bps')}, pf={row.get('profit_factor')}, "
            f"max_slip={row.get('max_slippage_proxy_bps')}, tail_losses={row.get('tail_loss_count')}, "
            f"flags={','.join(row.get('flags') or []) or 'none'}"
        )
    lines.extend(["", "## Reason Codes", ""])
    for code in report.get("reason_codes", []):
        lines.append(f"- `{code}`")
    lines.extend(["", "## Warnings", ""])
    for warning in report.get("warnings", []):
        lines.append(f"- `{warning}`")
    lines.extend(["", "## Recommendation", "", str(report.get("recommendation") or "")])
    return "\n".join(lines) + "\n"


def write_hyp005_symbol_risk_pruning_decision_report(
    report: dict[str, Any], out_dir: Path | str
) -> tuple[Path, Path]:
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    json_path = out_path / f"4B436625AC_hyp005_symbol_risk_pruning_decision_{stamp}.json"
    md_path = out_path / f"4B436625AC_hyp005_symbol_risk_pruning_decision_{stamp}.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(render_hyp005_symbol_risk_pruning_decision_markdown(report), encoding="utf-8")
    return json_path, md_path
