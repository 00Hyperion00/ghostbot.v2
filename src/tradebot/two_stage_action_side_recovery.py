from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from math import log2
from pathlib import Path
from statistics import mean, median
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import pandas as pd

from tradebot.cost_aware_label_policy_recovery import (
    CostAwareLabelPolicyCandidate,
    default_cost_aware_label_policy_candidates,
)
from tradebot.features import FEATURE_COLUMNS, clean_feature_frame
from tradebot.training.labeling import build_cost_aware_atr_targets

TWO_STAGE_ACTION_SIDE_CONTRACT_VERSION = "4B.4.3.6.6.24K"
TARGET_NAMES = {0: "HOLD", 1: "BUY", 2: "SELL"}
ACTION_IDS = (1, 2)


@dataclass(frozen=True, slots=True)
class TwoStageActionSideCandidateSpec:
    label_policy: CostAwareLabelPolicyCandidate
    action_profile: str = "balanced"
    side_profile: str = "balanced"
    action_threshold_profile: str = "balanced"
    side_margin_profile: str = "guarded"
    feature_lag: int | None = None
    max_depth: int = 3
    n_estimators: int = 32
    learning_rate: float = 0.04

    def slug(self) -> str:
        lag = "auto" if self.feature_lag is None else str(int(self.feature_lag))
        parts = [
            self.label_policy.name,
            f"action_{self.action_profile}",
            f"side_{self.side_profile}",
            f"ath_{self.action_threshold_profile}",
            f"sm_{self.side_margin_profile}",
            f"lag{lag}",
        ]
        return "_".join(str(part).replace(" ", "_") for part in parts)

    def to_dict(self) -> dict[str, Any]:
        return {
            "label_policy": self.label_policy.to_dict(),
            "action_profile": str(self.action_profile),
            "side_profile": str(self.side_profile),
            "action_threshold_profile": str(self.action_threshold_profile),
            "side_margin_profile": str(self.side_margin_profile),
            "feature_lag": self.feature_lag,
            "max_depth": int(self.max_depth),
            "n_estimators": int(self.n_estimators),
            "learning_rate": float(self.learning_rate),
        }


@dataclass(frozen=True, slots=True)
class TwoStageGateLimits:
    min_clean_samples: int = 1_000
    min_target_action_pct: float = 8.0
    max_target_action_pct: float = 45.0
    min_target_hold_pct: float = 35.0
    max_target_action_side_pct: float = 76.0
    min_action_precision: float = 0.10
    min_action_recall: float = 0.08
    min_action_f1: float = 0.09
    min_staged_action_pct: float = 1.0
    max_staged_action_pct: float = 35.0
    max_staged_action_side_pct: float = 82.0
    min_action_probability_gap_mean: float = 0.015
    min_side_accuracy: float = 0.515
    min_side_precision: float = 0.08
    min_directional_entropy: float = 0.62
    min_expected_edge_proxy_bps: float = 1.0
    min_validation_action_classes: int = 2
    min_action_auc_proxy_gap: float = 0.010
    target_staged_action_pct: float = 12.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class TwoStageThresholds:
    action_threshold: float
    side_margin_floor: float

    def to_dict(self) -> dict[str, float]:
        return asdict(self)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    if not np.isfinite(parsed):
        return default
    return float(parsed)


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _pct(part: int | float, total: int | float) -> float:
    total_f = float(total or 0.0)
    if total_f <= 0.0:
        return 0.0
    return round((float(part) / total_f) * 100.0, 6)


def _append_unique(target: list[str], code: str) -> None:
    if code not in target:
        target.append(code)


def _summary(values: Iterable[Any]) -> dict[str, float]:
    vals = sorted(_safe_float(v) for v in values if v is not None and np.isfinite(_safe_float(v)))
    if not vals:
        return {"min": 0.0, "median": 0.0, "mean": 0.0, "max": 0.0}
    return {
        "min": round(float(vals[0]), 8),
        "median": round(float(median(vals)), 8),
        "mean": round(float(mean(vals)), 8),
        "max": round(float(vals[-1]), 8),
    }


def _class_distribution(values: Iterable[Any]) -> dict[str, int]:
    counts = Counter(_safe_int(value, 0) for value in values)
    return {name: int(counts.get(cls, 0)) for cls, name in TARGET_NAMES.items()}


def _dist_total(distribution: Mapping[str, Any]) -> int:
    return sum(_safe_int(distribution.get(name), 0) for name in TARGET_NAMES.values())


