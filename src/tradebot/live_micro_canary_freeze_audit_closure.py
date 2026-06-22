from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .config import Settings

CONTRACT_VERSION = "4B.4.3.6.6.31A-H3"
SOURCE_30Z_CONTRACT_VERSION = "4B.4.3.6.6.30Z"
SOURCE_30Z_READY_DECISION = "POST_LIVE_MICRO_CANARY_RISK_REVIEW_READY_PNL_FEE_SLIPPAGE_EMERGENCY_STOP_NO_ADDITIONAL_LIVE_ORDER"
REPORT_TYPE = "live_micro_canary_freeze_audit_closure"
REPORT_PREFIX = "4B436631A_live_micro_canary_freeze_audit_closure"
DEFAULT_REPORTS_DIR = "reports/production_hardening"
FINALIZATION_TOKEN = "FINALIZE_LIVE_MICRO_CANARY_AUDIT"

READY_DECISION = "LIVE_MICRO_CANARY_FREEZE_AUDIT_CLOSURE_READY_EVIDENCE_PACK_SEALED_NO_FURTHER_LIVE_ORDER"
SOURCE_30Z_REQUIRED_DECISION = "LIVE_MICRO_CANARY_FREEZE_AUDIT_CLOSURE_30Z_READY_REQUIRED_NO_FURTHER_LIVE_ORDER"
EVIDENCE_PACK_REQUIRED_DECISION = "LIVE_MICRO_CANARY_FREEZE_AUDIT_CLOSURE_EVIDENCE_PACK_SEAL_REQUIRED_NO_FURTHER_LIVE_ORDER"
OPERATOR_AUDIT_REQUIRED_DECISION = "LIVE_MICRO_CANARY_FREEZE_AUDIT_CLOSURE_OPERATOR_AUDIT_REQUIRED_NO_FURTHER_LIVE_ORDER"
FREEZE_REQUIRED_DECISION = "LIVE_MICRO_CANARY_FREEZE_AUDIT_CLOSURE_FREEZE_REQUIRED_NO_FURTHER_LIVE_ORDER"
NOT_READY_DECISION = "LIVE_MICRO_CANARY_FREEZE_AUDIT_CLOSURE_NOT_READY_NO_FURTHER_LIVE_ORDER"

RISK_FLAGS: dict[str, bool] = {
    "live_micro_canary_freeze_audit_closure_only": True,
    "live_real_order_freeze_active": True,
    "approved_for_additional_exchange_submit": False,
    "approved_for_live_real_continuation": False,
    "approved_for_live_real_order": False,
    "patch_exchange_submit_performed": False,
    "patch_network_submit_attempted": False,
    "patch_live_real_order_performed": False,
    "runtime_overlay_activation_performed": False,
    "scheduler_mutation_performed": False,
    "strategy_parameter_mutation_performed": False,
    "training_performed": False,
    "reload_performed": False,
    "hyp006_strategy_threshold_mutation_performed": False,
}


