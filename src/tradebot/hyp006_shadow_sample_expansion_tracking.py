from __future__ import annotations

import json
import math
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median
from typing import Any, Mapping, Sequence

CONTRACT_VERSION = "4B.4.3.6.6.28G"
SOURCE_BASELINE_CONTRACT_VERSION = "4B.4.3.6.6.28F"
BRANCH_ID = "HYP-006-R1"
HYPOTHESIS_ID = "HYP-006"
BRANCH_NAME = "failed_downside_sweep_reversal_continuation_short"
STRATEGY_FAMILY = "short_failed_liquidity_sweep_continuation"
REPORT_PREFIX = "4B436628G_hyp006_r1_shadow_sample_expansion_acceptance_tracking"
ACCEPTANCE_DELTA_PREFIX = "4B436628G_hyp006_r1_acceptance_tracking_delta"
CONTINUITY_DELTA_PREFIX = "4B436628G_hyp006_r1_operator_cockpit_continuity_delta"
DASHBOARD_DELTA_PREFIX = "4B436628G_hyp006_r1_operator_cockpit_dashboard_delta_seed"
DEFAULT_REPEAT_GATE = "28G_REPEAT_SHADOW_SAMPLE_EXPANSION_AND_ACCEPTANCE_TRACKING"
DEFAULT_NEXT_GATE = "28H_HYP006_SHADOW_ACCEPTANCE_REVIEW_AND_NO_ORDER_MATURITY_DECISION"

REQUIRED_METRICS: tuple[dict[str, Any], ...] = (
    {"name": "min_shadow_sample_target", "operator": ">=", "threshold": 30},
    {"name": "shadow_mean_forward_edge_bps", "operator": ">", "threshold": 0.0},
    {"name": "shadow_median_forward_edge_bps", "operator": ">", "threshold": 0.0},
    {"name": "shadow_profit_factor", "operator": ">=", "threshold": 1.15},
    {"name": "shadow_walk_forward_positive_rate_pct", "operator": ">=", "threshold": 55.0},
    {"name": "shadow_data_quality_pct", "operator": ">=", "threshold": 99.0},
    {"name": "max_slippage_proxy_bps", "operator": "<=", "threshold": 12.0},
)


@dataclass(frozen=True)
class MetricResult:
    name: str
    operator: str
    threshold: float
    value: float | int | None
    previous_value: float | int | None
    delta: float | int | None
    passed: bool


@dataclass(frozen=True)
class LedgerMetrics:
    ledger_row_count: int
    unique_observation_ids: int
    duplicate_observation_count: int
    duplicate_observation_ids: list[str]
    unsafe_row_count: int
    unsafe_rows: list[str]
    matured_count: int
    win_count: int
    loss_count: int
    win_rate_pct: float
    mean_return_bps: float | None
    median_return_bps: float | None
    net_return_bps: float | None
    profit_factor: float | None
    best_return_bps: float | None
    worst_return_bps: float | None
    max_slippage_proxy_bps: float | None
    data_quality_pct: float
    sample_target: int
    sample_progress_pct: float
    sample_target_reached: bool
    symbols_observed: list[str]
    symbols_observed_count: int
    latest_observation_utc: str | None
    earliest_observation_utc: str | None
    observation_ids: list[str]


@dataclass(frozen=True)
class ExpansionDelta:
    previous_unique_observation_ids: int
    current_unique_observation_ids: int
    new_unique_observation_count: int
    target_remaining_count: int
    sample_progress_delta_pct: float
    new_observation_ids: list[str]
    removed_observation_ids: list[str]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _safe_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(result) or math.isinf(result):
        return None
    return result


def _safe_int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def load_json(path: str | os.PathLike[str] | None) -> Any:
    if path is None:
        return None
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def load_jsonl(path: str | os.PathLike[str] | None) -> list[dict[str, Any]]:
    if path is None:
        return []
    rows: list[dict[str, Any]] = []
    text = Path(path).read_text(encoding="utf-8-sig")
    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        value = json.loads(stripped)
        if not isinstance(value, dict):
            raise ValueError(f"JSONL row {line_number} is not an object")
        rows.append(value)
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


