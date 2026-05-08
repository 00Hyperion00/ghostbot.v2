from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean, median
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import pandas as pd

from tradebot.features import FEATURE_COLUMNS, clean_feature_frame
from tradebot.training.labeling import build_cost_aware_atr_targets
from tradebot.two_stage_action_side_recovery import (
    TwoStageActionSideCandidateSpec,
    _prob_positive,
    _thresholds,
    _validate_split_indices,
    cost_aware_policy_from_dict,
)

EDGE_META_LABEL_REGIME_CONTRACT_VERSION = "4B.4.3.6.6.24L"
TARGET_NAMES = {0: "HOLD", 1: "BUY", 2: "SELL"}
ACTION_IDS = (1, 2)


@dataclass(frozen=True, slots=True)
class EdgeRegimeFilterSpec:
    name: str
    require_mtf_alignment: bool = False
    require_ema_alignment: bool = False
    require_volume_confirmed: bool = False
    require_vwap_near: bool = False
    require_mid_volatility: bool = False
    require_high_action_confidence: bool = False
    require_high_side_margin: bool = False
    approvable: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class EdgeMetaLabelGateLimits:
    min_clean_samples: int = 1_000
    min_subset_signals: int = 40
    min_subset_coverage_pct: float = 0.75
    max_subset_coverage_pct: float = 25.0
    max_action_side_pct: float = 80.0
    min_expected_edge_bps: float = 1.0
    min_median_edge_bps: float = -3.0
    min_win_rate_pct: float = 51.0
    min_action_precision: float = 0.20
    min_edge_lift_bps: float = 5.0
    min_good_action_lift_pct: float = 3.0
    target_subset_coverage_pct: float = 8.0

    def to_dict(self) -> dict[str, Any]:
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


def _dominant_action_pct_from_preds(values: Sequence[int]) -> float:
    counts = Counter(int(v) for v in values if int(v) in ACTION_IDS)
    total = int(counts.get(1, 0) + counts.get(2, 0))
    if total <= 0:
        return 0.0
    return _pct(max(counts.get(1, 0), counts.get(2, 0)), total)


def _class_distribution(values: Iterable[Any]) -> dict[str, int]:
    counts = Counter(_safe_int(v, 0) for v in values)
    return {name: int(counts.get(cls, 0)) for cls, name in TARGET_NAMES.items()}


def _normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    rename = {"openTime": "open_time", "closeTime": "close_time", "quoteVolume": "quote_volume"}
    out = out.rename(columns={key: val for key, val in rename.items() if key in out.columns})
    for col in ("open_time", "close_time", "open", "high", "low", "close", "volume", "quote_volume"):
        if col not in out.columns:
            out[col] = 0.0
        out[col] = pd.to_numeric(out[col], errors="coerce")
    return out.sort_values("close_time" if "close_time" in out.columns else "open_time").reset_index(drop=True)


def default_edge_regime_filter_specs() -> list[EdgeRegimeFilterSpec]:
    return [
        EdgeRegimeFilterSpec("all_staged_actions", approvable=False),
        EdgeRegimeFilterSpec("mtf_trend_aligned", require_mtf_alignment=True),
        EdgeRegimeFilterSpec("ema_trend_aligned", require_ema_alignment=True),
        EdgeRegimeFilterSpec("trend_double_aligned", require_mtf_alignment=True, require_ema_alignment=True),
        EdgeRegimeFilterSpec("volume_confirmed", require_volume_confirmed=True),
        EdgeRegimeFilterSpec("vwap_near", require_vwap_near=True),
        EdgeRegimeFilterSpec("mid_volatility", require_mid_volatility=True),
        EdgeRegimeFilterSpec("trend_volume_confirmed", require_mtf_alignment=True, require_ema_alignment=True, require_volume_confirmed=True),
        EdgeRegimeFilterSpec("trend_vwap_volume", require_mtf_alignment=True, require_ema_alignment=True, require_volume_confirmed=True, require_vwap_near=True),
        EdgeRegimeFilterSpec("confidence_side_guarded", require_high_action_confidence=True, require_high_side_margin=True),
        EdgeRegimeFilterSpec("trend_confidence_side_guarded", require_mtf_alignment=True, require_ema_alignment=True, require_high_action_confidence=True, require_high_side_margin=True),
    ]


