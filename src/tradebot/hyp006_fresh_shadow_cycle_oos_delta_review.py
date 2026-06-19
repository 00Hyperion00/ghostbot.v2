from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

CONTRACT_VERSION = "4B.4.3.6.6.28G-H9"
SOURCE_H3_CONTRACT_VERSION = "4B.4.3.6.6.28G-H3"
SOURCE_H8_CONTRACT_VERSION = "4B.4.3.6.6.28G-H8"
REPORT_TYPE = "hyp006_r1_fresh_shadow_cycle_oos_delta_review_paper_transition_still_blocked_decision_pack"
REPORT_PREFIX = "4B436628G_H9_hyp006_r1_fresh_shadow_cycle_oos_delta_review"
DEFAULT_REPORTS_DIR = "reports/hyp006_r1_canonical"
TARGET_FRESH_H3_STAMP = "20260619T210504Z"

READY_DECISION = "HYP006_R1_FRESH_SHADOW_CYCLE_OOS_DELTA_REVIEW_READY_PAPER_TRANSITION_STILL_BLOCKED"
BLOCKED_DECISION = "HYP006_R1_FRESH_SHADOW_CYCLE_OOS_DELTA_REVIEW_BLOCKED"

H3_PATTERN = "4B436628G_H3_hyp006_r1_runtime_candidate_scan_gate_level_near_miss_*.json"
H4_PATTERN = "4B436628G_H4_hyp006_r1_near_miss_outcome_attribution_*.json"
H5_PATTERN = "4B436628G_H5_hyp006_r1_counterfactual_filter_candidate_ranking_*.json"
H6_PATTERN = "4B436628G_H6_hyp006_r1_no_order_filter_shadow_overlay_design_*.json"
H7_PATTERN = "4B436628G_H7_hyp006_r1_no_order_overlay_simulation_bnbusdt_primary_filter_shadow_measurement_*.json"
H8_PATTERN = "4B436628G_H8_hyp006_r1_bnbusdt_overlay_oos_evaluation_runtime_activation_blocked_decision_*.json"

H4_H8_CHAIN_TOOLS: tuple[str, ...] = (
    "tools/run_4B436628G_H4_hyp006_near_miss_outcome_attribution.py",
    "tools/run_4B436628G_H5_hyp006_counterfactual_filter_candidate_ranking.py",
    "tools/run_4B436628G_H6_hyp006_no_order_filter_shadow_overlay_design.py",
    "tools/run_4B436628G_H7_hyp006_no_order_overlay_simulation_bnbusdt.py",
    "tools/run_4B436628G_H8_hyp006_bnbusdt_overlay_oos_evaluation.py",
)

