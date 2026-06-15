from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median
from typing import Any, Mapping, Sequence

OPERATOR_COCKPIT_HYP006_BINDING_VERSION = "4B.4.3.6.6.28F-H2"
BRANCH_ID = "HYP-006-R1"
HYPOTHESIS_ID = "HYP-006"
FRESH_LEDGER_NAMESPACE = "HYP006_R1"
BRANCH_NAME = "failed_downside_sweep_reversal_continuation_short"
STRATEGY_FAMILY = "short_failed_liquidity_sweep_continuation"
REPORTS_RELATIVE_DIR = Path("reports") / "hyp006_r1_canonical"
HYP006_SCHEDULER_TASK_NAME = "TradeBot_HYP006_R1_Canonical_NoOrderShadowCollection"

JsonObject = dict[str, Any]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _as_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(result) or math.isinf(result):
        return None
    return result


def _as_int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _read_json(path: Path | None) -> JsonObject:
    if path is None or not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _read_jsonl(path: Path | None) -> list[JsonObject]:
    if path is None or not path.exists():
        return []
    rows: list[JsonObject] = []
    try:
        text = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError):
        return []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            value = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            rows.append(value)
    return rows


def _latest_file(directory: Path, pattern: str) -> Path | None:
    if not directory.exists():
        return None
    candidates = [path for path in directory.glob(pattern) if path.is_file()]
    if not candidates:
        return None
    return max(candidates, key=lambda path: (path.stat().st_mtime_ns, path.name))


def _relative_or_name(path: Path | None, root: Path) -> str | None:
    if path is None:
        return None
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def _return_bps(row: Mapping[str, Any]) -> float | None:
    for key in ("forward_return_bps_final_short_probe", "forward_return_bps_final", "forward_return_bps"):
        value = _as_float(row.get(key))
        if value is not None:
            return value
    return None


def _profit_factor(values: Sequence[float]) -> float | None:
    gross_profit = sum(value for value in values if value > 0)
    gross_loss = abs(sum(value for value in values if value < 0))
    if gross_profit <= 0 and gross_loss <= 0:
        return None
    if gross_loss <= 0:
        return round(float("inf"), 6)
    return round(gross_profit / gross_loss, 6)


def _ledger_metrics(rows: Sequence[Mapping[str, Any]]) -> JsonObject:
    observation_ids: list[str] = []
    duplicate_ids: list[str] = []
    seen: set[str] = set()
    unsafe_rows: list[str] = []
    returns: list[float] = []
    symbols: set[str] = set()
    timestamps: list[str] = []
    slippages: list[float] = []

    for index, row in enumerate(rows):
        obs_id = str(row.get("observation_id") or f"row_{index}")
        observation_ids.append(obs_id)
        if obs_id in seen:
            duplicate_ids.append(obs_id)
        seen.add(obs_id)

        if row.get("branch_id") != BRANCH_ID or row.get("no_order_measurement_only") is not True:
            unsafe_rows.append(obs_id)

        ret = _return_bps(row)
        if ret is not None:
            returns.append(ret)

        slip = _as_float(row.get("spread_slippage_proxy_bps"))
        if slip is not None:
            slippages.append(slip)

        symbol = row.get("symbol")
        if isinstance(symbol, str) and symbol:
            symbols.add(symbol)
        timestamp = row.get("timestamp_utc")
        if isinstance(timestamp, str) and timestamp:
            timestamps.append(timestamp)

    row_count = len(rows)
    unique_count = len(seen)
    matured_count = len(returns)
    win_count = sum(1 for value in returns if value > 0)
    loss_count = sum(1 for value in returns if value < 0)
    return {
        "sample_count": unique_count,
        "matured_count": matured_count,
        "maturity_pending_count": max(row_count - matured_count, 0),
        "win_count": win_count,
        "loss_count": loss_count,
        "win_rate_pct": round(win_count / matured_count * 100, 6) if matured_count else None,
        "gross_profit_bps": round(sum(value for value in returns if value > 0), 6),
        "gross_loss_bps": round(abs(sum(value for value in returns if value < 0)), 6),
        "net_return_bps": round(sum(returns), 6) if returns else 0.0,
        "mean_return_bps": round(mean(returns), 6) if returns else None,
        "median_return_bps": round(median(returns), 6) if returns else None,
        "profit_factor": _profit_factor(returns),
        "worst_return_bps": round(min(returns), 6) if returns else None,
        "best_return_bps": round(max(returns), 6) if returns else None,
        "unique_observation_ids": unique_count,
        "ledger_row_count": row_count,
        "duplicate_observation_count": len(set(duplicate_ids)),
        "unsafe_row_count": len(unsafe_rows),
        "symbols_observed": sorted(symbols),
        "symbols_observed_count": len(symbols),
        "earliest_observation_utc": min(timestamps) if timestamps else None,
        "latest_observation_utc": max(timestamps) if timestamps else None,
        "max_slippage_proxy_bps": round(max(slippages), 6) if slippages else None,
        "data_quality_pct": round(((row_count - len(unsafe_rows)) / row_count) * 100, 6) if row_count else 0.0,
    }


