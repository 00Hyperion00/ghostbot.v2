from __future__ import annotations

import argparse
import json
import math
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

CONTRACT_VERSION = "4B.4.3.6.6.28G-H8"
SOURCE_H7_CONTRACT_VERSION = "4B.4.3.6.6.28G-H7"
REPORT_TYPE = "hyp006_r1_bnbusdt_overlay_out_of_sample_evaluation_runtime_activation_blocked_decision_pack"
REPORT_PREFIX = "4B436628G_H8_hyp006_r1_bnbusdt_overlay_oos_evaluation_runtime_activation_blocked_decision"
DEFAULT_REPORTS_DIR = "reports/hyp006_r1_canonical"
DEFAULT_H7_PATTERN = "4B436628G_H7_hyp006_r1_no_order_overlay_simulation_bnbusdt_primary_filter_shadow_measurement_*.json"
PRIMARY_SYMBOL = "BNBUSDT"
READY_DECISION = "HYP006_R1_BNBUSDT_OVERLAY_OOS_EVALUATION_READY_RUNTIME_ACTIVATION_BLOCKED"
BLOCKED_DECISION = "HYP006_R1_BNBUSDT_OVERLAY_OOS_EVALUATION_BLOCKED"

OOS_GUARDS = {
    "min_latest_matured_count": 13,
    "min_matured_count_delta": 1,
    "min_event_count_delta": 1,
    "min_win_rate_pct": 60.0,
    "min_profit_factor": 1.5,
    "min_mean_return_bps": 0.0,
    "min_worst_return_bps": -500.0,
    "min_worst_mae_bps": -500.0,
}

