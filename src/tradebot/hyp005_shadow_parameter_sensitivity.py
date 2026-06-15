from __future__ import annotations

import json
import math
import os
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tradebot.hyp005_shadow_stagnation_diagnostics import (
    BRANCH_NAME,
    HYPOTHESIS_ID,
    STRATEGY_FAMILY,
    Candle,
    CandidateAudit,
    RuntimeSpec,
    fetch_public_klines,
    group_by_symbol,
    ledger_identity_set,
    load_json,
    load_jsonl,
    parse_csv_rows,
    parse_runtime_spec,
    safe_float,
    safe_int,
    scan_candidate_audit,
    utc_now_iso,
)

CONTRACT_VERSION = "4B.4.3.6.6.27G-H4"
REPORT_PREFIX = "4B436627GH4_hyp005_shadow_parameter_sensitivity_matrix"
DEFAULT_MIN_SWEEP_BPS_VALUES = (18.0, 15.0, 12.0)
DEFAULT_MIN_WICK_PCT_VALUES = (42.0, 38.0, 35.0)
DEFAULT_MAX_COMPRESSION_RATIO_VALUES = (1.05, 1.10, 1.15)


def _round(value: float | None, digits: int = 6) -> float | None:
    if value is None or math.isnan(value) or math.isinf(value):
        return None
    return round(value, digits)


def _parse_float_csv(text: str | None, default: Sequence[float]) -> list[float]:
    if text is None or not str(text).strip():
        return list(default)
    values: list[float] = []
    for item in str(text).split(","):
        item = item.strip()
        if not item:
            continue
        value = safe_float(item, float("nan"))
        if math.isnan(value):
            raise ValueError(f"HYP005_H4_INVALID_FLOAT_VALUE:{item}")
        values.append(value)
    if not values:
        raise ValueError("HYP005_H4_EMPTY_THRESHOLD_VECTOR")
    return sorted(set(values), reverse=True)


def threshold_grid(
    *,
    min_sweep_bps_values: Sequence[float] | None = None,
    min_wick_pct_values: Sequence[float] | None = None,
    max_compression_ratio_values: Sequence[float] | None = None,
) -> list[dict[str, float]]:
    variants: list[dict[str, float]] = []
    for sweep in list(min_sweep_bps_values or DEFAULT_MIN_SWEEP_BPS_VALUES):
        for wick in list(min_wick_pct_values or DEFAULT_MIN_WICK_PCT_VALUES):
            for compression in list(max_compression_ratio_values or DEFAULT_MAX_COMPRESSION_RATIO_VALUES):
                variants.append(
                    {
                        "min_sweep_bps": float(sweep),
                        "min_wick_pct": float(wick),
                        "max_compression_ratio": float(compression),
                    }
                )
    return variants


def _variant_id(thresholds: Mapping[str, float]) -> str:
    sweep = str(thresholds["min_sweep_bps"]).replace(".", "p")
    wick = str(thresholds["min_wick_pct"]).replace(".", "p")
    comp = str(thresholds["max_compression_ratio"]).replace(".", "p")
    return f"sweep_{sweep}__wick_{wick}__compression_{comp}"


def _variant_spec(base: RuntimeSpec, thresholds: Mapping[str, float]) -> RuntimeSpec:
    return replace(
        base,
        min_sweep_bps=float(thresholds["min_sweep_bps"]),
        min_wick_pct=float(thresholds["min_wick_pct"]),
        max_compression_ratio=float(thresholds["max_compression_ratio"]),
    )


def _candidate_returns(
    exact_candidates: Sequence[CandidateAudit],
    grouped: Mapping[str, Sequence[Candle]],
    spec: RuntimeSpec,
) -> list[float]:
    returns: list[float] = []
    index_by_symbol_ts: dict[tuple[str, str], int] = {}
    rows_by_symbol = {symbol.upper(): list(rows) for symbol, rows in grouped.items()}
    for symbol, rows in rows_by_symbol.items():
        for index, candle in enumerate(rows):
            index_by_symbol_ts[(symbol, candle.timestamp_utc)] = index
    for candidate in exact_candidates:
        symbol = candidate.symbol.upper()
        rows = rows_by_symbol.get(symbol, [])
        index = index_by_symbol_ts.get((symbol, candidate.timestamp_utc))
        if index is None:
            continue
        final_index = index + spec.hold_bars
        if final_index >= len(rows):
            continue
        entry = candidate.entry_reference_price
        final_close = rows[final_index].close
        if entry <= 0 or final_close <= 0:
            continue
        returns.append(round((final_close - entry) / entry * 10000.0, 6))
    return returns