def _filter_mask(samples: pd.DataFrame, spec: EdgeRegimeFilterSpec) -> pd.Series:
    mask = pd.Series(True, index=samples.index)
    pred = pd.to_numeric(samples.get("staged_pred"), errors="coerce").fillna(0).astype(int)
    if spec.require_mtf_alignment:
        mtf = pd.to_numeric(samples.get("mtf_15m_trend_flag"), errors="coerce").fillna(0.0)
        aligned = ((pred == 1) & (mtf >= 0.0)) | ((pred == 2) & (mtf <= 0.0))
        mask &= aligned
    if spec.require_ema_alignment:
        ema = pd.to_numeric(samples.get("ema_spread_pct"), errors="coerce").fillna(0.0)
        aligned = ((pred == 1) & (ema >= 0.0)) | ((pred == 2) & (ema <= 0.0))
        mask &= aligned
    if spec.require_volume_confirmed:
        volume_ratio = pd.to_numeric(samples.get("volume_ratio"), errors="coerce").fillna(0.0)
        mask &= volume_ratio >= max(float(volume_ratio.quantile(0.55)), 1.0)
    if spec.require_vwap_near:
        vwap_distance = pd.to_numeric(samples.get("abs_close_to_vwap_pct"), errors="coerce").fillna(999.0)
        mask &= vwap_distance <= float(vwap_distance.quantile(0.55))
    if spec.require_mid_volatility:
        atr_pct = pd.to_numeric(samples.get("atr_pct"), errors="coerce").fillna(0.0)
        low = float(atr_pct.quantile(0.25))
        high = float(atr_pct.quantile(0.75))
        mask &= (atr_pct >= low) & (atr_pct <= high)
    if spec.require_high_action_confidence:
        action_prob = pd.to_numeric(samples.get("action_prob"), errors="coerce").fillna(0.0)
        mask &= action_prob >= float(action_prob.quantile(0.60))
    if spec.require_high_side_margin:
        side_margin = pd.to_numeric(samples.get("side_margin"), errors="coerce").fillna(0.0)
        mask &= side_margin >= float(side_margin.quantile(0.60))
    return mask.fillna(False)


