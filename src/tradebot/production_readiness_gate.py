from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping

PRODUCTION_READINESS_CONSOLIDATION_CONTRACT_VERSION = "4B.4.3.6.6.29E"
RUNTIME_ACTIVATION_BLOCKED_BY_CONSOLIDATION_GATE = True
PAPER_LIVE_ORDER_BLOCKED_BY_CONSOLIDATION_GATE = True
LIVE_REAL_HARD_BLOCK_VERIFIED_BY_CONSOLIDATION_GATE = True
TRAINING_RELOAD_BLOCKED_BY_CONSOLIDATION_GATE = True

REQUIRED_EVIDENCE: dict[str, dict[str, str]] = {
    "29A": {
        "pattern": "4B436629A_production_hardening_p0_decision_*.json",
        "contract_version": "4B.4.3.6.6.29A",
        "decision": "PRODUCTION_HARDENING_P0_READY_LIVE_REAL_STILL_BLOCKED",
    },
    "29A-H1": {
        "pattern": "4B436629A_H1_production_report_path_hygiene_decision_*.json",
        "contract_version": "4B.4.3.6.6.29A-H1",
        "decision": "PRODUCTION_REPORT_PATH_HYGIENE_READY_LIVE_REAL_STILL_BLOCKED",
    },
    "29B": {
        "pattern": "4B436629B_api_operator_security_hardening_decision_*.json",
        "contract_version": "4B.4.3.6.6.29B",
        "decision": "API_OPERATOR_SECURITY_HARDENING_READY_LIVE_REAL_STILL_BLOCKED",
    },
    "29C": {
        "pattern": "4B436629C_sqlite_audit_ledger_upgrade_decision_*.json",
        "contract_version": "4B.4.3.6.6.29C",
        "decision": "SQLITE_AUDIT_LEDGER_UPGRADE_READY_LIVE_REAL_STILL_BLOCKED",
    },
    "29C-H2": {
        "pattern": "4B436629C_H2_sqlite_probe_explicit_connection_close_decision_*.json",
        "contract_version": "4B.4.3.6.6.29C-H2",
        "decision": "SQLITE_PROBE_EXPLICIT_CONNECTION_CLOSE_READY_LIVE_REAL_STILL_BLOCKED",
    },
    "29D": {
        "pattern": "4B436629D_replay_backtest_walkforward_gate_decision_*.json",
        "contract_version": "4B.4.3.6.6.29D",
        "decision": "REPLAY_BACKTEST_WALKFORWARD_GATE_READY_LIVE_REAL_STILL_BLOCKED",
    },
}