NUMERIC_SUMMARY_FIELDS = (
    "event_count",
    "matured_count",
    "win_rate_pct",
    "mean_return_bps",
    "median_return_bps",
    "profit_factor",
    "worst_return_bps",
    "worst_mae_bps",
    "net_return_bps",
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def safe_float(value: Any, default: float | None = None) -> float | None:
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


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _sequence(value: Any) -> Sequence[Any]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return value
    return []


def load_json(path: str | os.PathLike[str]) -> Any:
    with Path(path).open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


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


def latest_h7_artifacts(
    reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR,
    *,
    limit: int = 2,
) -> list[Path]:
    target = Path(reports_dir)
    matches = sorted(target.glob(DEFAULT_H7_PATTERN), key=lambda item: item.stat().st_mtime, reverse=True)
    return matches[:limit]


def _summary_from_h7(h7_artifact: Mapping[str, Any]) -> dict[str, Any]:
    summary = _mapping(h7_artifact.get("primary_measurement_summary"))
    candidate = _mapping(h7_artifact.get("primary_measurement_candidate"))
    symbol = str(summary.get("symbol") or candidate.get("measurement_symbol") or candidate.get("key") or "")
    result: dict[str, Any] = {
        "symbol": symbol,
        "measurement_candidate_present": bool(summary.get("measurement_candidate_present", bool(candidate))),
        "measurement_guard_pass": bool(summary.get("measurement_guard_pass", candidate.get("measurement_guard_pass", False))),
        "measurement_guard_reasons": list(_sequence(summary.get("measurement_guard_reasons") or candidate.get("measurement_guard_reasons"))),
    }
    for field in NUMERIC_SUMMARY_FIELDS:
        raw = summary.get(field, candidate.get(field))
        if field in {"event_count", "matured_count"}:
            result[field] = safe_int(raw)
        else:
            value = safe_float(raw)
            result[field] = round(value, 6) if value is not None else None
    return result


def _delta(latest: Mapping[str, Any], previous: Mapping[str, Any] | None) -> dict[str, Any]:
    if previous is None:
        return {
            "previous_measurement_present": False,
            "event_count_delta": None,
            "matured_count_delta": None,
            "win_rate_pct_delta": None,
            "mean_return_bps_delta": None,
            "median_return_bps_delta": None,
            "profit_factor_delta": None,
            "worst_return_bps_delta": None,
            "worst_mae_bps_delta": None,
            "net_return_bps_delta": None,
        }
    result: dict[str, Any] = {"previous_measurement_present": True}
    for field in NUMERIC_SUMMARY_FIELDS:
        latest_value = safe_float(latest.get(field))
        previous_value = safe_float(previous.get(field))
        if latest_value is None or previous_value is None:
            result[f"{field}_delta"] = None
            continue
        delta_value = latest_value - previous_value
        if field in {"event_count", "matured_count"}:
            result[f"{field}_delta"] = int(round(delta_value))
        else:
            result[f"{field}_delta"] = round(delta_value, 6)
    return result


def _source_safety_blockers(h7_artifact: Mapping[str, Any], *, label: str) -> list[str]:
    blockers: list[str] = []
    prefix = label.upper()
    if h7_artifact.get("contract_version") != SOURCE_H7_CONTRACT_VERSION:
        blockers.append(f"{prefix}_SOURCE_H7_CONTRACT_VERSION_MISMATCH")
    if not h7_artifact.get("read_only", False):
        blockers.append(f"{prefix}_SOURCE_H7_NOT_READ_ONLY")
    if not h7_artifact.get("overlay_simulation_measurement_only", False):
        blockers.append(f"{prefix}_SOURCE_H7_NOT_MEASUREMENT_ONLY")
    if h7_artifact.get("runtime_overlay_activation_performed") is not False:
        blockers.append(f"{prefix}_SOURCE_H7_RUNTIME_OVERLAY_ACTIVATION_ALREADY_PERFORMED")
    if h7_artifact.get("approved_for_runtime_overlay_activation_candidate") is not False:
        blockers.append(f"{prefix}_SOURCE_H7_RUNTIME_OVERLAY_GATE_NOT_CLOSED")
    if h7_artifact.get("approved_for_parameter_relaxation_candidate") is not False:
        blockers.append(f"{prefix}_SOURCE_H7_PARAMETER_RELAXATION_GATE_NOT_CLOSED")
    if h7_artifact.get("approved_for_paper_candidate") is not False or h7_artifact.get("approved_for_live_real") is not False:
        blockers.append(f"{prefix}_SOURCE_H7_TRADING_GATE_NOT_CLOSED")
    if h7_artifact.get("training_performed") is not False or h7_artifact.get("reload_performed") is not False:
        blockers.append(f"{prefix}_SOURCE_H7_TRAINING_OR_RELOAD_OCCURRED")
    if h7_artifact.get("trading_action_performed") is not False or h7_artifact.get("order_actions_performed") is not False:
        blockers.append(f"{prefix}_SOURCE_H7_ORDER_ACTION_OCCURRED")
    return blockers


def _oos_guard_reasons(latest: Mapping[str, Any], delta_summary: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    if str(latest.get("symbol") or "").upper() != PRIMARY_SYMBOL:
        reasons.append("LATEST_SYMBOL_NOT_BNBUSDT")
    if not bool(latest.get("measurement_candidate_present")):
        reasons.append("LATEST_MEASUREMENT_CANDIDATE_MISSING")
    if not bool(latest.get("measurement_guard_pass")):
        reasons.append("LATEST_H7_MEASUREMENT_GUARD_FAILED")
    if safe_int(latest.get("matured_count")) < int(OOS_GUARDS["min_latest_matured_count"]):
        reasons.append("LATEST_MATURED_COUNT_BELOW_OOS_MIN")
    if safe_int(delta_summary.get("matured_count_delta"), default=-999) < int(OOS_GUARDS["min_matured_count_delta"]):
        reasons.append("MATURED_COUNT_DELTA_BELOW_OOS_MIN")
    if safe_int(delta_summary.get("event_count_delta"), default=-999) < int(OOS_GUARDS["min_event_count_delta"]):
        reasons.append("EVENT_COUNT_DELTA_BELOW_OOS_MIN")
    if (safe_float(latest.get("win_rate_pct"), 0.0) or 0.0) < float(OOS_GUARDS["min_win_rate_pct"]):
        reasons.append("WIN_RATE_BELOW_OOS_MIN")
    if (safe_float(latest.get("profit_factor"), 0.0) or 0.0) < float(OOS_GUARDS["min_profit_factor"]):
        reasons.append("PROFIT_FACTOR_BELOW_OOS_MIN")
    if (safe_float(latest.get("mean_return_bps"), 0.0) or 0.0) <= float(OOS_GUARDS["min_mean_return_bps"]):
        reasons.append("MEAN_RETURN_NOT_POSITIVE")
    if (safe_float(latest.get("worst_return_bps"), 0.0) or 0.0) <= float(OOS_GUARDS["min_worst_return_bps"]):
        reasons.append("WORST_RETURN_BELOW_OOS_TAIL_LIMIT")
    if (safe_float(latest.get("worst_mae_bps"), 0.0) or 0.0) <= float(OOS_GUARDS["min_worst_mae_bps"]):
        reasons.append("WORST_MAE_BELOW_OOS_TAIL_LIMIT")
    if _sequence(latest.get("measurement_guard_reasons")):
        reasons.append("LATEST_H7_MEASUREMENT_GUARD_REASONS_PRESENT")
    return reasons


def _tail_risk_assessment(latest: Mapping[str, Any], previous: Mapping[str, Any] | None, delta_summary: Mapping[str, Any]) -> dict[str, Any]:
    latest_worst_return = safe_float(latest.get("worst_return_bps"), 0.0) or 0.0
    latest_worst_mae = safe_float(latest.get("worst_mae_bps"), 0.0) or 0.0
    reasons: list[str] = []
    if latest_worst_return <= -350.0:
        reasons.append("WORST_RETURN_MONITORING_REQUIRED")
    if latest_worst_mae <= -400.0:
        reasons.append("WORST_MAE_MONITORING_REQUIRED")
    if previous is not None:
        worst_return_delta = safe_float(delta_summary.get("worst_return_bps_delta"), 0.0) or 0.0
        worst_mae_delta = safe_float(delta_summary.get("worst_mae_bps_delta"), 0.0) or 0.0
        if worst_return_delta < 0.0:
            reasons.append("WORST_RETURN_DETERIORATED")
        if worst_mae_delta < 0.0:
            reasons.append("WORST_MAE_DETERIORATED")
    return {
        "tail_risk_monitoring_required": bool(reasons),
        "tail_risk_reasons": reasons,
        "latest_worst_return_bps": round(latest_worst_return, 6),
        "latest_worst_mae_bps": round(latest_worst_mae, 6),
    }


def build_bnbusdt_overlay_oos_evaluation_report(
    latest_h7_artifact: Mapping[str, Any],
    previous_h7_artifact: Mapping[str, Any] | None = None,
    *,
    latest_source: str | None = None,
    previous_source: str | None = None,
) -> dict[str, Any]:
    blockers: list[str] = []
    blockers.extend(_source_safety_blockers(latest_h7_artifact, label="latest"))
    if previous_h7_artifact is None:
        blockers.append("PREVIOUS_H7_ARTIFACT_NOT_FOUND")
    else:
        blockers.extend(_source_safety_blockers(previous_h7_artifact, label="previous"))

    latest_summary = _summary_from_h7(latest_h7_artifact)
    previous_summary = _summary_from_h7(previous_h7_artifact) if previous_h7_artifact is not None else None
    delta_summary = _delta(latest_summary, previous_summary)
    guard_reasons = _oos_guard_reasons(latest_summary, delta_summary)
    tail_risk = _tail_risk_assessment(latest_summary, previous_summary, delta_summary)
    oos_guard_pass = not guard_reasons
    ok = not blockers
    approved_for_oos_evaluation = bool(ok and oos_guard_pass)

    return {
        "ok": ok,
        "contract_version": CONTRACT_VERSION,
        "source_h7_contract_version": latest_h7_artifact.get("contract_version"),
        "previous_h7_contract_version": previous_h7_artifact.get("contract_version") if previous_h7_artifact else None,
        "report_type": REPORT_TYPE,
        "generated_at_utc": utc_now_iso(),
        "branch_id": latest_h7_artifact.get("branch_id", "HYP-006-R1"),
        "branch_name": latest_h7_artifact.get("branch_name", "failed_downside_sweep_reversal_continuation_short"),
        "hypothesis_id": latest_h7_artifact.get("hypothesis_id", "HYP-006"),
        "strategy_family": latest_h7_artifact.get("strategy_family", "short_failed_liquidity_sweep_continuation"),
        "timeframe": latest_h7_artifact.get("timeframe", "4h"),
        "decision": READY_DECISION if approved_for_oos_evaluation else BLOCKED_DECISION,
        "blockers": blockers,
        "read_only": True,
        "no_order_oos_evaluation_only": True,
        "counterfactual_research_only": True,
        "runtime_activation_blocked_decision_pack": True,
        "network_request_performed": False,
        "config_mutation_performed": False,
        "scheduler_mutation_performed": False,
        "scheduler_task_created": False,
        "scheduler_task_modified": False,
        "strategy_parameter_mutation_performed": False,
        "runtime_overlay_activation_performed": False,
        "approved_for_bnbusdt_oos_evaluation": approved_for_oos_evaluation,
        "approved_for_oos_monitoring_continuation": approved_for_oos_evaluation,
        "approved_for_runtime_overlay_activation_candidate": False,
        "approved_for_runtime_overlay_activation": False,
        "approved_for_parameter_relaxation_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "order_actions_performed": False,
        "source_h7_artifact_json": latest_source,
        "previous_h7_artifact_json": previous_source,
        "oos_quality_guards": OOS_GUARDS,
        "latest_bnbusdt_measurement_summary": latest_summary,
        "previous_bnbusdt_measurement_summary": previous_summary,
        "oos_delta_summary": delta_summary,
        "oos_guard_pass": oos_guard_pass,
        "oos_guard_reasons": guard_reasons,
        "tail_risk_assessment": tail_risk,
        "runtime_activation_decision": {
            "runtime_overlay_activation_allowed": False,
            "runtime_overlay_activation_reason": "OOS_EVALUATION_IS_MEASUREMENT_ONLY_RUNTIME_ACTIVATION_REQUIRES_SEPARATE_GATE",
            "parameter_relaxation_allowed": False,
            "paper_live_order_allowed": False,
            "training_reload_allowed": False,
        },
        "recommendation": "Continue BNBUSDT no-order OOS monitoring only. Runtime overlay activation remains blocked; parameter, paper/live, and order gates remain closed." if approved_for_oos_evaluation else "Do not promote BNBUSDT overlay. Keep runtime activation, parameter, paper/live, and order gates closed.",
    }


def render_markdown_report(payload: Mapping[str, Any]) -> str:
    lines: list[str] = []
    lines.append(f"# {CONTRACT_VERSION} HYP-006 BNBUSDT Overlay OOS Evaluation")
    lines.append("")
    lines.append("This decision pack compares the latest BNBUSDT no-order overlay measurement with the previous H7 measurement. It blocks runtime activation and all trading gates.")
    lines.append("")
    lines.append("## Decision")
    lines.append("")
    for key in (
        "decision",
        "read_only",
        "no_order_oos_evaluation_only",
        "approved_for_bnbusdt_oos_evaluation",
        "approved_for_oos_monitoring_continuation",
        "approved_for_runtime_overlay_activation_candidate",
        "approved_for_runtime_overlay_activation",
        "approved_for_parameter_relaxation_candidate",
        "approved_for_paper_candidate",
        "approved_for_live_real",
        "runtime_overlay_activation_performed",
        "training_performed",
        "reload_performed",
        "trading_action_performed",
        "order_actions_performed",
    ):
        lines.append(f"- `{key}`: `{payload.get(key)}`")
    lines.append("")
    lines.append("## Latest measurement")
    lines.append("")
    latest = _mapping(payload.get("latest_bnbusdt_measurement_summary"))
    for key in ("symbol", "event_count", "matured_count", "win_rate_pct", "mean_return_bps", "median_return_bps", "profit_factor", "worst_return_bps", "worst_mae_bps", "net_return_bps"):
        lines.append(f"- `{key}`: `{latest.get(key)}`")
    lines.append("")
    lines.append("## OOS delta")
    lines.append("")
    delta = _mapping(payload.get("oos_delta_summary"))
    for key in ("event_count_delta", "matured_count_delta", "win_rate_pct_delta", "mean_return_bps_delta", "median_return_bps_delta", "profit_factor_delta", "worst_return_bps_delta", "worst_mae_bps_delta", "net_return_bps_delta"):
        lines.append(f"- `{key}`: `{delta.get(key)}`")
    lines.append("")
    lines.append("## Guards")
    lines.append("")
    lines.append(f"- `oos_guard_pass`: `{payload.get('oos_guard_pass')}`")
    guard_reasons = _sequence(payload.get("oos_guard_reasons"))
    lines.append(f"- `oos_guard_reasons`: `{', '.join(str(item) for item in guard_reasons) if guard_reasons else '[]'}`")
    tail = _mapping(payload.get("tail_risk_assessment"))
    lines.append(f"- `tail_risk_monitoring_required`: `{tail.get('tail_risk_monitoring_required')}`")
    lines.append(f"- `tail_risk_reasons`: `{', '.join(str(item) for item in _sequence(tail.get('tail_risk_reasons'))) if _sequence(tail.get('tail_risk_reasons')) else '[]'}`")
    lines.append("")
    lines.append("## Recommendation")
    lines.append("")
    lines.append(str(payload.get("recommendation", "")))
    lines.append("")
    return "\n".join(lines)


def write_report_bundle(payload: Mapping[str, Any], out_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR) -> tuple[Path, Path]:
    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)
    stamp = utc_stamp()
    json_path = target / f"{REPORT_PREFIX}_{stamp}.json"
    md_path = target / f"{REPORT_PREFIX}_{stamp}.md"
    write_json_atomic(json_path, payload)
    md_path.write_text(render_markdown_report(payload), encoding="utf-8", newline="\n")
    return json_path, md_path


def build_and_write_latest_report(reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR) -> tuple[dict[str, Any], Path, Path]:
    artifacts = latest_h7_artifacts(reports_dir, limit=2)
    latest_payload: Mapping[str, Any] = {}
    previous_payload: Mapping[str, Any] | None = None
    latest_source: str | None = None
    previous_source: str | None = None
    if artifacts:
        latest_source = str(artifacts[0])
        latest_payload = _mapping(load_json(artifacts[0]))
    if len(artifacts) > 1:
        previous_source = str(artifacts[1])
        previous_payload = _mapping(load_json(artifacts[1]))
    report = build_bnbusdt_overlay_oos_evaluation_report(
        latest_payload,
        previous_payload,
        latest_source=latest_source,
        previous_source=previous_source,
    )
    if not artifacts:
        report["ok"] = False
        report["decision"] = BLOCKED_DECISION
        report["blockers"] = [*report.get("blockers", []), "LATEST_H7_ARTIFACT_NOT_FOUND"]
        report["approved_for_bnbusdt_oos_evaluation"] = False
        report["approved_for_oos_monitoring_continuation"] = False
    json_path, md_path = write_report_bundle(report, reports_dir)
    return report, json_path, md_path


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build HYP-006 BNBUSDT overlay OOS evaluation decision pack")
    parser.add_argument("--reports-dir", default=DEFAULT_REPORTS_DIR)
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)
    report, json_path, md_path = build_and_write_latest_report(args.reports_dir)
    if args.once_json:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    else:
        print(f"{CONTRACT_VERSION} HYP-006 BNBUSDT overlay OOS evaluation {report.get('decision')}")
        for key in (
            "read_only",
            "no_order_oos_evaluation_only",
            "approved_for_bnbusdt_oos_evaluation",
            "approved_for_oos_monitoring_continuation",
            "approved_for_runtime_overlay_activation_candidate",
            "approved_for_parameter_relaxation_candidate",
            "approved_for_paper_candidate",
            "approved_for_live_real",
            "runtime_overlay_activation_performed",
            "training_performed",
            "reload_performed",
            "trading_action_performed",
        ):
            print(f" - {key}: {report.get(key)}")
        latest = _mapping(report.get("latest_bnbusdt_measurement_summary"))
        delta = _mapping(report.get("oos_delta_summary"))
        print(f" - latest_matured_count: {latest.get('matured_count')}")
        print(f" - latest_win_rate_pct: {latest.get('win_rate_pct')}")
        print(f" - latest_mean_return_bps: {latest.get('mean_return_bps')}")
        print(f" - latest_profit_factor: {latest.get('profit_factor')}")
        print(f" - matured_count_delta: {delta.get('matured_count_delta')}")
        print(f"report_json: {json_path}")
        print(f"report_md: {md_path}")
    return 0 if report.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
