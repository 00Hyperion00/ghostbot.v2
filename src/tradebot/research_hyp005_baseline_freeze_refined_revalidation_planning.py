from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

HYP005_BASELINE_FREEZE_REVALIDATION_PLANNING_CONTRACT_VERSION = "4B.4.3.6.6.25AD"
HYP005_R1_REVALIDATION_PLANNING_READY = "HYP005_R1_REVALIDATION_PLANNING_READY"
HYP005_R1_REVALIDATION_PLANNING_BLOCK = "HYP005_R1_REVALIDATION_PLANNING_BLOCK"

SOURCE_25AC_BRANCH_REFINEMENT_REQUIRED_CONFIRMED = "SOURCE_25AC_BRANCH_REFINEMENT_REQUIRED_CONFIRMED"
BASELINE_EVIDENCE_FROZEN = "BASELINE_EVIDENCE_FROZEN"
REFINED_CANDIDATE_REVALIDATION_PLANNED = "REFINED_CANDIDATE_REVALIDATION_PLANNED"
HYP005_R1_FRESH_LEDGER_NAMESPACE_DECLARED = "HYP005_R1_FRESH_LEDGER_NAMESPACE_DECLARED"
LEGACY_BASELINE_OBSERVATIONS_NOT_REUSED = "LEGACY_BASELINE_OBSERVATIONS_NOT_REUSED"
SCHEDULER_REGENERATION_REQUIRES_SEPARATE_OPERATOR_PATCH = "SCHEDULER_REGENERATION_REQUIRES_SEPARATE_OPERATOR_PATCH"
NO_AUTOMATIC_SCHEDULER_CONFIG_MUTATION = "NO_AUTOMATIC_SCHEDULER_CONFIG_MUTATION"
NO_TRAINING_PAPER_LIVE_APPROVALS_DETECTED = "NO_TRAINING_PAPER_LIVE_APPROVALS_DETECTED"
BASELINE_SCHEDULER_DISABLE_BEFORE_REGENERATION_REQUIRED = "BASELINE_SCHEDULER_DISABLE_BEFORE_REGENERATION_REQUIRED"

EXPECTED_SOURCE_DECISION = "HYP005_BRANCH_REFINEMENT_REQUIRED"
DEFAULT_REFINED_BRANCH_ID = "HYP-005-R1"
DEFAULT_FRESH_LEDGER_NAMESPACE = "HYP005_R1"
DEFAULT_NEXT_SCHEDULER_PATCH_CONTRACT = "4B.4.3.6.6.25AE"
DEFAULT_REVALIDATION_SAMPLE_TARGET = 30
DEFAULT_MIN_REFINED_SYMBOL_COUNT = 6


@dataclass(frozen=True)
class Hyp005RefinedCandidateRevalidationPlanningLimits:
    revalidation_sample_target: int = DEFAULT_REVALIDATION_SAMPLE_TARGET
    min_refined_symbol_count: int = DEFAULT_MIN_REFINED_SYMBOL_COUNT
    max_refined_symbol_count: int = 10


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_now_iso() -> str:
    return _utc_now().replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _utc_file_stamp() -> str:
    return _utc_now().strftime("%Y%m%d_%H%M%S")


def _canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_payload(payload: Any) -> str:
    return _sha256_bytes(_canonical_json_bytes(payload))


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return payload if isinstance(payload, dict) else {}


def _latest_file(directory: Path, pattern: str) -> Path | None:
    matches = sorted(directory.glob(pattern), key=lambda path: path.stat().st_mtime, reverse=True)
    return matches[0] if matches else None


def _sorted_unique_symbols(values: Iterable[Any]) -> list[str]:
    return sorted({str(value).strip().upper() for value in values if str(value).strip()})


def _normalize_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, (list, tuple)) else []


def _extract_refined_symbols(source_report: dict[str, Any]) -> tuple[list[str], list[str]]:
    pruned = _sorted_unique_symbols(_normalize_list(source_report.get("recommended_pruned_symbols")))
    refined = _sorted_unique_symbols(_normalize_list(source_report.get("recommended_symbols")))
    if not refined:
        arg = str(source_report.get("recommended_symbols_arg") or "")
        refined = _sorted_unique_symbols(part for part in arg.split(",") if part.strip())
    return refined, pruned