def _action_pct(distribution: Mapping[str, Any]) -> float:
    total = _dist_total(distribution)
    return _pct(_safe_int(distribution.get("BUY"), 0) + _safe_int(distribution.get("SELL"), 0), total)


def _hold_pct(distribution: Mapping[str, Any]) -> float:
    return _pct(_safe_int(distribution.get("HOLD"), 0), _dist_total(distribution))


def _dominant_action_pct(distribution: Mapping[str, Any]) -> float:
    buy = _safe_int(distribution.get("BUY"), 0)
    sell = _safe_int(distribution.get("SELL"), 0)
    total = buy + sell
    if total <= 0:
        return 0.0
    return _pct(max(buy, sell), total)


def _directional_entropy(distribution: Mapping[str, Any]) -> float:
    buy = _safe_int(distribution.get("BUY"), 0)
    sell = _safe_int(distribution.get("SELL"), 0)
    total = buy + sell
    if total <= 0:
        return 0.0
    entropy = 0.0
    for count in (buy, sell):
        if count > 0:
            p = count / total
            entropy -= p * log2(p)
    return round(float(entropy), 6)


def _normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    rename = {"openTime": "open_time", "closeTime": "close_time", "quoteVolume": "quote_volume"}
    out = out.rename(columns={key: val for key, val in rename.items() if key in out.columns})
    for col in ("open_time", "close_time", "open", "high", "low", "close", "volume", "quote_volume"):
        if col not in out.columns:
            out[col] = 0.0
        out[col] = pd.to_numeric(out[col], errors="coerce")
    return out.sort_values("close_time" if "close_time" in out.columns else "open_time").reset_index(drop=True)


def _feature_columns() -> list[str]:
    return list(FEATURE_COLUMNS)


def _training_matrix(labeled: pd.DataFrame, feature_columns: Sequence[str]) -> tuple[pd.DataFrame, pd.Series]:
    clean = clean_feature_frame(labeled, require_target=True, feature_columns=list(feature_columns))
    if clean.empty:
        raise RuntimeError("No clean two-stage training matrix produced")
    return clean[list(feature_columns)].astype("float32"), clean["target"].astype("int64")


def _thresholds(action_threshold_profile: str, side_margin_profile: str) -> TwoStageThresholds:
    action_profiles = {
        "conservative": 0.64,
        "balanced": 0.56,
        "recall_light": 0.48,
        "coverage_seek": 0.42,
    }
    side_profiles = {
        "strict": 0.12,
        "guarded": 0.08,
        "balanced": 0.05,
        "light": 0.03,
    }
    return TwoStageThresholds(
        action_threshold=float(action_profiles.get(str(action_threshold_profile), 0.56)),
        side_margin_floor=float(side_profiles.get(str(side_margin_profile), 0.08)),
    )


def _binary_sample_weights(y: Sequence[int] | np.ndarray, profile: str) -> np.ndarray:
    arr = np.asarray(y, dtype=int)
    counts = Counter(int(v) for v in arr)
    total = max(len(arr), 1)
    weights = {cls: total / (max(len(counts), 1) * max(count, 1)) for cls, count in counts.items()}
    profile = str(profile or "balanced")
    if profile == "action_precision_guarded":
        weights[1] = weights.get(1, 1.0) * 0.85
        weights[0] = weights.get(0, 1.0) * 1.10
    elif profile == "action_recall_light":
        weights[1] = weights.get(1, 1.0) * 1.25
    elif profile == "action_recall_medium":
        weights[1] = weights.get(1, 1.0) * 1.55
    elif profile == "side_balance_guarded":
        weights[0] = weights.get(0, 1.0) * 1.0
        weights[1] = weights.get(1, 1.0) * 1.0
    return np.asarray([float(weights.get(int(v), 1.0)) for v in arr], dtype="float32")


def _xgb_classifier(*, max_depth: int, n_estimators: int, learning_rate: float, seed: int):
    from xgboost import XGBClassifier

    return XGBClassifier(
        n_estimators=int(n_estimators),
        max_depth=int(max_depth),
        learning_rate=float(learning_rate),
        subsample=0.90,
        colsample_bytree=0.90,
        objective="binary:logistic",
        eval_metric="logloss",
        random_state=int(seed),
        tree_method="hist",
        n_jobs=1,
    )


def _prob_positive(model: Any, x: pd.DataFrame) -> np.ndarray:
    proba = model.predict_proba(x)
    arr = np.asarray(proba, dtype="float64")
    if arr.ndim == 1:
        return arr
    if arr.shape[1] == 1:
        return arr[:, 0]
    return arr[:, 1]