RISK_FLAGS = {
    "read_only": True,
    "fresh_shadow_cycle_review_only": True,
    "paper_transition_still_blocked": True,
    "runtime_activation_blocked": True,
    "paper_live_order_blocked": True,
    "training_reload_blocked": True,
    "runtime_overlay_activation_performed": False,
    "scheduler_mutation_performed": False,
    "strategy_parameter_mutation_performed": False,
    "training_performed": False,
    "reload_performed": False,
    "trading_action_performed": False,
    "order_actions_performed": False,
    "paper_live_order_enablement_present": False,
    "hyp006_strategy_threshold_mutation_performed": False,
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _sequence(value: Any) -> Sequence[Any]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return value
    return []


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


def load_json(path: str | os.PathLike[str]) -> Any:
    with Path(path).open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


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


def latest_matching(reports_dir: str | os.PathLike[str], pattern: str, *, limit: int = 1) -> list[Path]:
    target = Path(reports_dir)
    matches = [item for item in target.glob(pattern) if item.is_file()]
    return sorted(matches, key=lambda item: item.name, reverse=True)[:limit]


def latest_matching_with_stamp(reports_dir: str | os.PathLike[str], pattern: str, stamp: str | None) -> Path | None:
    target = Path(reports_dir)
    matches = [item for item in target.glob(pattern) if item.is_file()]
    if stamp:
        exact = [item for item in matches if stamp in item.name]
        if exact:
            return sorted(exact, key=lambda item: item.name, reverse=True)[0]
    return sorted(matches, key=lambda item: item.name, reverse=True)[0] if matches else None


def _artifact_summary(path: Path | None, expected_contract: str | None = None) -> dict[str, Any]:
    if path is None:
        return {"present": False, "path": None, "contract_version": None, "decision": None, "ok": False, "reason": "ARTIFACT_MISSING"}
    try:
        payload = _mapping(load_json(path))
    except Exception as exc:
        return {"present": True, "path": path.as_posix(), "contract_version": None, "decision": None, "ok": False, "reason": f"ARTIFACT_LOAD_FAILED:{exc}"}
    ok = True
    reason = "ARTIFACT_ACCEPTED"
    if expected_contract is not None and str(payload.get("contract_version") or "") != expected_contract:
        ok = False
        reason = "CONTRACT_VERSION_MISMATCH"
    return {
        "present": True,
        "path": path.as_posix(),
        "contract_version": payload.get("contract_version"),
        "decision": payload.get("decision"),
        "ok": ok,
        "reason": reason,
    }


def _h3_summary(payload: Mapping[str, Any], *, source: str | None = None) -> dict[str, Any]:
    symbol_near = _mapping(payload.get("symbol_near_miss_counter"))
    symbol_candidates = _mapping(payload.get("symbol_candidate_counter"))
    return {
        "source": source,
        "contract_version": payload.get("contract_version"),
        "branch_id": payload.get("branch_id"),
        "branch_name": payload.get("branch_name"),
        "timeframe": payload.get("timeframe"),
        "read_only": bool(payload.get("read_only", False)),
        "candidate_count": safe_int(payload.get("candidate_count")),
        "near_miss_count": safe_int(payload.get("near_miss_count")),
        "trigger_count": safe_int(payload.get("trigger_count")),
        "scanned_candle_count": safe_int(payload.get("scanned_candle_count")),
        "bnbusdt_near_miss_count": safe_int(symbol_near.get("BNBUSDT")),
        "bnbusdt_candidate_count": safe_int(symbol_candidates.get("BNBUSDT")),
    }


def _h3_delta(latest: Mapping[str, Any], previous: Mapping[str, Any] | None) -> dict[str, Any]:
    fields = ("candidate_count", "near_miss_count", "trigger_count", "scanned_candle_count", "bnbusdt_near_miss_count", "bnbusdt_candidate_count")
    if previous is None:
        return {"previous_h3_present": False, **{f"{key}_delta": None for key in fields}}
    out: dict[str, Any] = {"previous_h3_present": True}
    for key in fields:
        out[f"{key}_delta"] = safe_int(latest.get(key)) - safe_int(previous.get(key))
    return out


def _h8_summary(payload: Mapping[str, Any], *, source: str | None = None) -> dict[str, Any]:
    latest = _mapping(payload.get("latest_bnbusdt_measurement_summary"))
    delta = _mapping(payload.get("oos_delta_summary"))
    tail = _mapping(payload.get("tail_risk_assessment"))
    return {
        "source": source,
        "contract_version": payload.get("contract_version"),
        "decision": payload.get("decision"),
        "ok": bool(payload.get("ok", False)),
        "oos_guard_pass": bool(payload.get("oos_guard_pass", False)),
        "oos_guard_reasons": list(_sequence(payload.get("oos_guard_reasons"))),
        "approved_for_bnbusdt_oos_evaluation": bool(payload.get("approved_for_bnbusdt_oos_evaluation", False)),
        "approved_for_oos_monitoring_continuation": bool(payload.get("approved_for_oos_monitoring_continuation", False)),
        "symbol": latest.get("symbol"),
        "event_count": safe_int(latest.get("event_count")),
        "matured_count": safe_int(latest.get("matured_count")),
        "win_rate_pct": safe_float(latest.get("win_rate_pct")),
        "mean_return_bps": safe_float(latest.get("mean_return_bps")),
        "median_return_bps": safe_float(latest.get("median_return_bps")),
        "profit_factor": safe_float(latest.get("profit_factor")),
        "worst_return_bps": safe_float(latest.get("worst_return_bps")),
        "worst_mae_bps": safe_float(latest.get("worst_mae_bps")),
        "net_return_bps": safe_float(latest.get("net_return_bps")),
        "event_count_delta": delta.get("event_count_delta"),
        "matured_count_delta": delta.get("matured_count_delta"),
        "win_rate_pct_delta": delta.get("win_rate_pct_delta"),
        "mean_return_bps_delta": delta.get("mean_return_bps_delta"),
        "profit_factor_delta": delta.get("profit_factor_delta"),
        "worst_return_bps_delta": delta.get("worst_return_bps_delta"),
        "worst_mae_bps_delta": delta.get("worst_mae_bps_delta"),
        "tail_risk_monitoring_required": bool(tail.get("tail_risk_monitoring_required", False)),
        "tail_risk_reasons": list(_sequence(tail.get("tail_risk_reasons"))),
    }


def run_h4_h8_chain(root: str | os.PathLike[str], reports_dir: str | os.PathLike[str]) -> list[dict[str, Any]]:
    base = Path(root).resolve()
    env = os.environ.copy()
    src_path = str(base / "src")
    env["PYTHONPATH"] = src_path + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    results: list[dict[str, Any]] = []
    for tool in H4_H8_CHAIN_TOOLS:
        path = base / tool
        if not path.exists():
            results.append({"tool": tool, "returncode": None, "ok": False, "stdout_tail": "", "stderr_tail": "TOOL_MISSING"})
            continue
        proc = subprocess.run(
            [sys.executable, str(path), "--reports-dir", str(reports_dir)],
            cwd=base,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=420,
            check=False,
        )
        results.append({
            "tool": tool,
            "returncode": proc.returncode,
            "ok": proc.returncode == 0,
            "stdout_tail": proc.stdout[-4000:],
            "stderr_tail": proc.stderr[-4000:],
        })
    return results


def _chain_complete(chain_results: Sequence[Mapping[str, Any]]) -> bool:
    if not chain_results:
        return False
    return all(bool(item.get("ok", False)) for item in chain_results)


def build_fresh_shadow_cycle_oos_delta_review(
    reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR,
    *,
    fresh_h3_stamp: str | None = TARGET_FRESH_H3_STAMP,
    chain_results: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    reports = Path(reports_dir)
    latest_h3_path = latest_matching_with_stamp(reports, H3_PATTERN, fresh_h3_stamp)
    h3_paths = latest_matching(reports, H3_PATTERN, limit=5)
    previous_h3_path = next((item for item in h3_paths if item != latest_h3_path), None)

    latest_h3_payload = _mapping(load_json(latest_h3_path)) if latest_h3_path else {}
    previous_h3_payload = _mapping(load_json(previous_h3_path)) if previous_h3_path else None
    latest_h3_summary = _h3_summary(latest_h3_payload, source=latest_h3_path.as_posix() if latest_h3_path else None)
    previous_h3_summary = _h3_summary(previous_h3_payload, source=previous_h3_path.as_posix()) if previous_h3_payload is not None else None
    h3_delta = _h3_delta(latest_h3_summary, previous_h3_summary)

    h4 = latest_matching(reports, H4_PATTERN, limit=1)
    h5 = latest_matching(reports, H5_PATTERN, limit=1)
    h6 = latest_matching(reports, H6_PATTERN, limit=1)
    h7 = latest_matching(reports, H7_PATTERN, limit=1)
    h8 = latest_matching(reports, H8_PATTERN, limit=2)
    latest_h8_path = h8[0] if h8 else None
    previous_h8_path = h8[1] if len(h8) > 1 else None
    latest_h8_payload = _mapping(load_json(latest_h8_path)) if latest_h8_path else {}
    previous_h8_payload = _mapping(load_json(previous_h8_path)) if previous_h8_path else None
    latest_h8_summary = _h8_summary(latest_h8_payload, source=latest_h8_path.as_posix() if latest_h8_path else None)
    previous_h8_summary = _h8_summary(previous_h8_payload, source=previous_h8_path.as_posix()) if previous_h8_payload is not None else None

    evidence = {
        "H3": _artifact_summary(latest_h3_path, SOURCE_H3_CONTRACT_VERSION),
        "H4": _artifact_summary(h4[0] if h4 else None, "4B.4.3.6.6.28G-H4"),
        "H5": _artifact_summary(h5[0] if h5 else None, "4B.4.3.6.6.28G-H5"),
        "H6": _artifact_summary(h6[0] if h6 else None, "4B.4.3.6.6.28G-H6"),
        "H7": _artifact_summary(h7[0] if h7 else None, "4B.4.3.6.6.28G-H7"),
        "H8": _artifact_summary(latest_h8_path, SOURCE_H8_CONTRACT_VERSION),
    }

    blockers: list[str] = []
    if latest_h3_path is None:
        blockers.append("FRESH_H3_ARTIFACT_NOT_FOUND")
    if latest_h3_path is not None and fresh_h3_stamp and fresh_h3_stamp not in latest_h3_path.name:
        blockers.append("FRESH_H3_TARGET_STAMP_MISMATCH")
    if latest_h3_summary.get("contract_version") != SOURCE_H3_CONTRACT_VERSION:
        blockers.append("FRESH_H3_CONTRACT_VERSION_MISMATCH")
    if not latest_h3_summary.get("read_only", False):
        blockers.append("FRESH_H3_NOT_READ_ONLY")
    missing_evidence = [key for key, item in evidence.items() if key != "H3" and not item.get("present")]
    if missing_evidence:
        blockers.append("FRESH_H4_H8_EVIDENCE_MISSING:" + ",".join(missing_evidence))
    if latest_h8_summary.get("contract_version") != SOURCE_H8_CONTRACT_VERSION:
        blockers.append("LATEST_H8_CONTRACT_VERSION_MISMATCH")
    if latest_h8_summary.get("decision") != "HYP006_R1_BNBUSDT_OVERLAY_OOS_EVALUATION_READY_RUNTIME_ACTIVATION_BLOCKED":
        blockers.append("LATEST_H8_DECISION_NOT_READY")
    if bool(latest_h8_payload.get("approved_for_runtime_overlay_activation_candidate", False)):
        blockers.append("LATEST_H8_RUNTIME_OVERLAY_UNEXPECTEDLY_APPROVED")
    if bool(latest_h8_payload.get("approved_for_paper_candidate", False)) or bool(latest_h8_payload.get("approved_for_live_real", False)):
        blockers.append("LATEST_H8_TRADING_GATE_UNEXPECTEDLY_APPROVED")
    if bool(latest_h8_payload.get("trading_action_performed", False)) or bool(latest_h8_payload.get("order_actions_performed", False)):
        blockers.append("LATEST_H8_ORDER_ACTION_UNEXPECTEDLY_PERFORMED")
    if bool(latest_h8_payload.get("training_performed", False)) or bool(latest_h8_payload.get("reload_performed", False)):
        blockers.append("LATEST_H8_TRAINING_RELOAD_UNEXPECTEDLY_PERFORMED")
    if chain_results is not None and not _chain_complete(chain_results):
        blockers.append("H4_H8_CHAIN_EXECUTION_INCOMPLETE")

    tail_risk_reasons = [str(item) for item in _sequence(latest_h8_summary.get("tail_risk_reasons"))]
    tail_risk_worsened = any("DETERIORATED" in reason for reason in tail_risk_reasons)
    if tail_risk_worsened:
        blockers.append("TAIL_RISK_DETERIORATED")

    h4_h8_evidence_complete = not missing_evidence and latest_h8_summary.get("decision") == "HYP006_R1_BNBUSDT_OVERLAY_OOS_EVALUATION_READY_RUNTIME_ACTIVATION_BLOCKED"
    ready = not blockers and h4_h8_evidence_complete

    return {
        "ok": True,
        "contract_version": CONTRACT_VERSION,
        "report_type": REPORT_TYPE,
        "generated_at_utc": utc_now_iso(),
        "decision": READY_DECISION if ready else BLOCKED_DECISION,
        **RISK_FLAGS,
        "fresh_h3_target_stamp": fresh_h3_stamp,
        "fresh_h3_artifact_json": latest_h3_path.as_posix() if latest_h3_path else None,
        "previous_h3_artifact_json": previous_h3_path.as_posix() if previous_h3_path else None,
        "h4_h8_chain_executed": chain_results is not None,
        "h4_h8_chain_results": list(chain_results or []),
        "h4_h8_chain_complete": _chain_complete(chain_results or []),
        "h4_h8_evidence_complete": h4_h8_evidence_complete,
        "evidence": evidence,
        "blockers": blockers,
        "approved_for_hyp006_oos_delta_review": ready,
        "approved_for_hyp006_oos_monitoring_continuation": ready,
        "approved_for_runtime_overlay_activation_candidate": False,
        "approved_for_parameter_relaxation_candidate": False,
        "approved_for_paper_transition_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "latest_h3_summary": latest_h3_summary,
        "previous_h3_summary": previous_h3_summary,
        "h3_delta_summary": h3_delta,
        "latest_h8_summary": latest_h8_summary,
        "previous_h8_summary": previous_h8_summary,
        "bnbusdt_matured_count": latest_h8_summary.get("matured_count"),
        "bnbusdt_matured_count_delta": latest_h8_summary.get("matured_count_delta"),
        "tail_risk_worsened": tail_risk_worsened,
        "tail_risk_reasons": tail_risk_reasons,
        "paper_transition_decision": {
            "paper_transition_candidate_allowed": False,
            "paper_transition_reason": "HYP006_H9_IS_NO_ORDER_OOS_DELTA_REVIEW_ONLY_PAPER_TRANSITION_REQUIRES_30B_OPERATOR_APPROVAL_GATE",
            "paper_candidate_allowed": False,
            "live_real_allowed": False,
        },
        "recommendation": "Continue HYP-006 no-order OOS monitoring. Paper transition remains blocked until the separate 30B operator approval/sandbox envelope gate passes." if ready else "Do not promote. Complete fresh H4-H8 evidence and keep paper/live/live-real/order gates closed.",
    }


def render_markdown_report(payload: Mapping[str, Any]) -> str:
    lines: list[str] = []
    lines.append(f"# {CONTRACT_VERSION} HYP-006 Fresh Shadow Cycle OOS Delta Review")
    lines.append("")
    lines.append("This report reviews the fresh 20260619T210504Z H3 shadow cycle and the latest H4-H8 no-order OOS evidence. It does not enable paper, live, live-real, runtime overlays, orders, training, or reloads.")
    lines.append("")
    lines.append("## Decision")
    lines.append("")
    for key in (
        "decision",
        "read_only",
        "fresh_shadow_cycle_review_only",
        "approved_for_hyp006_oos_delta_review",
        "approved_for_hyp006_oos_monitoring_continuation",
        "approved_for_runtime_overlay_activation_candidate",
        "approved_for_parameter_relaxation_candidate",
        "approved_for_paper_transition_candidate",
        "approved_for_paper_candidate",
        "approved_for_live_real",
        "trading_action_performed",
    ):
        lines.append(f"- `{key}`: `{payload.get(key)}`")
    lines.append("")
    lines.append("## H3 delta")
    latest_h3 = _mapping(payload.get("latest_h3_summary"))
    delta = _mapping(payload.get("h3_delta_summary"))
    for key in ("candidate_count", "near_miss_count", "trigger_count", "bnbusdt_near_miss_count"):
        lines.append(f"- `{key}`: `{latest_h3.get(key)}` / delta `{delta.get(key + '_delta')}`")
    lines.append("")
    lines.append("## BNBUSDT OOS")
    h8 = _mapping(payload.get("latest_h8_summary"))
    for key in ("event_count", "matured_count", "matured_count_delta", "win_rate_pct", "mean_return_bps", "profit_factor", "worst_return_bps", "worst_mae_bps"):
        lines.append(f"- `{key}`: `{h8.get(key)}`")
    lines.append("")
    lines.append("## Blockers")
    blockers = _sequence(payload.get("blockers"))
    lines.append(f"- `{', '.join(str(item) for item in blockers) if blockers else '[]'}`")
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


def build_and_write_latest_report(
    reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR,
    *,
    fresh_h3_stamp: str | None = TARGET_FRESH_H3_STAMP,
    root: str | os.PathLike[str] | None = None,
    run_chain: bool = False,
) -> tuple[dict[str, Any], Path, Path]:
    chain_results: list[dict[str, Any]] | None = None
    if run_chain:
        chain_results = run_h4_h8_chain(root or Path.cwd(), reports_dir)
    payload = build_fresh_shadow_cycle_oos_delta_review(reports_dir, fresh_h3_stamp=fresh_h3_stamp, chain_results=chain_results)
    json_path, md_path = write_report_bundle(payload, reports_dir)
    return payload, json_path, md_path


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build HYP-006 fresh shadow cycle OOS delta review decision pack")
    parser.add_argument("--reports-dir", default=DEFAULT_REPORTS_DIR)
    parser.add_argument("--fresh-h3-stamp", default=TARGET_FRESH_H3_STAMP)
    parser.add_argument("--run-h4-h8-chain", action="store_true")
    parser.add_argument("--root", default=str(Path.cwd()))
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)
    payload, json_path, md_path = build_and_write_latest_report(
        args.reports_dir,
        fresh_h3_stamp=args.fresh_h3_stamp,
        root=args.root,
        run_chain=args.run_h4_h8_chain,
    )
    if args.once_json:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2))
    else:
        print(f"{CONTRACT_VERSION} HYP-006 Fresh Shadow Cycle OOS Delta Review {payload.get('decision')}")
        for key in (
            "read_only",
            "h4_h8_evidence_complete",
            "approved_for_hyp006_oos_delta_review",
            "approved_for_hyp006_oos_monitoring_continuation",
            "approved_for_runtime_overlay_activation_candidate",
            "approved_for_parameter_relaxation_candidate",
            "approved_for_paper_transition_candidate",
            "approved_for_paper_candidate",
            "approved_for_live_real",
            "training_performed",
            "reload_performed",
            "trading_action_performed",
        ):
            print(f" - {key}: {payload.get(key)}")
        print(f" - bnbusdt_matured_count: {payload.get('bnbusdt_matured_count')}")
        print(f" - bnbusdt_matured_count_delta: {payload.get('bnbusdt_matured_count_delta')}")
        print(f" - tail_risk_worsened: {payload.get('tail_risk_worsened')}")
        print(f"report_json: {json_path}")
        print(f"report_md: {md_path}")
    return 0 if payload.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