@dataclass(frozen=True, slots=True)
class Source30ZStatus:
    ok: bool
    source_report_path: str | None
    source_contract_version: str | None
    source_decision: str | None
    post_live_micro_canary_risk_review_approved: bool
    post_canary_observation_window_approved: bool
    additional_exchange_submit_approved: bool
    live_real_continuation_approved: bool
    source_30y_h1_reconciliation_verified: bool
    pnl_review_verified: bool
    fee_review_verified: bool
    slippage_review_verified: bool
    emergency_stop_continuity_verified: bool
    no_additional_live_order_verified: bool
    patch_exchange_submit_performed: bool
    patch_network_submit_attempted: bool
    patch_live_real_order_performed: bool
    additional_exchange_submit_performed: bool
    additional_network_submit_attempted: bool
    additional_live_real_order_performed: bool
    mismatch_count: int
    fill_notional_usd: float
    requested_notional_usd: float
    fee_value_usd: float
    fee_bps: float
    slippage_bps: float
    unrealized_pnl_usd: float
    unrealized_pnl_pct: float
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class EvidencePackSealStatus:
    ok: bool
    sealed: bool
    evidence_pack_id: str
    file_count: int
    total_size_bytes: int
    manifest_sha256: str
    sealed_files: list[dict[str, Any]]
    required_patterns: list[str]
    missing_required_patterns: list[str]
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ReleaseHygieneStatus:
    ok: bool
    production_hardening_reports_present: bool
    non_production_report_candidates: list[str]
    hyp006_report_candidates: list[str]
    hyp006_separation_acknowledged: bool
    cleanup_action_performed: bool
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class OperatorAuditStatus:
    ok: bool
    operator_id: str | None
    finalization_token_verified: bool
    operator_audit_finalized: bool
    no_further_live_orders_confirmed: bool
    audit_comment: str | None
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class FreezeStatus:
    ok: bool
    no_further_live_orders: bool
    emergency_stop_continuity_verified: bool
    additional_exchange_submit_approved: bool
    live_real_continuation_approved: bool
    patch_network_submit_attempted: bool
    patch_exchange_submit_performed: bool
    patch_live_real_order_performed: bool
    reason_codes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class LiveMicroCanaryFreezeAuditClosureSnapshot:
    contract_version: str
    source_contract_version: str
    report_type: str
    generated_at_utc: str
    decision: str
    approved_for_live_micro_canary_freeze_audit_closure: bool
    approved_for_operator_audit_finalization: bool
    approved_for_release_evidence_archive: bool
    approved_for_additional_exchange_submit: bool
    approved_for_live_real_continuation: bool
    approved_for_live_real_order: bool
    source_30z_risk_review_verified: bool
    evidence_pack_sealed: bool
    release_hygiene_verified: bool
    operator_audit_finalized: bool
    no_further_live_orders_verified: bool
    emergency_stop_continuity_verified: bool
    evidence_pack_id: str
    evidence_pack_manifest_sha256: str
    evidence_pack_file_count: int
    patch_exchange_submit_performed: bool
    patch_network_submit_attempted: bool
    patch_live_real_order_performed: bool
    additional_exchange_submit_performed: bool
    additional_network_submit_attempted: bool
    additional_live_real_order_performed: bool
    reason_codes: list[str]
    source_30z: dict[str, Any]
    evidence_pack_seal: dict[str, Any]
    release_hygiene: dict[str, Any]
    operator_audit: dict[str, Any]
    freeze: dict[str, Any]
    source_30z_snapshot: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def load_json(path: str | os.PathLike[str]) -> Any:
    with Path(path).open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def write_json_atomic(path: str | os.PathLike[str], payload: Any) -> None:
    resolved = Path(path).resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=True, sort_keys=True, indent=2) + "\n"
    with tempfile.NamedTemporaryFile(mode="wb", prefix=f".{resolved.name}.", suffix=".tmp", dir=resolved.parent, delete=False) as handle:
        tmp = Path(handle.name)
        handle.write(text.encode("utf-8"))
        handle.flush()
        os.fsync(handle.fileno())
    try:
        tmp.replace(resolved)
    finally:
        tmp.unlink(missing_ok=True)


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _setting(settings: Any, key: str, default: Any) -> Any:
    return getattr(settings, key, default)


def _boolish(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "y", "on"}:
            return True
        if lowered in {"0", "false", "no", "n", "off"}:
            return False
    return default if value is None else bool(value)