def _recent_observations(rows: Sequence[Mapping[str, Any]], *, limit: int = 12) -> list[JsonObject]:
    ordered = sorted(rows, key=lambda row: str(row.get("timestamp_utc") or ""), reverse=True)
    output: list[JsonObject] = []
    for row in ordered[:limit]:
        output.append({
            "symbol": str(row.get("symbol") or "UNKNOWN"),
            "timestamp_utc": str(row.get("timestamp_utc") or ""),
            "spread_slippage_proxy_bps": _as_float(row.get("spread_slippage_proxy_bps")),
            "forward_return_bps_final": _return_bps(row),
            "observation_id": str(row.get("observation_id") or ""),
        })
    return output


def _symbol_distribution(rows: Sequence[Mapping[str, Any]]) -> list[JsonObject]:
    counts: dict[str, int] = {}
    for row in rows:
        symbol = str(row.get("symbol") or "UNKNOWN")
        counts[symbol] = counts.get(symbol, 0) + 1
    return [{"symbol": symbol, "count": count} for symbol, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))]


def _worst_cluster(rows: Sequence[Mapping[str, Any]]) -> JsonObject:
    buckets: dict[str, dict[str, Any]] = {}
    for row in rows:
        timestamp = str(row.get("timestamp_utc") or "UNKNOWN")
        ret = _return_bps(row) or 0.0
        bucket = buckets.setdefault(timestamp, {"timestamp_utc": timestamp, "net_return_bps": 0.0, "gross_loss_bps": 0.0, "symbols": set()})
        bucket["net_return_bps"] += ret
        if ret < 0:
            bucket["gross_loss_bps"] += abs(ret)
        symbol = row.get("symbol")
        if isinstance(symbol, str) and symbol:
            bucket["symbols"].add(symbol)
    if not buckets:
        return {"timestamp_utc": None, "net_return_bps": None, "gross_loss_share_pct": None, "symbols": []}
    total_loss = sum(value["gross_loss_bps"] for value in buckets.values())
    worst = max(buckets.values(), key=lambda item: item["gross_loss_bps"])
    return {
        "timestamp_utc": worst["timestamp_utc"],
        "net_return_bps": round(worst["net_return_bps"], 6),
        "gross_loss_share_pct": round((worst["gross_loss_bps"] / total_loss) * 100, 6) if total_loss else 0.0,
        "symbols": sorted(worst["symbols"]),
    }


def _sample_timeline(rows: Sequence[Mapping[str, Any]]) -> list[JsonObject]:
    ordered = sorted(rows, key=lambda row: str(row.get("timestamp_utc") or ""))
    output: list[JsonObject] = []
    cumulative = 0
    for row in ordered:
        cumulative += 1
        output.append({
            "timestamp_utc": row.get("timestamp_utc"),
            "sample_count": cumulative,
            "symbol": row.get("symbol"),
            "return_bps": _return_bps(row),
        })
    return output