def _performance_summary(returns: Sequence[float]) -> dict[str, Any]:
    wins = [value for value in returns if value > 0]
    losses = [abs(value) for value in returns if value < 0]
    gross_profit = sum(wins)
    gross_loss = sum(losses)
    net = gross_profit - gross_loss
    if gross_loss > 0:
        profit_factor: float | None = gross_profit / gross_loss
    elif gross_profit > 0:
        profit_factor = 999.0
    else:
        profit_factor = None
    sorted_returns = sorted(returns)
    median: float | None = None
    if sorted_returns:
        mid = len(sorted_returns) // 2
        median = sorted_returns[mid] if len(sorted_returns) % 2 else (sorted_returns[mid - 1] + sorted_returns[mid]) / 2.0
    return {
        "matured_count": len(returns),
        "win_count": len(wins),
        "loss_count": len(losses),
        "win_rate_pct": _round(len(wins) / len(returns) * 100.0 if returns else 0.0),
        "gross_profit_bps": _round(gross_profit),
        "gross_loss_bps": _round(gross_loss),
        "net_return_bps": _round(net),
        "mean_return_bps": _round(sum(returns) / len(returns) if returns else None),
        "median_return_bps": _round(median),
        "profit_factor": _round(profit_factor),
        "worst_return_bps": _round(min(returns) if returns else None),
        "best_return_bps": _round(max(returns) if returns else None),
    }


def _variant_score(row: Mapping[str, Any]) -> float:
    perf = row.get("performance") if isinstance(row.get("performance"), Mapping) else {}
    new_unique = safe_float(row.get("new_unique_candidate_count"), 0.0)
    pf = safe_float(perf.get("profit_factor"), 0.0)
    mean_return = safe_float(perf.get("mean_return_bps"), -9999.0)
    exact_count = safe_float(row.get("exact_candidate_count"), 0.0)
    return round(new_unique * 1000.0 + pf * 100.0 + mean_return - max(0.0, exact_count - new_unique) * 2.5, 6)


def _status_for_variant(row: Mapping[str, Any], baseline: Mapping[str, Any]) -> str:
    perf = row.get("performance") if isinstance(row.get("performance"), Mapping) else {}
    baseline_perf = baseline.get("performance") if isinstance(baseline.get("performance"), Mapping) else {}
    new_unique = safe_float(row.get("new_unique_candidate_count"), 0.0)
    mean_return = safe_float(perf.get("mean_return_bps"), -9999.0)
    baseline_mean = safe_float(baseline_perf.get("mean_return_bps"), -9999.0)
    pf = safe_float(perf.get("profit_factor"), 0.0)
    if new_unique <= 0:
        return "NO_NEW_UNIQUE_CANDIDATES"
    if mean_return <= 0 or pf < 1.0:
        return "REJECTED_NEGATIVE_EXPECTANCY"
    if mean_return <= baseline_mean:
        return "REJECTED_NO_BASELINE_IMPROVEMENT"
    return "PROMISING_RESEARCH_ONLY_VARIANT"


