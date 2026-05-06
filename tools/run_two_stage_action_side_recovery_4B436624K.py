"""4B.4.3.6.6.24K two-stage action/side model recovery.

Trains candidate ACTION-vs-HOLD and BUY-vs-SELL model pairs, then gates them.
This tool never reloads models, mutates config, starts paper trading, or sends orders.
Optional promotion only copies PASS candidate files when explicitly requested.
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

from tradebot.two_stage_action_side_recovery import (  # noqa: E402
    TWO_STAGE_ACTION_SIDE_CONTRACT_VERSION,
    build_two_stage_candidate_specs,
    build_two_stage_recovery_report,
    evaluate_two_stage_training_result,
    select_policies_from_cost_aware_report,
    train_two_stage_candidate,
)
from tradebot.cost_aware_label_policy_recovery import default_cost_aware_label_policy_candidates  # noqa: E402

PHASE = TWO_STAGE_ACTION_SIDE_CONTRACT_VERSION
REPORT_PREFIX = "4B436624K_two_stage_action_side_recovery"


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
        with urllib.request.urlopen(url, timeout=25) as response:  # noqa: S310 - operator-supplied public market-data URL
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


def load_policy_candidates(args: argparse.Namespace):
    if args.policies:
        wanted = {item.strip() for item in str(args.policies).split(",") if item.strip()}
        policies = [p for p in default_cost_aware_label_policy_candidates() if p.name in wanted]
        if not policies:
            raise ValueError("No known policies matched --policies")
        return policies
    if args.input_json:
        payload = json.loads(Path(args.input_json).read_text(encoding="utf-8"))
        return select_policies_from_cost_aware_report(payload, limit=int(args.policy_limit))
    preferred = {"h30_cost16_edge30_atr3_0", "h20_cost16_edge25_atr2_5", "h15_cost12_edge20_atr2_0"}
    return [p for p in default_cost_aware_label_policy_candidates() if p.name in preferred]


def _copy_model_family(src_path: Path, dst_path: Path) -> None:
    src_stem = src_path.with_suffix("")
    dst_stem = dst_path.with_suffix("")
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
        report["promote_error"] = "PROMOTION_BLOCKED_NO_PASS_TWO_STAGE_CANDIDATE"
        return report
    selection = report.get("selection") if isinstance(report.get("selection"), Mapping) else {}
    best = selection.get("best_candidate") if isinstance(selection.get("best_candidate"), Mapping) else {}
    action_path = best.get("action_model_path")
    side_path = best.get("side_model_path")
    if not action_path or not side_path:
        report["promotion_performed"] = False
        report["promote_error"] = "PROMOTION_BLOCKED_MODEL_PATH_MISSING"
        return report
    promote_prefix = Path(args.promote_prefix or f"models/{args.symbol.upper()}_two_stage_4b436624K")
    action_to = Path(f"{promote_prefix}_action.ubj")
    side_to = Path(f"{promote_prefix}_side.ubj")
    _copy_model_family(Path(str(action_path)), action_to)
    _copy_model_family(Path(str(side_path)), side_to)
    report["promotion_performed"] = True
    report["promoted_action_model"] = action_to.as_posix()
    report["promoted_side_model"] = side_to.as_posix()
    report["recommendation"] = "Best PASS two-stage candidate was copied by explicit --promote. Reload is still manual; paper/live remain blocked."
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
    selection = report.get("selection") if isinstance(report.get("selection"), Mapping) else {}
    best = selection.get("best_candidate") if isinstance(selection.get("best_candidate"), Mapping) else {}
    best_gate = best.get("candidate_gate") if isinstance(best.get("candidate_gate"), Mapping) else {}
    best_metrics = best_gate.get("metrics") if isinstance(best_gate.get("metrics"), Mapping) else {}
    lines = [
        "# 4B.4.3.6.6.24K Two-Stage Action/Side Model Recovery",
        "",
        f"- contract_version: `{report.get('contract_version')}`",
        f"- decision: **{report.get('decision')}**",
        f"- candidate_count: `{report.get('candidate_count')}`",
        f"- approved_for_training_candidate: `{report.get('approved_for_training_candidate')}`",
        f"- approved_for_paper_candidate: `{report.get('approved_for_paper_candidate')}`",
        f"- approved_for_live_real: `{report.get('approved_for_live_real')}`",
        f"- selected_action_model: `{report.get('selected_action_model')}`",
        f"- selected_side_model: `{report.get('selected_side_model')}`",
        f"- selected_score: `{report.get('selected_score')}`",
        f"- selected_staged_action_pct: `{_fmt(report.get('selected_staged_action_pct'))}`",
        f"- selected_action_precision: `{_fmt(report.get('selected_action_precision'))}`",
        f"- selected_side_accuracy: `{_fmt(report.get('selected_side_accuracy'))}`",
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
        "## Selected Candidate Metrics",
        "",
        f"- reason_codes: `{best.get('reason_codes') or []}`",
        f"- validation_staged_action_pct: `{_fmt(best_metrics.get('validation_staged_action_pct'))}`",
        f"- validation_action_precision: `{_fmt(best_metrics.get('validation_action_precision'))}`",
        f"- validation_action_recall: `{_fmt(best_metrics.get('validation_action_recall'))}`",
        f"- validation_action_f1: `{_fmt(best_metrics.get('validation_action_f1'))}`",
        f"- validation_side_accuracy: `{_fmt(best_metrics.get('validation_side_accuracy'))}`",
        f"- action_probability_gap_mean: `{_fmt(best_metrics.get('action_probability_gap_mean'))}`",
        f"- expected_edge_proxy_bps: `{_fmt(best_metrics.get('expected_edge_proxy_bps'))}`",
        "",
        "## Candidates",
        "",
        "| # | decision | score | policy | action_profile | side_profile | staged_action_pct | action_precision | action_recall | side_accuracy | edge_proxy_bps | reasons | warnings |",
        "|---:|---|---:|---|---|---|---:|---:|---:|---:|---:|---|---|",
    ])
    for idx, item in enumerate(report.get("candidates") or [], start=1):
        if not isinstance(item, Mapping):
            continue
        gate = item.get("candidate_gate") if isinstance(item.get("candidate_gate"), Mapping) else {}
        metrics = gate.get("metrics") if isinstance(gate.get("metrics"), Mapping) else {}
        spec = item.get("candidate_spec") if isinstance(item.get("candidate_spec"), Mapping) else {}
        label_policy = spec.get("label_policy") if isinstance(spec.get("label_policy"), Mapping) else {}
        lines.append(
            "| {idx} | {decision} | {score} | {policy} | {action_profile} | {side_profile} | {action_pct} | {precision} | {recall} | {side_acc} | {edge} | `{reasons}` | `{warnings}` |".format(
                idx=idx,
                decision=item.get("decision"),
                score=_fmt(item.get("score")),
                policy=label_policy.get("name"),
                action_profile=spec.get("action_profile"),
                side_profile=spec.get("side_profile"),
                action_pct=_fmt(metrics.get("validation_staged_action_pct")),
                precision=_fmt(metrics.get("validation_action_precision")),
                recall=_fmt(metrics.get("validation_action_recall")),
                side_acc=_fmt(metrics.get("validation_side_accuracy")),
                edge=_fmt(metrics.get("expected_edge_proxy_bps")),
                reasons=item.get("reason_codes") or [],
                warnings=item.get("warnings") or [],
            )
        )
    lines.extend([
        "",
        "## Policy",
        "",
        "This tool may train two-stage candidate model files and write sidecars, but it never reloads models, mutates config, starts paper trading, or sends orders. A PASS only identifies a candidate for manual review and later controlled reload/probe checks; real live trading remains blocked.",
        "",
    ])
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="4B.4.3.6.6.24K two-stage action/side recovery")
    parser.add_argument("--symbol", default="ETHUSDT")
    parser.add_argument("--interval", default="1m")
    parser.add_argument("--days", type=int, default=90)
    parser.add_argument("--base-url", default="https://api.binance.com")
    parser.add_argument("--input-csv")
    parser.add_argument("--input-json", help="24I cost-aware label policy report JSON")
    parser.add_argument("--candidate-json", help="Precomputed 24K candidate list/report JSON for report-only evaluation")
    parser.add_argument("--policies", help="Comma-separated cost-aware policy names")
    parser.add_argument("--policy-limit", type=int, default=3)
    parser.add_argument("--action-profiles", default="balanced,action_precision_guarded,action_recall_light")
    parser.add_argument("--side-profiles", default="balanced,side_balance_guarded")
    parser.add_argument("--action-threshold-profiles", default="balanced,recall_light")
    parser.add_argument("--side-margin-profiles", default="guarded,balanced")
    parser.add_argument("--max-candidates", type=int, default=6)
    parser.add_argument("--out-dir", default="reports")
    parser.add_argument("--model-dir", default="models/4B436624K_candidates")
    parser.add_argument("--promote", action="store_true")
    parser.add_argument("--promote-prefix")
    parser.add_argument("--review-ok", action="store_true")
    return parser.parse_args()


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in str(value or "").split(",") if item.strip()]


def main() -> int:
    args = parse_args()
    if not args.review_ok:
        raise SystemExit("Refusing to run without --review-ok guardrail acknowledgement")
    if args.candidate_json:
        payload = json.loads(Path(args.candidate_json).read_text(encoding="utf-8"))
        candidates = payload.get("candidates") if isinstance(payload, Mapping) else payload
        if not isinstance(candidates, list):
            raise SystemExit("--candidate-json must contain a candidate list or report with candidates")
        report = build_two_stage_recovery_report(candidates, source=f"candidate-json:{args.candidate_json}")
    else:
        ohlcv, source = load_ohlcv(args)
        policies = load_policy_candidates(args)
        specs = build_two_stage_candidate_specs(
            policies,
            action_profiles=_split_csv(args.action_profiles),
            side_profiles=_split_csv(args.side_profiles),
            action_threshold_profiles=_split_csv(args.action_threshold_profiles),
            side_margin_profiles=_split_csv(args.side_margin_profiles),
            max_candidates=int(args.max_candidates),
        )
        candidates = []
        for spec in specs:
            candidates.append(
                train_two_stage_candidate(
                    ohlcv,
                    spec,
                    symbol=args.symbol,
                    interval=args.interval,
                    days=int(args.days),
                    output_dir=args.model_dir,
                )
            )
        report = build_two_stage_recovery_report(candidates, source=source)
    report = maybe_promote(report, args)
    json_path, md_path = write_reports(report, out_dir=args.out_dir)
    print(f"{PHASE} two-stage action/side recovery {report.get('decision')}")
    print(f" - candidates: {report.get('candidate_count')}")
    print(f" - approved_for_training_candidate: {report.get('approved_for_training_candidate')}")
    print(f" - approved_for_paper_candidate: {report.get('approved_for_paper_candidate')}")
    print(f" - approved_for_live_real: {report.get('approved_for_live_real')}")
    print(f" - selected_action_model: {report.get('selected_action_model')}")
    print(f" - selected_side_model: {report.get('selected_side_model')}")
    print(f" - selected_score: {report.get('selected_score')}")
    print(f" - recommendation: {report.get('recommendation')}")
    print(f"report_json: {json_path.as_posix()}")
    print(f"report_md: {md_path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
