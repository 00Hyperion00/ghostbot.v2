from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

CONTRACT_VERSION = "4B.4.3.6.6.28B"
SOURCE_DISCOVERY_CONTRACT_VERSION = "4B.4.3.6.6.28A"
REPORT_PREFIX = "4B436628B_hyp006_r1_candidate_spec_registration_gate"
CANDIDATE_SPEC_PREFIX = "4B436628B_hyp006_r1_candidate_spec_draft"
HYPOTHESIS_ID = "HYP-006"
BRANCH_ID = "HYP-006-R1"
BRANCH_NAME = "failed_downside_sweep_reversal_continuation_short"
STRATEGY_FAMILY = "short_failed_liquidity_sweep_continuation"
FAILED_SOURCE_HYPOTHESIS = "HYP-005-R1"
NEXT_REQUIRED_GATE = "28C_NO_ORDER_SHADOW_RUNNER_DRY_RUN_AND_OPERATOR_REGISTRATION_APPROVAL"


@dataclass(frozen=True)
class CandidateSpecDraft:
    contract_version: str
    spec_version: str
    status: str
    hypothesis_id: str
    branch_id: str
    branch_name: str
    strategy_family: str
    inherited_from_failed_branch: str
    no_order_shadow_only: bool
    runtime_probe_only: bool
    operator_review_required: bool
    entry_signal_definition: dict[str, Any]
    exit_observation_definition: dict[str, Any]
    required_shadow_acceptance_metrics: list[dict[str, Any]]
    registration_gate: dict[str, Any]
    risk_controls: dict[str, Any]
    hard_blockers: list[str]
    approvals: dict[str, bool]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_json(path: str | os.PathLike[str] | None) -> Any:
    if path is None:
        return None
    return json.loads(Path(path).read_text(encoding="utf-8"))


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


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def selected_discovery_candidate(discovery_report: Mapping[str, Any] | None) -> Mapping[str, Any]:
    report = _mapping(discovery_report)
    selected = report.get("selected_research_candidate")
    return selected if isinstance(selected, Mapping) else {}


def discovery_supports_hyp006(discovery_report: Mapping[str, Any] | None) -> bool:
    report = _mapping(discovery_report)
    selected = selected_discovery_candidate(report)
    return bool(
        report.get("contract_version") == SOURCE_DISCOVERY_CONTRACT_VERSION
        and report.get("decision") == "HYP005_FAILED_BRANCH_LESSONS_CANDIDATE_DISCOVERY_READY"
        and selected.get("candidate_id") == BRANCH_ID
        and selected.get("branch_name") == BRANCH_NAME
        and selected.get("approved_for_candidate_spec_drafting") is True
        and selected.get("approved_for_shadow_collection") is False
        and selected.get("approved_for_paper_candidate") is False
        and selected.get("approved_for_live_real") is False
    )


