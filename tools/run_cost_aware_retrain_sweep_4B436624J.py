"""4B.4.3.6.6.24J cost-aware retrain sweep + separation gate.

This tool trains candidate models from cost-aware label policies and gates them
with validation probability-separation metrics. It never reloads a model, mutates
config, starts paper trading, sends orders, or approves real-live trading.
Optional promotion only copies the best PASS candidate files when explicitly
requested.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradebot.cost_aware_label_policy_recovery import (  # noqa: E402
    CostAwareLabelPolicyCandidate,
    default_cost_aware_label_policy_candidates,
)
from tradebot.cost_aware_retrain_sweep import (  # noqa: E402
    COST_AWARE_RETRAIN_SWEEP_CONTRACT_VERSION,
    CostAwareRetrainGateLimits,
    build_cost_aware_candidate_specs,
    build_cost_aware_retrain_sweep_report,
    evaluate_sweep_candidate,
    select_cost_aware_policies_from_report,
    train_cost_aware_candidate,
)

PHASE = COST_AWARE_RETRAIN_SWEEP_CONTRACT_VERSION
REPORT_PREFIX = "4B436624J_cost_aware_retrain_sweep"


def utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%d_%H%M%S")


def fetch_klines(symbol: str, interval: str, days: int, *, base_url: str = "https://api.binance.com") -> pd.DataFrame:
    candles_per_call = 1000
    total_candles = max(1, int(days)) * 24 * 60
    end_time = int(time.time() * 1000)
    all_klines: list[list[Any]] = []
    base = str(base_url).rstrip("/")
    while len(all_klines) < total_candles:
        query = urllib.parse.urlencode({"symbol": symbol.upper(), "interval": interval, "limit": candles_per_call, "endTime": end_time})
        url = f"{base}/api/v3/klines?{query}"
        with urllib.request.urlopen(url, timeout=25) as response:  # noqa: S310 - operator-supplied public API URL
            data = json.loads(response.read().decode("utf-8"))
        if not data:
            break
        all_klines = list(data) + all_klines
        end_time = int(data[0][0]) - 1
        time.sleep(0.15)
    if not all_klines:
        raise RuntimeError("No klines returned")
    rows = all_klines[-total_candles:]
    df = pd.DataFrame(rows, columns=["open_time", "open", "high", "low", "close", "volume", "close_time", "quote_volume", "trades", "taker_base", "taker_quote", "ignore"])
    return df[["open_time", "close_time", "open", "high", "low", "close", "volume", "quote_volume"]].astype(float)


def load_ohlcv(args: argparse.Namespace) -> tuple[pd.DataFrame, str]:
    if args.input_csv:
        return pd.read_csv(args.input_csv), f"csv:{args.input_csv}"
    return fetch_klines(args.symbol, args.interval, int(args.days), base_url=args.base_url), f"binance:{args.symbol}:{args.interval}:{args.days}d"


def _policy_from_name(name: str) -> CostAwareLabelPolicyCandidate | None:
    for policy in default_cost_aware_label_policy_candidates():
        if policy.name == name:
            return policy
    return None


def load_policy_candidates(args: argparse.Namespace) -> list[CostAwareLabelPolicyCandidate]:
    if args.policies:
        policies: list[CostAwareLabelPolicyCandidate] = []
        for item in str(args.policies).split(","):
            policy = _policy_from_name(item.strip())
            if policy is not None:
                policies.append(policy)
        if not policies:
            raise ValueError("No known policies matched --policies")
        return policies
    if args.policy_json or args.input_json:
        path = Path(args.policy_json or args.input_json)
        payload = json.loads(path.read_text(encoding="utf-8"))
        return select_cost_aware_policies_from_report(payload, limit=int(args.policy_limit))
    # Default to the strongest 24I cost-aware policy and two close alternatives.
    preferred = {"h30_cost16_edge30_atr3_0", "h20_cost16_edge25_atr2_5", "h15_cost12_edge20_atr2_0"}
    return [policy for policy in default_cost_aware_label_policy_candidates() if policy.name in preferred]


def _copy_sidecars(src_model: Path, dst_model: Path) -> None:
    src_stem = src_model.with_suffix("")
    dst_stem = dst_model.with_suffix("")
    for suffix in (".ubj", ".schema.json", ".manifest.json"):
        src = Path(f"{src_stem}{suffix}")
        dst = Path(f"{dst_stem}{suffix}")
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)


def maybe_promote(report: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    if not bool(args.promote):
        return report
    if report.get("decision") != "PASS":
        report["promotion_performed"] = False
        report["promote_error"] = "PROMOTION_BLOCKED_NO_PASS_CANDIDATE"
        return report
    selection = report.get("selection") if isinstance(report.get("selection"), Mapping) else {}
    best = selection.get("best_candidate") if isinstance(selection.get("best_candidate"), Mapping) else {}
    model_path = best.get("model_path") or best.get("output")
    if not model_path:
        report["promotion_performed"] = False
        report["promote_error"] = "PROMOTION_BLOCKED_MODEL_PATH_MISSING"
        return report
    promote_to = Path(args.promote_to or f"models/{args.symbol.upper()}_model_4b436624J.ubj")
    _copy_sidecars(Path(model_path), promote_to)
    report["promotion_performed"] = True
    report["promoted_to"] = promote_to.as_posix()
    report["recommendation"] = "Best PASS candidate was copied by explicit --promote. Reload is still manual; paper/live remain blocked."
    return report


def write_reports(report: Mapping[str, Any], *, out_dir: str | Path) -> tuple[Path, Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    stamp = utc_stamp()
    json_path = out / f"{REPORT_PREFIX}_{stamp}.json"
    md_path = out / f"{REPORT_PREFIX}_{stamp}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    return json_path, md_path


def _fmt(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.6f}".rstrip("0").rstrip(".")
    return str(value)


def render_markdown(report: Mapping[str, Any]) -> str:
    selected = report.get("selection") if isinstance(report.get("selection"), Mapping) else {}
    best = selected.get("best_candidate") if isinstance(selected.get("best_candidate"), Mapping) else {}
    best_metrics = ((best.get("candidate_gate") or {}).get("metrics") if isinstance(best.get("candidate_gate"), Mapping) else {}) or {}
    lines = [
        "# 4B.4.3.6.6.24J Cost-Aware Retrain Sweep + Separation Gate",
        "",
        f"- contract_version: `{report.get('contract_version')}`",
        f"- decision: **{report.get('decision')}**",
        f"- candidate_count: `{report.get('candidate_count')}`",
        f"- approved_for_training_candidate: `{report.get('approved_for_training_candidate')}`",
        f"- approved_for_paper_candidate: `{report.get('approved_for_paper_candidate')}`",
        f"- approved_for_live_real: `{report.get('approved_for_live_real')}`",
        f"- selected_model: `{best.get('model_path')}`",
        f"- selected_score: `{best.get('score')}`",
        f"- selected_calibrated_action_pct: `{_fmt(best_metrics.get('validation_calibrated_action_pct'))}`",
        f"- selected_buy_sell_margin_mean: `{_fmt(best_metrics.get('buy_sell_margin_mean'))}`",
        f"- selected_low_margin_rejection_pct: `{_fmt(best_metrics.get('low_margin_rejection_pct'))}`",
        f"- promoted_to: `{report.get('promoted_to')}`",
        f"- recommendation: {report.get('recommendation')}",
        "",
        "## Guardrails",
        "",
    ]
    guard = report.get("guardrails") if isinstance(report.get("guardrails"), Mapping) else {}
    for key in ("observation_only", "no_post_actions", "post_requests_allowed", "config_mutation_performed", "order_actions_performed", "reload_performed", "live_real_allowed", "promotion_requires_explicit_flag"):
        lines.append(f"- {key}: `{guard.get(key)}`")
    lines.extend([
        "",
        "## Candidates",
        "",
        "| # | decision | score | policy | class_weight | threshold | calibrated_action_pct | raw_action_pct | buy_sell_margin_mean | low_margin_pct | reasons | warnings |",
        "|---:|---|---:|---|---|---|---:|---:|---:|---:|---|---|",
    ])
    for idx, item in enumerate(report.get("candidates") or [], start=1):
        if not isinstance(item, Mapping):
            continue
        gate = item.get("candidate_gate") if isinstance(item.get("candidate_gate"), Mapping) else {}
        metrics = gate.get("metrics") if isinstance(gate.get("metrics"), Mapping) else {}
        spec = item.get("candidate_spec") if isinstance(item.get("candidate_spec"), Mapping) else {}
        label_policy = spec.get("label_policy") if isinstance(spec.get("label_policy"), Mapping) else item.get("label_policy", {})
        lines.append(
            "| {idx} | {decision} | {score} | {policy} | {weight} | {threshold} | {cal_action} | {raw_action} | {margin} | {low_margin} | `{reasons}` | `{warnings}` |".format(
                idx=idx,
                decision=item.get("decision"),
                score=_fmt(item.get("score")),
                policy=(label_policy or {}).get("name"),
                weight=spec.get("class_weight_profile") or item.get("class_weight_profile"),
                threshold=spec.get("threshold_profile") or item.get("threshold_profile"),
                cal_action=_fmt(metrics.get("validation_calibrated_action_pct")),
                raw_action=_fmt(metrics.get("validation_raw_action_pct")),
                margin=_fmt(metrics.get("buy_sell_margin_mean")),
                low_margin=_fmt(metrics.get("low_margin_rejection_pct")),
                reasons=item.get("reason_codes") or [],
                warnings=item.get("warnings") or [],
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="4B436624J cost-aware retrain sweep + separation gate")
    parser.add_argument("--symbol", default="ETHUSDT")
    parser.add_argument("--interval", default="1m")
    parser.add_argument("--days", type=int, default=90)
    parser.add_argument("--base-url", default="https://api.binance.com")
    parser.add_argument("--input-csv")
    parser.add_argument("--input-json", help="24I report JSON used to select PASS label policies")
    parser.add_argument("--candidate-json", help="precomputed candidate training result JSON for offline gate/report tests")
    parser.add_argument("--policy-json", help="alias for --input-json")
    parser.add_argument("--policies", help="comma-separated cost-aware label policy names")
    parser.add_argument("--policy-limit", type=int, default=3)
    parser.add_argument("--class-weight-profiles", default="balanced,buy_sell_boost_light")
    parser.add_argument("--threshold-profiles", default="balanced,action_seek_light")
    parser.add_argument("--max-candidates", type=int, default=6)
    parser.add_argument("--model-dir", default="models/4B436624J_candidates")
    parser.add_argument("--out-dir", default="reports")
    parser.add_argument("--min-clean-samples", type=int)
    parser.add_argument("--min-buy-sell-margin-mean", type=float)
    parser.add_argument("--min-buy-sell-margin-median", type=float)
    parser.add_argument("--max-low-margin-rejection-pct", type=float)
    parser.add_argument("--min-calibrated-action-pct", type=float)
    parser.add_argument("--max-calibrated-action-pct", type=float)
    parser.add_argument("--promote", action="store_true", help="explicitly copy best PASS candidate files; does not reload")
    parser.add_argument("--promote-to")
    parser.add_argument("--review-ok", action="store_true", help="required acknowledgement that this is not a live/paper trading approval")
    return parser


def build_limits(args: argparse.Namespace) -> CostAwareRetrainGateLimits:
    values: dict[str, Any] = {}
    if args.min_clean_samples is not None:
        values["min_clean_samples"] = int(args.min_clean_samples)
    if args.min_buy_sell_margin_mean is not None:
        values["min_buy_sell_margin_mean"] = float(args.min_buy_sell_margin_mean)
    if args.min_buy_sell_margin_median is not None:
        values["min_buy_sell_margin_median"] = float(args.min_buy_sell_margin_median)
    if args.max_low_margin_rejection_pct is not None:
        values["max_low_margin_rejection_pct"] = float(args.max_low_margin_rejection_pct)
    if args.min_calibrated_action_pct is not None:
        values["min_calibrated_action_pct"] = float(args.min_calibrated_action_pct)
    if args.max_calibrated_action_pct is not None:
        values["max_calibrated_action_pct"] = float(args.max_calibrated_action_pct)
    return CostAwareRetrainGateLimits(**values)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.review_ok:
        print("ERROR: --review-ok is required; 24J trains candidates only and does not approve paper/live trading.", file=sys.stderr)
        return 2
    try:
        limits = build_limits(args)
        if args.candidate_json:
            payload = json.loads(Path(args.candidate_json).read_text(encoding="utf-8"))
            raw_candidates = payload.get("candidates") if isinstance(payload, Mapping) else None
            if raw_candidates is None:
                raw_candidates = payload if isinstance(payload, list) else [payload]
            candidates = [evaluate_sweep_candidate(item, limits=limits) for item in raw_candidates if isinstance(item, Mapping)]
            report = build_cost_aware_retrain_sweep_report(candidates, source=f"candidate-json:{args.candidate_json}")
        else:
            df, source = load_ohlcv(args)
            policies = load_policy_candidates(args)
            class_weights = [item.strip() for item in str(args.class_weight_profiles).split(",") if item.strip()]
            thresholds = [item.strip() for item in str(args.threshold_profiles).split(",") if item.strip()]
            specs = build_cost_aware_candidate_specs(policies, class_weight_profiles=class_weights, threshold_profiles=thresholds, max_candidates=args.max_candidates)
            candidates: list[dict[str, Any]] = []
            for spec in specs:
                try:
                    result = train_cost_aware_candidate(
                        df,
                        spec,
                        symbol=args.symbol,
                        interval=args.interval,
                        days=int(args.days),
                        model_dir=args.model_dir,
                    )
                    candidates.append(evaluate_sweep_candidate(result, limits=limits))
                except Exception as exc:
                    candidates.append({
                        "contract_version": PHASE,
                        "decision": "BLOCK",
                        "ok": False,
                        "candidate_spec": spec.to_dict(),
                        "model_path": None,
                        "score": -999.0,
                        "reason_codes": ["CANDIDATE_TRAINING_FAILED"],
                        "warnings": [],
                        "error": str(exc),
                        "approved_for_paper_candidate": False,
                        "approved_for_live_real": False,
                        "reload_allowed": False,
                    })
            report = build_cost_aware_retrain_sweep_report(candidates, source=source)
        report = maybe_promote(report, args)
    except Exception as exc:
        report = {
            "contract_version": PHASE,
            "phase": PHASE,
            "report_type": "cost_aware_retrain_sweep_separation_gate",
            "decision": "BLOCK",
            "ok": False,
            "candidate_count": 0,
            "approved_for_training_candidate": False,
            "approved_for_paper_candidate": False,
            "approved_for_live_real": False,
            "live_real_allowed": False,
            "reload_performed": False,
            "config_mutation_performed": False,
            "order_actions_performed": False,
            "no_post_actions": True,
            "observation_only": True,
            "reason_codes": ["SWEEP_TOOL_FAILED"],
            "error": str(exc),
            "recommendation": "Cost-aware retrain sweep failed; do not promote/reload.",
            "selection": {"decision": "BLOCK", "approved": False, "best_candidate": None},
            "candidates": [],
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
    json_path, md_path = write_reports(report, out_dir=args.out_dir)
    decision = report.get("decision")
    print(f"4B.4.3.6.6.24J cost-aware retrain sweep {decision}")
    print(f" - candidates: {report.get('candidate_count')}")
    print(f" - approved_for_training_candidate: {report.get('approved_for_training_candidate')}")
    print(f" - approved_for_paper_candidate: {report.get('approved_for_paper_candidate')}")
    print(f" - approved_for_live_real: {report.get('approved_for_live_real')}")
    selection = report.get("selection") if isinstance(report.get("selection"), Mapping) else {}
    best = selection.get("best_candidate") if isinstance(selection.get("best_candidate"), Mapping) else {}
    print(f" - selected_model: {best.get('model_path')}")
    print(f" - selected_score: {best.get('score')}")
    print(f" - recommendation: {report.get('recommendation')}")
    print(f"report_json: {json_path.as_posix()}")
    print(f"report_md: {md_path.as_posix()}")
    return 0 if report.get("decision") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
