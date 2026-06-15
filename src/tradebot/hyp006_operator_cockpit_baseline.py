from __future__ import annotations

import json
import math
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median
from typing import Any, Iterable, Mapping, Sequence

CONTRACT_VERSION = "4B.4.3.6.6.28F"
SOURCE_HEALTH_CONTRACT_VERSION = "4B.4.3.6.6.28E"
BRANCH_ID = "HYP-006-R1"
HYPOTHESIS_ID = "HYP-006"
BRANCH_NAME = "failed_downside_sweep_reversal_continuation_short"
STRATEGY_FAMILY = "short_failed_liquidity_sweep_continuation"
REPORT_PREFIX = "4B436628F_hyp006_r1_operator_cockpit_baseline"
DASHBOARD_SEED_PREFIX = "4B436628F_hyp006_r1_operator_cockpit_dashboard_seed"
ACCEPTANCE_BASELINE_PREFIX = "4B436628F_hyp006_r1_acceptance_baseline_metrics"
CONTINUITY_MONITOR_PREFIX = "4B436628F_hyp006_r1_no_order_continuity_monitor"
NEXT_REQUIRED_GATE = "28G_HYP006_SHADOW_SAMPLE_EXPANSION_AND_ACCEPTANCE_TRACKING"

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
    passed: bool


@dataclass(frozen=True)
class BaselineComputation:
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
    metric_results: list[MetricResult]
    acceptance_requirements_met: bool


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _sequence(value: Any) -> Sequence[Any]:
    return value if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)) else []


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