def build_hyp006_candidate_spec_draft(discovery_report: Mapping[str, Any] | None) -> dict[str, Any]:
    selected = selected_discovery_candidate(discovery_report)
    discovery_ok = discovery_supports_hyp006(discovery_report)
    expected_edge_proxy = selected.get("expected_edge_proxy_bps")
    spec = CandidateSpecDraft(
        contract_version=CONTRACT_VERSION,
        spec_version="HYP-006-R1-DRAFT-001",
        status="DRAFT_REQUIRES_NO_ORDER_SHADOW_REGISTRATION_APPROVAL" if discovery_ok else "BLOCKED_INVALID_DISCOVERY_SOURCE",
        hypothesis_id=HYPOTHESIS_ID,
        branch_id=BRANCH_ID,
        branch_name=BRANCH_NAME,
        strategy_family=STRATEGY_FAMILY,
        inherited_from_failed_branch=FAILED_SOURCE_HYPOTHESIS,
        no_order_shadow_only=True,
        runtime_probe_only=True,
        operator_review_required=True,
        entry_signal_definition={
            "side": "SHORT_RESEARCH_PROBE_ONLY",
            "timeframe": "4h",
            "strategy_family": STRATEGY_FAMILY,
            "hypothesis_thesis": (
                "A downside liquidity sweep reversal setup that produced negative forward returns for HYP-005-R1 "
                "may represent failed reversal continuation. This is only a no-order hypothesis seed; it is not executable edge."
            ),
            "signal_logic": [
                "Detect downside liquidity sweep below the prior lookback low.",
                "Require the event to satisfy the failed-branch liquidity-sweep identity envelope used only for research comparability.",
                "Evaluate short-side forward return as an independent no-order shadow observation.",
                "Do not place orders, train models, reload models, or change paper/live state from this spec.",
            ],
            "parameters": {
                "lookback_bars": 24,
                "hold_bars": 6,
                "min_sweep_bps": 18.0,
                "min_wick_pct_reference": 42.0,
                "compression_window": 12,
                "compression_baseline_bars": 48,
                "max_compression_ratio_reference": 1.05,
                "confirmation_mode": "same_close_reference_probe_before_28C_runner_design",
                "forward_return_direction": "SHORT_INVERSE_RETURN_PROBE",
                "entry_reference_price": "signal_close_research_reference_only",
            },
            "known_limitations": [
                "Mirror-return evidence is not executable edge.",
                "Short-side borrow, funding, liquidation, and slippage are not yet modeled.",
                "Timestamp-cluster tail risk may invert into gap risk.",
            ],
        },
        exit_observation_definition={
            "hold_horizon_bars": 6,
            "forward_return_fields": [
                "forward_return_bps_h1_short_probe",
                "forward_return_bps_h2_short_probe",
                "forward_return_bps_h3_short_probe",
                "forward_return_bps_final_short_probe",
            ],
            "mae_mfe_fields": ["mae_bps_short_probe", "mfe_bps_short_probe"],
            "no_order_measurement_only": True,
        },
        required_shadow_acceptance_metrics=[
            {"name": "min_shadow_sample_target", "operator": ">=", "threshold": 30},
            {"name": "shadow_mean_forward_edge_bps", "operator": ">", "threshold": 0.0},
            {"name": "shadow_median_forward_edge_bps", "operator": ">", "threshold": 0.0},
            {"name": "shadow_profit_factor", "operator": ">=", "threshold": 1.15},
            {"name": "shadow_walk_forward_positive_rate_pct", "operator": ">=", "threshold": 55.0},
            {"name": "shadow_oos_edge_bps", "operator": ">", "threshold": 0.0},
            {"name": "shadow_data_quality_pct", "operator": ">=", "threshold": 99.0},
            {"name": "max_slippage_proxy_bps", "operator": "<=", "threshold": 12.0},
        ],
        registration_gate={
            "gate_status": "READY_FOR_28C_DRY_RUN_DESIGN" if discovery_ok else "BLOCKED_INVALID_28A_DISCOVERY",
            "source_discovery_contract_version": _mapping(discovery_report).get("contract_version"),
            "selected_candidate_id": selected.get("candidate_id"),
            "selected_candidate_score": selected.get("score"),
            "selected_candidate_risk_level": selected.get("risk_level"),
            "expected_edge_proxy_bps": expected_edge_proxy,
            "approved_for_candidate_spec_drafting": bool(discovery_ok),
            "approved_for_no_order_shadow_registration_candidate": bool(discovery_ok),
            "approved_for_shadow_collection": False,
            "registration_requires_28c_runner": True,
            "next_required_gate": NEXT_REQUIRED_GATE,
        },
        risk_controls={
            "fail_closed_on_missing_28a_discovery": True,
            "paper_transition_requires_separate_enablement": True,
            "live_transition_requires_separate_enablement": True,
            "model_training_blocked": True,
            "model_reload_blocked": True,
            "order_actions_blocked": True,
            "strategy_parameter_mutation_blocked": True,
            "scheduler_mutation_blocked": True,
        },
        hard_blockers=[
            "NO_28C_RUNNER_DRY_RUN_EVIDENCE",
            "NO_SHADOW_COLLECTION_LEDGER_FOR_HYP006_R1",
            "NO_ACCEPTANCE_METRICS_FOR_HYP006_R1",
            "NO_OPERATOR_SHADOW_REGISTRATION_APPROVAL",
            "NO_PAPER_LIVE_TRAINING_RELOAD_ORDER_ENABLEMENT",
        ],
        approvals={
            "approved_for_shadow_collection": False,
            "approved_for_training_candidate": False,
            "approved_for_paper_candidate": False,
            "approved_for_live_real": False,
            "order_actions_allowed": False,
        },
    )
    return asdict(spec)