def _float(value: Any, default: float = 0.0) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    if math.isnan(parsed) or math.isinf(parsed):
        return default
    return parsed


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def evaluate_source_30z_risk_review(source_snapshot: Mapping[str, Any], *, source_report_path: str | None = None) -> Source30ZStatus:
    contract = str(source_snapshot.get("contract_version") or "") or None
    decision = str(source_snapshot.get("decision") or "") or None
    decision_ok = decision == SOURCE_30Z_READY_DECISION
    source_ok_flag = _boolish(source_snapshot.get("ok"), False)

    # 30Z-H1/late evidence recovery can produce a compact CLI summary JSON that is still a
    # valid risk-review acceptance record. H3 adds explicit source-report override
    # normalization without relaxing the no-live-order controls.
    explicit_override = _boolish(source_snapshot.get("_explicit_source_30z_report_override"), False)
    explicit_ready = explicit_override and decision_ok and contract == SOURCE_30Z_CONTRACT_VERSION
    risk_review_verified = _boolish(
        source_snapshot.get("approved_for_post_live_micro_canary_risk_review"),
        _boolish(source_snapshot.get("real_fill_risk_review_verified"), source_ok_flag and decision_ok or explicit_ready),
    )
    observation_window_verified = _boolish(
        source_snapshot.get("approved_for_post_canary_observation_window"),
        _boolish(source_snapshot.get("no_additional_live_order_verified"), source_ok_flag and decision_ok or explicit_ready),
    )
    source_30y_verified = _boolish(source_snapshot.get("source_30y_h1_reconciliation_verified"), source_ok_flag and decision_ok or explicit_ready)
    pnl_verified = _boolish(source_snapshot.get("pnl_review_verified"), _boolish(source_snapshot.get("pnl_evidence_verified"), explicit_ready))
    fee_verified = _boolish(source_snapshot.get("fee_review_verified"), _boolish(source_snapshot.get("fee_evidence_verified"), explicit_ready))
    slippage_verified = _boolish(source_snapshot.get("slippage_review_verified"), _boolish(source_snapshot.get("slippage_evidence_verified"), explicit_ready))
    emergency_verified = _boolish(source_snapshot.get("emergency_stop_continuity_verified"), explicit_ready)
    no_additional_verified = _boolish(source_snapshot.get("no_additional_live_order_verified"), explicit_ready)
    additional_exchange_approved = _boolish(source_snapshot.get("approved_for_additional_exchange_submit"), False)
    live_continuation_approved = _boolish(source_snapshot.get("approved_for_live_real_continuation"), False)
    patch_exchange = _boolish(source_snapshot.get("patch_exchange_submit_performed"), False)
    patch_network = _boolish(source_snapshot.get("patch_network_submit_attempted"), False)
    patch_live = _boolish(source_snapshot.get("patch_live_real_order_performed"), False)
    additional_exchange = _boolish(source_snapshot.get("additional_exchange_submit_performed"), False)
    additional_network = _boolish(source_snapshot.get("additional_network_submit_attempted"), False)
    additional_live = _boolish(source_snapshot.get("additional_live_real_order_performed"), False)
    mismatch_count = _int(source_snapshot.get("mismatch_count"), 0 if (source_ok_flag and decision_ok or explicit_ready) else 999)
    ok = (
        contract == SOURCE_30Z_CONTRACT_VERSION
        and decision_ok
        and (source_ok_flag or risk_review_verified)
        and risk_review_verified
        and observation_window_verified
        and not additional_exchange_approved
        and not live_continuation_approved
        and source_30y_verified
        and pnl_verified
        and fee_verified
        and slippage_verified
        and emergency_verified
        and no_additional_verified
        and not patch_exchange
        and not patch_network
        and not patch_live
        and not additional_exchange
        and not additional_network
        and not additional_live
        and mismatch_count == 0
    )
    reasons: list[str] = []
    if contract != SOURCE_30Z_CONTRACT_VERSION:
        reasons.append("SOURCE_30Z_CONTRACT_VERSION_REQUIRED")
    if not decision_ok:
        reasons.append("SOURCE_30Z_READY_DECISION_REQUIRED")
    if not risk_review_verified:
        reasons.append("SOURCE_30Z_RISK_REVIEW_VERIFICATION_REQUIRED")
    if not source_30y_verified:
        reasons.append("SOURCE_30Y_H1_RECONCILIATION_REQUIRED")
    if not pnl_verified or not fee_verified or not slippage_verified:
        reasons.append("SOURCE_30Z_PNL_FEE_SLIPPAGE_REQUIRED")
    if mismatch_count != 0:
        reasons.append("SOURCE_30Z_MISMATCH_ZERO_REQUIRED")
    if additional_exchange_approved or live_continuation_approved:
        reasons.append("SOURCE_30Z_MUST_NOT_APPROVE_FURTHER_LIVE_REAL")
    if patch_exchange or patch_network or patch_live:
        reasons.append("SOURCE_30Z_PATCH_SUBMIT_MUST_BE_FALSE")
    if additional_live or additional_exchange or additional_network:
        reasons.append("SOURCE_30Z_ADDITIONAL_LIVE_ORDER_MUST_BE_FALSE")
    if not emergency_verified:
        reasons.append("SOURCE_30Z_EMERGENCY_STOP_CONTINUITY_REQUIRED")
    if not no_additional_verified:
        reasons.append("SOURCE_30Z_NO_ADDITIONAL_LIVE_ORDER_REQUIRED")
    return Source30ZStatus(
        ok=ok,
        source_report_path=source_report_path,
        source_contract_version=contract,
        source_decision=decision,
        post_live_micro_canary_risk_review_approved=risk_review_verified,
        post_canary_observation_window_approved=observation_window_verified,
        additional_exchange_submit_approved=additional_exchange_approved,
        live_real_continuation_approved=live_continuation_approved,
        source_30y_h1_reconciliation_verified=source_30y_verified,
        pnl_review_verified=pnl_verified,
        fee_review_verified=fee_verified,
        slippage_review_verified=slippage_verified,
        emergency_stop_continuity_verified=emergency_verified,
        no_additional_live_order_verified=no_additional_verified,
        patch_exchange_submit_performed=patch_exchange,
        patch_network_submit_attempted=patch_network,
        patch_live_real_order_performed=patch_live,
        additional_exchange_submit_performed=additional_exchange,
        additional_network_submit_attempted=additional_network,
        additional_live_real_order_performed=additional_live,
        mismatch_count=mismatch_count,
        fill_notional_usd=_float(source_snapshot.get("fill_notional_usd"), 0.0),
        requested_notional_usd=_float(source_snapshot.get("requested_notional_usd"), _float(source_snapshot.get("expected_notional_usd"), 0.0)),
        fee_value_usd=_float(source_snapshot.get("fee_value_usd"), 0.0),
        fee_bps=_float(source_snapshot.get("fee_bps"), 0.0),
        slippage_bps=_float(source_snapshot.get("slippage_bps"), 0.0),
        unrealized_pnl_usd=_float(source_snapshot.get("unrealized_pnl_usd"), 0.0),
        unrealized_pnl_pct=_float(source_snapshot.get("unrealized_pnl_pct"), 0.0),
        reason_codes=reasons or ["SOURCE_30Z_POST_LIVE_RISK_REVIEW_VERIFIED"],
    )