def _return_distribution(rows: Sequence[Mapping[str, Any]]) -> list[JsonObject]:
    values = [value for row in rows if (value := _return_bps(row)) is not None]
    buckets = [(-1000, -500), (-500, -200), (-200, 0), (0, 200), (200, 500), (500, 1000)]
    output: list[JsonObject] = []
    for low, high in buckets:
        count = sum(1 for value in values if low <= value < high)
        output.append({"range": f"{low}..{high}", "low": low, "high": high, "count": count})
    return output


def _symbol_performance(rows: Sequence[Mapping[str, Any]]) -> list[JsonObject]:
    grouped: dict[str, list[float]] = {}
    for row in rows:
        symbol = str(row.get("symbol") or "UNKNOWN")
        ret = _return_bps(row)
        if ret is not None:
            grouped.setdefault(symbol, []).append(ret)
    output = []
    for symbol, values in grouped.items():
        output.append({
            "symbol": symbol,
            "sample_count": len(values),
            "net_return_bps": round(sum(values), 6),
            "mean_return_bps": round(mean(values), 6),
            "profit_factor": _profit_factor(values),
        })
    return sorted(output, key=lambda item: (-float(item.get("net_return_bps") or 0), str(item.get("symbol") or "")))


def _visualizations(rows: Sequence[Mapping[str, Any]], cluster: Mapping[str, Any]) -> JsonObject:
    return {
        "sample_timeline": _sample_timeline(rows),
        "return_distribution": _return_distribution(rows),
        "symbol_performance": _symbol_performance(rows),
        "timestamp_clusters": [dict(cluster)] if cluster else [],
        "slippage_observations": [
            {
                "symbol": row.get("symbol"),
                "timestamp_utc": row.get("timestamp_utc"),
                "spread_slippage_proxy_bps": _as_float(row.get("spread_slippage_proxy_bps")),
                "return_bps": _return_bps(row),
            }
            for row in rows
        ],
        "mae_mfe_scatter": [],
        "performance_comparison": [],
    }


def _latest_hyp006_artifacts(project_root: Path) -> JsonObject:
    reports_dir = project_root / REPORTS_RELATIVE_DIR
    return {
        "reports_dir": reports_dir,
        "latest_28g_tracking": _latest_file(reports_dir, "4B436628G_hyp006_r1_shadow_sample_expansion_acceptance_tracking_*.json"),
        "latest_28f_baseline": _latest_file(reports_dir, "4B436628F_hyp006_r1_operator_cockpit_baseline_*.json"),
        "latest_28f_dashboard_seed": _latest_file(reports_dir, "4B436628F_hyp006_r1_operator_cockpit_dashboard_seed_*.json"),
        "latest_28e_health": _latest_file(reports_dir, "4B436628E_hyp006_r1_scheduler_execution_health_verify_*.json"),
        "latest_28d_ledger": _latest_file(reports_dir, "4B436628D_hyp006_r1_shadow_ledger_*.jsonl"),
    }


def hyp006_binding_available(project_root: Path) -> bool:
    artifacts = _latest_hyp006_artifacts(project_root.resolve())
    tracking = _read_json(artifacts["latest_28g_tracking"])
    baseline = _read_json(artifacts["latest_28f_baseline"])
    return bool(
        tracking.get("branch_id") == BRANCH_ID
        and tracking.get("ok") is True
        and baseline.get("branch_id") == BRANCH_ID
        and baseline.get("ok") is True
    )