def _latest_25ac_report(reports_dir: Path, input_json: Path | None) -> tuple[dict[str, Any], Path | None]:
    if input_json is not None:
        return _read_json(input_json), input_json
    latest = _latest_file(reports_dir, "4B436625AC_hyp005_symbol_risk_pruning_decision_*.json")
    if latest is None:
        return {}, None
    return _read_json(latest), latest


def _build_baseline_freeze_snapshot(
    source_report: dict[str, Any],
    *,
    source_path: Path,
    source_sha256: str,
    refined_symbols: list[str],
    pruned_symbols: list[str],
) -> dict[str, Any]:
    baseline = source_report.get("baseline_scenario") if isinstance(source_report.get("baseline_scenario"), dict) else {}
    selected = source_report.get("selected_scenario") if isinstance(source_report.get("selected_scenario"), dict) else {}
    dedupe = source_report.get("deduplication") if isinstance(source_report.get("deduplication"), dict) else {}
    snapshot: dict[str, Any] = {
        "snapshot_contract_version": HYP005_BASELINE_FREEZE_REVALIDATION_PLANNING_CONTRACT_VERSION,
        "snapshot_type": "hyp005_baseline_evidence_freeze_write_once_digest_snapshot",
        "frozen_at_utc": _utc_now_iso(),
        "immutable_by_convention": True,
        "write_once_filename_required": True,
        "source_25ac_report": str(source_path),
        "source_25ac_report_sha256": source_sha256,
        "source_25ac_contract_version": source_report.get("contract_version"),
        "source_25ac_decision": source_report.get("decision"),
        "hypothesis_id": source_report.get("hypothesis_id", "HYP-005"),
        "baseline_branch_name": source_report.get("branch_name", "liquidity_sweep_reversal_vol_compression"),
        "canonical_deduplication": {
            "raw_observation_count": dedupe.get("raw_observation_count"),
            "unique_observation_count": dedupe.get("unique_observation_count"),
            "duplicate_removed_count": dedupe.get("duplicate_removed_count"),
        },
        "baseline_metrics": {
            "observation_count": baseline.get("observation_count"),
            "matured_forward_return_count": baseline.get("matured_forward_return_count"),
            "maturity_pending_count": baseline.get("maturity_pending_count"),
            "mean_forward_edge_bps": baseline.get("mean_forward_edge_bps"),
            "median_forward_edge_bps": baseline.get("median_forward_edge_bps"),
            "profit_factor": baseline.get("profit_factor"),
            "win_rate_pct": baseline.get("win_rate_pct"),
            "high_slippage_symbols": baseline.get("high_slippage_symbols", []),
            "tail_loss_count": baseline.get("tail_loss_count"),
            "tail_loss_symbols": baseline.get("tail_loss_symbols", []),
            "true_missing_required_fields_pct": baseline.get("true_missing_required_fields_pct"),
        },
        "selected_refinement_scenario": {
            "scenario_id": selected.get("scenario_id"),
            "excluded_symbols": selected.get("excluded_symbols", pruned_symbols),
            "included_symbols": selected.get("included_symbols", refined_symbols),
            "passes_continuation_gate": selected.get("passes_continuation_gate"),
        },
        "recommended_pruned_symbols": pruned_symbols,
        "recommended_refined_symbols": refined_symbols,
        "baseline_observation_carry_forward_allowed": False,
        "baseline_observations_reused_in_refined_branch": False,
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "order_actions_allowed": False,
        "post_requests_allowed": False,
        "config_mutation_performed": False,
    }
    snapshot["baseline_evidence_digest_sha256"] = _sha256_payload(snapshot)
    return snapshot


