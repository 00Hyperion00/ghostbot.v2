"""4B.4.3.6.6.25B - 15m Multi-Timeframe Retrain Sweep + Gate.

This module is intentionally self-contained and conservative. It can train
candidate 15m models from public market data, evaluate them with a separation
and expected-edge gate, and write reports/sidecars. It never reloads models,
mutates config, starts paper trading, or sends orders.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
import csv
import json
import math
import shutil
import time
import urllib.parse
import urllib.request

CONTRACT_VERSION = "4B.4.3.6.6.25B"
REPORT_PREFIX = "4B436625B_15m_mtf_retrain_sweep"
CANDIDATE_DIR = "models/4B436625B_candidates"

ACTION_CLASS = {"HOLD": 0, "BUY": 1, "SELL": 2}
CLASS_NAME = {0: "HOLD", 1: "BUY", 2: "SELL"}

DEFAULT_POLICY_NAMES = [
    "mtf_15m_h16_cost20_edge40_atr3_0",
    "mtf_15m_h8_cost16_edge30_atr2_5",
]


@dataclass(frozen=True)
class MultiTimeframeRetrainPolicy:
    name: str
    interval: str = "15m"
    lookahead: int = 16
    cost_bps: float = 20.0
    min_edge_bps: float = 40.0
    atr_multiplier: float = 3.0
    approvable: bool = True
    family: str = "mtf_directional"

    @property
    def effective_floor_bps(self) -> float:
        return float(self.cost_bps + self.min_edge_bps)


@dataclass(frozen=True)
class MultiTimeframeRetrainCandidateSpec:
    policy: MultiTimeframeRetrainPolicy
    class_weight_profile: str = "balanced"
    threshold_profile: str = "balanced"
    max_depth: int = 3
    n_estimators: int = 96
    learning_rate: float = 0.045
    subsample: float = 0.9
    colsample_bytree: float = 0.9


@dataclass(frozen=True)
class MultiTimeframeRetrainGateLimits:
    min_clean_samples: int = 500
    min_target_action_pct: float = 3.0
    max_target_action_pct: float = 45.0
    min_target_hold_pct: float = 35.0
    max_target_side_pct: float = 78.0
    min_raw_action_pct: float = 2.0
    max_raw_action_pct: float = 55.0
    min_calibrated_action_pct: float = 1.0
    max_calibrated_action_pct: float = 38.0
    max_calibrated_side_pct: float = 82.0
    min_buy_sell_margin_mean: float = 0.018
    min_buy_sell_margin_median: float = 0.012
    min_action_hold_margin_mean: float = 0.006
    min_accuracy: float = 0.30
    min_calibrated_accuracy: float = 0.30
    min_action_precision: float = 0.22
    min_expected_edge_proxy_bps: float = 0.0
    target_calibrated_action_pct: float = 15.0


@dataclass
class CandidateEvaluation:
    contract_version: str
    report_type: str
    decision: str
    ok: bool
    approved_for_training_candidate: bool
    approved_for_paper_candidate: bool
    approved_for_live_real: bool
    reload_allowed: bool
    model_path: str | None
    candidate_spec: dict[str, Any]
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


def parse_policy_name(name: str) -> MultiTimeframeRetrainPolicy:
    """Parse names such as mtf_15m_h16_cost20_edge40_atr3_0."""
    parts = name.split("_")
    interval = "15m"
    lookahead = 16
    cost_bps = 20.0
    edge_bps = 40.0
    atr_multiplier = 3.0
    for idx, part in enumerate(parts):
        if part.endswith("m") or part.endswith("h"):
            if part not in {"mtf"}:
                interval = part
        if part.startswith("h") and part[1:].isdigit():
            lookahead = int(part[1:])
        if part.startswith("cost"):
            cost_bps = _safe_float(part.replace("cost", ""), cost_bps)
        if part.startswith("edge"):
            edge_bps = _safe_float(part.replace("edge", ""), edge_bps)
        if part.startswith("atr"):
            tail = part.replace("atr", "")
            if idx + 1 < len(parts) and parts[idx + 1].isdigit():
                tail = f"{tail}.{parts[idx + 1]}"
            atr_multiplier = _safe_float(tail.replace("_", "."), atr_multiplier)
    return MultiTimeframeRetrainPolicy(
        name=name,
        interval=interval,
        lookahead=lookahead,
        cost_bps=cost_bps,
        min_edge_bps=edge_bps,
        atr_multiplier=atr_multiplier,
    )


def policies_from_25a_report(report: Mapping[str, Any] | None) -> list[MultiTimeframeRetrainPolicy]:
    names: list[str] = []
    if report:
        selected = report.get("selected_policy") or (report.get("selection") or {}).get("selected_policy")
        if isinstance(selected, str):
            names.append(selected)
        selected_candidate = report.get("selected_candidate") or report.get("selected") or {}
        if isinstance(selected_candidate, Mapping):
            cand_name = selected_candidate.get("policy") or selected_candidate.get("name")
            if isinstance(cand_name, str):
                names.append(cand_name)
        for cand in report.get("candidates", []) if isinstance(report.get("candidates", []), list) else []:
            if not isinstance(cand, Mapping):
                continue
            if cand.get("decision") == "PASS" or cand.get("ok") is True or cand.get("approved_for_training_candidate") is True:
                name = cand.get("policy") or cand.get("name") or cand.get("policy_name")
                if isinstance(name, str):
                    names.append(name)
    for default in DEFAULT_POLICY_NAMES:
        names.append(default)
    seen: set[str] = set()
    parsed: list[MultiTimeframeRetrainPolicy] = []
    for name in names:
        if name in seen or not name.startswith("mtf_15m"):
            continue
        seen.add(name)
        parsed.append(parse_policy_name(name))
    return parsed[:4]


def threshold_config(profile: str) -> dict[str, float]:
    profiles = {
        "balanced": {
            "buy_threshold": 0.62,
            "sell_threshold": 0.60,
            "hold_band_low": 0.44,
            "hold_band_high": 0.56,
            "indecision_margin": 0.055,
        },
        "action_seek_light": {
            "buy_threshold": 0.56,
            "sell_threshold": 0.55,
            "hold_band_low": 0.42,
            "hold_band_high": 0.54,
            "indecision_margin": 0.035,
        },
        "paper_guarded": {
            "buy_threshold": 0.58,
            "sell_threshold": 0.57,
            "hold_band_low": 0.43,
            "hold_band_high": 0.55,
            "indecision_margin": 0.045,
        },
    }
    return dict(profiles.get(profile, profiles["balanced"]))


def class_weight_map(profile: str, y: Sequence[int]) -> dict[int, float]:
    counts = {0: 0, 1: 0, 2: 0}
    for value in y:
        counts[int(value)] = counts.get(int(value), 0) + 1
    n = max(1, len(y))
    base = {k: n / (3.0 * max(1, v)) for k, v in counts.items()}
    if profile == "buy_sell_boost_light":
        base[1] *= 1.15
        base[2] *= 1.15
        base[0] *= 0.9
    elif profile == "buy_sell_boost_medium":
        base[1] *= 1.35
        base[2] *= 1.35
        base[0] *= 0.78
    elif profile == "hold_guarded":
        base[0] *= 1.10
    return base


def fetch_binance_klines(symbol: str, interval: str, days: int, base_url: str) -> list[dict[str, Any]]:
    interval_ms = {
        "1m": 60_000,
        "5m": 300_000,
        "15m": 900_000,
        "1h": 3_600_000,
    }.get(interval, 900_000)
    end_ms = int(time.time() * 1000)
    start_ms = end_ms - int(days * 24 * 60 * 60 * 1000)
    rows: list[dict[str, Any]] = []
    limit = 1000
    current = start_ms
    while current < end_ms:
        params = urllib.parse.urlencode(
            {
                "symbol": symbol.upper(),
                "interval": interval,
                "limit": limit,
                "startTime": current,
                "endTime": end_ms,
            }
        )
        url = f"{base_url.rstrip('/')}/api/v3/klines?{params}"
        with urllib.request.urlopen(url, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if not payload:
            break
        for k in payload:
            rows.append(
                {
                    "open_time": int(k[0]),
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5]),
                    "close_time": int(k[6]),
                    "quote_volume": float(k[7]),
                    "trades": float(k[8]),
                    "taker_buy_base": float(k[9]),
                    "taker_buy_quote": float(k[10]),
                }
            )
        next_time = int(payload[-1][0]) + interval_ms
        if next_time <= current:
            break
        current = next_time
        if len(payload) < limit:
            break
        time.sleep(0.05)
    # de-duplicate and sort
    dedup = {int(r["open_time"]): r for r in rows}
    return [dedup[k] for k in sorted(dedup)]


def read_ohlcv_csv(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for idx, row in enumerate(reader):
            rows.append(
                {
                    "open_time": int(_safe_float(row.get("open_time") or row.get("timestamp") or idx)),
                    "open": _safe_float(row.get("open")),
                    "high": _safe_float(row.get("high")),
                    "low": _safe_float(row.get("low")),
                    "close": _safe_float(row.get("close")),
                    "volume": _safe_float(row.get("volume")),
                    "quote_volume": _safe_float(row.get("quote_volume") or row.get("quoteVolume")),
                    "taker_buy_quote": _safe_float(row.get("taker_buy_quote") or row.get("takerBuyQuote")),
                }
            )
    return rows


def _ema(values: Sequence[float], period: int) -> list[float]:
    if not values:
        return []
    alpha = 2.0 / (period + 1.0)
    out = [float(values[0])]
    for value in values[1:]:
        out.append(alpha * float(value) + (1 - alpha) * out[-1])
    return out


def _rolling_mean(values: Sequence[float], period: int) -> list[float]:
    out: list[float] = []
    total = 0.0
    q: list[float] = []
    for value in values:
        v = float(value)
        q.append(v)
        total += v
        if len(q) > period:
            total -= q.pop(0)
        out.append(total / max(1, len(q)))
    return out


def _rsi(closes: Sequence[float], period: int = 14) -> list[float]:
    gains: list[float] = [0.0]
    losses: list[float] = [0.0]
    for i in range(1, len(closes)):
        delta = closes[i] - closes[i - 1]
        gains.append(max(0.0, delta))
        losses.append(max(0.0, -delta))
    avg_gain = _rolling_mean(gains, period)
    avg_loss = _rolling_mean(losses, period)
    out = []
    for g, l in zip(avg_gain, avg_loss):
        if l <= 1e-12:
            out.append(100.0 if g > 0 else 50.0)
        else:
            rs = g / l
            out.append(100.0 - (100.0 / (1.0 + rs)))
    return out


def _atr(rows: Sequence[Mapping[str, Any]], period: int = 14) -> list[float]:
    trs: list[float] = []
    prev_close: float | None = None
    for r in rows:
        high = _safe_float(r.get("high"))
        low = _safe_float(r.get("low"))
        close = _safe_float(r.get("close"))
        if prev_close is None:
            tr = high - low
        else:
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        trs.append(max(0.0, tr))
        prev_close = close
    return _rolling_mean(trs, period)


def build_feature_frame(rows: list[dict[str, Any]], policy: MultiTimeframeRetrainPolicy) -> tuple[list[list[float]], list[int], list[float], list[str], dict[str, Any]]:
    closes = [_safe_float(r["close"]) for r in rows]
    highs = [_safe_float(r["high"]) for r in rows]
    lows = [_safe_float(r["low"]) for r in rows]
    opens = [_safe_float(r["open"]) for r in rows]
    volumes = [_safe_float(r.get("volume")) for r in rows]
    quote_volumes = [_safe_float(r.get("quote_volume")) for r in rows]
    taker_buy_quote = [_safe_float(r.get("taker_buy_quote")) for r in rows]

    ema9 = _ema(closes, 9)
    ema21 = _ema(closes, 21)
    ema55 = _ema(closes, 55)
    ema144 = _ema(closes, 144)
    rsi14 = _rsi(closes, 14)
    atr14 = _atr(rows, 14)
    vol_mean = _rolling_mean(volumes, 48)
    qv_mean = _rolling_mean(quote_volumes, 48)
    feature_names = [
        "ret_1", "ret_3", "ret_8", "ret_16", "range_pct", "body_pct",
        "ema9_21_pct", "ema21_55_pct", "ema55_144_pct", "rsi14_norm",
        "atr_pct", "volume_ratio", "quote_volume_ratio", "taker_buy_pressure",
        "close_location_pct", "trend_strength", "volatility_expansion", "vwap_proxy_dist",
    ]
    features: list[list[float]] = []
    labels: list[int] = []
    forward_edge_bps: list[float] = []

    min_start = 160
    last_i = len(rows) - policy.lookahead - 1
    for i in range(min_start, max(min_start, last_i)):
        close = max(1e-12, closes[i])
        ret_1 = (closes[i] / max(1e-12, closes[i - 1]) - 1.0) if i >= 1 else 0.0
        ret_3 = (closes[i] / max(1e-12, closes[i - 3]) - 1.0) if i >= 3 else 0.0
        ret_8 = (closes[i] / max(1e-12, closes[i - 8]) - 1.0) if i >= 8 else 0.0
        ret_16 = (closes[i] / max(1e-12, closes[i - 16]) - 1.0) if i >= 16 else 0.0
        rng = max(0.0, highs[i] - lows[i])
        body = closes[i] - opens[i]
        close_location = (closes[i] - lows[i]) / max(1e-12, rng)
        vol_ratio = volumes[i] / max(1e-12, vol_mean[i])
        qv_ratio = quote_volumes[i] / max(1e-12, qv_mean[i])
        pressure = taker_buy_quote[i] / max(1e-12, quote_volumes[i]) if quote_volumes[i] > 0 else 0.5
        vwap_proxy = (highs[i] + lows[i] + closes[i]) / 3.0
        f = [
            ret_1,
            ret_3,
            ret_8,
            ret_16,
            rng / close,
            body / close,
            (ema9[i] - ema21[i]) / close,
            (ema21[i] - ema55[i]) / close,
            (ema55[i] - ema144[i]) / close,
            (rsi14[i] - 50.0) / 50.0,
            atr14[i] / close,
            vol_ratio,
            qv_ratio,
            pressure - 0.5,
            close_location - 0.5,
            abs(ema9[i] - ema55[i]) / close,
            (atr14[i] / close) / max(1e-12, _safe_float(sum((atr14[j] / max(1e-12, closes[j])) for j in range(max(0, i - 48), i + 1)) / max(1, min(49, i + 1)))),
            (closes[i] - vwap_proxy) / close,
        ]
        future_high = max(highs[i + 1 : i + 1 + policy.lookahead])
        future_low = min(lows[i + 1 : i + 1 + policy.lookahead])
        future_close = closes[i + policy.lookahead]
        up_bps = (future_high / close - 1.0) * 10000.0
        down_bps = (1.0 - future_low / close) * 10000.0
        close_ret_bps = (future_close / close - 1.0) * 10000.0
        atr_floor_bps = (atr14[i] / close) * policy.atr_multiplier * 10000.0
        floor = max(policy.effective_floor_bps, atr_floor_bps)
        if up_bps >= floor and up_bps > down_bps:
            label = ACTION_CLASS["BUY"]
            edge = close_ret_bps - policy.cost_bps
        elif down_bps >= floor and down_bps > up_bps:
            label = ACTION_CLASS["SELL"]
            edge = -close_ret_bps - policy.cost_bps
        else:
            label = ACTION_CLASS["HOLD"]
            edge = 0.0
        if all(math.isfinite(x) for x in f):
            features.append(f)
            labels.append(label)
            forward_edge_bps.append(edge)
    metadata = {
        "feature_columns": feature_names,
        "clean_samples": len(labels),
        "policy": asdict(policy),
    }
    return features, labels, forward_edge_bps, feature_names, metadata


def _softmax_scores_from_predict_proba(proba: Any) -> list[list[float]]:
    out: list[list[float]] = []
    for row in proba:
        vals = [float(x) for x in list(row)]
        if len(vals) == 2:
            # binary fallback -> [hold, buy, sell(0)] not ideal, normalized below
            vals = [vals[0], vals[1], 0.0]
        while len(vals) < 3:
            vals.append(0.0)
        s = sum(max(0.0, v) for v in vals[:3])
        if s <= 1e-12:
            out.append([1.0, 0.0, 0.0])
        else:
            out.append([max(0.0, vals[0]) / s, max(0.0, vals[1]) / s, max(0.0, vals[2]) / s])
    return out


def calibrate_probabilities(probabilities: Sequence[Sequence[float]], config: Mapping[str, float]) -> tuple[list[int], list[str]]:
    preds: list[int] = []
    reasons: list[str] = []
    buy_th = _safe_float(config.get("buy_threshold"), 0.62)
    sell_th = _safe_float(config.get("sell_threshold"), 0.60)
    hold_low = _safe_float(config.get("hold_band_low"), 0.44)
    hold_high = _safe_float(config.get("hold_band_high"), 0.56)
    margin = _safe_float(config.get("indecision_margin"), 0.055)
    for p in probabilities:
        hold, buy, sell = [float(x) for x in p[:3]]
        action_prob = max(buy, sell)
        side = 1 if buy >= sell else 2
        side_gap = abs(buy - sell)
        action_hold_gap = action_prob - hold
        if hold_low <= hold <= hold_high and action_hold_gap < margin:
            preds.append(0); reasons.append("REJECT_ACTION_HOLD_MARGIN")
        elif side_gap < margin:
            preds.append(0); reasons.append("REJECT_LOW_SIDE_MARGIN")
        elif side == 1 and buy >= buy_th and action_hold_gap >= 0:
            preds.append(1); reasons.append("ACCEPT_BUY")
        elif side == 2 and sell >= sell_th and action_hold_gap >= 0:
            preds.append(2); reasons.append("ACCEPT_SELL")
        elif action_prob >= max(buy_th, sell_th) and action_hold_gap >= margin:
            preds.append(side); reasons.append("ACCEPT_ACTION_FALLBACK")
        else:
            preds.append(0); reasons.append("REJECT_FALLBACK_HOLD")
    return preds, reasons


def _distribution(values: Sequence[int]) -> dict[str, int]:
    counts = {"HOLD": 0, "BUY": 0, "SELL": 0}
    for v in values:
        counts[CLASS_NAME.get(int(v), str(v))] = counts.get(CLASS_NAME.get(int(v), str(v)), 0) + 1
    return counts


def _pct(part: float, total: float) -> float:
    return round(100.0 * part / total, 6) if total else 0.0


def _mean(values: Sequence[float]) -> float:
    return round(sum(values) / len(values), 8) if values else 0.0


def _median(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    mid = len(s) // 2
    if len(s) % 2:
        return round(s[mid], 8)
    return round((s[mid - 1] + s[mid]) / 2.0, 8)


def evaluate_mtf_retrain_candidate_result(result: Mapping[str, Any], limits: MultiTimeframeRetrainGateLimits | None = None) -> CandidateEvaluation:
    limits = limits or MultiTimeframeRetrainGateLimits()
    metrics = dict(result.get("metrics", {}))
    reason_codes: list[str] = []
    warnings: list[str] = []

    clean_samples = int(_safe_float(metrics.get("clean_samples")))
    target_action_pct = _safe_float(metrics.get("target_action_pct"))
    target_hold_pct = _safe_float(metrics.get("target_hold_pct"))
    target_side_pct = _safe_float(metrics.get("target_action_side_pct"))
    raw_action_pct = _safe_float(metrics.get("validation_raw_action_pct"))
    calibrated_action_pct = _safe_float(metrics.get("validation_calibrated_action_pct"))
    calibrated_side_pct = _safe_float(metrics.get("validation_calibrated_action_side_pct"))
    buy_sell_margin_mean = _safe_float(metrics.get("buy_sell_margin_mean"))
    buy_sell_margin_median = _safe_float(metrics.get("buy_sell_margin_median"))
    action_hold_margin_mean = _safe_float(metrics.get("action_hold_margin_mean"))
    accuracy = _safe_float(metrics.get("accuracy"))
    calibrated_accuracy = _safe_float(metrics.get("calibrated_accuracy"))
    action_precision = _safe_float(metrics.get("action_precision"))
    expected_edge_proxy_bps = _safe_float(metrics.get("expected_edge_proxy_bps"))

    if clean_samples < limits.min_clean_samples:
        reason_codes.append("MTF_RETRAIN_CLEAN_SAMPLE_COUNT_LOW")
    if target_action_pct < limits.min_target_action_pct:
        reason_codes.append("MTF_RETRAIN_TARGET_ACTION_COVERAGE_LOW")
    if target_action_pct > limits.max_target_action_pct:
        reason_codes.append("MTF_RETRAIN_TARGET_ACTION_COVERAGE_HIGH")
    if target_hold_pct < limits.min_target_hold_pct:
        reason_codes.append("MTF_RETRAIN_TARGET_HOLD_COVERAGE_LOW")
    if target_side_pct > limits.max_target_side_pct:
        reason_codes.append("MTF_RETRAIN_TARGET_SIDE_IMBALANCE_HIGH")
    if raw_action_pct < limits.min_raw_action_pct:
        reason_codes.append("MTF_RETRAIN_RAW_ACTION_COVERAGE_LOW")
    if raw_action_pct > limits.max_raw_action_pct:
        reason_codes.append("MTF_RETRAIN_RAW_ACTION_COVERAGE_HIGH")
    if calibrated_action_pct < limits.min_calibrated_action_pct:
        reason_codes.append("MTF_RETRAIN_CALIBRATED_ACTION_COVERAGE_LOW")
    if calibrated_action_pct > limits.max_calibrated_action_pct:
        reason_codes.append("MTF_RETRAIN_CALIBRATED_ACTION_COVERAGE_HIGH")
    if calibrated_side_pct > limits.max_calibrated_side_pct:
        reason_codes.append("MTF_RETRAIN_CALIBRATED_SIDE_IMBALANCE_HIGH")
    if buy_sell_margin_mean < limits.min_buy_sell_margin_mean:
        reason_codes.append("MTF_RETRAIN_BUY_SELL_SEPARATION_MEAN_LOW")
    if buy_sell_margin_median < limits.min_buy_sell_margin_median:
        reason_codes.append("MTF_RETRAIN_BUY_SELL_SEPARATION_MEDIAN_LOW")
    if action_hold_margin_mean < limits.min_action_hold_margin_mean:
        reason_codes.append("MTF_RETRAIN_ACTION_HOLD_SEPARATION_MEAN_LOW")
    if accuracy < limits.min_accuracy:
        reason_codes.append("MTF_RETRAIN_ACCURACY_LOW")
    if calibrated_accuracy < limits.min_calibrated_accuracy:
        reason_codes.append("MTF_RETRAIN_CALIBRATED_ACCURACY_LOW")
    if action_precision < limits.min_action_precision:
        reason_codes.append("MTF_RETRAIN_ACTION_PRECISION_LOW")
    if expected_edge_proxy_bps < limits.min_expected_edge_proxy_bps:
        reason_codes.append("MTF_RETRAIN_EXPECTED_EDGE_PROXY_LOW")

    if 0 < calibrated_action_pct < limits.min_calibrated_action_pct * 1.5:
        warnings.append("CALIBRATED_ACTION_COVERAGE_NEAR_FLOOR")
    if abs(calibrated_action_pct - limits.target_calibrated_action_pct) <= 3.0:
        warnings.append("CALIBRATED_ACTION_RATE_NEAR_TARGET")

    score = 0.0
    score += min(35.0, expected_edge_proxy_bps / 3.0)
    score += 20.0 * action_precision
    score += 6.0 * calibrated_accuracy
    score += 5.0 * buy_sell_margin_mean
    score += 8.0 * action_hold_margin_mean
    score -= abs(calibrated_action_pct - limits.target_calibrated_action_pct) * 0.7
    score -= max(0.0, calibrated_side_pct - 65.0) * 0.8
    score -= len(reason_codes) * 25.0
    score = round(score, 6)

    ok = not reason_codes
    return CandidateEvaluation(
        contract_version=CONTRACT_VERSION,
        report_type="mtf_15m_retrain_candidate_gate",
        decision="PASS" if ok else "BLOCK",
        ok=ok,
        approved_for_training_candidate=ok,
        approved_for_paper_candidate=False,
        approved_for_live_real=False,
        reload_allowed=False,
        model_path=str(result.get("model_path") or ""),
        candidate_spec=dict(result.get("candidate_spec", {})),
        reason_codes=reason_codes,
        warnings=warnings,
        metrics=metrics,
        limits=asdict(limits),
        score=score,
    )


def _train_model_xgb(X_train: list[list[float]], y_train: list[int], weights: list[float], spec: MultiTimeframeRetrainCandidateSpec, out_path: Path) -> tuple[Any, str]:
    try:
        from xgboost import XGBClassifier  # type: ignore
    except Exception as exc:  # pragma: no cover - dependency specific
        raise RuntimeError("xgboost is required for 25B retrain sweep") from exc
    model = XGBClassifier(
        objective="multi:softprob",
        num_class=3,
        max_depth=spec.max_depth,
        n_estimators=spec.n_estimators,
        learning_rate=spec.learning_rate,
        subsample=spec.subsample,
        colsample_bytree=spec.colsample_bytree,
        eval_metric="mlogloss",
        tree_method="hist",
        random_state=42,
        n_jobs=2,
    )
    model.fit(X_train, y_train, sample_weight=weights)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    model.save_model(str(out_path))
    return model, "xgboost"


def train_mtf_15m_candidate(
    rows: list[dict[str, Any]],
    spec: MultiTimeframeRetrainCandidateSpec,
    symbol: str,
    days: int,
    output_dir: str | Path = CANDIDATE_DIR,
) -> dict[str, Any]:
    X, y, edges, feature_names, metadata = build_feature_frame(rows, spec.policy)
    if len(y) < 1000:
        raise RuntimeError(f"not enough clean samples for 25B candidate: {len(y)}")
    split = int(len(y) * 0.80)
    X_train, X_val = X[:split], X[split:]
    y_train, y_val = y[:split], y[split:]
    edges_val = edges[split:]
    weight_map = class_weight_map(spec.class_weight_profile, y_train)
    weights = [weight_map.get(int(v), 1.0) for v in y_train]

    safe_name = f"{symbol}_model_4b436625B_{spec.policy.name}_{spec.class_weight_profile}_{spec.threshold_profile}.ubj"
    model_path = Path(output_dir) / safe_name
    model, model_format = _train_model_xgb(X_train, y_train, weights, spec, model_path)
    probabilities = _softmax_scores_from_predict_proba(model.predict_proba(X_val))
    raw_pred = [int(max(range(3), key=lambda idx: p[idx])) for p in probabilities]
    calibrated_pred, reasons = calibrate_probabilities(probabilities, threshold_config(spec.threshold_profile))

    total = len(y_val)
    raw_action = [p for p in raw_pred if p != 0]
    cal_action = [p for p in calibrated_pred if p != 0]
    cal_buy = sum(1 for p in calibrated_pred if p == 1)
    cal_sell = sum(1 for p in calibrated_pred if p == 2)
    cal_actions = cal_buy + cal_sell
    target_buy = sum(1 for v in y if v == 1)
    target_sell = sum(1 for v in y if v == 2)
    target_action = target_buy + target_sell
    target_hold = sum(1 for v in y if v == 0)
    actual_action_count = max(1, sum(1 for v in y_val if v != 0))
    correct = sum(1 for a, b in zip(raw_pred, y_val) if a == b)
    cal_correct = sum(1 for a, b in zip(calibrated_pred, y_val) if a == b)
    predicted_action_count = max(1, len(cal_action))
    action_precision = sum(1 for p, a in zip(calibrated_pred, y_val) if p != 0 and p == a) / predicted_action_count if cal_actions else 0.0
    action_recall = sum(1 for p, a in zip(calibrated_pred, y_val) if a != 0 and p == a) / actual_action_count
    expected_edges = [edge if pred == actual and pred != 0 else -abs(edge) for pred, actual, edge in zip(calibrated_pred, y_val, edges_val) if pred != 0]
    expected_edge_proxy_bps = _mean(expected_edges) if expected_edges else -spec.policy.cost_bps
    buy_sell_margins = [abs(p[1] - p[2]) for p in probabilities]
    action_hold_margins = [max(p[1], p[2]) - p[0] for p in probabilities]

    metrics = {
        "clean_samples": len(y),
        "target_distribution": _distribution(y),
        "target_action_pct": _pct(target_action, len(y)),
        "target_hold_pct": _pct(target_hold, len(y)),
        "target_action_side_pct": _pct(max(target_buy, target_sell), target_action),
        "validation_actual_distribution": _distribution(y_val),
        "validation_raw_distribution": _distribution(raw_pred),
        "validation_raw_action_pct": _pct(len(raw_action), total),
        "validation_calibrated_distribution": _distribution(calibrated_pred),
        "validation_calibrated_action_pct": _pct(len(cal_action), total),
        "validation_calibrated_action_side_pct": _pct(max(cal_buy, cal_sell), cal_actions),
        "buy_sell_margin_mean": _mean(buy_sell_margins),
        "buy_sell_margin_median": _median(buy_sell_margins),
        "action_hold_margin_mean": _mean(action_hold_margins),
        "accuracy": round(correct / max(1, total), 8),
        "calibrated_accuracy": round(cal_correct / max(1, total), 8),
        "action_precision": round(action_precision, 8),
        "action_recall": round(action_recall, 8),
        "expected_edge_proxy_bps": expected_edge_proxy_bps,
        "calibrated_reason_counts": {r: reasons.count(r) for r in sorted(set(reasons))},
        "threshold_config": threshold_config(spec.threshold_profile),
        "class_weight_profile": spec.class_weight_profile,
        "threshold_profile": spec.threshold_profile,
        "label_policy": asdict(spec.policy),
    }
    candidate_spec = {
        "policy": asdict(spec.policy),
        "class_weight_profile": spec.class_weight_profile,
        "threshold_profile": spec.threshold_profile,
        "max_depth": spec.max_depth,
        "n_estimators": spec.n_estimators,
        "learning_rate": spec.learning_rate,
    }
    result = {
        "contract_version": CONTRACT_VERSION,
        "workflow_version": CONTRACT_VERSION,
        "symbol": symbol,
        "interval": spec.policy.interval,
        "days": days,
        "model_path": str(model_path).replace("\\", "/"),
        "output": str(model_path).replace("\\", "/"),
        "model_format": model_format,
        "candidate_spec": candidate_spec,
        "feature_columns": feature_names,
        "feature_schema_version": "4B.3.4+25B15m",
        "feature_pack_name": "mtf_15m_cost_aware_core_v1",
        "metrics": metrics,
        "target_distribution": metrics["target_distribution"],
        "prediction_distribution": {
            "actual_class_distribution": metrics["validation_actual_distribution"],
            "predicted_class_distribution": metrics["validation_raw_distribution"],
        },
        "calibrated_action_report": {
            "action_coverage": metrics["validation_calibrated_action_pct"] / 100.0,
            "action_precision": action_precision,
            "action_recall": action_recall,
        },
    }
    gate = evaluate_mtf_retrain_candidate_result(result)
    result["candidate_gate"] = asdict(gate)
    result["decision"] = gate.decision
    result["ok"] = gate.ok
    result["reason_codes"] = gate.reason_codes
    result["warnings"] = gate.warnings
    result["score"] = gate.score
    result["reload_allowed"] = False
    result["approved_for_live_real"] = False
    result["approved_for_paper_candidate"] = False
    # sidecars
    schema_path = model_path.with_suffix(".schema.json")
    manifest_path = model_path.with_suffix(".manifest.json")
    schema = {
        "contract_version": CONTRACT_VERSION,
        "schema_version": result["feature_schema_version"],
        "feature_pack_name": result["feature_pack_name"],
        "feature_columns": feature_names,
        "feature_count": len(feature_names),
        "interval": spec.policy.interval,
        "label_policy": asdict(spec.policy),
    }
    manifest = {
        "contract_version": CONTRACT_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model_path": str(model_path).replace("\\", "/"),
        "schema_path": str(schema_path).replace("\\", "/"),
        "candidate_spec": candidate_spec,
        "candidate_gate": asdict(gate),
        "guardrails": guardrails(),
    }
    schema_path.write_text(json.dumps(schema, indent=2, ensure_ascii=False), encoding="utf-8")
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    result["schema_path"] = str(schema_path).replace("\\", "/")
    result["manifest_path"] = str(manifest_path).replace("\\", "/")
    result["sidecars_written"] = True
    return result


def select_best_candidate(candidates: Sequence[Mapping[str, Any]]) -> dict[str, Any] | None:
    if not candidates:
        return None
    return dict(max(candidates, key=lambda c: _safe_float(c.get("score"))))


def guardrails() -> dict[str, Any]:
    return {
        "observation_only": True,
        "no_post_actions": True,
        "post_requests_allowed": False,
        "config_mutation_performed": False,
        "order_actions_performed": False,
        "reload_performed": False,
        "live_real_allowed": False,
        "promotion_requires_explicit_flag": True,
    }


def build_mtf_15m_retrain_sweep(
    candidates: Sequence[Mapping[str, Any]],
    source: str,
    promoted_to: str | None = None,
    promotion_performed: bool = False,
) -> dict[str, Any]:
    candidate_list = [dict(c) for c in candidates]
    best = select_best_candidate(candidate_list)
    approved = bool(best and best.get("decision") == "PASS" and best.get("ok") is True)
    reason_codes: list[str] = []
    if not approved:
        reason_codes.append("NO_MTF_15M_RETRAIN_CANDIDATE_PASSED")
        for c in candidate_list:
            for reason in c.get("reason_codes", []):
                if reason not in reason_codes:
                    reason_codes.append(reason)
    selection = {
        "contract_version": CONTRACT_VERSION,
        "decision": "PASS" if approved else "BLOCK",
        "approved": approved,
        "reason_codes": [] if approved else reason_codes,
        "best_candidate": best,
    }
    report = {
        "contract_version": CONTRACT_VERSION,
        "phase": CONTRACT_VERSION,
        "report_type": "mtf_15m_retrain_sweep_gate",
        "decision": "PASS" if approved else "BLOCK",
        "ok": approved,
        "source": source,
        "candidate_count": len(candidate_list),
        "approved_for_training_candidate": approved,
        "approved_for_paper_candidate": False,
        "approved_for_live_real": False,
        "live_real_allowed": False,
        "reload_performed": False,
        "config_mutation_performed": False,
        "order_actions_performed": False,
        "no_post_actions": True,
        "observation_only": True,
        "promoted_to": promoted_to,
        "promotion_performed": promotion_performed,
        "reason_codes": reason_codes,
        "recommendation": (
            "A 15m multi-timeframe retrain candidate passed the gate. Use it only for manual review and later controlled reload/probe checks."
            if approved else
            "No 15m multi-timeframe retrain candidate passed. Do not promote/reload; revisit policy, features, or model objective."
        ),
        "selection": selection,
        "candidates": candidate_list,
        "guardrails": guardrails(),
    }
    return report


def write_reports(report: Mapping[str, Any], out_dir: str | Path = "reports") -> tuple[Path, Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    stamp = utc_stamp()
    json_path = out / f"{REPORT_PREFIX}_{stamp}.json"
    md_path = out / f"{REPORT_PREFIX}_{stamp}.md"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    return json_path, md_path


def render_markdown(report: Mapping[str, Any]) -> str:
    selection = report.get("selection") or {}
    best = selection.get("best_candidate") if isinstance(selection, Mapping) else None
    best = best if isinstance(best, Mapping) else {}
    metrics = best.get("metrics") if isinstance(best, Mapping) else {}
    metrics = metrics if isinstance(metrics, Mapping) else {}
    lines = [
        f"# {CONTRACT_VERSION} 15m Multi-Timeframe Retrain Sweep + Gate",
        "",
        f"- contract_version: `{report.get('contract_version')}`",
        f"- decision: **{report.get('decision')}**",
        f"- candidate_count: `{report.get('candidate_count')}`",
        f"- approved_for_training_candidate: `{report.get('approved_for_training_candidate')}`",
        f"- approved_for_paper_candidate: `{report.get('approved_for_paper_candidate')}`",
        f"- approved_for_live_real: `{report.get('approved_for_live_real')}`",
        f"- selected_model: `{best.get('model_path')}`",
        f"- selected_score: `{best.get('score')}`",
        f"- selected_calibrated_action_pct: `{metrics.get('validation_calibrated_action_pct')}`",
        f"- selected_expected_edge_proxy_bps: `{metrics.get('expected_edge_proxy_bps')}`",
        f"- promoted_to: `{report.get('promoted_to')}`",
        f"- recommendation: {report.get('recommendation')}",
        "",
        "## Guardrails",
        "",
    ]
    for k, v in (report.get("guardrails") or {}).items():
        lines.append(f"- {k}: `{v}`")
    lines.extend([
        "",
        "## Candidates",
        "",
        "| # | decision | score | policy | class_weight | threshold | calibrated_action_pct | raw_action_pct | action_precision | edge_proxy_bps | reasons | warnings |",
        "|---:|---|---:|---|---|---|---:|---:|---:|---:|---|---|",
    ])
    for idx, c in enumerate(report.get("candidates", []) or [], start=1):
        if not isinstance(c, Mapping):
            continue
        spec = c.get("candidate_spec") or {}
        policy = (spec.get("policy") or {}) if isinstance(spec, Mapping) else {}
        cm = c.get("metrics") or {}
        lines.append(
            "| {idx} | {decision} | {score} | {policy} | {cw} | {th} | {ca} | {ra} | {ap} | {edge} | `{reasons}` | `{warnings}` |".format(
                idx=idx,
                decision=c.get("decision"),
                score=c.get("score"),
                policy=policy.get("name") if isinstance(policy, Mapping) else None,
                cw=spec.get("class_weight_profile") if isinstance(spec, Mapping) else None,
                th=spec.get("threshold_profile") if isinstance(spec, Mapping) else None,
                ca=cm.get("validation_calibrated_action_pct") if isinstance(cm, Mapping) else None,
                ra=cm.get("validation_raw_action_pct") if isinstance(cm, Mapping) else None,
                ap=cm.get("action_precision") if isinstance(cm, Mapping) else None,
                edge=cm.get("expected_edge_proxy_bps") if isinstance(cm, Mapping) else None,
                reasons=c.get("reason_codes"),
                warnings=c.get("warnings"),
            )
        )
    lines.extend([
        "",
        "## Policy",
        "",
        "This tool may train candidate model files and write sidecars, but it never reloads models, mutates config, starts paper trading, or sends orders. A PASS only identifies a candidate for manual review and later controlled reload/probe checks; real live trading remains blocked.",
        "",
    ])
    return "\n".join(lines)


def promote_best(report: Mapping[str, Any], promote_to: str | Path) -> str | None:
    selection = report.get("selection") or {}
    best = selection.get("best_candidate") if isinstance(selection, Mapping) else None
    if not isinstance(best, Mapping) or best.get("decision") != "PASS" or best.get("ok") is not True:
        return None
    src = Path(str(best.get("model_path")))
    if not src.exists():
        return None
    dst = Path(promote_to)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    for suffix in [".schema.json", ".manifest.json"]:
        side_src = src.with_suffix(suffix)
        if side_src.exists():
            side_dst = dst.with_suffix(suffix)
            shutil.copy2(side_src, side_dst)
    return str(dst).replace("\\", "/")
