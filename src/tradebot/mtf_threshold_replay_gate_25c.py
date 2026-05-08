"""4B.4.3.6.6.25C - 15m Threshold/Calibration Replay Gate.

This module replays threshold/calibration profiles against 15m validation
probabilities produced by a 25B candidate model. It is intentionally
observation-only: no config mutation, no model reload, no orders, no paper/live
arming.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
import json
import math
import shutil

CONTRACT_VERSION = "4B.4.3.6.6.25C"
REPORT_PREFIX = "4B436625C_15m_threshold_replay_gate"

CLASS_NAME = {0: "HOLD", 1: "BUY", 2: "SELL"}
ACTION_CLASS = {"HOLD": 0, "BUY": 1, "SELL": 2}


@dataclass(frozen=True)
class ThresholdReplayProfile:
    name: str
    buy_threshold: float = 0.58
    sell_threshold: float = 0.57
    hold_band_low: float = 0.42
    hold_band_high: float = 0.55
    indecision_margin: float = 0.04
    approvable: bool = True
    family: str = "paper_replay"


@dataclass(frozen=True)
class ThresholdReplayGateLimits:
    min_samples: int = 500
    min_calibrated_action_pct: float = 3.0
    max_calibrated_action_pct: float = 22.0
    max_calibrated_action_side_pct: float = 82.0
    min_action_precision: float = 0.16
    min_action_recall: float = 0.03
    min_expected_edge_proxy_bps: float = 0.0
    max_low_margin_rejection_pct: float = 35.0
    min_buy_sell_margin_mean: float = 0.018
    min_action_hold_margin_mean: float = -0.025
    min_indecision_margin: float = 0.004
    target_calibrated_action_pct: float = 9.0


@dataclass
class ThresholdReplayEvaluation:
    contract_version: str
    report_type: str
    profile: dict[str, Any]
    decision: str
    ok: bool
    approvable: bool
    approved_for_training_candidate: bool
    approved_for_paper_candidate: bool
    approved_for_live_real: bool
    reload_allowed: bool
    reason_codes: list[str]
    warnings: list[str]
    metrics: dict[str, Any]
    limits: dict[str, Any]
    score: float


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        v = float(value)
        if math.isnan(v) or math.isinf(v):
            return default
        return v
    except Exception:
        return default


def _pct(part: float, total: float) -> float:
    if total <= 0:
        return 0.0
    return round(100.0 * float(part) / float(total), 6)


def _mean(values: Sequence[float]) -> float:
    vals = [float(v) for v in values if math.isfinite(float(v))]
    return round(sum(vals) / len(vals), 8) if vals else 0.0


def _median(values: Sequence[float]) -> float:
    vals = sorted(float(v) for v in values if math.isfinite(float(v)))
    if not vals:
        return 0.0
    mid = len(vals) // 2
    if len(vals) % 2:
        return round(vals[mid], 8)
    return round((vals[mid - 1] + vals[mid]) / 2.0, 8)


def _distribution(values: Iterable[int]) -> dict[str, int]:
    counts = {"HOLD": 0, "BUY": 0, "SELL": 0}
    for value in values:
        counts[CLASS_NAME.get(int(value), str(value))] = counts.get(CLASS_NAME.get(int(value), str(value)), 0) + 1
    return counts


def threshold_profile(profile: str) -> ThresholdReplayProfile:
    profiles: dict[str, ThresholdReplayProfile] = {
        "current_report": ThresholdReplayProfile("current_report", 0.58, 0.56, 0.42, 0.52, 0.05, approvable=False, family="diagnostic"),
        "balanced": ThresholdReplayProfile("balanced", 0.60, 0.59, 0.43, 0.55, 0.045),
        "action_seek_light": ThresholdReplayProfile("action_seek_light", 0.56, 0.55, 0.42, 0.54, 0.030),
        "paper_guarded": ThresholdReplayProfile("paper_guarded", 0.54, 0.535, 0.41, 0.54, 0.020),
        "paper_recall_guarded": ThresholdReplayProfile("paper_recall_guarded", 0.515, 0.510, 0.39, 0.55, 0.012, family="paper_replay_aggressive"),
        "edge_guarded_precision": ThresholdReplayProfile("edge_guarded_precision", 0.545, 0.540, 0.42, 0.54, 0.025),
        "micro_action_probe": ThresholdReplayProfile("micro_action_probe", 0.46, 0.46, 0.35, 0.65, 0.0, approvable=False, family="diagnostic"),
    }
    return profiles.get(profile, profiles["paper_guarded"])


def default_threshold_profiles() -> list[ThresholdReplayProfile]:
    return [
        threshold_profile("current_report"),
        threshold_profile("balanced"),
        threshold_profile("action_seek_light"),
        threshold_profile("paper_guarded"),
        threshold_profile("paper_recall_guarded"),
        threshold_profile("edge_guarded_precision"),
        threshold_profile("micro_action_probe"),
    ]


def calibrate_probabilities(probabilities: Sequence[Sequence[float]], profile: ThresholdReplayProfile) -> tuple[list[int], list[str]]:
    preds: list[int] = []
    reasons: list[str] = []
    for p in probabilities:
        hold, buy, sell = [float(x) for x in list(p)[:3]]
        action_prob = max(buy, sell)
        side = 1 if buy >= sell else 2
        side_gap = abs(buy - sell)
        action_hold_gap = action_prob - hold
        if profile.indecision_margin <= 0.0:
            if action_prob >= min(profile.buy_threshold, profile.sell_threshold):
                preds.append(side); reasons.append("RAW_ACTION_FIRST_ACCEPT")
            else:
                preds.append(0); reasons.append("RAW_TOP_HOLD")
            continue
        if profile.hold_band_low <= hold <= profile.hold_band_high and action_hold_gap < profile.indecision_margin:
            preds.append(0); reasons.append("REJECT_ACTION_HOLD_MARGIN")
            continue
        if side_gap < profile.indecision_margin:
            preds.append(0); reasons.append("REJECT_LOW_MARGIN")
            continue
        if side == 1 and buy >= profile.buy_threshold:
            preds.append(1); reasons.append("BUY_THRESHOLD_ACCEPT")
            continue
        if side == 2 and sell >= profile.sell_threshold:
            preds.append(2); reasons.append("SELL_THRESHOLD_ACCEPT")
            continue
        if action_prob >= max(profile.buy_threshold, profile.sell_threshold) - 0.035 and action_hold_gap >= profile.indecision_margin:
            preds.append(side); reasons.append("ACTION_HOLD_GAP_ACCEPT")
            continue
        preds.append(0); reasons.append("REJECT_LOW_ACTION_PROB")
    return preds, reasons


def evaluate_threshold_replay_profile(
    probabilities: Sequence[Sequence[float]],
    actual_labels: Sequence[int],
    forward_edge_bps: Sequence[float],
    profile: ThresholdReplayProfile,
    limits: ThresholdReplayGateLimits | None = None,
) -> ThresholdReplayEvaluation:
    limits = limits or ThresholdReplayGateLimits()
    n = min(len(probabilities), len(actual_labels), len(forward_edge_bps))
    probs = [[float(x) for x in p[:3]] for p in probabilities[:n]]
    actual = [int(x) for x in actual_labels[:n]]
    edges = [float(x) for x in forward_edge_bps[:n]]
    pred, reasons = calibrate_probabilities(probs, profile)

    action_preds = [p for p in pred if p != 0]
    buy_count = sum(1 for p in pred if p == 1)
    sell_count = sum(1 for p in pred if p == 2)
    action_count = buy_count + sell_count
    actual_action_count = max(1, sum(1 for a in actual if a != 0))
    correct_action = sum(1 for p, a in zip(pred, actual) if p != 0 and p == a)
    action_precision = correct_action / max(1, action_count) if action_count else 0.0
    action_recall = correct_action / actual_action_count
    expected_edges = [edge if p == a and p != 0 else -abs(edge) for p, a, edge in zip(pred, actual, edges) if p != 0]
    expected_edge_proxy_bps = _mean(expected_edges) if expected_edges else -1.0
    action_indices = [idx for idx, cls in enumerate(pred) if cls != 0]
    margin_indices = action_indices or [idx for idx, p in enumerate(probs) if max(p[1], p[2]) >= p[0]]
    buy_sell_margins = [abs(probs[idx][1] - probs[idx][2]) for idx in margin_indices]
    action_hold_margins = [max(probs[idx][1], probs[idx][2]) - probs[idx][0] for idx in margin_indices]
    low_margin_count = sum(1 for r, p in zip(reasons, probs) if (max(p[1], p[2]) >= p[0]) and ("LOW_MARGIN" in r or "ACTION_HOLD_MARGIN" in r))
    action_pct = _pct(action_count, n)
    side_pct = _pct(max(buy_count, sell_count), action_count)
    metrics = {
        "sample_count": n,
        "calibrated_distribution": _distribution(pred),
        "actual_distribution": _distribution(actual),
        "calibrated_action_pct": action_pct,
        "calibrated_action_side_pct": side_pct,
        "action_precision": round(action_precision, 8),
        "action_recall": round(action_recall, 8),
        "expected_edge_proxy_bps": expected_edge_proxy_bps,
        "low_margin_rejection_pct": _pct(low_margin_count, n),
        "buy_sell_margin_mean": _mean(buy_sell_margins),
        "buy_sell_margin_median": _median(buy_sell_margins),
        "action_hold_margin_mean": _mean(action_hold_margins),
        "calibration_reason_counts": {r: reasons.count(r) for r in sorted(set(reasons))},
    }
    reason_codes: list[str] = []
    warnings: list[str] = []
    if n < limits.min_samples:
        reason_codes.append("MTF_THRESHOLD_REPLAY_SAMPLE_COUNT_LOW")
    if not profile.approvable:
        reason_codes.append("DIAGNOSTIC_THRESHOLD_PROFILE_NOT_APPROVABLE")
    if profile.indecision_margin < limits.min_indecision_margin:
        reason_codes.append("INDECISION_MARGIN_BELOW_FLOOR")
    if action_pct < limits.min_calibrated_action_pct:
        reason_codes.append("MTF_THRESHOLD_REPLAY_ACTION_COVERAGE_LOW")
    if action_pct > limits.max_calibrated_action_pct:
        reason_codes.append("MTF_THRESHOLD_REPLAY_ACTION_COVERAGE_HIGH")
    if side_pct > limits.max_calibrated_action_side_pct:
        reason_codes.append("MTF_THRESHOLD_REPLAY_SIDE_IMBALANCE_HIGH")
    if action_precision < limits.min_action_precision:
        reason_codes.append("MTF_THRESHOLD_REPLAY_ACTION_PRECISION_LOW")
    if action_recall < limits.min_action_recall:
        reason_codes.append("MTF_THRESHOLD_REPLAY_ACTION_RECALL_LOW")
    if expected_edge_proxy_bps < limits.min_expected_edge_proxy_bps:
        reason_codes.append("MTF_THRESHOLD_REPLAY_EXPECTED_EDGE_LOW")
    if metrics["low_margin_rejection_pct"] > limits.max_low_margin_rejection_pct:
        reason_codes.append("MTF_THRESHOLD_REPLAY_LOW_MARGIN_REJECTION_HIGH")
    if metrics["buy_sell_margin_mean"] < limits.min_buy_sell_margin_mean:
        reason_codes.append("MTF_THRESHOLD_REPLAY_BUY_SELL_SEPARATION_LOW")
    if metrics["action_hold_margin_mean"] < limits.min_action_hold_margin_mean:
        reason_codes.append("MTF_THRESHOLD_REPLAY_ACTION_HOLD_MARGIN_LOW")
    if 0 < action_pct < limits.min_calibrated_action_pct * 1.5:
        warnings.append("ACTION_COVERAGE_NEAR_FLOOR")
    if expected_edge_proxy_bps > 0 and action_pct < limits.min_calibrated_action_pct:
        warnings.append("POSITIVE_EDGE_BUT_TOO_FEW_ACTIONS")

    score = 0.0
    score += min(45.0, expected_edge_proxy_bps / 2.0)
    score += 25.0 * action_precision
    score += 8.0 * action_recall
    score += 10.0 * metrics["buy_sell_margin_mean"]
    score += 6.0 * metrics["action_hold_margin_mean"]
    score -= abs(action_pct - limits.target_calibrated_action_pct) * 0.9
    score -= max(0.0, side_pct - 65.0) * 0.7
    score -= len(reason_codes) * 24.0
    score = round(score, 6)
    ok = not reason_codes
    return ThresholdReplayEvaluation(
        contract_version=CONTRACT_VERSION,
        report_type="mtf_15m_threshold_replay_profile_gate",
        profile=asdict(profile),
        decision="PASS" if ok else "BLOCK",
        ok=ok,
        approvable=profile.approvable,
        approved_for_training_candidate=ok,
        approved_for_paper_candidate=False,
        approved_for_live_real=False,
        reload_allowed=False,
        reason_codes=reason_codes,
        warnings=warnings,
        metrics=metrics,
        limits=asdict(limits),
        score=score,
    )


def _best_key(ev: ThresholdReplayEvaluation) -> tuple[int, float]:
    return (1 if ev.ok else 0, ev.score)


def build_threshold_replay_gate(
    evaluations: Sequence[ThresholdReplayEvaluation | Mapping[str, Any]],
    *,
    source: str = "unknown",
    candidate_model: str | None = None,
) -> dict[str, Any]:
    eval_dicts: list[dict[str, Any]] = []
    ev_objs: list[ThresholdReplayEvaluation] = []
    for ev in evaluations:
        if isinstance(ev, ThresholdReplayEvaluation):
            ev_objs.append(ev)
            eval_dicts.append(asdict(ev))
        else:
            eval_dicts.append(dict(ev))
    if ev_objs:
        selected_obj = max(ev_objs, key=_best_key)
        selected = asdict(selected_obj)
    else:
        selected = max(eval_dicts, key=lambda d: (1 if d.get("ok") else 0, _safe_float(d.get("score"))), default={})
    ok = bool(selected.get("ok"))
    reason_codes = sorted({code for e in eval_dicts for code in e.get("reason_codes", [])})
    if not ok and "NO_15M_THRESHOLD_REPLAY_PROFILE_PASSED" not in reason_codes:
        reason_codes.insert(0, "NO_15M_THRESHOLD_REPLAY_PROFILE_PASSED")
    report = {
        "contract_version": CONTRACT_VERSION,
        "phase": CONTRACT_VERSION,
        "report_type": "mtf_15m_threshold_calibration_replay_gate",
        "decision": "PASS" if ok else "BLOCK",
        "ok": ok,
        "source": source,
        "candidate_model": candidate_model,
        "profile_count": len(eval_dicts),
        "approved_for_training_candidate": ok,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "live_real_allowed": False,
        "reload_performed": False,
        "config_mutation_performed": False,
        "order_actions_performed": False,
        "no_post_actions": True,
        "observation_only": True,
        "reason_codes": [] if ok else reason_codes,
        "recommendation": (
            "A 15m threshold replay profile passed the offline gate. Use it only for controlled model/replay research; do not start paper/live trading."
            if ok else
            "No safe 15m threshold/calibration replay profile passed. Do not change runtime thresholds or promote/reload."
        ),
        "selection": {
            "decision": "PASS" if ok else "BLOCK",
            "approved": ok,
            "selected_profile": selected,
            "reason_codes": [] if ok else reason_codes,
        },
        "profiles": eval_dicts,
        "guardrails": {
            "observation_only": True,
            "no_post_actions": True,
            "post_requests_allowed": False,
            "config_mutation_performed": False,
            "order_actions_performed": False,
            "reload_performed": False,
            "live_real_allowed": False,
        },
    }
    return report


def samples_from_json(data: Mapping[str, Any]) -> tuple[list[list[float]], list[int], list[float]]:
    samples = data.get("samples")
    if not isinstance(samples, list):
        return [], [], []
    probabilities: list[list[float]] = []
    actual: list[int] = []
    edges: list[float] = []
    for row in samples:
        if not isinstance(row, Mapping):
            continue
        p = row.get("probabilities") or row.get("proba") or [row.get("holdProbability"), row.get("buyProbability"), row.get("sellProbability")]
        if not isinstance(p, Sequence) or len(p) < 3:
            continue
        probabilities.append([_safe_float(p[0]), _safe_float(p[1]), _safe_float(p[2])])
        actual_value = row.get("actual") or row.get("actual_class") or row.get("label") or 0
        if isinstance(actual_value, str):
            actual.append(ACTION_CLASS.get(actual_value.upper(), 0))
        else:
            actual.append(int(_safe_float(actual_value, 0)))
        edges.append(_safe_float(row.get("edge_bps") or row.get("forward_edge_bps") or row.get("expected_edge_bps"), 0.0))
    return probabilities, actual, edges


def evaluate_samples_with_profiles(
    probabilities: Sequence[Sequence[float]],
    actual_labels: Sequence[int],
    forward_edge_bps: Sequence[float],
    profile_names: Sequence[str] | None = None,
    limits: ThresholdReplayGateLimits | None = None,
) -> list[ThresholdReplayEvaluation]:
    profiles = [threshold_profile(name) for name in profile_names] if profile_names else default_threshold_profiles()
    return [evaluate_threshold_replay_profile(probabilities, actual_labels, forward_edge_bps, profile, limits) for profile in profiles]


def load_25b_report(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def selected_candidate_from_25b(report: Mapping[str, Any], candidate_index: int | None = None) -> dict[str, Any]:
    candidates = report.get("candidates") if isinstance(report.get("candidates"), list) else []
    if candidate_index is not None and candidates:
        idx = max(0, min(len(candidates) - 1, candidate_index - 1))
        return dict(candidates[idx])
    best = ((report.get("selection") or {}).get("best_candidate") or {}) if isinstance(report.get("selection"), Mapping) else {}
    if best:
        return dict(best)
    if candidates:
        return dict(candidates[0])
    return {}


def replay_candidate_model_from_25b_report(
    report: Mapping[str, Any],
    *,
    rows: list[dict[str, Any]],
    candidate_index: int | None = None,
    model_path: str | None = None,
    profile_names: Sequence[str] | None = None,
) -> tuple[list[ThresholdReplayEvaluation], str]:
    # Reuse 25B feature construction to ensure validation replay matches the candidate training pipeline.
    from tradebot.multitimeframe_retrain_sweep_25b import build_feature_frame, parse_policy_name  # type: ignore

    candidate = selected_candidate_from_25b(report, candidate_index)
    spec = candidate.get("candidate_spec") or {}
    policy_data = spec.get("policy") or spec.get("label_policy") or candidate.get("label_policy") or {}
    policy_name = policy_data.get("name") if isinstance(policy_data, Mapping) else None
    if not policy_name:
        policy_name = "mtf_15m_h16_cost20_edge40_atr3_0"
    policy = parse_policy_name(str(policy_name))
    X, y, edges, _, _ = build_feature_frame(rows, policy)
    split = int(len(y) * 0.80)
    X_val = X[split:]
    y_val = y[split:]
    edges_val = edges[split:]
    resolved_model_path = model_path or candidate.get("model_path") or candidate.get("output")
    if not resolved_model_path:
        raise RuntimeError("25B candidate model_path missing; cannot replay thresholds without probabilities")
    path = Path(str(resolved_model_path))
    if not path.exists():
        raise RuntimeError(f"25B candidate model file not found: {path}")
    try:
        from xgboost import XGBClassifier  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("xgboost is required for 25C replay from candidate model") from exc
    model = XGBClassifier()
    model.load_model(str(path))
    raw = model.predict_proba(X_val)
    probabilities: list[list[float]] = []
    for row in raw:
        vals = [float(x) for x in list(row)]
        while len(vals) < 3:
            vals.append(0.0)
        s = sum(max(0.0, x) for x in vals[:3])
        if s <= 1e-12:
            probabilities.append([1.0, 0.0, 0.0])
        else:
            probabilities.append([max(0.0, vals[0]) / s, max(0.0, vals[1]) / s, max(0.0, vals[2]) / s])
    return evaluate_samples_with_profiles(probabilities, y_val, edges_val, profile_names), str(path).replace("\\", "/")


def write_reports(report: Mapping[str, Any], out_dir: str | Path = "reports") -> tuple[Path, Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    stamp = utc_stamp()
    json_path = out / f"{REPORT_PREFIX}_{stamp}.json"
    md_path = out / f"{REPORT_PREFIX}_{stamp}.md"
    with json_path.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, sort_keys=True)
    selected = (report.get("selection") or {}).get("selected_profile") or {}
    selected_metrics = selected.get("metrics") or {}
    lines = [
        f"# {CONTRACT_VERSION} 15m Threshold/Calibration Replay Gate",
        "",
        f"- contract_version: `{CONTRACT_VERSION}`",
        f"- decision: **{report.get('decision')}**",
        f"- profile_count: `{report.get('profile_count')}`",
        f"- approved_for_training_candidate: `{report.get('approved_for_training_candidate')}`",
        f"- approved_for_paper_candidate: `{report.get('approved_for_paper_candidate')}`",
        f"- approved_for_live_real: `{report.get('approved_for_live_real')}`",
        f"- selected_profile: `{(selected.get('profile') or {}).get('name')}`",
        f"- selected_action_pct: `{selected_metrics.get('calibrated_action_pct')}`",
        f"- selected_expected_edge_proxy_bps: `{selected_metrics.get('expected_edge_proxy_bps')}`",
        f"- recommendation: {report.get('recommendation')}",
        "",
        "## Guardrails",
        "",
        "- observation_only: `True`",
        "- no_post_actions: `True`",
        "- post_requests_allowed: `False`",
        "- config_mutation_performed: `False`",
        "- order_actions_performed: `False`",
        "- reload_performed: `False`",
        "- live_real_allowed: `False`",
        "",
        "## Profiles",
        "",
        "| profile | approvable | decision | score | action_pct | precision | recall | edge_proxy_bps | side_pct | reasons | warnings |",
        "|---|---:|---|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for item in report.get("profiles", []):
        profile = item.get("profile", {})
        metrics = item.get("metrics", {})
        lines.append(
            "| {name} | {approvable} | {decision} | {score} | {action} | {precision} | {recall} | {edge} | {side} | `{reasons}` | `{warnings}` |".format(
                name=profile.get("name"),
                approvable=item.get("approvable"),
                decision=item.get("decision"),
                score=item.get("score"),
                action=metrics.get("calibrated_action_pct"),
                precision=metrics.get("action_precision"),
                recall=metrics.get("action_recall"),
                edge=metrics.get("expected_edge_proxy_bps"),
                side=metrics.get("calibrated_action_side_pct"),
                reasons=item.get("reason_codes", []),
                warnings=item.get("warnings", []),
            )
        )
    lines.extend([
        "",
        "## Policy",
        "",
        "This replay gate never applies thresholds, mutates config, reloads models, starts paper trading, or sends orders. A PASS only identifies an offline research candidate; real live trading remains blocked.",
    ])
    with md_path.open("w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
    return json_path, md_path


def promote_best(report: Mapping[str, Any], promote_to: str | Path) -> str | None:
    # 25C profiles are threshold candidates, not model artifacts; promotion is intentionally disabled.
    return None