def _evaluate_filter(
    samples: pd.DataFrame,
    spec: EdgeRegimeFilterSpec,
    *,
    total_validation_samples: int,
    base_edge_bps: float,
    base_good_action_pct: float,
    limits: EdgeMetaLabelGateLimits,
) -> dict[str, Any]:
    staged = samples[pd.to_numeric(samples.get("staged_pred"), errors="coerce").fillna(0).astype(int).isin(ACTION_IDS)].copy()
    if staged.empty:
        selected = staged
    else:
        selected = staged[_filter_mask(staged, spec)].copy()
    signal_count = int(len(selected))
    coverage_pct = _pct(signal_count, total_validation_samples)
    pred = pd.to_numeric(selected.get("staged_pred"), errors="coerce").fillna(0).astype(int).to_numpy(dtype=int) if signal_count else np.array([], dtype=int)
    actual = pd.to_numeric(selected.get("actual_target"), errors="coerce").fillna(0).astype(int).to_numpy(dtype=int) if signal_count else np.array([], dtype=int)
    net_edge = pd.to_numeric(selected.get("net_edge_bps"), errors="coerce").dropna().to_numpy(dtype=float) if signal_count else np.array([], dtype=float)
    correct = int(((pred == actual) & np.isin(pred, ACTION_IDS)).sum()) if signal_count else 0
    action_precision = float(correct / max(signal_count, 1)) if signal_count else 0.0
    good_count = int((net_edge > 0.0).sum()) if len(net_edge) else 0
    win_rate_pct = _pct(good_count, len(net_edge)) if len(net_edge) else 0.0
    mean_edge = round(float(np.nanmean(net_edge)), 6) if len(net_edge) else 0.0
    median_edge = round(float(np.nanmedian(net_edge)), 6) if len(net_edge) else 0.0
    action_side_pct = _dominant_action_pct_from_preds(pred.tolist()) if signal_count else 0.0
    edge_lift = round(float(mean_edge - base_edge_bps), 6)
    good_lift = round(float(win_rate_pct - base_good_action_pct), 6)
    distribution = _class_distribution(pred.tolist())
    reasons: list[str] = []
    warnings: list[str] = []
    if not spec.approvable:
        _append_unique(reasons, "DIAGNOSTIC_FILTER_NOT_APPROVABLE")
    if signal_count < int(limits.min_subset_signals):
        _append_unique(reasons, "META_LABEL_SUBSET_SIGNAL_COUNT_LOW")
    if coverage_pct < float(limits.min_subset_coverage_pct):
        _append_unique(reasons, "META_LABEL_SUBSET_COVERAGE_LOW")
    if coverage_pct > float(limits.max_subset_coverage_pct):
        _append_unique(reasons, "META_LABEL_SUBSET_COVERAGE_HIGH")
    if action_side_pct > float(limits.max_action_side_pct):
        _append_unique(reasons, "META_LABEL_ACTION_SIDE_IMBALANCE_HIGH")
    if mean_edge < float(limits.min_expected_edge_bps):
        _append_unique(reasons, "META_LABEL_EXPECTED_EDGE_LOW")
    if median_edge < float(limits.min_median_edge_bps):
        _append_unique(reasons, "META_LABEL_MEDIAN_EDGE_LOW")
    if win_rate_pct < float(limits.min_win_rate_pct):
        _append_unique(reasons, "META_LABEL_WIN_RATE_LOW")
    if action_precision < float(limits.min_action_precision):
        _append_unique(reasons, "META_LABEL_ACTION_PRECISION_LOW")
    if edge_lift < float(limits.min_edge_lift_bps):
        _append_unique(reasons, "META_LABEL_EDGE_LIFT_LOW")
    if good_lift < float(limits.min_good_action_lift_pct):
        _append_unique(reasons, "META_LABEL_GOOD_ACTION_LIFT_LOW")
    if coverage_pct < float(limits.min_subset_coverage_pct) * 1.5:
        _append_unique(warnings, "META_LABEL_COVERAGE_NEAR_FLOOR")
    decision = "PASS" if not reasons else "BLOCK"
    score = 0.0
    score += mean_edge * 2.0
    score += edge_lift * 1.2
    score += (win_rate_pct - 50.0) * 0.75
    score += action_precision * 80.0
    score -= abs(coverage_pct - float(limits.target_subset_coverage_pct)) * 0.6
    score -= max(0.0, action_side_pct - 55.0) * 0.45
    score -= len(reasons) * 20.0
    return {
        "contract_version": EDGE_META_LABEL_REGIME_CONTRACT_VERSION,
        "report_type": "edge_meta_label_regime_filter_candidate",
        "filter": spec.to_dict(),
        "filter_name": spec.name,
        "decision": decision,
        "ok": decision == "PASS",
        "approvable": bool(spec.approvable),
        "reason_codes": reasons,
        "warnings": warnings,
        "metrics": {
            "total_validation_samples": int(total_validation_samples),
            "signal_count": signal_count,
            "subset_coverage_pct": round(float(coverage_pct), 6),
            "staged_distribution": distribution,
            "dominant_action_pct": round(float(action_side_pct), 6),
            "action_precision": round(float(action_precision), 8),
            "good_action_count": good_count,
            "good_action_pct": round(float(win_rate_pct), 6),
            "mean_net_edge_bps": round(float(mean_edge), 6),
            "median_net_edge_bps": round(float(median_edge), 6),
            "net_edge_summary": _summary(net_edge.tolist()),
            "base_mean_net_edge_bps": round(float(base_edge_bps), 6),
            "base_good_action_pct": round(float(base_good_action_pct), 6),
            "edge_lift_bps": round(float(edge_lift), 6),
            "good_action_lift_pct": round(float(good_lift), 6),
        },
        "limits": limits.to_dict(),
        "score": round(float(score), 6),
    }


def _base_staged_metrics(samples: pd.DataFrame, total_validation_samples: int) -> dict[str, Any]:
    staged = samples[pd.to_numeric(samples.get("staged_pred"), errors="coerce").fillna(0).astype(int).isin(ACTION_IDS)].copy()
    if staged.empty:
        return {
            "signal_count": 0,
            "staged_action_pct": 0.0,
            "mean_net_edge_bps": 0.0,
            "median_net_edge_bps": 0.0,
            "good_action_pct": 0.0,
            "action_precision": 0.0,
            "dominant_action_pct": 0.0,
            "staged_distribution": {"HOLD": 0, "BUY": 0, "SELL": 0},
        }
    pred = pd.to_numeric(staged.get("staged_pred"), errors="coerce").fillna(0).astype(int).to_numpy(dtype=int)
    actual = pd.to_numeric(staged.get("actual_target"), errors="coerce").fillna(0).astype(int).to_numpy(dtype=int)
    net_edge = pd.to_numeric(staged.get("net_edge_bps"), errors="coerce").dropna().to_numpy(dtype=float)
    correct = int(((pred == actual) & np.isin(pred, ACTION_IDS)).sum())
    return {
        "signal_count": int(len(staged)),
        "staged_action_pct": _pct(int(len(staged)), total_validation_samples),
        "mean_net_edge_bps": round(float(np.nanmean(net_edge)), 6) if len(net_edge) else 0.0,
        "median_net_edge_bps": round(float(np.nanmedian(net_edge)), 6) if len(net_edge) else 0.0,
        "good_action_pct": _pct(int((net_edge > 0.0).sum()), len(net_edge)) if len(net_edge) else 0.0,
        "action_precision": round(float(correct / max(len(staged), 1)), 8),
        "dominant_action_pct": _dominant_action_pct_from_preds(pred.tolist()),
        "staged_distribution": _class_distribution(pred.tolist()),
    }