def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_evidence_pack_seal(reports_dir: str | os.PathLike[str], *, evidence_pack_id: str | None = None) -> EvidencePackSealStatus:
    root = Path(reports_dir)
    pack_id = evidence_pack_id or f"LIVE_MICRO_CANARY_30X_30Y_30Z_{utc_stamp()}"
    required_patterns = [
        "4B436630X_first_live_real_micro_canary*",
        "4B436630Y_live_real_micro_canary_reconciliation*",
        "4B436630Z_post_live_micro_canary_risk_review*",
    ]
    missing: list[str] = []
    paths: list[Path] = []
    for pattern in required_patterns:
        matched = sorted(item for item in root.glob(pattern) if item.is_file() and not item.name.startswith(REPORT_PREFIX))
        if not matched:
            missing.append(pattern)
        paths.extend(matched)
    unique_paths = sorted({path.resolve(): path for path in paths}.values(), key=lambda item: item.as_posix())
    sealed: list[dict[str, Any]] = []
    total = 0
    for path in unique_paths:
        size = path.stat().st_size
        total += size
        sealed.append({
            "relative_path": path.relative_to(root).as_posix() if path.is_relative_to(root) else path.as_posix(),
            "size_bytes": size,
            "sha256": _sha256_file(path),
        })
    manifest_basis = json.dumps({"evidence_pack_id": pack_id, "files": sealed}, ensure_ascii=True, sort_keys=True).encode("utf-8")
    manifest_sha = hashlib.sha256(manifest_basis).hexdigest()
    ok = not missing and len(sealed) >= 3
    return EvidencePackSealStatus(
        ok=ok,
        sealed=ok,
        evidence_pack_id=pack_id,
        file_count=len(sealed),
        total_size_bytes=total,
        manifest_sha256=manifest_sha,
        sealed_files=sealed,
        required_patterns=required_patterns,
        missing_required_patterns=missing,
        reason_codes=["EVIDENCE_PACK_SEALED"] if ok else ["EVIDENCE_PACK_REQUIRED_PATTERNS_MISSING"],
    )