def health_report_is_ready(report: Mapping[str, Any] | None) -> bool:
    payload = _mapping(report)
    return bool(
        payload.get("contract_version") == SOURCE_HEALTH_CONTRACT_VERSION
        and payload.get("decision") == "HYP006_R1_CANONICAL_SHADOW_SCHEDULER_EXECUTION_HEALTH_READY"
        and payload.get("ok") is True
        and payload.get("branch_id") == BRANCH_ID
        and payload.get("approved_for_shadow_collection_continuity") is True
        and payload.get("approved_for_paper_candidate") is False
        and payload.get("approved_for_live_real") is False
        and payload.get("order_actions_performed") is False
        and payload.get("training_performed") is False
        and payload.get("reload_performed") is False
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


def _profit_factor(returns: Sequence[float]) -> float | None:
    gross_profit = sum(value for value in returns if value > 0)
    gross_loss = abs(sum(value for value in returns if value < 0))
    if gross_profit <= 0 and gross_loss <= 0:
        return None
    if gross_loss <= 0:
        return round(float("inf"), 6)
    return round(gross_profit / gross_loss, 6)


def compute_acceptance_baseline(rows: Sequence[Mapping[str, Any]], *, sample_target: int = 30) -> BaselineComputation:
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

    values: dict[str, float | int | None] = {
        "min_shadow_sample_target": unique_count,
        "shadow_mean_forward_edge_bps": mean_return,
        "shadow_median_forward_edge_bps": median_return,
        "shadow_profit_factor": pf,
        "shadow_walk_forward_positive_rate_pct": win_rate,
        "shadow_data_quality_pct": data_quality,
        "max_slippage_proxy_bps": max_slip,
    }
    metric_results = [
        MetricResult(
            name=str(metric["name"]),
            operator=str(metric["operator"]),
            threshold=float(metric["threshold"]),
            value=values.get(str(metric["name"])),
            passed=_comparison_pass(values.get(str(metric["name"])), str(metric["operator"]), float(metric["threshold"])),
        )
        for metric in REQUIRED_METRICS
    ]

    return BaselineComputation(
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
        metric_results=metric_results,
        acceptance_requirements_met=all(result.passed for result in metric_results),
    )


def _metric_dicts(computation: BaselineComputation) -> list[dict[str, Any]]:
    return [asdict(result) for result in computation.metric_results]


def _failed_metric_codes(computation: BaselineComputation) -> list[str]:
    return [f"ACCEPTANCE_METRIC_FAILED_{result.name.upper()}" for result in computation.metric_results if not result.passed]


def build_dashboard_seed(
    *,
    health_report: Mapping[str, Any] | None,
    computation: BaselineComputation,
    source_paths: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    health = _mapping(health_report)
    scheduler_health = _mapping(health.get("scheduler_task_health"))
    return {
        "contract_version": CONTRACT_VERSION,
        "dashboard_seed_version": "HYP-006-R1-DASHBOARD-SEED-001",
        "generated_at_utc": utc_now_iso(),
        "hypothesis_id": HYPOTHESIS_ID,
        "branch_id": BRANCH_ID,
        "branch_name": BRANCH_NAME,
        "strategy_family": STRATEGY_FAMILY,
        "operator_cockpit_visibility": True,
        "display_state": "NO_ORDER_SHADOW_COLLECTION_ACTIVE_BASELINE_INCOMPLETE",
        "read_only": True,
        "no_order_shadow_only": True,
        "scheduler": {
            "task_name": scheduler_health.get("task_name", "TradeBot_HYP006_R1_Canonical_NoOrderShadowCollection"),
            "state": scheduler_health.get("state"),
            "last_task_result": scheduler_health.get("last_task_result"),
            "number_of_missed_runs": scheduler_health.get("number_of_missed_runs"),
            "last_run_time": scheduler_health.get("last_run_time"),
            "next_run_time": scheduler_health.get("next_run_time"),
            "health_ready": _mapping(health.get("scheduler_task_health_validation")).get("ok") is True,
        },
        "acceptance_baseline": {
            "sample_target": computation.sample_target,
            "unique_observation_ids": computation.unique_observation_ids,
            "sample_progress_pct": computation.sample_progress_pct,
            "sample_target_reached": computation.sample_target_reached,
            "acceptance_requirements_met": computation.acceptance_requirements_met,
            "mean_return_bps": computation.mean_return_bps,
            "median_return_bps": computation.median_return_bps,
            "profit_factor": computation.profit_factor,
            "win_rate_pct": computation.win_rate_pct,
            "duplicate_observation_count": computation.duplicate_observation_count,
        },
        "gate_status": {
            "approved_for_shadow_collection_continuity": True,
            "approved_for_acceptance_tracking": True,
            "approved_for_paper_candidate": False,
            "approved_for_live_real": False,
            "approved_for_training_candidate": False,
            "order_actions_allowed": False,
            "next_required_gate": NEXT_REQUIRED_GATE,
        },
        "risk_banner": "NO_ORDER_SHADOW_ONLY__PAPER_LIVE_TRAINING_RELOAD_ORDER_BLOCKED",
        "source_paths": dict(source_paths or {}),
    }


def build_acceptance_baseline_report(
    *,
    health_report: Mapping[str, Any] | None,
    ledger_rows: Sequence[Mapping[str, Any]],
    source_paths: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    source_paths = dict(source_paths or {})
    health_ready = health_report_is_ready(health_report)
    computation = compute_acceptance_baseline(ledger_rows)
    dashboard_seed = build_dashboard_seed(health_report=health_report, computation=computation, source_paths=source_paths)
    metric_failures = _failed_metric_codes(computation)
    blockers: list[str] = []
    if not health_ready:
        blockers.append("VALID_28E_SCHEDULER_HEALTH_EVIDENCE_NOT_FOUND")
    if computation.duplicate_observation_count:
        blockers.append("DUPLICATE_OBSERVATION_IDS_PRESENT")
    if computation.unsafe_row_count:
        blockers.append("UNSAFE_OR_NON_NO_ORDER_LEDGER_ROWS_PRESENT")
    blockers.extend(metric_failures)
    if not computation.sample_target_reached:
        blockers.append("SHADOW_SAMPLE_COUNT_BELOW_TARGET")
    if not computation.acceptance_requirements_met:
        blockers.append("ACCEPTANCE_BASELINE_REQUIREMENTS_NOT_MET")
    blockers.append("PAPER_LIVE_TRAINING_RELOAD_ORDER_ENABLEMENT_NOT_PRESENT")

    ok = bool(health_ready and computation.duplicate_observation_count == 0 and computation.unsafe_row_count == 0)
    return {
        "contract_version": CONTRACT_VERSION,
        "report_type": "hyp006_r1_shadow_operator_cockpit_dashboard_seed_acceptance_baseline_no_order_continuity_monitor",
        "decision": "HYP006_R1_SHADOW_OPERATOR_COCKPIT_BASELINE_READY" if ok else "HYP006_R1_SHADOW_OPERATOR_COCKPIT_BASELINE_BLOCKED",
        "ok": ok,
        "generated_at_utc": utc_now_iso(),
        "hypothesis_id": HYPOTHESIS_ID,
        "branch_id": BRANCH_ID,
        "branch_name": BRANCH_NAME,
        "strategy_family": STRATEGY_FAMILY,
        "source_health_contract_version": _mapping(health_report).get("contract_version"),
        "source_health_decision": _mapping(health_report).get("decision"),
        "dashboard_seed_ready": ok,
        "acceptance_baseline_ready": ok,
        "no_order_continuity_monitor_ready": ok,
        "operator_cockpit_visibility_seed_ready": ok,
        "dashboard_seed": dashboard_seed,
        "acceptance_baseline_metrics": {
            "required_metrics": [dict(metric) for metric in REQUIRED_METRICS],
            "metric_results": _metric_dicts(computation),
            "acceptance_requirements_met": computation.acceptance_requirements_met,
            "failed_metric_codes": metric_failures,
            "sample_target": computation.sample_target,
            "sample_progress_pct": computation.sample_progress_pct,
            "sample_target_reached": computation.sample_target_reached,
            "paper_transition_candidate_found": False,
        },
        "no_order_continuity_monitor": {
            "ledger_row_count": computation.ledger_row_count,
            "unique_observation_ids": computation.unique_observation_ids,
            "duplicate_observation_count": computation.duplicate_observation_count,
            "duplicate_observation_ids": computation.duplicate_observation_ids,
            "unsafe_row_count": computation.unsafe_row_count,
            "unsafe_rows": computation.unsafe_rows,
            "no_order_rows_ok": computation.unsafe_row_count == 0,
            "symbols_observed": computation.symbols_observed,
            "symbols_observed_count": computation.symbols_observed_count,
            "earliest_observation_utc": computation.earliest_observation_utc,
            "latest_observation_utc": computation.latest_observation_utc,
            "scheduler_last_task_result": _mapping(_mapping(health_report).get("scheduler_task_health")).get("last_task_result"),
            "scheduler_number_of_missed_runs": _mapping(_mapping(health_report).get("scheduler_task_health")).get("number_of_missed_runs"),
        },
        "baseline_summary": {
            "ledger_row_count": computation.ledger_row_count,
            "unique_observation_ids": computation.unique_observation_ids,
            "matured_count": computation.matured_count,
            "win_count": computation.win_count,
            "loss_count": computation.loss_count,
            "win_rate_pct": computation.win_rate_pct,
            "mean_return_bps": computation.mean_return_bps,
            "median_return_bps": computation.median_return_bps,
            "net_return_bps": computation.net_return_bps,
            "profit_factor": computation.profit_factor,
            "best_return_bps": computation.best_return_bps,
            "worst_return_bps": computation.worst_return_bps,
            "max_slippage_proxy_bps": computation.max_slippage_proxy_bps,
            "data_quality_pct": computation.data_quality_pct,
        },
        "blockers": sorted(set(blockers)),
        "reason_codes": [
            "HYP006_R1_SHADOW_OPERATOR_COCKPIT_DASHBOARD_SEED",
            "ACCEPTANCE_BASELINE_METRICS_COMPUTED",
            "NO_ORDER_CONTINUITY_MONITOR_READY",
            "PAPER_LIVE_GATES_REMAIN_CLOSED",
            "NO_TRAINING_RELOAD_ORDER_ENABLEMENT",
        ],
        "risk_items": [
            {"level": "critical", "code": "NO_ORDER_SHADOW_ONLY", "detail": "28F exposes HYP-006-R1 in operator cockpit only; it does not approve trading."},
            {"level": "warning", "code": "ACCEPTANCE_SAMPLE_INCOMPLETE", "detail": "Minimum sample target remains 30 observations before acceptance can be considered."},
            {"level": "warning", "code": "PAPER_LIVE_STILL_BLOCKED", "detail": "Paper/live/training/reload/order gates remain explicitly false."},
        ],
        "recommendation": "Continue no-order HYP-006-R1 shadow collection. Do not train, reload, paper trade, live trade, or send orders.",
        "source_paths": source_paths,
        "read_only": True,
        "post_requests_allowed": False,
        "network_request_performed": False,
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
        "approved_for_shadow_collection_continuity": ok,
        "approved_for_acceptance_tracking": ok,
        "approved_for_training_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "paper_transition_candidate_found": False,
        "next_required_gate": NEXT_REQUIRED_GATE,
        "warnings": ["28G_REQUIRED_BEFORE_ACCEPTANCE_EXPANSION_OR_PAPER_TRANSITION_CANDIDACY"],
    }


def write_markdown(path: str | os.PathLike[str], payload: Mapping[str, Any]) -> None:
    summary = _mapping(payload.get("baseline_summary"))
    baseline = _mapping(payload.get("acceptance_baseline_metrics"))
    lines = [
        "# 4B.4.3.6.6.28F HYP-006-R1 Operator Cockpit Baseline",
        "",
        f"- decision: `{payload.get('decision')}`",
        f"- branch_id: `{payload.get('branch_id')}`",
        f"- dashboard_seed_ready: `{payload.get('dashboard_seed_ready')}`",
        f"- no_order_continuity_monitor_ready: `{payload.get('no_order_continuity_monitor_ready')}`",
        f"- acceptance_requirements_met: `{baseline.get('acceptance_requirements_met')}`",
        f"- ledger_row_count: `{summary.get('ledger_row_count')}`",
        f"- unique_observation_ids: `{summary.get('unique_observation_ids')}`",
        f"- mean_return_bps: `{summary.get('mean_return_bps')}`",
        f"- profit_factor: `{summary.get('profit_factor')}`",
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


def write_report_bundle(payload: Mapping[str, Any], out_dir: str | os.PathLike[str]) -> tuple[Path, Path, Path, Path, Path]:
    target_dir = Path(out_dir)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_json = target_dir / f"{REPORT_PREFIX}_{stamp}.json"
    dashboard_json = target_dir / f"{DASHBOARD_SEED_PREFIX}_{stamp}.json"
    acceptance_json = target_dir / f"{ACCEPTANCE_BASELINE_PREFIX}_{stamp}.json"
    continuity_json = target_dir / f"{CONTINUITY_MONITOR_PREFIX}_{stamp}.json"
    report_md = target_dir / f"{REPORT_PREFIX}_{stamp}.md"
    write_json_atomic(report_json, payload)
    write_json_atomic(dashboard_json, payload.get("dashboard_seed", {}))
    write_json_atomic(acceptance_json, payload.get("acceptance_baseline_metrics", {}))
    write_json_atomic(continuity_json, payload.get("no_order_continuity_monitor", {}))
    write_markdown(report_md, payload)
    return report_json, dashboard_json, acceptance_json, continuity_json, report_md