def baseline_report_is_ready(report: Mapping[str, Any] | None) -> bool:
    payload = _mapping(report)
    return bool(
        payload.get("contract_version") == SOURCE_BASELINE_CONTRACT_VERSION
        and payload.get("decision") == "HYP006_R1_SHADOW_OPERATOR_COCKPIT_BASELINE_READY"
        and payload.get("ok") is True
        and payload.get("branch_id") == BRANCH_ID
        and payload.get("approved_for_acceptance_tracking") is True
        and payload.get("approved_for_shadow_collection_continuity") is True
        and payload.get("approved_for_paper_candidate") is False
        and payload.get("approved_for_live_real") is False
        and payload.get("order_actions_performed") is False
        and payload.get("training_performed") is False
        and payload.get("reload_performed") is False
    )


def _profit_factor(returns: Sequence[float]) -> float | None:
    gross_profit = sum(value for value in returns if value > 0)
    gross_loss = abs(sum(value for value in returns if value < 0))
    if gross_profit <= 0 and gross_loss <= 0:
        return None
    if gross_loss <= 0:
        return round(float("inf"), 6)
    return round(gross_profit / gross_loss, 6)


def compute_ledger_metrics(rows: Sequence[Mapping[str, Any]], *, sample_target: int = 30) -> LedgerMetrics:
    observation_ids: list[str] = []
    duplicate_ids: list[str] = []
    seen: set[str] = set()
    unsafe_rows: list[str] = []
    returns: list[float] = []
    slippage_values: list[float] = []
    symbols: set[str] = set()
    timestamps: list[str] = []

    for index, row in enumerate(rows):
        obs_id = str(row.get("observation_id") or f"row_{index}")
        observation_ids.append(obs_id)
        if obs_id in seen:
            duplicate_ids.append(obs_id)
        seen.add(obs_id)

        if row.get("branch_id") != BRANCH_ID or row.get("no_order_measurement_only") is not True:
            unsafe_rows.append(obs_id)

        forward = _safe_float(row.get("forward_return_bps_final_short_probe"))
        if forward is None:
            forward = _safe_float(row.get("forward_return_bps"))
        if forward is not None:
            returns.append(forward)

        slip = _safe_float(row.get("spread_slippage_proxy_bps"))
        if slip is not None:
            slippage_values.append(slip)

        symbol = row.get("symbol")
        if isinstance(symbol, str) and symbol:
            symbols.add(symbol)

        ts = row.get("timestamp_utc")
        if isinstance(ts, str) and ts:
            timestamps.append(ts)

    row_count = len(rows)
    unique_count = len(seen)
    matured_count = len(returns)
    win_count = sum(1 for value in returns if value > 0)
    loss_count = sum(1 for value in returns if value < 0)
    win_rate = round((win_count / matured_count) * 100, 6) if matured_count else 0.0
    mean_return = round(mean(returns), 6) if returns else None
    median_return = round(median(returns), 6) if returns else None
    net_return = round(sum(returns), 6) if returns else None
    best_return = round(max(returns), 6) if returns else None
    worst_return = round(min(returns), 6) if returns else None
    pf = _profit_factor(returns)
    max_slip = round(max(slippage_values), 6) if slippage_values else None
    data_quality = round(((row_count - len(unsafe_rows)) / row_count) * 100, 6) if row_count else 0.0
    progress = round((unique_count / sample_target) * 100, 6) if sample_target else 0.0

    return LedgerMetrics(
        ledger_row_count=row_count,
        unique_observation_ids=unique_count,
        duplicate_observation_count=len(duplicate_ids),
        duplicate_observation_ids=sorted(set(duplicate_ids)),
        unsafe_row_count=len(unsafe_rows),
        unsafe_rows=unsafe_rows,
        matured_count=matured_count,
        win_count=win_count,
        loss_count=loss_count,
        win_rate_pct=win_rate,
        mean_return_bps=mean_return,
        median_return_bps=median_return,
        net_return_bps=net_return,
        profit_factor=pf,
        best_return_bps=best_return,
        worst_return_bps=worst_return,
        max_slippage_proxy_bps=max_slip,
        data_quality_pct=data_quality,
        sample_target=sample_target,
        sample_progress_pct=progress,
        sample_target_reached=unique_count >= sample_target,
        symbols_observed=sorted(symbols),
        symbols_observed_count=len(symbols),
        latest_observation_utc=max(timestamps) if timestamps else None,
        earliest_observation_utc=min(timestamps) if timestamps else None,
        observation_ids=sorted(seen),
    )