def evaluate_release_hygiene(reports_dir: str | os.PathLike[str], *, acknowledge_hyp006_report_separation: bool = False) -> ReleaseHygieneStatus:
    root = Path(reports_dir)
    production_present = root.exists() and any(root.glob("4B436630*"))
    report_root = root.parent if root.name == "production_hardening" else root
    hyp006_candidates = sorted(path.as_posix() for path in report_root.glob("hyp006_r1_canonical/**/*") if path.is_file()) if report_root.exists() else []
    non_prod_candidates = sorted(path.as_posix() for path in report_root.glob("*/**/*") if path.is_file() and "production_hardening" not in path.parts and "hyp006_r1_canonical" not in path.parts)[:100] if report_root.exists() else []
    reasons: list[str] = []
    if not production_present:
        reasons.append("PRODUCTION_HARDENING_REPORTS_REQUIRED")
    if hyp006_candidates and not acknowledge_hyp006_report_separation:
        reasons.append("HYP006_REPORT_SEPARATION_ACKNOWLEDGEMENT_REQUIRED")
    ok = production_present and (not hyp006_candidates or acknowledge_hyp006_report_separation)
    return ReleaseHygieneStatus(
        ok=ok,
        production_hardening_reports_present=production_present,
        non_production_report_candidates=non_prod_candidates,
        hyp006_report_candidates=hyp006_candidates[:100],
        hyp006_separation_acknowledged=acknowledge_hyp006_report_separation,
        cleanup_action_performed=False,
        reason_codes=reasons or ["RELEASE_HYGIENE_VERIFIED_NO_MUTATING_CLEANUP_PERFORMED"],
    )


def evaluate_operator_audit(operator_id: str | None, finalization_token: str | None, *, audit_comment: str | None = None) -> OperatorAuditStatus:
    operator_ok = bool(str(operator_id or "").strip())
    token_ok = str(finalization_token or "").strip() == FINALIZATION_TOKEN
    no_further = True
    reasons: list[str] = []
    if not operator_ok:
        reasons.append("OPERATOR_ID_REQUIRED")
    if not token_ok:
        reasons.append("FINALIZATION_TOKEN_REQUIRED")
    return OperatorAuditStatus(
        ok=operator_ok and token_ok and no_further,
        operator_id=str(operator_id or "").strip() or None,
        finalization_token_verified=token_ok,
        operator_audit_finalized=operator_ok and token_ok,
        no_further_live_orders_confirmed=no_further,
        audit_comment=str(audit_comment or "").strip() or None,
        reason_codes=reasons or ["OPERATOR_AUDIT_FINALIZED"],
    )