def _build_refined_candidate_spec(
    *,
    baseline_snapshot: dict[str, Any],
    refined_symbols: list[str],
    pruned_symbols: list[str],
    limits: Hyp005RefinedCandidateRevalidationPlanningLimits,
) -> dict[str, Any]:
    return {
        "candidate_spec_contract_version": HYP005_BASELINE_FREEZE_REVALIDATION_PLANNING_CONTRACT_VERSION,
        "candidate_spec_type": "hyp005_r1_fresh_no_order_shadow_revalidation_plan",
        "hypothesis_id": "HYP-005",
        "refined_branch_id": DEFAULT_REFINED_BRANCH_ID,
        "refined_branch_name": "liquidity_sweep_reversal_vol_compression_r1_pruned_symbol_revalidation",
        "parent_baseline_branch": baseline_snapshot.get("baseline_branch_name"),
        "strategy_family": "long_liquidity_sweep_reversal",
        "symbols": refined_symbols,
        "symbols_arg": ",".join(refined_symbols),
        "excluded_symbols": pruned_symbols,
        "interval": "4h",
        "fresh_ledger_required": True,
        "fresh_ledger_namespace": DEFAULT_FRESH_LEDGER_NAMESPACE,
        "fresh_ledger_report_prefix": "4B436625AE_hyp005_r1_shadow_observation_ledger",
        "fresh_logger_report_prefix": "4B436625AE_hyp005_r1_shadow_observation_logger",
        "baseline_evidence_digest_sha256": baseline_snapshot.get("baseline_evidence_digest_sha256"),
        "legacy_baseline_observation_reuse_allowed": False,
        "legacy_baseline_observations_reused": False,
        "starting_unique_shadow_observation_count": 0,
        "shadow_sample_target": limits.revalidation_sample_target,
        "no_order_shadow_only": True,
        "observation_only": True,
        "runtime_probe_only": True,
        "scheduler_pack_contract_required": DEFAULT_NEXT_SCHEDULER_PATCH_CONTRACT,
        "scheduler_pack_generation_requires_separate_operator_patch": True,
        "scheduler_registration_requires_operator_action": True,
        "baseline_scheduler_disable_required_before_refined_registration": True,
        "approved_for_training_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "training_allowed": False,
        "model_reload_allowed": False,
        "paper_trading_allowed": False,
        "live_trading_allowed": False,
        "orders_allowed": False,
        "post_requests_allowed": False,
        "config_mutation_allowed": False,
        "config_mutation_performed": False,
    }