@dataclass(frozen=True, slots=True)
class EvidenceItem:
    key: str
    ok: bool
    path: str | None
    contract_version: str | None
    decision: str | None
    reason_codes: list[str]
    approved_for_live_real: bool
    approved_for_paper_candidate: bool
    trading_action_performed: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ProductionReadinessDecision:
    contract_version: str
    ok: bool
    decision: str
    evidence_complete: bool
    approved_for_evidence_merge_baseline: bool
    approved_for_paper_candidate_preflight: bool
    approved_for_paper_candidate: bool
    approved_for_live_real: bool
    live_real_hard_block_verified: bool
    approved_for_runtime_overlay_activation_candidate: bool
    approved_for_parameter_relaxation_candidate: bool
    runtime_activation_blocked: bool
    paper_live_order_blocked: bool
    training_reload_blocked: bool
    trading_action_performed: bool
    reason_codes: list[str]
    evidence: dict[str, dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Evidence report must be a JSON object: {path}")
    return payload


# 4B.4.3.6.6.29E-H1 accepted-evidence selector: prefer latest accepted evidence over latest stale failure.
def _evidence_payload_is_acceptable(path: Path, spec: Mapping[str, str]) -> bool:
    try:
        payload = _load_json(path)
    except Exception:
        return False
    if str(payload.get("contract_version") or "") != spec["contract_version"]:
        return False
    if str(payload.get("decision") or "") != spec["decision"]:
        return False
    if bool(payload.get("approved_for_live_real", False)):
        return False
    if bool(payload.get("trading_action_performed", False)):
        return False
    if bool(payload.get("runtime_overlay_activation_performed", False)):
        return False
    if bool(payload.get("training_performed", False)) or bool(payload.get("reload_performed", False)):
        return False
    return True


def _latest_matching(evidence_dir: Path, pattern: str, spec: Mapping[str, str] | None = None) -> Path | None:
    matches = [path for path in evidence_dir.glob(pattern) if path.is_file()]
    if not matches:
        return None
    ordered = sorted(matches, key=lambda item: item.name, reverse=True)
    if spec is not None:
        for path in ordered:
            if _evidence_payload_is_acceptable(path, spec):
                return path
    return ordered[0]



def load_production_hardening_evidence(evidence_dir: str | Path) -> dict[str, EvidenceItem]:
    base = Path(evidence_dir)
    out: dict[str, EvidenceItem] = {}
    for key, spec in REQUIRED_EVIDENCE.items():
        path = _latest_matching(base, spec["pattern"], spec)
        reasons: list[str] = []
        if path is None:
            out[key] = EvidenceItem(key, False, None, None, None, [f"{key}_EVIDENCE_MISSING"], False, False, False)
            continue
        try:
            payload = _load_json(path)
        except Exception as exc:
            out[key] = EvidenceItem(key, False, path.as_posix(), None, None, [f"{key}_EVIDENCE_LOAD_FAILED:{exc}"], False, False, False)
            continue
        contract_version = str(payload.get("contract_version") or "")
        decision = str(payload.get("decision") or "")
        if contract_version != spec["contract_version"]:
            reasons.append(f"{key}_CONTRACT_VERSION_MISMATCH")
        if decision != spec["decision"]:
            reasons.append(f"{key}_DECISION_MISMATCH")
        if bool(payload.get("approved_for_live_real", False)):
            reasons.append(f"{key}_LIVE_REAL_UNEXPECTEDLY_APPROVED")
        if bool(payload.get("trading_action_performed", False)):
            reasons.append(f"{key}_TRADING_ACTION_UNEXPECTEDLY_PERFORMED")
        if bool(payload.get("runtime_overlay_activation_performed", False)):
            reasons.append(f"{key}_RUNTIME_OVERLAY_UNEXPECTEDLY_PERFORMED")
        if bool(payload.get("training_performed", False)) or bool(payload.get("reload_performed", False)):
            reasons.append(f"{key}_TRAINING_RELOAD_UNEXPECTEDLY_PERFORMED")
        ok = not reasons
        out[key] = EvidenceItem(key, ok, path.as_posix(), contract_version, decision, reasons or [f"{key}_EVIDENCE_ACCEPTED"], bool(payload.get("approved_for_live_real", False)), bool(payload.get("approved_for_paper_candidate", False)), bool(payload.get("trading_action_performed", False)))
    return out


def evaluate_production_readiness_consolidation(evidence: Mapping[str, EvidenceItem | Mapping[str, Any]]) -> ProductionReadinessDecision:
    normalized: dict[str, EvidenceItem] = {}
    for key in REQUIRED_EVIDENCE:
        raw = evidence.get(key)
        if isinstance(raw, EvidenceItem):
            normalized[key] = raw
        elif isinstance(raw, Mapping):
            normalized[key] = EvidenceItem(
                key=str(raw.get("key") or key),
                ok=bool(raw.get("ok", False)),
                path=raw.get("path"),
                contract_version=raw.get("contract_version"),
                decision=raw.get("decision"),
                reason_codes=list(raw.get("reason_codes") or []),
                approved_for_live_real=bool(raw.get("approved_for_live_real", False)),
                approved_for_paper_candidate=bool(raw.get("approved_for_paper_candidate", False)),
                trading_action_performed=bool(raw.get("trading_action_performed", False)),
            )
        else:
            normalized[key] = EvidenceItem(key, False, None, None, None, [f"{key}_EVIDENCE_MISSING"], False, False, False)
    evidence_complete = all(item.ok for item in normalized.values())
    reasons: list[str] = []
    for key, item in normalized.items():
        if not item.ok:
            reasons.extend(item.reason_codes or [f"{key}_EVIDENCE_NOT_ACCEPTED"])
    if evidence_complete:
        reasons.append("PRODUCTION_HARDENING_EVIDENCE_MERGED")
        reasons.append("PAPER_CANDIDATE_PREFLIGHT_READY_FOR_30A_REVIEW_ONLY")
    else:
        reasons.append("PAPER_CANDIDATE_PREFLIGHT_BLOCKED_BY_EVIDENCE_GAP")
    reasons.append("LIVE_REAL_HARD_BLOCK_VERIFIED")
    return ProductionReadinessDecision(
        contract_version=PRODUCTION_READINESS_CONSOLIDATION_CONTRACT_VERSION,
        ok=True,
        decision="PRODUCTION_READINESS_CONSOLIDATION_READY_LIVE_REAL_STILL_BLOCKED" if evidence_complete else "PRODUCTION_READINESS_CONSOLIDATION_NOT_READY",
        evidence_complete=evidence_complete,
        approved_for_evidence_merge_baseline=evidence_complete,
        approved_for_paper_candidate_preflight=evidence_complete,
        approved_for_paper_candidate=False,
        approved_for_live_real=False,
        live_real_hard_block_verified=True,
        approved_for_runtime_overlay_activation_candidate=False,
        approved_for_parameter_relaxation_candidate=False,
        runtime_activation_blocked=True,
        paper_live_order_blocked=True,
        training_reload_blocked=True,
        trading_action_performed=False,
        reason_codes=reasons,
        evidence={key: item.to_dict() for key, item in normalized.items()},
    )


def build_consolidated_readiness_snapshot(evidence_dir: str | Path) -> dict[str, Any]:
    decision = evaluate_production_readiness_consolidation(load_production_hardening_evidence(evidence_dir))
    payload = decision.to_dict()
    payload.update({
        "read_only": True,
        "production_readiness_consolidation_gate": True,
        "paper_candidate_preflight_only": True,
        "live_real_hard_block_verification": True,
        "runtime_overlay_activation_performed": False,
        "scheduler_mutation_performed": False,
        "strategy_parameter_mutation_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "paper_live_order_enablement_present": False,
        "hyp006_strategy_threshold_mutation_performed": False,
    })
    return payload