def validate_candidate_spec_draft(spec: Mapping[str, Any]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if spec.get("contract_version") != CONTRACT_VERSION:
        reasons.append("CONTRACT_VERSION_MISMATCH")
    if spec.get("hypothesis_id") != HYPOTHESIS_ID:
        reasons.append("HYPOTHESIS_ID_MISMATCH")
    if spec.get("branch_id") != BRANCH_ID:
        reasons.append("BRANCH_ID_MISMATCH")
    if spec.get("branch_name") != BRANCH_NAME:
        reasons.append("BRANCH_NAME_MISMATCH")
    if spec.get("no_order_shadow_only") is not True:
        reasons.append("NO_ORDER_SHADOW_ONLY_MISSING")
    approvals = _mapping(spec.get("approvals"))
    for flag in ("approved_for_shadow_collection", "approved_for_training_candidate", "approved_for_paper_candidate", "approved_for_live_real", "order_actions_allowed"):
        if approvals.get(flag) is not False:
            reasons.append(f"UNSAFE_APPROVAL_{flag.upper()}")
    gate = _mapping(spec.get("registration_gate"))
    if gate.get("registration_requires_28c_runner") is not True:
        reasons.append("REGISTRATION_28C_GATE_MISSING")
    return not reasons, reasons


def build_hyp006_registration_gate_report(
    *,
    discovery_report: Mapping[str, Any] | None,
    source_paths: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    source_paths = dict(source_paths or {})
    spec = build_hyp006_candidate_spec_draft(discovery_report)
    spec_ok, spec_reasons = validate_candidate_spec_draft(spec)
    discovery_ok = discovery_supports_hyp006(discovery_report)
    selected = selected_discovery_candidate(discovery_report)
    ok = bool(discovery_ok and spec_ok)
    blockers: list[str] = []
    if not discovery_ok:
        blockers.append("VALID_28A_HYP006_SELECTION_NOT_FOUND")
    blockers.extend(spec_reasons)
    blockers.extend(spec.get("hard_blockers", []))
    return {
        "contract_version": CONTRACT_VERSION,
        "report_type": "hyp006_r1_candidate_spec_draft_no_order_shadow_registration_gate_fail_closed_research_activation_pack",
        "decision": "HYP006_R1_CANDIDATE_SPEC_DRAFT_REGISTRATION_GATE_READY" if ok else "HYP006_R1_CANDIDATE_SPEC_DRAFT_REGISTRATION_GATE_BLOCKED",
        "ok": ok,
        "generated_at_utc": utc_now_iso(),
        "source_discovery_contract_version": _mapping(discovery_report).get("contract_version"),
        "source_discovery_decision": _mapping(discovery_report).get("decision"),
        "selected_candidate_id": selected.get("candidate_id"),
        "selected_candidate_branch": selected.get("branch_name"),
        "selected_candidate_score": selected.get("score"),
        "selected_candidate_risk_level": selected.get("risk_level"),
        "hypothesis_id": HYPOTHESIS_ID,
        "branch_id": BRANCH_ID,
        "branch_name": BRANCH_NAME,
        "strategy_family": STRATEGY_FAMILY,
        "candidate_spec_draft_ready": ok,
        "candidate_spec_generation_required_next": False,
        "no_order_shadow_registration_gate_ready": ok,
        "research_activation_pack_ready": ok,
        "operator_review_required_for_28c": True,
        "next_required_gate": NEXT_REQUIRED_GATE,
        "candidate_spec_draft": spec,
        "candidate_spec_safety_checks": {
            "spec_ok": spec_ok,
            "discovery_ok": discovery_ok,
            "no_order_shadow_only": spec.get("no_order_shadow_only") is True,
            "paper_approval_blocked": _mapping(spec.get("approvals")).get("approved_for_paper_candidate") is False,
            "live_approval_blocked": _mapping(spec.get("approvals")).get("approved_for_live_real") is False,
            "training_blocked": _mapping(spec.get("approvals")).get("approved_for_training_candidate") is False,
            "order_actions_blocked": _mapping(spec.get("approvals")).get("order_actions_allowed") is False,
            "requires_28c_runner": _mapping(spec.get("registration_gate")).get("registration_requires_28c_runner") is True,
        },
        "blockers": sorted(set(blockers)),
        "reason_codes": [
            "NO_ORDER_CANDIDATE_SPEC_DRAFT_ONLY",
            "HYP006_R1_REQUIRES_28C_DRY_RUN_BEFORE_SHADOW_COLLECTION",
            "PAPER_LIVE_GATES_REMAIN_CLOSED",
            "STRATEGY_PARAMETER_MUTATION_NOT_PERFORMED",
            "SCHEDULER_MUTATION_NOT_PERFORMED",
        ],
        "risk_items": [
            {"level": "critical", "code": "MIRROR_EVIDENCE_NOT_EXECUTABLE_EDGE", "detail": "HYP-006-R1 must produce independent no-order shadow evidence."},
            {"level": "warning", "code": "SHORT_SIDE_COSTS_NOT_MODELED", "detail": "Borrow, funding, liquidation, and slippage require separate research instrumentation."},
            {"level": "warning", "code": "28C_REQUIRED", "detail": NEXT_REQUIRED_GATE},
        ],
        "recommendation": "Proceed to 28C dry-run runner design only after operator review. Do not start shadow collection, train, reload, paper trade, live trade, or send orders.",
        "source_paths": source_paths,
        "read_only": True,
        "no_order_candidate_spec_draft_only": True,
        "post_requests_allowed": False,
        "network_request_performed": False,
        "config_mutation_performed": False,
        "scheduler_mutation_performed": False,
        "strategy_parameter_mutation_performed": False,
        "branch_state_mutation_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "order_actions_performed": False,
        "approved_for_no_order_shadow_registration_candidate": ok,
        "approved_for_shadow_collection": False,
        "approved_for_training_candidate": False,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "paper_transition_candidate_found": False,
        "warnings": ["28C_REQUIRED_BEFORE_ANY_SHADOW_COLLECTION_REGISTRATION"],
    }


def write_markdown(path: str | os.PathLike[str], payload: Mapping[str, Any]) -> None:
    lines = [
        "# 4B.4.3.6.6.28B HYP-006-R1 Candidate Spec Draft",
        "",
        f"- decision: `{payload.get('decision')}`",
        f"- hypothesis_id: `{payload.get('hypothesis_id')}`",
        f"- branch_id: `{payload.get('branch_id')}`",
        f"- branch_name: `{payload.get('branch_name')}`",
        f"- candidate_spec_draft_ready: `{payload.get('candidate_spec_draft_ready')}`",
        f"- no_order_shadow_registration_gate_ready: `{payload.get('no_order_shadow_registration_gate_ready')}`",
        f"- approved_for_shadow_collection: `{payload.get('approved_for_shadow_collection')}`",
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


def write_report_bundle(payload: Mapping[str, Any], out_dir: str | os.PathLike[str]) -> tuple[Path, Path, Path]:
    target_dir = Path(out_dir)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_json = target_dir / f"{REPORT_PREFIX}_{stamp}.json"
    candidate_spec_json = target_dir / f"{CANDIDATE_SPEC_PREFIX}_{stamp}.json"
    report_md = target_dir / f"{REPORT_PREFIX}_{stamp}.md"
    write_json_atomic(report_json, payload)
    write_json_atomic(candidate_spec_json, payload.get("candidate_spec_draft", {}))
    write_markdown(report_md, payload)
    return report_json, candidate_spec_json, report_md