def build_hyp005_baseline_freeze_refined_revalidation_planning_report(
    reports_dir: Path | str,
    *,
    input_json: Path | str | None = None,
    review_ok: bool = False,
    limits: Hyp005RefinedCandidateRevalidationPlanningLimits | None = None,
) -> dict[str, Any]:
    active_limits = limits or Hyp005RefinedCandidateRevalidationPlanningLimits()
    reports_path = Path(reports_dir)
    input_path = Path(input_json) if input_json is not None else None
    source_report, source_path = _latest_25ac_report(reports_path, input_path)
    source_sha256 = _sha256_file(source_path) if source_path is not None and source_path.exists() else None
    refined_symbols, pruned_symbols = _extract_refined_symbols(source_report)
    baseline_symbols = _sorted_unique_symbols(
        _normalize_list((source_report.get("baseline_scenario") or {}).get("included_symbols"))
        if isinstance(source_report.get("baseline_scenario"), dict)
        else []
    )

    blockers: list[str] = []
    if not review_ok:
        blockers.append("REVIEW_OK_REQUIRED")
    if source_path is None:
        blockers.append("SOURCE_25AC_REPORT_NOT_FOUND")
    if source_report.get("decision") != EXPECTED_SOURCE_DECISION:
        blockers.append("SOURCE_25AC_DECISION_NOT_REFINEMENT_REQUIRED")
    if not pruned_symbols:
        blockers.append("REFINED_PRUNED_SYMBOLS_MISSING")
    if not refined_symbols:
        blockers.append("REFINED_SYMBOL_SET_MISSING")
    if len(refined_symbols) < active_limits.min_refined_symbol_count:
        blockers.append("REFINED_SYMBOL_SET_TOO_SMALL")
    if len(refined_symbols) > active_limits.max_refined_symbol_count:
        blockers.append("REFINED_SYMBOL_SET_TOO_LARGE")
    if active_limits.revalidation_sample_target <= 0:
        blockers.append("REVALIDATION_SAMPLE_TARGET_INVALID")
    if baseline_symbols and refined_symbols == baseline_symbols:
        blockers.append("REFINED_SYMBOL_SET_NOT_CHANGED")
    if set(pruned_symbols).intersection(refined_symbols):
        blockers.append("PRUNED_SYMBOL_PRESENT_IN_REFINED_SET")

    ready = not blockers and source_path is not None and source_sha256 is not None
    decision = HYP005_R1_REVALIDATION_PLANNING_READY if ready else HYP005_R1_REVALIDATION_PLANNING_BLOCK
    baseline_snapshot = (
        _build_baseline_freeze_snapshot(
            source_report,
            source_path=source_path,
            source_sha256=source_sha256,
            refined_symbols=refined_symbols,
            pruned_symbols=pruned_symbols,
        )
        if ready and source_path is not None and source_sha256 is not None
        else None
    )
    refined_spec = (
        _build_refined_candidate_spec(
            baseline_snapshot=baseline_snapshot,
            refined_symbols=refined_symbols,
            pruned_symbols=pruned_symbols,
            limits=active_limits,
        )
        if baseline_snapshot is not None
        else None
    )

    reason_codes: list[str] = [
        NO_TRAINING_PAPER_LIVE_APPROVALS_DETECTED,
        NO_AUTOMATIC_SCHEDULER_CONFIG_MUTATION,
        SCHEDULER_REGENERATION_REQUIRES_SEPARATE_OPERATOR_PATCH,
        BASELINE_SCHEDULER_DISABLE_BEFORE_REGENERATION_REQUIRED,
        LEGACY_BASELINE_OBSERVATIONS_NOT_REUSED,
    ]
    if ready:
        reason_codes.extend(
            [
                SOURCE_25AC_BRANCH_REFINEMENT_REQUIRED_CONFIRMED,
                BASELINE_EVIDENCE_FROZEN,
                REFINED_CANDIDATE_REVALIDATION_PLANNED,
                HYP005_R1_FRESH_LEDGER_NAMESPACE_DECLARED,
            ]
        )
    else:
        reason_codes.extend(blockers)

    recommendation = (
        "HYP-005 baseline evidence is frozen and HYP-005-R1 fresh no-order revalidation planning is ready. "
        "Keep paper/live/order disabled. Disable the baseline scheduler before a separate operator-reviewed 25AE scheduler pack is registered. "
        "Do not reuse legacy baseline observations in the refined branch."
        if ready
        else "HYP-005-R1 refined candidate revalidation planning is blocked. Keep paper/live/order disabled and resolve planning blockers before any scheduler regeneration patch."
    )
    return {
        "contract_version": HYP005_BASELINE_FREEZE_REVALIDATION_PLANNING_CONTRACT_VERSION,
        "report_type": "hyp005_baseline_evidence_freeze_refined_candidate_revalidation_planning_gate",
        "generated_at_utc": _utc_now_iso(),
        "decision": decision,
        "ok": ready,
        "hypothesis_id": "HYP-005",
        "refined_branch_id": DEFAULT_REFINED_BRANCH_ID,
        "source_25ac_report": str(source_path) if source_path else None,
        "source_25ac_report_sha256": source_sha256,
        "source_25ac_decision": source_report.get("decision"),
        "limits": asdict(active_limits),
        "baseline_evidence_snapshot": baseline_snapshot,
        "refined_candidate_spec": refined_spec,
        "baseline_evidence_frozen": baseline_snapshot is not None,
        "baseline_observation_carry_forward_allowed": False,
        "baseline_observations_reused_in_refined_branch": False,
        "fresh_ledger_required": True,
        "fresh_ledger_namespace": DEFAULT_FRESH_LEDGER_NAMESPACE,
        "starting_unique_shadow_observation_count": 0,
        "recommended_pruned_symbols": pruned_symbols,
        "recommended_refined_symbols": refined_symbols,
        "recommended_refined_symbols_arg": ",".join(refined_symbols),
        "approved_for_refined_candidate_revalidation_plan": ready,
        "approved_for_next_scheduler_pack_patch": ready,
        "next_scheduler_pack_contract": DEFAULT_NEXT_SCHEDULER_PATCH_CONTRACT,
        "approved_for_scheduler_regeneration": False,
        "approved_for_scheduler_registration": False,
        "scheduler_regeneration_requires_separate_operator_patch": True,
        "baseline_scheduler_disable_recommended": ready,
        "baseline_scheduler_disable_performed": False,
        "approved_for_continued_baseline_collection": False,
        "approved_for_training_candidate": False,
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
        "blockers": sorted(dict.fromkeys(blockers)),
        "recommendation": recommendation,
    }