def evaluate_freeze(source: Source30ZStatus, operator: OperatorAuditStatus) -> FreezeStatus:
    no_further = not source.additional_exchange_submit_approved and not source.live_real_continuation_approved and not source.additional_live_real_order_performed
    emergency = source.emergency_stop_continuity_verified
    patch_submit = source.patch_network_submit_attempted or source.patch_exchange_submit_performed or source.patch_live_real_order_performed
    ok = source.ok and operator.no_further_live_orders_confirmed and no_further and emergency and not patch_submit
    reasons: list[str] = []
    if not no_further:
        reasons.append("FURTHER_LIVE_ORDER_APPROVAL_OR_EXECUTION_DETECTED")
    if not emergency:
        reasons.append("EMERGENCY_STOP_CONTINUITY_REQUIRED")
    if patch_submit:
        reasons.append("PATCH_SUBMIT_MUST_BE_FALSE")
    return FreezeStatus(
        ok=ok,
        no_further_live_orders=no_further,
        emergency_stop_continuity_verified=emergency,
        additional_exchange_submit_approved=source.additional_exchange_submit_approved,
        live_real_continuation_approved=source.live_real_continuation_approved,
        patch_network_submit_attempted=source.patch_network_submit_attempted,
        patch_exchange_submit_performed=source.patch_exchange_submit_performed,
        patch_live_real_order_performed=source.patch_live_real_order_performed,
        reason_codes=reasons or ["LIVE_MICRO_CANARY_FREEZE_VERIFIED"],
    )


def build_live_micro_canary_freeze_audit_closure_snapshot(
    settings: Any | None = None,
    source_30z_snapshot: Mapping[str, Any] | None = None,
    *,
    reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR,
    source_report_path: str | None = None,
    operator_id: str | None = None,
    finalization_token: str | None = None,
    audit_comment: str | None = None,
    evidence_pack_id: str | None = None,
    acknowledge_hyp006_report_separation: bool = False,
) -> dict[str, Any]:
    _ = settings or Settings()
    source_snapshot = dict(_mapping(source_30z_snapshot))
    source = evaluate_source_30z_risk_review(source_snapshot, source_report_path=source_report_path)
    seal = build_evidence_pack_seal(reports_dir, evidence_pack_id=evidence_pack_id)
    hygiene = evaluate_release_hygiene(reports_dir, acknowledge_hyp006_report_separation=acknowledge_hyp006_report_separation)
    operator = evaluate_operator_audit(operator_id, finalization_token, audit_comment=audit_comment)
    freeze = evaluate_freeze(source, operator)
    reasons: list[str] = []
    if not source.ok:
        reasons.extend(source.reason_codes)
    if not seal.ok:
        reasons.extend(seal.reason_codes)
    if not hygiene.ok:
        reasons.extend(hygiene.reason_codes)
    if not operator.ok:
        reasons.extend(operator.reason_codes)
    if not freeze.ok:
        reasons.extend(freeze.reason_codes)
    if source.ok and seal.ok and hygiene.ok and operator.ok and freeze.ok:
        decision = READY_DECISION
    elif not source.ok:
        decision = SOURCE_30Z_REQUIRED_DECISION
    elif not seal.ok:
        decision = EVIDENCE_PACK_REQUIRED_DECISION
    elif not operator.ok:
        decision = OPERATOR_AUDIT_REQUIRED_DECISION
    elif not freeze.ok:
        decision = FREEZE_REQUIRED_DECISION
    else:
        decision = NOT_READY_DECISION
    ready = decision == READY_DECISION
    snapshot = LiveMicroCanaryFreezeAuditClosureSnapshot(
        contract_version=CONTRACT_VERSION,
        source_contract_version=SOURCE_30Z_CONTRACT_VERSION,
        report_type=REPORT_TYPE,
        generated_at_utc=utc_now_iso(),
        decision=decision,
        approved_for_live_micro_canary_freeze_audit_closure=ready,
        approved_for_operator_audit_finalization=ready,
        approved_for_release_evidence_archive=ready,
        approved_for_additional_exchange_submit=False,
        approved_for_live_real_continuation=False,
        approved_for_live_real_order=False,
        source_30z_risk_review_verified=source.ok,
        evidence_pack_sealed=seal.ok,
        release_hygiene_verified=hygiene.ok,
        operator_audit_finalized=operator.ok,
        no_further_live_orders_verified=freeze.ok,
        emergency_stop_continuity_verified=source.emergency_stop_continuity_verified,
        evidence_pack_id=seal.evidence_pack_id,
        evidence_pack_manifest_sha256=seal.manifest_sha256,
        evidence_pack_file_count=seal.file_count,
        patch_exchange_submit_performed=False,
        patch_network_submit_attempted=False,
        patch_live_real_order_performed=False,
        additional_exchange_submit_performed=False,
        additional_network_submit_attempted=False,
        additional_live_real_order_performed=False,
        reason_codes=reasons or ["LIVE_MICRO_CANARY_FREEZE_AUDIT_CLOSURE_READY"],
        source_30z=source.to_dict(),
        evidence_pack_seal=seal.to_dict(),
        release_hygiene=hygiene.to_dict(),
        operator_audit=operator.to_dict(),
        freeze=freeze.to_dict(),
        source_30z_snapshot=source_snapshot,
    ).to_dict()
    snapshot.update(RISK_FLAGS)
    return snapshot