def apply_hyp006_operator_cockpit_binding(snapshot: Mapping[str, Any], project_root: Path) -> JsonObject:
    """Overlay latest HYP-006 no-order dashboard seed over legacy HYP-005 cockpit data."""
    root = project_root.resolve()
    artifacts = _latest_hyp006_artifacts(root)
    tracking = _read_json(artifacts["latest_28g_tracking"])
    baseline = _read_json(artifacts["latest_28f_baseline"])
    health = _read_json(artifacts["latest_28e_health"])
    ledger_rows = _read_jsonl(artifacts["latest_28d_ledger"])

    if tracking.get("branch_id") != BRANCH_ID or tracking.get("ok") is not True:
        return dict(snapshot)
    if baseline.get("branch_id") != BRANCH_ID or baseline.get("ok") is not True:
        return dict(snapshot)

    base = dict(snapshot)
    metrics = _ledger_metrics(ledger_rows)
    baseline_summary = dict(_mapping(tracking.get("baseline_summary")) or _mapping(baseline.get("baseline_summary")) or metrics)
    acceptance = dict(_mapping(tracking.get("acceptance_tracking_metrics")) or _mapping(baseline.get("acceptance_baseline_metrics")))
    sample_target = _as_int(acceptance.get("sample_target"), 30)
    sample_count = _as_int(metrics.get("unique_observation_ids"), _as_int(baseline_summary.get("unique_observation_ids"), 0))
    progress_pct = _as_float(acceptance.get("sample_progress_pct"))
    if progress_pct is None and sample_target:
        progress_pct = round((sample_count / sample_target) * 100, 6)

    scheduler_seed = _mapping(_mapping(baseline.get("dashboard_seed")).get("scheduler"))
    if not scheduler_seed:
        scheduler_seed = _mapping(_mapping(health.get("scheduler_task_health")))

    cluster = _worst_cluster(ledger_rows)
    risk_items = [
        {
            "level": "info",
            "code": "HYP006_ACTIVE_NO_ORDER_SHADOW",
            "title": "HYP-006-R1 aktif shadow branch",
            "detail": "Operator cockpit HYP-006 dashboard seed ve 28G delta evidence üzerinden görüntüleniyor.",
        },
        {
            "level": "warning",
            "code": "ACCEPTANCE_INCOMPLETE",
            "title": "Acceptance tamamlanmadı",
            "detail": f"{sample_count} / {sample_target} sample; paper/live/training/reload/order kapalı.",
        },
    ]
    for code in tracking.get("blockers") or []:
        risk_items.append({"level": "warning", "code": str(code), "title": str(code), "detail": "28G acceptance tracking blocker."})

    model = {
        "status": "HYP006_NO_MODEL_RELOAD_READ_ONLY",
        "file_name": "HYP-006-R1 no-order shadow research branch",
        "relative_path": None,
        "sha256": None,
        "size_bytes": None,
        "modified_utc": None,
    }

    sources = dict(_mapping(base.get("sources")))
    sources.update({
        "hyp006_reports_dir": _relative_or_name(artifacts["reports_dir"], root),
        "latest_28g_tracking": _relative_or_name(artifacts["latest_28g_tracking"], root),
        "latest_28f_baseline": _relative_or_name(artifacts["latest_28f_baseline"], root),
        "latest_28f_dashboard_seed": _relative_or_name(artifacts["latest_28f_dashboard_seed"], root),
        "latest_28e_health": _relative_or_name(artifacts["latest_28e_health"], root),
        "latest_hyp006_ledger": _relative_or_name(artifacts["latest_28d_ledger"], root),
        "legacy_hyp005_suppressed": True,
    })

    base.update({
        "contract_version": OPERATOR_COCKPIT_HYP006_BINDING_VERSION,
        "read_only": True,
        "generated_at_utc": _utc_now_iso(),
        "system_status": "WATCH" if tracking.get("blockers") else "HEALTHY",
        "mode": "SHADOW",
        "branch_id": BRANCH_ID,
        "branch_name": BRANCH_NAME,
        "hypothesis_id": HYPOTHESIS_ID,
        "strategy_family": STRATEGY_FAMILY,
        "fresh_ledger_namespace": FRESH_LEDGER_NAMESPACE,
        "operator_cockpit_active_binding": "HYP006_DASHBOARD_SEED_BINDING",
        "legacy_hyp005_panel_suppressed": True,
        "active_research_branch_display_parity_ok": True,
        "sources": sources,
        "scheduler": {
            "baseline_task": {"task_name": "TradeBot_HYP005_NoOrderShadowCollection", "state": "Disabled", "legacy_suppressed": True},
            "r1_task": {
                "task_name": scheduler_seed.get("task_name") or HYP006_SCHEDULER_TASK_NAME,
                "state": scheduler_seed.get("state") or "Ready",
                "last_run_time": scheduler_seed.get("last_run_time"),
                "last_task_result": scheduler_seed.get("last_task_result"),
                "next_run_time": scheduler_seed.get("next_run_time"),
                "number_of_missed_runs": scheduler_seed.get("number_of_missed_runs"),
                "hyp006_bound": True,
            },
        },
        "audit": {
            "decision": tracking.get("decision"),
            "dashboard_status": _mapping(tracking.get("dashboard_delta_seed")).get("display_state") or _mapping(baseline.get("dashboard_seed")).get("display_state"),
            "latest_logger_decision": tracking.get("source_baseline_decision") or baseline.get("source_health_decision"),
            "latest_collection_decision": tracking.get("decision"),
            "latest_acceptance_decision": "ACCEPTANCE_TRACKING_REQUIREMENTS_NOT_MET" if not acceptance.get("acceptance_requirements_met") else "ACCEPTANCE_TRACKING_METRICS_MET_REVIEW_REQUIRED",
            "shadow_observation_count": sample_count,
            "shadow_sample_target": sample_target,
            "progress_pct": progress_pct,
            "paper_transition_ready": False,
            "approved_for_acceptance_tracking": bool(tracking.get("approved_for_acceptance_tracking")),
            "approved_for_acceptance_review_candidate": bool(tracking.get("approved_for_acceptance_review_candidate")),
            "approved_for_paper_candidate": False,
            "approved_for_live_real": False,
            "post_requests_allowed": False,
            "order_actions_performed": False,
            "source_ledgers": 1 if artifacts["latest_28d_ledger"] else 0,
            "source_reports": sum(1 for key in ("latest_28g_tracking", "latest_28f_baseline", "latest_28e_health") if artifacts.get(key)),
            "blockers": list(tracking.get("blockers") or []),
        },
        "performance": {
            "sample_count": sample_count,
            "matured_count": _as_int(baseline_summary.get("matured_count"), _as_int(metrics.get("matured_count"), 0)),
            "maturity_pending_count": 0,
            "win_count": _as_int(baseline_summary.get("win_count"), _as_int(metrics.get("win_count"), 0)),
            "loss_count": _as_int(baseline_summary.get("loss_count"), _as_int(metrics.get("loss_count"), 0)),
            "win_rate_pct": _as_float(baseline_summary.get("win_rate_pct")) or metrics.get("win_rate_pct"),
            "gross_profit_bps": metrics.get("gross_profit_bps"),
            "gross_loss_bps": metrics.get("gross_loss_bps"),
            "net_return_bps": _as_float(baseline_summary.get("net_return_bps")) or metrics.get("net_return_bps"),
            "mean_return_bps": _as_float(baseline_summary.get("mean_return_bps")) or metrics.get("mean_return_bps"),
            "median_return_bps": _as_float(baseline_summary.get("median_return_bps")) or metrics.get("median_return_bps"),
            "profit_factor": _as_float(baseline_summary.get("profit_factor")) or metrics.get("profit_factor"),
            "worst_return_bps": _as_float(baseline_summary.get("worst_return_bps")) or metrics.get("worst_return_bps"),
            "best_return_bps": _as_float(baseline_summary.get("best_return_bps")) or metrics.get("best_return_bps"),
        },
        "worst_timestamp_cluster": cluster,
        "symbol_distribution": _symbol_distribution(ledger_rows),
        "recent_observations": _recent_observations(ledger_rows),
        "risk_items": risk_items,
        "activity_feed": [
            {"kind": "branch", "timestamp": None, "title": "Aktif branch", "detail": f"{BRANCH_ID} · {STRATEGY_FAMILY}"},
            {"kind": "sample", "timestamp": metrics.get("latest_observation_utc"), "title": "HYP-006 observation kümesi", "detail": f"{sample_count}/{sample_target} unique sample"},
            {"kind": "risk", "timestamp": None, "title": "Paper geçişi", "detail": "Kapalı — 28H+ ayrı gate gerekli"},
        ],
        "model": model,
        "visualizations": _visualizations(ledger_rows, cluster),
        "operator_guidance": "HYP-006-R1 no-order shadow sample expansion devam ediyor. 28H öncesi 30/30 sample ve acceptance metric olgunluğu gerekli.",
    })
    return base