def _comparison_pass(value: float | int | None, operator: str, threshold: float) -> bool:
    if value is None:
        return False
    numeric = float(value)
    if operator == ">=":
        return numeric >= threshold
    if operator == ">":
        return numeric > threshold
    if operator == "<=":
        return numeric <= threshold
    if operator == "<":
        return numeric < threshold
    if operator == "==":
        return numeric == threshold
    raise ValueError(f"Unsupported operator: {operator}")


def _metric_values(metrics: LedgerMetrics) -> dict[str, float | int | None]:
    return {
        "min_shadow_sample_target": metrics.unique_observation_ids,
        "shadow_mean_forward_edge_bps": metrics.mean_return_bps,
        "shadow_median_forward_edge_bps": metrics.median_return_bps,
        "shadow_profit_factor": metrics.profit_factor,
        "shadow_walk_forward_positive_rate_pct": metrics.win_rate_pct,
        "shadow_data_quality_pct": metrics.data_quality_pct,
        "max_slippage_proxy_bps": metrics.max_slippage_proxy_bps,
    }


def _previous_metric_values(baseline_report: Mapping[str, Any] | None) -> dict[str, float | int | None]:
    report = _mapping(baseline_report)
    summary = _mapping(report.get("baseline_summary"))
    baseline = _mapping(report.get("acceptance_baseline_metrics"))
    values: dict[str, float | int | None] = {
        "min_shadow_sample_target": summary.get("unique_observation_ids"),
        "shadow_mean_forward_edge_bps": summary.get("mean_return_bps"),
        "shadow_median_forward_edge_bps": summary.get("median_return_bps"),
        "shadow_profit_factor": summary.get("profit_factor"),
        "shadow_walk_forward_positive_rate_pct": summary.get("win_rate_pct"),
        "shadow_data_quality_pct": summary.get("data_quality_pct"),
        "max_slippage_proxy_bps": summary.get("max_slippage_proxy_bps"),
    }
    for item in baseline.get("metric_results", []) if isinstance(baseline.get("metric_results"), list) else []:
        item_map = _mapping(item)
        name = item_map.get("name")
        if isinstance(name, str) and name not in values:
            values[name] = item_map.get("value")
    return values


def _numeric_delta(current: float | int | None, previous: float | int | None) -> float | int | None:
    current_float = _safe_float(current)
    previous_float = _safe_float(previous)
    if current_float is None or previous_float is None:
        return None
    result = round(current_float - previous_float, 6)
    if isinstance(current, int) and isinstance(previous, int):
        return int(result)
    return result


def compute_metric_results(metrics: LedgerMetrics, baseline_report: Mapping[str, Any] | None) -> list[MetricResult]:
    current = _metric_values(metrics)
    previous = _previous_metric_values(baseline_report)
    return [
        MetricResult(
            name=str(metric["name"]),
            operator=str(metric["operator"]),
            threshold=float(metric["threshold"]),
            value=current.get(str(metric["name"])),
            previous_value=previous.get(str(metric["name"])),
            delta=_numeric_delta(current.get(str(metric["name"])), previous.get(str(metric["name"]))),
            passed=_comparison_pass(current.get(str(metric["name"])), str(metric["operator"]), float(metric["threshold"])),
        )
        for metric in REQUIRED_METRICS
    ]


def compute_expansion_delta(metrics: LedgerMetrics, baseline_report: Mapping[str, Any] | None) -> ExpansionDelta:
    baseline = _mapping(baseline_report)
    previous_monitor = _mapping(baseline.get("no_order_continuity_monitor"))
    previous_summary = _mapping(baseline.get("baseline_summary"))
    previous_ids_raw = previous_monitor.get("observation_ids")
    previous_ids: set[str] = set()
    if isinstance(previous_ids_raw, list):
        previous_ids = {str(value) for value in previous_ids_raw}
    elif isinstance(baseline.get("cycle_shadow_summary"), Mapping):
        previous_ids = {str(value) for value in _mapping(baseline.get("cycle_shadow_summary")).get("sample_observation_ids", []) if value}

    # 28F did not emit full observation_ids; fallback to previous unique count for count delta.
    previous_unique = _safe_int(previous_summary.get("unique_observation_ids"), _safe_int(previous_monitor.get("unique_observation_ids"), 0))
    current_ids = set(metrics.observation_ids)
    new_ids = sorted(current_ids - previous_ids) if previous_ids else []
    removed_ids = sorted(previous_ids - current_ids) if previous_ids else []
    new_count = max(metrics.unique_observation_ids - previous_unique, len(new_ids))
    progress_prev = round((previous_unique / metrics.sample_target) * 100, 6) if metrics.sample_target else 0.0
    progress_delta = round(metrics.sample_progress_pct - progress_prev, 6)
    target_remaining = max(metrics.sample_target - metrics.unique_observation_ids, 0)
    return ExpansionDelta(
        previous_unique_observation_ids=previous_unique,
        current_unique_observation_ids=metrics.unique_observation_ids,
        new_unique_observation_count=new_count,
        target_remaining_count=target_remaining,
        sample_progress_delta_pct=progress_delta,
        new_observation_ids=new_ids[:50],
        removed_observation_ids=removed_ids[:50],
    )