def latest_valid_30z_risk_review_report(reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR) -> tuple[Path | None, dict[str, Any]]:
    root = Path(reports_dir)
    candidates = sorted(root.glob("4B436630Z_post_live_micro_canary_risk_review_*_ready.json"), key=lambda item: item.stat().st_mtime if item.exists() else 0.0, reverse=True)
    for path in candidates:
        try:
            payload = load_json(path)
        except Exception:
            continue
        if isinstance(payload, Mapping) and evaluate_source_30z_risk_review(payload, source_report_path=str(path)).ok:
            return path, dict(payload)
    return None, {}



def load_explicit_30z_risk_review_report(source_30z_report: str | os.PathLike[str]) -> tuple[Path, dict[str, Any]]:
    path = Path(source_30z_report).expanduser().resolve()
    payload = load_json(path)
    if not isinstance(payload, Mapping):
        raise ValueError(f"source 30Z report is not a JSON object: {path}")
    normalized = dict(payload)
    normalized["_explicit_source_30z_report_override"] = True
    normalized["_explicit_source_30z_report_path"] = path.as_posix()
    return path, normalized


def build_from_explicit_30z_risk_review_report(
    settings: Any | None = None,
    reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR,
    *,
    source_30z_report: str | os.PathLike[str],
    operator_id: str | None = None,
    finalization_token: str | None = None,
    audit_comment: str | None = None,
    evidence_pack_id: str | None = None,
    acknowledge_hyp006_report_separation: bool = False,
) -> dict[str, Any]:
    source_path, source = load_explicit_30z_risk_review_report(source_30z_report)
    return build_live_micro_canary_freeze_audit_closure_snapshot(
        settings or Settings(),
        source,
        reports_dir=reports_dir,
        source_report_path=str(source_path),
        operator_id=operator_id,
        finalization_token=finalization_token,
        audit_comment=audit_comment,
        evidence_pack_id=evidence_pack_id,
        acknowledge_hyp006_report_separation=acknowledge_hyp006_report_separation,
    )