def evaluate_sensitivity_matrix(
    *,
    base_spec: RuntimeSpec,
    ledger_rows: Sequence[Mapping[str, Any]],
    candles: Sequence[Candle],
    min_sweep_bps_values: Sequence[float] | None = None,
    min_wick_pct_values: Sequence[float] | None = None,
    max_compression_ratio_values: Sequence[float] | None = None,
) -> list[dict[str, Any]]:
    existing_ids = ledger_identity_set(ledger_rows)
    grouped = group_by_symbol(candles)
    variants = threshold_grid(
        min_sweep_bps_values=min_sweep_bps_values,
        min_wick_pct_values=min_wick_pct_values,
        max_compression_ratio_values=max_compression_ratio_values,
    )
    rows: list[dict[str, Any]] = []
    for thresholds in variants:
        spec = _variant_spec(base_spec, thresholds)
        audits = scan_candidate_audit(candles, spec, existing_ids)
        exact = [item for item in audits if item.exact_candidate]
        new_unique = [item for item in exact if item.new_unique_candidate]
        duplicate = [item for item in exact if item.duplicate_existing_observation]
        near_miss = [item for item in audits if item.near_miss]
        returns = _candidate_returns(exact, grouped, spec)
        exact_symbols = {item.symbol for item in exact}
        new_symbols = {item.symbol for item in new_unique}
        row = {
            "variant_id": _variant_id(thresholds),
            "thresholds": dict(thresholds),
            "evaluated_candle_count": len(audits),
            "exact_candidate_count": len(exact),
            "new_unique_candidate_count": len(new_unique),
            "duplicate_candidate_count": len(duplicate),
            "near_miss_count": len(near_miss),
            "exact_candidates_by_symbol": dict(sorted({symbol: sum(1 for item in exact if item.symbol == symbol) for symbol in exact_symbols}.items())),
            "new_unique_candidates_by_symbol": dict(sorted({symbol: sum(1 for item in new_unique if item.symbol == symbol) for symbol in new_symbols}.items())),
            "performance": _performance_summary(returns),
            "sample_observation_ids": [item.observation_id for item in new_unique[:20]],
        }
        row["research_score"] = _variant_score(row)
        rows.append(row)
    baseline = None
    for row in rows:
        thresholds = row["thresholds"]
        if (
            abs(thresholds["min_sweep_bps"] - base_spec.min_sweep_bps) < 1e-9
            and abs(thresholds["min_wick_pct"] - base_spec.min_wick_pct) < 1e-9
            and abs(thresholds["max_compression_ratio"] - base_spec.max_compression_ratio) < 1e-9
        ):
            baseline = row
            break
    baseline = baseline or (rows[0] if rows else {})
    baseline_exact = safe_float(baseline.get("exact_candidate_count"), 0.0)
    baseline_new = safe_float(baseline.get("new_unique_candidate_count"), 0.0)
    for row in rows:
        row["delta_vs_baseline"] = {
            "exact_candidate_delta": safe_float(row.get("exact_candidate_count"), 0.0) - baseline_exact,
            "new_unique_candidate_delta": safe_float(row.get("new_unique_candidate_count"), 0.0) - baseline_new,
            "research_score_delta": _round(safe_float(row.get("research_score"), 0.0) - safe_float(baseline.get("research_score"), 0.0)),
        }
        row["research_status"] = _status_for_variant(row, baseline)
    return sorted(rows, key=lambda item: (safe_float(item.get("research_score"), -999999.0), safe_float(item.get("new_unique_candidate_count"), 0.0)), reverse=True)


def _baseline_row(matrix: Sequence[Mapping[str, Any]], base_spec: RuntimeSpec) -> Mapping[str, Any]:
    for row in matrix:
        thresholds = row.get("thresholds") if isinstance(row.get("thresholds"), Mapping) else {}
        if (
            abs(safe_float(thresholds.get("min_sweep_bps"), -1.0) - base_spec.min_sweep_bps) < 1e-9
            and abs(safe_float(thresholds.get("min_wick_pct"), -1.0) - base_spec.min_wick_pct) < 1e-9
            and abs(safe_float(thresholds.get("max_compression_ratio"), -1.0) - base_spec.max_compression_ratio) < 1e-9
        ):
            return row
    return matrix[0] if matrix else {}


def _research_summary(matrix: Sequence[Mapping[str, Any]], base_spec: RuntimeSpec) -> dict[str, Any]:
    baseline = _baseline_row(matrix, base_spec)
    promising = [row for row in matrix if row.get("research_status") == "PROMISING_RESEARCH_ONLY_VARIANT"]
    negative = [row for row in matrix if row.get("research_status") == "REJECTED_NEGATIVE_EXPECTANCY"]
    any_new = [row for row in matrix if safe_int(row.get("new_unique_candidate_count"), 0) > 0]
    best = matrix[0] if matrix else {}
    return {
        "baseline_variant_id": baseline.get("variant_id"),
        "baseline_exact_candidate_count": baseline.get("exact_candidate_count"),
        "baseline_new_unique_candidate_count": baseline.get("new_unique_candidate_count"),
        "variant_count": len(matrix),
        "variants_with_new_unique_candidates": len(any_new),
        "promising_research_only_variant_count": len(promising),
        "negative_expectancy_variant_count": len(negative),
        "best_research_variant_id": best.get("variant_id"),
        "best_research_status": best.get("research_status"),
        "best_research_score": best.get("research_score"),
        "paper_transition_candidate_found": False,
        "strategy_parameter_mutation_recommended": False,
    }


def _recommendation(summary: Mapping[str, Any]) -> str:
    if safe_int(summary.get("promising_research_only_variant_count"), 0) > 0:
        return "Some threshold variants are research-promising, but this is not paper approval. Run a separate out-of-sample validation gate before any strategy mutation."
    if safe_int(summary.get("variants_with_new_unique_candidates"), 0) > 0:
        return "Threshold relaxation creates new candidates but expectancy is not acceptable. Keep paper/live gates closed and do not mutate parameters."
    return "No threshold variant produced acceptable new unique evidence. Keep the canonical HYP-005-R1 parameters unchanged and continue no-order research only."