def _safe_precision(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    y_true = np.asarray(y_true, dtype=int)
    y_pred = np.asarray(y_pred, dtype=int)
    tp = int(((y_true == 1) & (y_pred == 1)).sum())
    fp = int(((y_true == 0) & (y_pred == 1)).sum())
    denom = tp + fp
    return float(tp / denom) if denom > 0 else 0.0


def _safe_recall(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    y_true = np.asarray(y_true, dtype=int)
    y_pred = np.asarray(y_pred, dtype=int)
    tp = int(((y_true == 1) & (y_pred == 1)).sum())
    fn = int(((y_true == 1) & (y_pred == 0)).sum())
    denom = tp + fn
    return float(tp / denom) if denom > 0 else 0.0


def _safe_f1(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    precision = _safe_precision(y_true, y_pred)
    recall = _safe_recall(y_true, y_pred)
    denom = precision + recall
    return float((2.0 * precision * recall) / denom) if denom > 0.0 else 0.0


def _expected_edge_proxy_bps(staged_pred: np.ndarray, y_true: np.ndarray, label_policy: CostAwareLabelPolicyCandidate) -> float:
    action_mask = staged_pred != 0
    if not bool(action_mask.any()):
        return 0.0
    correct = int(((staged_pred == y_true) & action_mask).sum())
    incorrect = int(((staged_pred != y_true) & action_mask).sum())
    total = int(action_mask.sum())
    edge = ((correct - incorrect) / max(total, 1)) * float(label_policy.effective_min_profit_bps)
    return round(float(edge), 6)


def _validate_split_indices(y: pd.Series) -> tuple[np.ndarray, np.ndarray]:
    idx = np.arange(len(y), dtype=int)
    y_arr = np.asarray(y, dtype=int)
    counts = Counter(int(v) for v in y_arr)
    stratify: np.ndarray | None = y_arr if min(counts.values() or [0]) >= 2 and len(counts) >= 2 else None
    rng = np.random.default_rng(436624)
    if stratify is None:
        shuffled = idx.copy()
        rng.shuffle(shuffled)
        split = max(1, int(len(shuffled) * 0.80))
        return np.asarray(shuffled[:split], dtype=int), np.asarray(shuffled[split:], dtype=int)
    train_parts: list[np.ndarray] = []
    val_parts: list[np.ndarray] = []
    for cls in sorted(set(int(v) for v in y_arr)):
        cls_idx = idx[y_arr == cls]
        rng.shuffle(cls_idx)
        split = max(1, int(len(cls_idx) * 0.80))
        if split >= len(cls_idx):
            split = len(cls_idx) - 1
        train_parts.append(cls_idx[:split])
        val_parts.append(cls_idx[split:])
    train_idx = np.concatenate(train_parts) if train_parts else np.array([], dtype=int)
    val_idx = np.concatenate(val_parts) if val_parts else np.array([], dtype=int)
    rng.shuffle(train_idx)
    rng.shuffle(val_idx)
    return np.asarray(train_idx, dtype=int), np.asarray(val_idx, dtype=int)


def train_two_stage_candidate(
    ohlcv: pd.DataFrame,
    spec: TwoStageActionSideCandidateSpec,
    *,
    symbol: str = "ETHUSDT",
    interval: str = "1m",
    days: int = 90,
    output_dir: str | Path = "models/4B436624K_candidates",
) -> dict[str, Any]:
    df = _normalize_ohlcv(ohlcv)
    feature_lag = int(spec.feature_lag if spec.feature_lag is not None else 1)
    labeled = build_cost_aware_atr_targets(df, spec.label_policy.to_label_config(), feature_lag=feature_lag)
    feature_columns = _feature_columns()
    x, y = _training_matrix(labeled, feature_columns)
    train_idx, val_idx = _validate_split_indices(y)
    x_train = x.iloc[train_idx]
    x_val = x.iloc[val_idx]
    y_train_multi = y.iloc[train_idx].to_numpy(dtype=int)
    y_val_multi = y.iloc[val_idx].to_numpy(dtype=int)
    y_train_action = (y_train_multi != 0).astype(int)
    y_val_action = (y_val_multi != 0).astype(int)

    if len(set(y_train_action.tolist())) < 2:
        raise RuntimeError("Action classifier training set has only one class")
    side_train_mask = y_train_multi != 0
    if int(side_train_mask.sum()) < 20:
        raise RuntimeError("Side classifier training set has insufficient action labels")
    y_train_side = (y_train_multi[side_train_mask] == 2).astype(int)
    if len(set(y_train_side.tolist())) < 2:
        raise RuntimeError("Side classifier training set has only one side class")

    action_model = _xgb_classifier(
        max_depth=spec.max_depth,
        n_estimators=spec.n_estimators,
        learning_rate=spec.learning_rate,
        seed=436624,
    )
    action_model.fit(x_train, y_train_action, sample_weight=_binary_sample_weights(y_train_action, spec.action_profile))

    side_model = _xgb_classifier(
        max_depth=spec.max_depth,
        n_estimators=spec.n_estimators,
        learning_rate=spec.learning_rate,
        seed=436625,
    )
    side_model.fit(
        x_train.iloc[np.where(side_train_mask)[0]],
        y_train_side,
        sample_weight=_binary_sample_weights(y_train_side, spec.side_profile),
    )

    thresholds = _thresholds(spec.action_threshold_profile, spec.side_margin_profile)
    action_prob = _prob_positive(action_model, x_val)
    action_pred = (action_prob >= thresholds.action_threshold).astype(int)
    side_sell_prob = _prob_positive(side_model, x_val)
    side_margin = np.abs(side_sell_prob - 0.5) * 2.0
    side_pred_multi = np.where(side_sell_prob >= 0.5, 2, 1).astype(int)
    staged_pred = np.where((action_pred == 1) & (side_margin >= thresholds.side_margin_floor), side_pred_multi, 0).astype(int)

    y_val_side_actual = (y_val_multi[y_val_multi != 0] == 2).astype(int)
    side_val_prob = side_sell_prob[y_val_multi != 0]
    side_val_pred = (side_val_prob >= 0.5).astype(int)
    side_accuracy = float((y_val_side_actual == side_val_pred).mean()) if len(y_val_side_actual) else 0.0
    side_precision = _safe_precision(y_val_side_actual, side_val_pred) if len(y_val_side_actual) else 0.0
    side_recall = _safe_recall(y_val_side_actual, side_val_pred) if len(y_val_side_actual) else 0.0

    hold_action_gap = float(np.nanmean(action_prob[y_val_action == 1]) - np.nanmean(action_prob[y_val_action == 0])) if (y_val_action == 1).any() and (y_val_action == 0).any() else 0.0
    auc_proxy_gap = float(np.nanmedian(action_prob[y_val_action == 1]) - np.nanmedian(action_prob[y_val_action == 0])) if (y_val_action == 1).any() and (y_val_action == 0).any() else 0.0

    target_distribution = _class_distribution(y.to_numpy(dtype=int))
    val_actual_distribution = _class_distribution(y_val_multi)
    staged_distribution = _class_distribution(staged_pred)
    raw_action_distribution = {"HOLD": int((action_pred == 0).sum()), "BUY": int(((action_pred == 1) & (side_pred_multi == 1)).sum()), "SELL": int(((action_pred == 1) & (side_pred_multi == 2)).sum())}

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    slug = spec.slug()
    action_model_path = out / f"{symbol.upper()}_two_stage_4b436624K_{slug}_action.ubj"
    side_model_path = out / f"{symbol.upper()}_two_stage_4b436624K_{slug}_side.ubj"
    action_model.save_model(action_model_path)
    side_model.save_model(side_model_path)
    sidecars = _write_sidecars(
        action_model_path=action_model_path,
        side_model_path=side_model_path,
        symbol=symbol,
        interval=interval,
        days=days,
        spec=spec,
        feature_columns=feature_columns,
        target_distribution=target_distribution,
    )

    result: dict[str, Any] = {
        "contract_version": TWO_STAGE_ACTION_SIDE_CONTRACT_VERSION,
        "workflow_version": TWO_STAGE_ACTION_SIDE_CONTRACT_VERSION,
        "candidate_spec": spec.to_dict(),
        "symbol": symbol.upper(),
        "interval": interval,
        "days": int(days),
        "action_model_path": action_model_path.as_posix(),
        "side_model_path": side_model_path.as_posix(),
        "action_schema_path": sidecars["action_schema_path"],
        "action_manifest_path": sidecars["action_manifest_path"],
        "side_schema_path": sidecars["side_schema_path"],
        "side_manifest_path": sidecars["side_manifest_path"],
        "sidecars_written": True,
        "clean_samples": int(len(y)),
        "feature_columns": list(feature_columns),
        "feature_lag": feature_lag,
        "feature_pack_name": "core_price_action_regime_vwap_mtf15_v1",
        "label_policy": spec.label_policy.to_dict(),
        "thresholds": thresholds.to_dict(),
        "target_distribution": target_distribution,
        "validation_actual_distribution": val_actual_distribution,
        "validation_action_raw_distribution": raw_action_distribution,
        "validation_staged_distribution": staged_distribution,
        "metrics": {
            "target_action_pct": _action_pct(target_distribution),
            "target_hold_pct": _hold_pct(target_distribution),
            "target_action_side_pct": _dominant_action_pct(target_distribution),
            "target_directional_entropy": _directional_entropy(target_distribution),
            "validation_actual_action_pct": _action_pct(val_actual_distribution),
            "validation_staged_action_pct": _action_pct(staged_distribution),
            "validation_staged_action_side_pct": _dominant_action_pct(staged_distribution),
            "validation_action_precision": round(_safe_precision(y_val_action, action_pred), 8),
            "validation_action_recall": round(_safe_recall(y_val_action, action_pred), 8),
            "validation_action_f1": round(_safe_f1(y_val_action, action_pred), 8),
            "validation_side_accuracy": round(side_accuracy, 8),
            "validation_side_precision_sell": round(side_precision, 8),
            "validation_side_recall_sell": round(side_recall, 8),
            "action_probability_gap_mean": round(float(hold_action_gap), 8),
            "action_auc_proxy_gap": round(float(auc_proxy_gap), 8),
            "action_probability_summary": _summary(action_prob),
            "side_margin_summary": _summary(side_margin),
            "expected_edge_proxy_bps": _expected_edge_proxy_bps(staged_pred, y_val_multi, spec.label_policy),
        },
        "model_format": "ubj",
    }
    gate = evaluate_two_stage_training_result(result)
    result["candidate_gate"] = gate
    result["decision"] = gate["decision"]
    result["ok"] = gate["ok"]
    result["reason_codes"] = list(gate.get("reason_codes") or [])
    result["warnings"] = list(gate.get("warnings") or [])
    result["score"] = gate.get("score", 0.0)
    result["reload_allowed"] = False
    result["approved_for_live_real"] = False
    result["approved_for_paper_candidate"] = False
    return result


def _write_sidecars(
    *,
    action_model_path: Path,
    side_model_path: Path,
    symbol: str,
    interval: str,
    days: int,
    spec: TwoStageActionSideCandidateSpec,
    feature_columns: Sequence[str],
    target_distribution: Mapping[str, int],
) -> dict[str, str]:
    import json
    from datetime import UTC, datetime

    payload = {
        "contract_version": TWO_STAGE_ACTION_SIDE_CONTRACT_VERSION,
        "created_at": datetime.now(UTC).isoformat(),
        "symbol": symbol.upper(),
        "interval": interval,
        "days": int(days),
        "feature_schema_version": "4B.3.4",
        "feature_pack_name": "core_price_action_regime_vwap_mtf15_v1",
        "feature_columns": list(feature_columns),
        "feature_lag": spec.feature_lag if spec.feature_lag is not None else 1,
        "label_policy": spec.label_policy.to_dict(),
        "candidate_spec": spec.to_dict(),
        "target_distribution": dict(target_distribution),
        "model_architecture": "two_stage_action_side",
        "live_real_allowed": False,
    }
    schema = {
        "schema_version": "4B.3.4",
        "feature_pack_name": payload["feature_pack_name"],
        "feature_columns": list(feature_columns),
        "feature_lag": payload["feature_lag"],
        "contract_version": TWO_STAGE_ACTION_SIDE_CONTRACT_VERSION,
    }
    paths: dict[str, str] = {}
    for role, model_path in (("action", action_model_path), ("side", side_model_path)):
        stem = model_path.with_suffix("")
        schema_path = Path(f"{stem}.schema.json")
        manifest_path = Path(f"{stem}.manifest.json")
        role_payload = dict(payload, model_role=role, model_path=model_path.as_posix())
        schema_path.write_text(json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8")
        manifest_path.write_text(json.dumps(role_payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        paths[f"{role}_schema_path"] = schema_path.as_posix()
        paths[f"{role}_manifest_path"] = manifest_path.as_posix()
    return paths


def evaluate_two_stage_training_result(
    result: Mapping[str, Any] | None,
    *,
    limits: TwoStageGateLimits | None = None,
) -> dict[str, Any]:
    limits = limits or TwoStageGateLimits()
    result = dict(result or {})
    metrics = dict(result.get("metrics") or {})
    reasons: list[str] = []
    warnings: list[str] = []
    clean_samples = _safe_int(result.get("clean_samples"), 0)
    target_distribution = result.get("target_distribution") if isinstance(result.get("target_distribution"), Mapping) else {}
    staged_distribution = result.get("validation_staged_distribution") if isinstance(result.get("validation_staged_distribution"), Mapping) else {}

    target_action_pct = _safe_float(metrics.get("target_action_pct", _action_pct(target_distribution)))
    target_hold_pct = _safe_float(metrics.get("target_hold_pct", _hold_pct(target_distribution)))
    target_side_pct = _safe_float(metrics.get("target_action_side_pct", _dominant_action_pct(target_distribution)))
    target_entropy = _safe_float(metrics.get("target_directional_entropy", _directional_entropy(target_distribution)))
    staged_action_pct = _safe_float(metrics.get("validation_staged_action_pct", _action_pct(staged_distribution)))
    staged_side_pct = _safe_float(metrics.get("validation_staged_action_side_pct", _dominant_action_pct(staged_distribution)))
    action_precision = _safe_float(metrics.get("validation_action_precision"))
    action_recall = _safe_float(metrics.get("validation_action_recall"))
    action_f1 = _safe_float(metrics.get("validation_action_f1"))
    side_accuracy = _safe_float(metrics.get("validation_side_accuracy"))
    side_precision = _safe_float(metrics.get("validation_side_precision_sell"))
    action_gap = _safe_float(metrics.get("action_probability_gap_mean"))
    auc_gap = _safe_float(metrics.get("action_auc_proxy_gap"))
    edge_proxy = _safe_float(metrics.get("expected_edge_proxy_bps"))

    if clean_samples < limits.min_clean_samples:
        _append_unique(reasons, "TWO_STAGE_CLEAN_SAMPLE_COUNT_LOW")
    if target_action_pct < limits.min_target_action_pct:
        _append_unique(reasons, "TARGET_ACTION_COVERAGE_LOW")
    if target_action_pct > limits.max_target_action_pct:
        _append_unique(reasons, "TARGET_ACTION_COVERAGE_HIGH")
    if target_hold_pct < limits.min_target_hold_pct:
        _append_unique(reasons, "TARGET_HOLD_COVERAGE_LOW")
    if target_side_pct > limits.max_target_action_side_pct:
        _append_unique(reasons, "TARGET_ACTION_SIDE_IMBALANCE_HIGH")
    if target_entropy < limits.min_directional_entropy:
        _append_unique(reasons, "TARGET_DIRECTIONAL_ENTROPY_LOW")
    if staged_action_pct < limits.min_staged_action_pct:
        _append_unique(reasons, "TWO_STAGE_STAGED_ACTION_COVERAGE_LOW")
    if staged_action_pct > limits.max_staged_action_pct:
        _append_unique(reasons, "TWO_STAGE_STAGED_ACTION_COVERAGE_HIGH")
    if staged_side_pct > limits.max_staged_action_side_pct:
        _append_unique(reasons, "TWO_STAGE_STAGED_ACTION_SIDE_IMBALANCE_HIGH")
    if action_precision < limits.min_action_precision:
        _append_unique(reasons, "ACTION_PRECISION_LOW")
    if action_recall < limits.min_action_recall:
        _append_unique(reasons, "ACTION_RECALL_LOW")
    if action_f1 < limits.min_action_f1:
        _append_unique(reasons, "ACTION_F1_LOW")
    if action_gap < limits.min_action_probability_gap_mean:
        _append_unique(reasons, "ACTION_HOLD_PROBABILITY_GAP_LOW")
    if auc_gap < limits.min_action_auc_proxy_gap:
        _append_unique(reasons, "ACTION_AUC_PROXY_GAP_LOW")
    if side_accuracy < limits.min_side_accuracy:
        _append_unique(reasons, "SIDE_ACCURACY_LOW")
    if side_precision < limits.min_side_precision:
        _append_unique(reasons, "SIDE_PRECISION_LOW")
    if edge_proxy < limits.min_expected_edge_proxy_bps:
        _append_unique(reasons, "EXPECTED_EDGE_PROXY_LOW")

    if staged_action_pct <= limits.min_staged_action_pct * 1.5:
        _append_unique(warnings, "STAGED_ACTION_COVERAGE_NEAR_FLOOR")
    if action_precision < max(0.12, limits.min_action_precision + 0.02):
        _append_unique(warnings, "ACTION_PRECISION_NEAR_FLOOR")

    decision = "PASS" if not reasons else "BLOCK"
    score = 0.0
    score += min(staged_action_pct, limits.max_staged_action_pct) * 0.8
    score += action_precision * 80.0
    score += action_recall * 35.0
    score += side_accuracy * 25.0
    score += action_gap * 250.0
    score += auc_gap * 120.0
    score += edge_proxy * 0.2
    score -= abs(staged_action_pct - limits.target_staged_action_pct) * 0.8
    score -= max(0.0, staged_side_pct - 55.0) * 0.5
    score -= len(reasons) * 25.0

    return {
        "contract_version": TWO_STAGE_ACTION_SIDE_CONTRACT_VERSION,
        "report_type": "two_stage_action_side_candidate_gate",
        "decision": decision,
        "ok": decision == "PASS",
        "approved_for_training_candidate": decision == "PASS",
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "reload_allowed": False,
        "action_model_path": result.get("action_model_path"),
        "side_model_path": result.get("side_model_path"),
        "reason_codes": reasons,
        "warnings": warnings,
        "metrics": {
            "clean_samples": clean_samples,
            "target_distribution": dict(target_distribution or {}),
            "validation_staged_distribution": dict(staged_distribution or {}),
            "target_action_pct": round(target_action_pct, 6),
            "target_hold_pct": round(target_hold_pct, 6),
            "target_action_side_pct": round(target_side_pct, 6),
            "target_directional_entropy": round(target_entropy, 6),
            "validation_staged_action_pct": round(staged_action_pct, 6),
            "validation_staged_action_side_pct": round(staged_side_pct, 6),
            "validation_action_precision": round(action_precision, 8),
            "validation_action_recall": round(action_recall, 8),
            "validation_action_f1": round(action_f1, 8),
            "validation_side_accuracy": round(side_accuracy, 8),
            "validation_side_precision_sell": round(side_precision, 8),
            "action_probability_gap_mean": round(action_gap, 8),
            "action_auc_proxy_gap": round(auc_gap, 8),
            "expected_edge_proxy_bps": round(edge_proxy, 6),
        },
        "limits": limits.to_dict(),
        "score": round(float(score), 6),
    }


def select_two_stage_retrain_candidate(candidates: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    best: Mapping[str, Any] | None = None
    for candidate in candidates:
        if not isinstance(candidate, Mapping):
            continue
        if best is None or _safe_float(candidate.get("score"), -1e9) > _safe_float(best.get("score"), -1e9):
            best = candidate
    approved = bool(best and best.get("decision") == "PASS")
    reasons: list[str] = [] if approved else ["NO_TWO_STAGE_ACTION_SIDE_CANDIDATE_PASSED"]
    if not approved and best:
        for code in best.get("reason_codes") or []:
            _append_unique(reasons, str(code))
    return {
        "contract_version": TWO_STAGE_ACTION_SIDE_CONTRACT_VERSION,
        "decision": "PASS" if approved else "BLOCK",
        "approved": approved,
        "reason_codes": reasons,
        "best_candidate": dict(best or {}),
    }


def build_two_stage_recovery_report(
    candidates: Sequence[Mapping[str, Any]],
    *,
    source: str = "unknown",
) -> dict[str, Any]:
    normalized: list[dict[str, Any]] = []
    for item in candidates:
        payload = dict(item)
        if "candidate_gate" not in payload:
            gate = evaluate_two_stage_training_result(payload)
            payload["candidate_gate"] = gate
            payload["decision"] = gate["decision"]
            payload["ok"] = gate["ok"]
            payload["reason_codes"] = list(gate.get("reason_codes") or [])
            payload["warnings"] = list(gate.get("warnings") or [])
            payload["score"] = gate.get("score", 0.0)
        normalized.append(payload)
    selection = select_two_stage_retrain_candidate(normalized)
    approved = bool(selection.get("approved"))
    best = selection.get("best_candidate") if isinstance(selection.get("best_candidate"), Mapping) else {}
    best_gate = best.get("candidate_gate") if isinstance(best.get("candidate_gate"), Mapping) else {}
    best_metrics = best_gate.get("metrics") if isinstance(best_gate.get("metrics"), Mapping) else {}
    return {
        "contract_version": TWO_STAGE_ACTION_SIDE_CONTRACT_VERSION,
        "phase": TWO_STAGE_ACTION_SIDE_CONTRACT_VERSION,
        "report_type": "two_stage_action_side_recovery",
        "decision": "PASS" if approved else "BLOCK",
        "ok": approved,
        "source": source,
        "candidate_count": len(normalized),
        "approved_for_training_candidate": approved,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "live_real_allowed": False,
        "reload_performed": False,
        "config_mutation_performed": False,
        "order_actions_performed": False,
        "no_post_actions": True,
        "observation_only": True,
        "promoted_to": None,
        "promotion_performed": False,
        "reason_codes": list(selection.get("reason_codes") or []),
        "recommendation": (
            "A two-stage ACTION/SIDE candidate passed the training-candidate gate. Review manually; reload and paper/live remain blocked."
            if approved
            else "No two-stage action/side candidate passed. Revisit action features, meta-labels, side objective, or regime split before promote/reload."
        ),
        "selected_action_model": best.get("action_model_path"),
        "selected_side_model": best.get("side_model_path"),
        "selected_score": best.get("score"),
        "selected_staged_action_pct": best_metrics.get("validation_staged_action_pct"),
        "selected_action_precision": best_metrics.get("validation_action_precision"),
        "selected_side_accuracy": best_metrics.get("validation_side_accuracy"),
        "selection": selection,
        "candidates": normalized,
        "guardrails": {
            "observation_only": True,
            "no_post_actions": True,
            "post_requests_allowed": False,
            "config_mutation_performed": False,
            "order_actions_performed": False,
            "reload_performed": False,
            "live_real_allowed": False,
            "promotion_requires_explicit_flag": True,
        },
    }


def build_two_stage_candidate_specs(
    policies: Sequence[CostAwareLabelPolicyCandidate],
    *,
    action_profiles: Sequence[str] | None = None,
    side_profiles: Sequence[str] | None = None,
    action_threshold_profiles: Sequence[str] | None = None,
    side_margin_profiles: Sequence[str] | None = None,
    max_candidates: int = 6,
) -> list[TwoStageActionSideCandidateSpec]:
    action_profiles = list(action_profiles or ["balanced", "action_precision_guarded", "action_recall_light"])
    side_profiles = list(side_profiles or ["balanced", "side_balance_guarded"])
    action_threshold_profiles = list(action_threshold_profiles or ["balanced", "recall_light"])
    side_margin_profiles = list(side_margin_profiles or ["guarded", "balanced"])
    specs: list[TwoStageActionSideCandidateSpec] = []
    for policy in policies:
        for action_profile in action_profiles:
            for side_profile in side_profiles:
                for action_threshold in action_threshold_profiles:
                    for side_margin in side_margin_profiles:
                        specs.append(
                            TwoStageActionSideCandidateSpec(
                                label_policy=policy,
                                action_profile=action_profile,
                                side_profile=side_profile,
                                action_threshold_profile=action_threshold,
                                side_margin_profile=side_margin,
                            )
                        )
                        if len(specs) >= int(max_candidates):
                            return specs
    return specs


def cost_aware_policy_from_dict(payload: Mapping[str, Any]) -> CostAwareLabelPolicyCandidate:
    allowed = {
        "name",
        "lookahead",
        "atr_multiplier",
        "cost_bps",
        "min_edge_bps",
        "entry_fee_bps",
        "exit_fee_bps",
        "entry_slippage_bps",
        "exit_slippage_bps",
        "use_high_low_barriers",
        "ambiguous_barrier_policy",
        "approvable",
        "family",
    }
    data = {key: payload.get(key) for key in allowed if key in payload}
    return CostAwareLabelPolicyCandidate(**data)  # type: ignore[arg-type]


def select_policies_from_cost_aware_report(payload: Mapping[str, Any], *, limit: int = 3) -> list[CostAwareLabelPolicyCandidate]:
    rows: list[Mapping[str, Any]] = []
    selected = payload.get("selected_policy")
    if isinstance(selected, Mapping):
        rows.append(selected)
    for item in payload.get("policies") or []:
        if isinstance(item, Mapping) and str(item.get("decision", "")).upper() == "PASS":
            profile = item.get("policy") if isinstance(item.get("policy"), Mapping) else item.get("label_policy")
            if isinstance(profile, Mapping):
                rows.append(profile)
    # 24I JSON may store selected_policy as a string and full policies as rows with policy dicts.
    name_seen: set[str] = set()
    policies: list[CostAwareLabelPolicyCandidate] = []
    default_by_name = {p.name: p for p in default_cost_aware_label_policy_candidates()}
    if isinstance(selected, str) and selected in default_by_name:
        policies.append(default_by_name[selected])
        name_seen.add(selected)
    for row in rows:
        try:
            policy = cost_aware_policy_from_dict(row)
        except Exception:
            name = str(row.get("name", ""))
            policy = default_by_name.get(name)
            if policy is None:
                continue
        if policy.name not in name_seen and policy.approvable:
            policies.append(policy)
            name_seen.add(policy.name)
        if len(policies) >= int(limit):
            break
    if not policies:
        preferred = ["h30_cost16_edge30_atr3_0", "h20_cost16_edge25_atr2_5", "h15_cost12_edge20_atr2_0"]
        policies = [default_by_name[name] for name in preferred if name in default_by_name]
    return policies[: int(limit)]