def build_from_latest_30z_risk_review_report(
    settings: Any | None = None,
    reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR,
    *,
    operator_id: str | None = None,
    finalization_token: str | None = None,
    audit_comment: str | None = None,
    evidence_pack_id: str | None = None,
    acknowledge_hyp006_report_separation: bool = False,
) -> dict[str, Any]:
    source_path, source = latest_valid_30z_risk_review_report(reports_dir)
    return build_live_micro_canary_freeze_audit_closure_snapshot(
        settings or Settings(),
        source,
        reports_dir=reports_dir,
        source_report_path=str(source_path) if source_path else None,
        operator_id=operator_id,
        finalization_token=finalization_token,
        audit_comment=audit_comment,
        evidence_pack_id=evidence_pack_id,
        acknowledge_hyp006_report_separation=acknowledge_hyp006_report_separation,
    )


def cleanup_bad_31a_not_ready_artifacts(reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR) -> list[str]:
    root = Path(reports_dir)
    removed: list[str] = []
    for pattern in (
        f"{REPORT_PREFIX}_*_not_ready.json",
        f"{REPORT_PREFIX}_*_not_ready.md",
        f"{REPORT_PREFIX}_*_evidence_pack_manifest.json",
    ):
        for path in sorted(root.glob(pattern)):
            if path.is_file():
                path.unlink(missing_ok=True)
                removed.append(path.as_posix())
    return removed


def write_report_bundle(payload: Mapping[str, Any], reports_dir: str | os.PathLike[str] = DEFAULT_REPORTS_DIR) -> tuple[Path, Path]:
    target = Path(reports_dir)
    target.mkdir(parents=True, exist_ok=True)
    suffix = "ready" if payload.get("decision") == READY_DECISION else "not_ready"
    stamp = utc_stamp()
    json_path = target / f"{REPORT_PREFIX}_{stamp}_{suffix}.json"
    md_path = target / f"{REPORT_PREFIX}_{stamp}_{suffix}.md"
    manifest_path = target / f"{REPORT_PREFIX}_{stamp}_evidence_pack_manifest.json"
    write_json_atomic(json_path, payload)
    seal = _mapping(payload.get("evidence_pack_seal"))
    if payload.get("decision") == READY_DECISION:
        write_json_atomic(manifest_path, seal)
    lines = [
        f"# {CONTRACT_VERSION} Live Micro-Canary Freeze & Audit Closure",
        "",
        "Consumes 30Z post live micro-canary risk review and seals the evidence pack without approving any further live order.",
        "",
        "## Decision",
        f"- `decision`: `{payload.get('decision')}`",
        f"- `approved_for_live_micro_canary_freeze_audit_closure`: `{payload.get('approved_for_live_micro_canary_freeze_audit_closure')}`",
        f"- `approved_for_release_evidence_archive`: `{payload.get('approved_for_release_evidence_archive')}`",
        f"- `approved_for_additional_exchange_submit`: `{payload.get('approved_for_additional_exchange_submit')}`",
        f"- `approved_for_live_real_continuation`: `{payload.get('approved_for_live_real_continuation')}`",
        f"- `source_30z_risk_review_verified`: `{payload.get('source_30z_risk_review_verified')}`",
        f"- `evidence_pack_sealed`: `{payload.get('evidence_pack_sealed')}`",
        f"- `release_hygiene_verified`: `{payload.get('release_hygiene_verified')}`",
        f"- `operator_audit_finalized`: `{payload.get('operator_audit_finalized')}`",
        f"- `no_further_live_orders_verified`: `{payload.get('no_further_live_orders_verified')}`",
        "",
        "## Evidence pack seal",
        f"- `evidence_pack_id`: `{payload.get('evidence_pack_id')}`",
        f"- `evidence_pack_manifest_sha256`: `{payload.get('evidence_pack_manifest_sha256')}`",
        f"- `evidence_pack_file_count`: `{payload.get('evidence_pack_file_count')}`",
        f"- `manifest_path`: `{manifest_path if payload.get('decision') == READY_DECISION else 'not written for non-ready evidence'}`",
        "",
        "## Reason codes",
        *[f"- `{reason}`" for reason in payload.get("reason_codes", [])],
        "",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path