def _failed_metric_codes(metric_results: Sequence[MetricResult]) -> list[str]:
    return [f"ACCEPTANCE_METRIC_FAILED_{result.name.upper()}" for result in metric_results if not result.passed]


def build_shadow_sample_expansion_report(
    *,
    baseline_report: Mapping[str, Any] | None,
    ledger_rows: Sequence[Mapping[str, Any]],
    source_paths: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    source_paths = dict(source_paths or {})
    baseline_ready = baseline_report_is_ready(baseline_report)
    metrics = compute_ledger_metrics(ledger_rows)
    delta = compute_expansion_delta(metrics, baseline_report)
    metric_results = compute_metric_results(metrics, baseline_report)
    metric_failures = _failed_metric_codes(metric_results)
    acceptance_requirements_met = all(result.passed for result in metric_results)

    blockers: list[str] = []
    if not baseline_ready:
        blockers.append("VALID_28F_OPERATOR_COCKPIT_BASELINE_NOT_FOUND")
    if metrics.duplicate_observation_count:
        blockers.append("DUPLICATE_OBSERVATION_IDS_PRESENT")
    if metrics.unsafe_row_count:
        blockers.append("UNSAFE_OR_NON_NO_ORDER_LEDGER_ROWS_PRESENT")
    if delta.new_unique_observation_count <= 0:
        blockers.append("NO_NEW_SHADOW_OBSERVATIONS_SINCE_28F_BASELINE")
    blockers.extend(metric_failures)
    if not metrics.sample_target_reached:
        blockers.append("SHADOW_SAMPLE_COUNT_BELOW_TARGET")
    if not acceptance_requirements_met:
        blockers.append("ACCEPTANCE_TRACKING_REQUIREMENTS_NOT_MET")
    blockers.append("PAPER_LIVE_TRAINING_RELOAD_ORDER_ENABLEMENT_NOT_PRESENT")

    hard_ok = bool(baseline_ready and metrics.duplicate_observation_count == 0 and metrics.unsafe_row_count == 0)
    next_gate = DEFAULT_NEXT_GATE if acceptance_requirements_met else DEFAULT_REPEAT_GATE
    display_state = "NO_ORDER_SHADOW_ACCEPTANCE_TRACKING_MATURED_REVIEW_REQUIRED" if acceptance_requirements_met else "NO_ORDER_SHADOW_SAMPLE_EXPANSION_ACTIVE_ACCEPTANCE_INCOMPLETE"

    dashboard_delta = {
        "contract_version": CONTRACT_VERSION,
        "dashboard_delta_version": "HYP-006-R1-DASHBOARD-DELTA-001",
        "generated_at_utc": utc_now_iso(),
        "hypothesis_id": HYPOTHESIS_ID,
        "branch_id": BRANCH_ID,
        "branch_name": BRANCH_NAME,
        "strategy_family": STRATEGY_FAMILY,
        "operator_cockpit_visibility": True,
        "display_state": display_state,
        "read_only": True,
        "no_order_shadow_only": True,
        "sample_expansion": asdict(delta),
        "acceptance_tracking": {
            "acceptance_requirements_met": acceptance_requirements_met,
            "sample_target": metrics.sample_target,
            "sample_target_reached": metrics.sample_target_reached,
            "sample_progress_pct": metrics.sample_progress_pct,
            "unique_observation_ids": metrics.unique_observation_ids,
            "mean_return_bps": metrics.mean_return_bps,
            "median_return_bps": metrics.median_return_bps,
            "profit_factor": metrics.profit_factor,
            "win_rate_pct": metrics.win_rate_pct,
            "failed_metric_codes": metric_failures,
        },
        "gate_status": {
            "approved_for_shadow_collection_continuity": True,
            "approved_for_acceptance_tracking": True,
            "approved_for_acceptance_review_candidate": acceptance_requirements_met,
            "approved_for_paper_candidate": False,
            "approved_for_live_real": False,
            "approved_for_training_candidate": False,
            "order_actions_allowed": False,
            "next_required_gate": next_gate,
        },
        "risk_banner": "NO_ORDER_SHADOW_ONLY__PAPER_LIVE_TRAINING_RELOAD_ORDER_BLOCKED",
        "source_paths": source_paths,
    }

    return {
        "contract_version": CONTRACT_VERSION,
        "report_type": "hyp006_r1_shadow_sample_expansion_acceptance_tracking_operator_cockpit_continuity_delta_evidence",
        "decision": "HYP006_R1_SHADOW_SAMPLE_EXPANSION_ACCEPTANCE_TRACKING_READY" if hard_ok else "HYP006_R1_SHADOW_SAMPLE_EXPANSION_ACCEPTANCE_TRACKING_BLOCKED",
        "ok": hard_ok,
        "generated_at_utc": utc_now_iso(),
        "hypothesis_id": HYPOTHESIS_ID,
        "branch_id": BRANCH_ID,
        "branch_name": BRANCH_NAME,
        "strategy_family": STRATEGY_FAMILY,
        "source_baseline_contract_version": _mapping(baseline_report).get("contract_version"),
        "source_baseline_decision": _mapping(baseline_report).get("decision"),
        "sample_expansion_tracking_ready": hard_ok,
        "acceptance_tracking_ready": hard_ok,
        "operator_cockpit_continuity_delta_ready": hard_ok,
        "approved_for_shadow_collection_continuity": True,
        "approved_for_acceptance_tracking": True,
        "approved_for_acceptance_review_candidate": bool(acceptance_requirements_met and hard_ok),
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "approved_for_training_candidate": False,
        "paper_transition_candidate_found": False,
        "order_actions_performed": False,
        "trading_action_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "post_requests_allowed": False,
        "network_request_performed": False,
        "read_only": True,
        "config_mutation_performed": False,
        "scheduler_mutation_performed": False,
        "scheduler_task_created": False,
        "scheduler_task_modified": False,
        "branch_state_mutation_performed": False,
        "strategy_parameter_mutation_performed": False,
        "next_required_gate": next_gate,
        "sample_expansion_delta": asdict(delta),
        "baseline_summary": {
            "ledger_row_count": metrics.ledger_row_count,
            "unique_observation_ids": metrics.unique_observation_ids,
            "matured_count": metrics.matured_count,
            "win_count": metrics.win_count,
            "loss_count": metrics.loss_count,
            "win_rate_pct": metrics.win_rate_pct,
            "mean_return_bps": metrics.mean_return_bps,
            "median_return_bps": metrics.median_return_bps,
            "net_return_bps": metrics.net_return_bps,
            "profit_factor": metrics.profit_factor,
            "best_return_bps": metrics.best_return_bps,
            "worst_return_bps": metrics.worst_return_bps,
            "max_slippage_proxy_bps": metrics.max_slippage_proxy_bps,
            "data_quality_pct": metrics.data_quality_pct,
        },
        "acceptance_tracking_metrics": {
            "required_metrics": [dict(metric) for metric in REQUIRED_METRICS],
            "metric_results": [asdict(result) for result in metric_results],
            "acceptance_requirements_met": acceptance_requirements_met,
            "failed_metric_codes": metric_failures,
            "sample_target": metrics.sample_target,
            "sample_progress_pct": metrics.sample_progress_pct,
            "sample_target_reached": metrics.sample_target_reached,
            "paper_transition_candidate_found": False,
        },
        "operator_cockpit_continuity_delta": {
            "ledger_row_count": metrics.ledger_row_count,
            "unique_observation_ids": metrics.unique_observation_ids,
            "duplicate_observation_count": metrics.duplicate_observation_count,
            "duplicate_observation_ids": metrics.duplicate_observation_ids,
            "unsafe_row_count": metrics.unsafe_row_count,
            "unsafe_rows": metrics.unsafe_rows,
            "no_order_rows_ok": metrics.unsafe_row_count == 0,
            "symbols_observed": metrics.symbols_observed,
            "symbols_observed_count": metrics.symbols_observed_count,
            "earliest_observation_utc": metrics.earliest_observation_utc,
            "latest_observation_utc": metrics.latest_observation_utc,
            "new_unique_observation_count": delta.new_unique_observation_count,
            "target_remaining_count": delta.target_remaining_count,
        },
        "dashboard_delta_seed": dashboard_delta,
        "blockers": sorted(set(blockers)),
        "reason_codes": [
            "HYP006_R1_SHADOW_SAMPLE_EXPANSION_TRACKING",
            "ACCEPTANCE_TRACKING_METRICS_COMPUTED",
            "OPERATOR_COCKPIT_CONTINUITY_DELTA_EVIDENCE",
            "PAPER_LIVE_GATES_REMAIN_CLOSED",
            "NO_TRAINING_RELOAD_ORDER_ENABLEMENT",
        ],
        "warnings": ["28H_REQUIRED_BEFORE_ANY_PAPER_TRANSITION_CANDIDACY"],
        "risk_items": [
            {"level": "critical", "code": "NO_ORDER_SHADOW_ONLY", "detail": "28G tracks shadow samples only; it does not approve trading."},
            {"level": "warning", "code": "ACCEPTANCE_REVIEW_SEPARATE_GATE", "detail": "Even if metrics mature, paper/live remain blocked until a separate review gate."},
            {"level": "warning", "code": "SHORT_SIDE_COSTS_STILL_UNMODELED", "detail": "Funding, liquidation, execution cost, and adverse selection remain outside this tracking report."},
        ],
        "recommendation": "Continue no-order HYP-006-R1 shadow sample expansion. Do not train, reload, paper trade, live trade, or send orders.",
        "source_paths": source_paths,
    }


def write_markdown(path: str | os.PathLike[str], payload: Mapping[str, Any]) -> None:
    summary = _mapping(payload.get("baseline_summary"))
    delta = _mapping(payload.get("sample_expansion_delta"))
    acceptance = _mapping(payload.get("acceptance_tracking_metrics"))
    lines = [
        "# HYP-006-R1 Shadow Sample Expansion / Acceptance Tracking",
        "",
        f"Contract: `{payload.get('contract_version')}`",
        f"Decision: `{payload.get('decision')}`",
        f"Generated: `{payload.get('generated_at_utc')}`",
        "",
        "## Delta",
        f"- Previous unique: `{delta.get('previous_unique_observation_ids')}`",
        f"- Current unique: `{delta.get('current_unique_observation_ids')}`",
        f"- New unique: `{delta.get('new_unique_observation_count')}`",
        f"- Target remaining: `{delta.get('target_remaining_count')}`",
        "",
        "## Acceptance Tracking",
        f"- Requirements met: `{acceptance.get('acceptance_requirements_met')}`",
        f"- Sample progress: `{acceptance.get('sample_progress_pct')}`",
        f"- Mean bps: `{summary.get('mean_return_bps')}`",
        f"- Median bps: `{summary.get('median_return_bps')}`",
        f"- Profit factor: `{summary.get('profit_factor')}`",
        f"- Win rate: `{summary.get('win_rate_pct')}`",
        "",
        "## Blockers",
    ]
    lines.extend(f"- `{item}`" for item in payload.get("blockers", []))
    lines.extend(["", "## Risk", "Paper/live/training/reload/order remain blocked.", ""])
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def write_report_bundle(payload: Mapping[str, Any], out_dir: str | os.PathLike[str]) -> tuple[Path, Path, Path, Path, Path]:
    target_dir = Path(out_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_json = target_dir / f"{REPORT_PREFIX}_{stamp}.json"
    acceptance_json = target_dir / f"{ACCEPTANCE_DELTA_PREFIX}_{stamp}.json"
    continuity_json = target_dir / f"{CONTINUITY_DELTA_PREFIX}_{stamp}.json"
    dashboard_json = target_dir / f"{DASHBOARD_DELTA_PREFIX}_{stamp}.json"
    report_md = target_dir / f"{REPORT_PREFIX}_{stamp}.md"
    write_json_atomic(report_json, payload)
    write_json_atomic(acceptance_json, payload.get("acceptance_tracking_metrics", {}))
    write_json_atomic(continuity_json, payload.get("operator_cockpit_continuity_delta", {}))
    write_json_atomic(dashboard_json, payload.get("dashboard_delta_seed", {}))
    write_markdown(report_md, payload)
    return report_json, acceptance_json, continuity_json, dashboard_json, report_md
