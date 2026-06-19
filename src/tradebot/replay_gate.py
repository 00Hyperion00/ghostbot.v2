from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

REPLAY_GATE_CONTRACT_VERSION = "4B.4.3.6.6.29D"
RUNTIME_ACTIVATION_BLOCKED_BY_REPLAY_GATE = True
PAPER_LIVE_ORDER_BLOCKED_BY_REPLAY_GATE = True
TRAINING_RELOAD_BLOCKED_BY_REPLAY_GATE = True


@dataclass(frozen=True, slots=True)
class ReplayDigest:
    contract_version: str
    ok: bool
    row_count: int
    digest: str
    deterministic_replay: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ModelArtifactManifest:
    contract_version: str
    ok: bool
    model_path: str
    sha256: str
    byte_size: int
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class WalkForwardWindow:
    window_id: int
    train_start: int
    train_end: int
    test_start: int
    test_end: int

    def to_dict(self) -> dict[str, int]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class OOSGateDecision:
    contract_version: str
    ok: bool
    approved_for_promotion_review_candidate: bool
    approved_for_runtime_overlay_activation_candidate: bool
    approved_for_parameter_relaxation_candidate: bool
    approved_for_paper_candidate: bool
    approved_for_live_real: bool
    runtime_activation_blocked: bool
    paper_live_order_blocked: bool
    training_reload_blocked: bool
    reason_codes: list[str]
    metrics: dict[str, Any]
    thresholds: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _canonical_payload(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def deterministic_decision_replay_digest(rows: Iterable[Mapping[str, Any]]) -> ReplayDigest:
    normalized = [dict(row) for row in rows]
    digest = hashlib.sha256(_canonical_payload(normalized).encode("utf-8")).hexdigest()
    return ReplayDigest(REPLAY_GATE_CONTRACT_VERSION, True, len(normalized), digest, True)


def verify_replay_digest(rows: Iterable[Mapping[str, Any]], expected_digest: str) -> ReplayDigest:
    digest = deterministic_decision_replay_digest(rows)
    ok = digest.digest == str(expected_digest or "").strip()
    return ReplayDigest(digest.contract_version, ok, digest.row_count, digest.digest, ok)


def hash_model_artifact(model_path: str | Path, *, metadata: Mapping[str, Any] | None = None) -> ModelArtifactManifest:
    path = Path(model_path)
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Model artifact not found: {path}")
    hasher = hashlib.sha256()
    byte_size = 0
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            byte_size += len(chunk)
            hasher.update(chunk)
    return ModelArtifactManifest(REPLAY_GATE_CONTRACT_VERSION, True, path.as_posix(), hasher.hexdigest(), byte_size, dict(metadata or {}))


def build_walk_forward_windows(*, total_samples: int, train_size: int, test_size: int, step_size: int | None = None) -> list[WalkForwardWindow]:
    total, train, test = int(total_samples), int(train_size), int(test_size)
    step = int(step_size or test)
    if total <= 0 or train <= 0 or test <= 0 or step <= 0:
        raise ValueError("total_samples, train_size, test_size and step_size must be positive")
    windows: list[WalkForwardWindow] = []
    start = 0
    idx = 1
    while start + train + test <= total:
        windows.append(WalkForwardWindow(idx, start, start + train, start + train, start + train + test))
        start += step
        idx += 1
    return windows


def _float_metric(metrics: Mapping[str, Any], key: str, default: float = 0.0) -> float:
    try:
        return float(metrics.get(key, default))
    except (TypeError, ValueError):
        return default


def _int_metric(metrics: Mapping[str, Any], key: str, default: int = 0) -> int:
    try:
        return int(metrics.get(key, default))
    except (TypeError, ValueError):
        return default


def evaluate_oos_report_gate(
    metrics: Mapping[str, Any],
    *,
    min_matured_count: int = 30,
    min_win_rate_pct: float = 60.0,
    min_profit_factor: float = 1.5,
    min_mean_return_bps: float = 0.0,
    min_worst_return_bps: float = -500.0,
    min_worst_mae_bps: float = -500.0,
    min_unique_days: int = 3,
    min_regime_count: int = 2,
) -> OOSGateDecision:
    snapshot = dict(metrics)
    thresholds = {
        "min_matured_count": int(min_matured_count),
        "min_win_rate_pct": float(min_win_rate_pct),
        "min_profit_factor": float(min_profit_factor),
        "min_mean_return_bps": float(min_mean_return_bps),
        "min_worst_return_bps": float(min_worst_return_bps),
        "min_worst_mae_bps": float(min_worst_mae_bps),
        "min_unique_days": int(min_unique_days),
        "min_regime_count": int(min_regime_count),
    }
    reasons: list[str] = []
    if _int_metric(snapshot, "matured_count") < min_matured_count:
        reasons.append("OOS_MATURED_COUNT_BELOW_MIN")
    if _float_metric(snapshot, "win_rate_pct") < min_win_rate_pct:
        reasons.append("OOS_WIN_RATE_BELOW_MIN")
    if _float_metric(snapshot, "profit_factor") < min_profit_factor:
        reasons.append("OOS_PROFIT_FACTOR_BELOW_MIN")
    if _float_metric(snapshot, "mean_return_bps") <= min_mean_return_bps:
        reasons.append("OOS_MEAN_RETURN_NOT_POSITIVE")
    if _float_metric(snapshot, "worst_return_bps") < min_worst_return_bps:
        reasons.append("OOS_WORST_RETURN_BELOW_MIN")
    if _float_metric(snapshot, "worst_mae_bps") < min_worst_mae_bps:
        reasons.append("OOS_WORST_MAE_BELOW_MIN")
    if _int_metric(snapshot, "unique_oos_days", _int_metric(snapshot, "unique_days")) < min_unique_days:
        reasons.append("OOS_UNIQUE_DAY_COUNT_BELOW_MIN")
    if _int_metric(snapshot, "regime_count") < min_regime_count:
        reasons.append("OOS_REGIME_COUNT_BELOW_MIN")
    if bool(snapshot.get("duplicate_or_stagnation_detected", False)):
        reasons.append("OOS_DUPLICATE_OR_STAGNATION_DETECTED")
    if bool(snapshot.get("tail_risk_worsened", False)):
        reasons.append("OOS_TAIL_RISK_WORSENED")
    if bool(snapshot.get("measurement_guard_pass", True)) is False:
        reasons.append("OOS_MEASUREMENT_GUARD_FAILED")
    review = not reasons
    return OOSGateDecision(
        contract_version=REPLAY_GATE_CONTRACT_VERSION,
        ok=True,
        approved_for_promotion_review_candidate=review,
        approved_for_runtime_overlay_activation_candidate=False,
        approved_for_parameter_relaxation_candidate=False,
        approved_for_paper_candidate=False,
        approved_for_live_real=False,
        runtime_activation_blocked=True,
        paper_live_order_blocked=True,
        training_reload_blocked=True,
        reason_codes=reasons or ["OOS_GATE_PROMOTION_REVIEW_CANDIDATE_ONLY"],
        metrics=snapshot,
        thresholds=thresholds,
    )


def load_last_known_good_registry(registry_path: str | Path) -> dict[str, Any]:
    path = Path(registry_path)
    if not path.exists():
        return {"contract_version": REPLAY_GATE_CONTRACT_VERSION, "models": []}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Last-known-good registry must be a JSON object")
    payload.setdefault("contract_version", REPLAY_GATE_CONTRACT_VERSION)
    payload.setdefault("models", [])
    if not isinstance(payload["models"], list):
        raise ValueError("Last-known-good registry models must be a list")
    return payload


def register_last_known_good_model(
    registry_path: str | Path,
    manifest: ModelArtifactManifest | Mapping[str, Any],
    *,
    reason: str,
    gate_snapshot: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    path = Path(registry_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    registry = load_last_known_good_registry(path)
    manifest_payload = manifest.to_dict() if hasattr(manifest, "to_dict") else dict(manifest)
    entry = {"contract_version": REPLAY_GATE_CONTRACT_VERSION, "reason": str(reason or "").strip() or "LKG_REGISTERED", "manifest": manifest_payload, "gate_snapshot": dict(gate_snapshot or {})}
    registry["models"].append(entry)
    registry["latest"] = entry
    path.write_text(_canonical_payload(registry) + "\n", encoding="utf-8", newline="\n")
    return registry


def build_replay_gate_snapshot(metrics: Mapping[str, Any], model_path: str | Path | None = None) -> dict[str, Any]:
    decision = evaluate_oos_report_gate(metrics)
    payload: dict[str, Any] = {"contract_version": REPLAY_GATE_CONTRACT_VERSION, "ok": True, "decision": decision.to_dict(), "runtime_activation_blocked": True, "paper_live_order_blocked": True, "training_reload_blocked": True}
    if model_path is not None:
        payload["model_artifact"] = hash_model_artifact(model_path).to_dict()
    return payload