def build_parameter_sensitivity_report(
    *,
    candidate_spec: Mapping[str, Any] | None,
    ledger_rows: Sequence[Mapping[str, Any]],
    candles: Sequence[Candle],
    min_sweep_bps_values: Sequence[float] | None = None,
    min_wick_pct_values: Sequence[float] | None = None,
    max_compression_ratio_values: Sequence[float] | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    generated = generated_at or utc_now_iso()
    base_spec = parse_runtime_spec(candidate_spec)
    matrix = evaluate_sensitivity_matrix(
        base_spec=base_spec,
        ledger_rows=ledger_rows,
        candles=candles,
        min_sweep_bps_values=min_sweep_bps_values,
        min_wick_pct_values=min_wick_pct_values,
        max_compression_ratio_values=max_compression_ratio_values,
    )
    summary = _research_summary(matrix, base_spec)
    ok = bool(candles) and bool(matrix)
    return {
        "contract_version": CONTRACT_VERSION,
        "report_type": "hyp005_no_order_parameter_sensitivity_matrix_near_miss_threshold_stress_audit",
        "generated_at_utc": generated,
        "ok": ok,
        "decision": "HYP005_PARAMETER_SENSITIVITY_MATRIX_READY" if ok else "HYP005_PARAMETER_SENSITIVITY_MATRIX_BLOCK",
        "hypothesis_id": HYPOTHESIS_ID,
        "branch_name": BRANCH_NAME,
        "selected_strategy_family": STRATEGY_FAMILY,
        "timeframe": base_spec.timeframe,
        "read_only": True,
        "no_order_research_variant_report_only": True,
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
        "paper_transition_candidate_found": False,
        "strategy_parameter_mutation_performed": False,
        "runtime_spec_baseline": asdict(base_spec),
        "threshold_vectors": {
            "min_sweep_bps": list(min_sweep_bps_values or DEFAULT_MIN_SWEEP_BPS_VALUES),
            "min_wick_pct": list(min_wick_pct_values or DEFAULT_MIN_WICK_PCT_VALUES),
            "max_compression_ratio": list(max_compression_ratio_values or DEFAULT_MAX_COMPRESSION_RATIO_VALUES),
        },
        "research_summary": summary,
        "sensitivity_matrix": matrix,
        "top_variants": list(matrix[:10]),
        "reason_codes": [
            "NO_ORDER_RESEARCH_VARIANT_REPORT_ONLY",
            "PAPER_LIVE_GATES_REMAIN_CLOSED",
            "STRATEGY_PARAMETER_MUTATION_NOT_PERFORMED",
        ],
        "warnings": ["PARAMETER_RELAXATION_NOT_APPROVAL"],
        "recommendation": _recommendation(summary),
    }


def write_json_atomic(path: str | os.PathLike[str], payload: Any) -> None:
    resolved = Path(path).resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=True, sort_keys=True, indent=2) + "\n"
    with tempfile.NamedTemporaryFile(mode="wb", prefix=f".{resolved.name}.", suffix=".tmp", dir=resolved.parent, delete=False) as handle:
        temp_path = Path(handle.name)
        handle.write(text.encode("utf-8"))
        handle.flush()
        os.fsync(handle.fileno())
    try:
        temp_path.replace(resolved)
    finally:
        temp_path.unlink(missing_ok=True)


def write_markdown(path: str | os.PathLike[str], payload: Mapping[str, Any]) -> None:
    summary = payload.get("research_summary") if isinstance(payload.get("research_summary"), Mapping) else {}
    lines = [
        "# 4B.4.3.6.6.27G-H4 Parameter Sensitivity Matrix",
        "",
        f"- decision: `{payload.get('decision')}`",
        f"- variant_count: `{summary.get('variant_count')}`",
        f"- variants_with_new_unique_candidates: `{summary.get('variants_with_new_unique_candidates')}`",
        f"- promising_research_only_variant_count: `{summary.get('promising_research_only_variant_count')}`",
        f"- best_research_variant_id: `{summary.get('best_research_variant_id')}`",
        f"- best_research_status: `{summary.get('best_research_status')}`",
        "",
        "## Recommendation",
        "",
        str(payload.get("recommendation", "")),
        "",
        "Paper/live/order gates remain closed.",
    ]
    resolved = Path(path).resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text("\n".join(lines) + "\n", encoding="utf-8")


__all__ = [
    "CONTRACT_VERSION",
    "REPORT_PREFIX",
    "build_parameter_sensitivity_report",
    "evaluate_sensitivity_matrix",
    "fetch_public_klines",
    "load_json",
    "load_jsonl",
    "parse_csv_rows",
    "_parse_float_csv",
    "write_json_atomic",
    "write_markdown",
]