def evaluate_edge_meta_label_samples(
    samples: Sequence[Mapping[str, Any]] | pd.DataFrame,
    *,
    candidate_name: str = "candidate",
    total_validation_samples: int | None = None,
    filters: Sequence[EdgeRegimeFilterSpec] | None = None,
    limits: EdgeMetaLabelGateLimits | None = None,
) -> dict[str, Any]:
    limits = limits or EdgeMetaLabelGateLimits()
    df = pd.DataFrame(list(samples) if not isinstance(samples, pd.DataFrame) else samples.copy())
    if df.empty:
        return {
            "contract_version": EDGE_META_LABEL_REGIME_CONTRACT_VERSION,
            "candidate_name": candidate_name,
            "decision": "BLOCK",
            "ok": False,
            "reason_codes": ["META_LABEL_SAMPLE_COUNT_LOW"],
            "base_metrics": {},
            "filters": [],
            "selection": {"approved": False, "reason_codes": ["META_LABEL_SAMPLE_COUNT_LOW"], "best_filter": {}},
            "score": -999.0,
        }
    total = int(total_validation_samples or max(len(df), 1))
    base = _base_staged_metrics(df, total)
    base_edge = _safe_float(base.get("mean_net_edge_bps"), 0.0)
    base_good = _safe_float(base.get("good_action_pct"), 0.0)
    evaluated = [
        _evaluate_filter(df, spec, total_validation_samples=total, base_edge_bps=base_edge, base_good_action_pct=base_good, limits=limits)
        for spec in (filters or default_edge_regime_filter_specs())
    ]
    best = max(evaluated, key=lambda item: _safe_float(item.get("score"), -1e9), default={})
    approved = bool(best and best.get("decision") == "PASS")
    reasons: list[str] = [] if approved else ["NO_EDGE_META_LABEL_REGIME_FILTER_PASSED"]
    if not approved and best:
        for code in best.get("reason_codes") or []:
            _append_unique(reasons, str(code))
    decision = "PASS" if approved else "BLOCK"
    return {
        "contract_version": EDGE_META_LABEL_REGIME_CONTRACT_VERSION,
        "candidate_name": candidate_name,
        "decision": decision,
        "ok": approved,
        "approved_for_training_candidate": approved,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "reload_allowed": False,
        "reason_codes": reasons,
        "base_metrics": base,
        "filters": evaluated,
        "selection": {"approved": approved, "decision": decision, "reason_codes": reasons, "best_filter": best},
        "score": best.get("score", -999.0) if best else -999.0,
    }


def _load_xgb(path: str | Path) -> Any:
    from xgboost import XGBClassifier

    model = XGBClassifier()
    model.load_model(str(path))
    return model


def _candidate_spec_from_dict(payload: Mapping[str, Any]) -> TwoStageActionSideCandidateSpec:
    label_payload = payload.get("label_policy") if isinstance(payload.get("label_policy"), Mapping) else {}
    return TwoStageActionSideCandidateSpec(
        label_policy=cost_aware_policy_from_dict(label_payload),
        action_profile=str(payload.get("action_profile", "balanced")),
        side_profile=str(payload.get("side_profile", "balanced")),
        action_threshold_profile=str(payload.get("action_threshold_profile", "balanced")),
        side_margin_profile=str(payload.get("side_margin_profile", "guarded")),
        feature_lag=None if payload.get("feature_lag") is None else _safe_int(payload.get("feature_lag"), 1),
        max_depth=_safe_int(payload.get("max_depth"), 3),
        n_estimators=_safe_int(payload.get("n_estimators"), 32),
        learning_rate=_safe_float(payload.get("learning_rate"), 0.04),
    )