def render_hyp005_baseline_freeze_refined_revalidation_planning_markdown(report: dict[str, Any]) -> str:
    spec = report.get("refined_candidate_spec") if isinstance(report.get("refined_candidate_spec"), dict) else {}
    freeze = report.get("baseline_evidence_snapshot") if isinstance(report.get("baseline_evidence_snapshot"), dict) else {}
    lines = [
        "# HYP-005 Baseline Evidence Freeze / Refined Candidate Revalidation Planning Gate",
        "",
        f"- contract_version: `{report.get('contract_version')}`",
        f"- decision: `{report.get('decision')}`",
        f"- generated_at_utc: `{report.get('generated_at_utc')}`",
        f"- source_25ac_report: `{report.get('source_25ac_report')}`",
        f"- source_25ac_report_sha256: `{report.get('source_25ac_report_sha256')}`",
        f"- baseline_evidence_digest_sha256: `{freeze.get('baseline_evidence_digest_sha256')}`",
        f"- refined_branch_id: `{report.get('refined_branch_id')}`",
        f"- fresh_ledger_namespace: `{report.get('fresh_ledger_namespace')}`",
        f"- starting_unique_shadow_observation_count: `{report.get('starting_unique_shadow_observation_count')}`",
        f"- shadow_sample_target: `{spec.get('shadow_sample_target')}`",
        f"- recommended_pruned_symbols: `{','.join(report.get('recommended_pruned_symbols') or [])}`",
        f"- recommended_refined_symbols_arg: `{report.get('recommended_refined_symbols_arg')}`",
        "",
        "## Safety",
        "",
        "- Baseline evidence is frozen by a write-once timestamped snapshot plus SHA-256 digest.",
        "- Legacy baseline observations are not reused in HYP-005-R1.",
        "- Scheduler regeneration requires a separate operator-reviewed 25AE patch.",
        "- This gate does not mutate scheduler configuration.",
        "- This gate does not train or reload a model.",
        "- This gate does not start paper trading.",
        "- This gate does not enable live trading.",
        "- This gate does not send POST requests or orders.",
        "- Paper/live remain blocked.",
        "",
        "## Reason codes",
        "",
    ]
    lines.extend(f"- `{code}`" for code in report.get("reason_codes") or [])
    if report.get("blockers"):
        lines.extend(["", "## Blockers", ""])
        lines.extend(f"- `{code}`" for code in report.get("blockers") or [])
    lines.extend(["", "## Recommendation", "", str(report.get("recommendation") or "")])
    return "\n".join(lines) + "\n"


def _unique_output_path(out_dir: Path, stem: str, suffix: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = _utc_file_stamp()
    candidate = out_dir / f"{stem}_{stamp}{suffix}"
    index = 1
    while candidate.exists():
        candidate = out_dir / f"{stem}_{stamp}_{index}{suffix}"
        index += 1
    return candidate


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_hyp005_baseline_freeze_refined_revalidation_planning_artifacts(
    report: dict[str, Any],
    out_dir: Path | str,
) -> dict[str, Path | None]:
    out_path = Path(out_dir)
    report_json = _unique_output_path(out_path, "4B436625AD_hyp005_baseline_freeze_refined_revalidation_planning", ".json")
    report_md = report_json.with_suffix(".md")
    freeze_json: Path | None = None
    spec_json: Path | None = None

    snapshot = report.get("baseline_evidence_snapshot")
    spec = report.get("refined_candidate_spec")
    if isinstance(snapshot, dict) and isinstance(spec, dict):
        freeze_json = _unique_output_path(out_path, "4B436625AD_hyp005_baseline_evidence_freeze", ".json")
        spec_json = _unique_output_path(out_path, "4B436625AD_hyp005_r1_refined_candidate_revalidation_plan", ".json")
        _write_json(freeze_json, snapshot)
        _write_json(spec_json, spec)
        report["artifact_paths"] = {
            "baseline_evidence_freeze_json": str(freeze_json),
            "refined_candidate_revalidation_plan_json": str(spec_json),
        }
        report["artifact_sha256"] = {
            "baseline_evidence_freeze_json": _sha256_file(freeze_json),
            "refined_candidate_revalidation_plan_json": _sha256_file(spec_json),
        }

    _write_json(report_json, report)
    report_md.write_text(render_hyp005_baseline_freeze_refined_revalidation_planning_markdown(report), encoding="utf-8")
    return {
        "report_json": report_json,
        "report_md": report_md,
        "baseline_evidence_freeze_json": freeze_json,
        "refined_candidate_revalidation_plan_json": spec_json,
    }