def _volume_ratio(clean: pd.DataFrame) -> pd.Series:
    volume = pd.to_numeric(clean.get("volume"), errors="coerce").fillna(0.0)
    rolling = volume.rolling(50, min_periods=5).mean().replace(0.0, np.nan)
    return (volume / rolling).replace([np.inf, -np.inf], np.nan).fillna(0.0)


def replay_two_stage_candidate_samples(
    ohlcv: pd.DataFrame,
    candidate: Mapping[str, Any],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    spec_payload = candidate.get("candidate_spec") if isinstance(candidate.get("candidate_spec"), Mapping) else {}
    spec = _candidate_spec_from_dict(spec_payload)
    action_model_path = candidate.get("action_model_path")
    side_model_path = candidate.get("side_model_path")
    if not action_model_path or not side_model_path:
        raise ValueError("Candidate model paths are missing")
    source = _normalize_ohlcv(ohlcv)
    feature_lag = int(spec.feature_lag if spec.feature_lag is not None else 1)
    labeled = build_cost_aware_atr_targets(source, spec.label_policy.to_label_config(), feature_lag=feature_lag)
    clean = clean_feature_frame(labeled, require_target=True, feature_columns=list(FEATURE_COLUMNS))
    if clean.empty:
        raise RuntimeError("No clean samples for edge meta-label replay")
    x = clean[list(FEATURE_COLUMNS)].astype("float32")
    y = clean["target"].astype("int64")
    _, val_idx = _validate_split_indices(y)
    x_val = x.iloc[val_idx]
    y_val = y.iloc[val_idx].to_numpy(dtype=int)
    val = clean.iloc[val_idx].copy().reset_index(drop=True)
    action_model = _load_xgb(str(action_model_path))
    side_model = _load_xgb(str(side_model_path))
    thresholds = _thresholds(spec.action_threshold_profile, spec.side_margin_profile)
    action_prob = _prob_positive(action_model, x_val)
    action_pred = (action_prob >= thresholds.action_threshold).astype(int)
    side_sell_prob = _prob_positive(side_model, x_val)
    side_margin = np.abs(side_sell_prob - 0.5) * 2.0
    side_pred_multi = np.where(side_sell_prob >= 0.5, 2, 1).astype(int)
    staged_pred = np.where((action_pred == 1) & (side_margin >= thresholds.side_margin_floor), side_pred_multi, 0).astype(int)

    close = pd.to_numeric(clean.get("close"), errors="coerce")
    future = close.shift(-int(spec.label_policy.lookahead))
    forward_return = ((future / close.replace(0.0, np.nan)) - 1.0) * 10_000.0
    fwd_val = pd.to_numeric(forward_return.iloc[val_idx], errors="coerce").fillna(0.0).to_numpy(dtype=float)
    signed = np.where(staged_pred == 1, fwd_val, np.where(staged_pred == 2, -fwd_val, 0.0))
    net_edge = signed - float(spec.label_policy.round_trip_cost_bps)

    replay = pd.DataFrame(
        {
            "actual_target": y_val,
            "staged_pred": staged_pred,
            "action_prob": action_prob,
            "side_sell_prob": side_sell_prob,
            "side_margin": side_margin,
            "forward_return_bps": fwd_val,
            "net_edge_bps": net_edge,
            "ema_spread_pct": pd.to_numeric(val.get("ema_spread_pct"), errors="coerce").fillna(0.0),
            "mtf_15m_trend_flag": pd.to_numeric(val.get("mtf_15m_trend_flag"), errors="coerce").fillna(0.0),
            "atr_pct": pd.to_numeric(val.get("atr_pct"), errors="coerce").fillna(0.0),
            "abs_close_to_vwap_pct": pd.to_numeric(val.get("close_to_vwap_pct"), errors="coerce").abs().fillna(999.0),
            "volume_ratio": _volume_ratio(clean).iloc[val_idx].reset_index(drop=True),
        }
    )
    metadata = {
        "action_model_path": str(action_model_path),
        "side_model_path": str(side_model_path),
        "candidate_spec": spec.to_dict(),
        "clean_samples": int(len(clean)),
        "validation_samples": int(len(val_idx)),
        "feature_pack_name": "core_price_action_regime_vwap_mtf15_v1",
        "feature_lag": feature_lag,
        "thresholds": thresholds.to_dict(),
    }
    return replay, metadata


def evaluate_two_stage_candidate_with_regime_filters(
    ohlcv: pd.DataFrame,
    candidate: Mapping[str, Any],
    *,
    limits: EdgeMetaLabelGateLimits | None = None,
) -> dict[str, Any]:
    samples, metadata = replay_two_stage_candidate_samples(ohlcv, candidate)
    name = Path(str(metadata.get("action_model_path", "candidate"))).name.replace("_action.ubj", "")
    report = evaluate_edge_meta_label_samples(
        samples,
        candidate_name=name,
        total_validation_samples=int(metadata.get("validation_samples", len(samples))),
        limits=limits,
    )
    report["candidate_metadata"] = metadata
    report["action_model_path"] = metadata.get("action_model_path")
    report["side_model_path"] = metadata.get("side_model_path")
    return report


def select_two_stage_candidates_from_report(payload: Mapping[str, Any], *, limit: int = 3) -> list[Mapping[str, Any]]:
    rows: list[Mapping[str, Any]] = []
    selection = payload.get("selection") if isinstance(payload.get("selection"), Mapping) else {}
    best = selection.get("best_candidate") if isinstance(selection.get("best_candidate"), Mapping) else None
    if best:
        rows.append(best)
    for item in payload.get("candidates") or []:
        if isinstance(item, Mapping):
            rows.append(item)
    seen: set[str] = set()
    unique: list[Mapping[str, Any]] = []
    for row in sorted(rows, key=lambda x: _safe_float(x.get("score"), -1e9), reverse=True):
        key = str(row.get("action_model_path") or row.get("model_path") or len(unique))
        if key in seen:
            continue
        if row.get("action_model_path") and row.get("side_model_path"):
            unique.append(row)
            seen.add(key)
        if len(unique) >= int(limit):
            break
    return unique


def select_edge_meta_label_candidate(candidates: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    best: Mapping[str, Any] | None = None
    for candidate in candidates:
        if not isinstance(candidate, Mapping):
            continue
        if best is None or _safe_float(candidate.get("score"), -1e9) > _safe_float(best.get("score"), -1e9):
            best = candidate
    approved = bool(best and best.get("decision") == "PASS")
    reasons: list[str] = [] if approved else ["NO_EDGE_META_LABEL_REGIME_CANDIDATE_PASSED"]
    if not approved and best:
        for code in best.get("reason_codes") or []:
            _append_unique(reasons, str(code))
    return {
        "contract_version": EDGE_META_LABEL_REGIME_CONTRACT_VERSION,
        "decision": "PASS" if approved else "BLOCK",
        "approved": approved,
        "reason_codes": reasons,
        "best_candidate": dict(best or {}),
    }


def build_edge_meta_label_recovery_report(
    candidates: Sequence[Mapping[str, Any]],
    *,
    source: str = "unknown",
) -> dict[str, Any]:
    normalized = [dict(item) for item in candidates]
    selection = select_edge_meta_label_candidate(normalized)
    approved = bool(selection.get("approved"))
    best = selection.get("best_candidate") if isinstance(selection.get("best_candidate"), Mapping) else {}
    best_filter = {}
    if isinstance(best.get("selection"), Mapping):
        maybe = best["selection"].get("best_filter")
        if isinstance(maybe, Mapping):
            best_filter = dict(maybe)
    best_metrics = best_filter.get("metrics") if isinstance(best_filter.get("metrics"), Mapping) else {}
    return {
        "contract_version": EDGE_META_LABEL_REGIME_CONTRACT_VERSION,
        "phase": EDGE_META_LABEL_REGIME_CONTRACT_VERSION,
        "report_type": "edge_meta_label_regime_filter_recovery",
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
            "An edge-aware meta-label/regime filter candidate passed. Review only; reload, paper, and live remain blocked."
            if approved
            else "No edge-positive regime/meta-label filter passed. Revisit regime features, meta-label objective, or market/timeframe before promote/reload."
        ),
        "selected_candidate": best.get("candidate_name"),
        "selected_filter": best_filter.get("filter_name"),
        "selected_score": best.get("score"),
        "selected_mean_edge_bps": best_metrics.get("mean_net_edge_bps"),
        "selected_good_action_pct": best_metrics.get("good_action_pct"),
        "selected_subset_coverage_pct": best_metrics.get("subset_coverage_pct"),
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
