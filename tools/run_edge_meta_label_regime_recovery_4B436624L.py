"""4B.4.3.6.6.24L edge-aware meta-label / regime filter recovery.

Replays two-stage 24K candidates and evaluates regime/meta-label filters for
positive expected edge. This tool never reloads models, mutates config, starts
paper trading, or sends orders. Optional promotion only copies PASS candidate
model files when explicitly requested.
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

from tradebot.edge_meta_label_regime_recovery import (  # noqa: E402
    EDGE_META_LABEL_REGIME_CONTRACT_VERSION,
    build_edge_meta_label_recovery_report,
    evaluate_edge_meta_label_samples,
    evaluate_two_stage_candidate_with_regime_filters,
    select_two_stage_candidates_from_report,
)

PHASE = EDGE_META_LABEL_REGIME_CONTRACT_VERSION
REPORT_PREFIX = "4B436624L_edge_meta_label_regime_recovery"


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
        with urllib.request.urlopen(url, timeout=25) as response:  # noqa: S310 - public market-data URL controlled by operator
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
        report["promote_error"] = "PROMOTION_BLOCKED_NO_PASS_EDGE_META_LABEL_CANDIDATE"
        return report
    selection = report.get("selection") if isinstance(report.get("selection"), Mapping) else {}
    best = selection.get("best_candidate") if isinstance(selection.get("best_candidate"), Mapping) else {}
    meta = best.get("candidate_metadata") if isinstance(best.get("candidate_metadata"), Mapping) else {}
    action_path = best.get("action_model_path") or meta.get("action_model_path")
    side_path = best.get("side_model_path") or meta.get("side_model_path")
    if not action_path or not side_path:
        report["promotion_performed"] = False
        report["promote_error"] = "PROMOTION_BLOCKED_MODEL_PATH_MISSING"
        return report
    promote_prefix = Path(args.promote_prefix or f"models/{args.symbol.upper()}_edge_meta_4b436624L")
    action_to = Path(f"{promote_prefix}_action.ubj")
    side_to = Path(f"{promote_prefix}_side.ubj")
    _copy_model_family(Path(str(action_path)), action_to)
    _copy_model_family(Path(str(side_path)), side_to)
    report["promotion_performed"] = True
    report["promoted_action_model"] = action_to.as_posix()
    report["promoted_side_model"] = side_to.as_posix()
    report["recommendation"] = "Best PASS edge/meta-label candidate was copied by explicit --promote. Reload is still manual; paper/live remain blocked."
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
    best_sel = best.get("selection") if isinstance(best.get("selection"), Mapping) else {}
    best_filter = best_sel.get("best_filter") if isinstance(best_sel.get("best_filter"), Mapping) else {}
    best_metrics = best_filter.get("metrics") if isinstance(best_filter.get("metrics"), Mapping) else {}
    lines = [
        "# 4B.4.3.6.6.24L Edge-Aware Meta-Label / Regime Filter Recovery",
        "",
        f"- contract_version: `{report.get('contract_version')}`",
        f"- decision: **{report.get('decision')}**",
        f"- candidate_count: `{report.get('candidate_count')}`",
        f"- approved_for_training_candidate: `{report.get('approved_for_training_candidate')}`",
        f"- approved_for_paper_candidate: `{report.get('approved_for_paper_candidate')}`",
        f"- approved_for_live_real: `{report.get('approved_for_live_real')}`",
        f"- selected_candidate: `{report.get('selected_candidate')}`",
        f"- selected_filter: `{report.get('selected_filter')}`",
        f"- selected_score: `{_fmt(report.get('selected_score'))}`",
        f"- selected_mean_edge_bps: `{_fmt(report.get('selected_mean_edge_bps'))}`",
        f"- selected_good_action_pct: `{_fmt(report.get('selected_good_action_pct'))}`",
        f"- selected_subset_coverage_pct: `{_fmt(report.get('selected_subset_coverage_pct'))}`",
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
        "## Selected Filter Metrics",
        "",
        f"- reason_codes: `{best_filter.get('reason_codes') or []}`",
        f"- signal_count: `{best_metrics.get('signal_count')}`",
        f"- subset_coverage_pct: `{_fmt(best_metrics.get('subset_coverage_pct'))}`",
        f"- mean_net_edge_bps: `{_fmt(best_metrics.get('mean_net_edge_bps'))}`",
        f"- median_net_edge_bps: `{_fmt(best_metrics.get('median_net_edge_bps'))}`",
        f"- good_action_pct: `{_fmt(best_metrics.get('good_action_pct'))}`",
        f"- action_precision: `{_fmt(best_metrics.get('action_precision'))}`",
        f"- dominant_action_pct: `{_fmt(best_metrics.get('dominant_action_pct'))}`",
        f"- edge_lift_bps: `{_fmt(best_metrics.get('edge_lift_bps'))}`",
        "",
        "## Candidates / Filters",
        "",
        "| candidate | filter | decision | score | coverage_pct | mean_edge_bps | win_pct | precision | reasons | warnings |",
        "|---|---|---:|---:|---:|---:|---:|---:|---|---|",
    ])
    for candidate in report.get("candidates") or []:
        if not isinstance(candidate, Mapping):
            continue
        candidate_name = str(candidate.get("candidate_name"))
        for item in candidate.get("filters") or []:
            if not isinstance(item, Mapping):
                continue
            metrics = item.get("metrics") if isinstance(item.get("metrics"), Mapping) else {}
            lines.append(
                "| "
                + " | ".join(
                    [
                        candidate_name,
                        str(item.get("filter_name")),
                        str(item.get("decision")),
                        _fmt(item.get("score")),
                        _fmt(metrics.get("subset_coverage_pct")),
                        _fmt(metrics.get("mean_net_edge_bps")),
                        _fmt(metrics.get("good_action_pct")),
                        _fmt(metrics.get("action_precision")),
                        f"`{item.get('reason_codes') or []}`",
                        f"`{item.get('warnings') or []}`",
                    ]
                )
                + " |"
            )
    lines.extend([
        "",
        "## Policy",
        "",
        "This tool may replay two-stage candidate models and write reports, but it never reloads models, mutates config, starts paper trading, or sends orders. A PASS only identifies an edge-aware training candidate for manual review; real live trading remains blocked.",
    ])
    return "\n".join(lines) + "\n"


def load_candidate_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_from_candidate_json(payload: Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(payload.get("samples"), list):
        candidate = evaluate_edge_meta_label_samples(payload.get("samples") or [], candidate_name=str(payload.get("candidate_name", "candidate_json")), total_validation_samples=payload.get("total_validation_samples"))
        return build_edge_meta_label_recovery_report([candidate], source="candidate-json:samples")
    if isinstance(payload.get("candidates"), list) and all(isinstance(x, Mapping) and "filters" in x for x in payload.get("candidates") or []):
        return build_edge_meta_label_recovery_report(payload.get("candidates") or [], source="candidate-json:precomputed")
    raise ValueError("--candidate-json must contain either samples[] or candidates[] with filters[]")


def run_replay(args: argparse.Namespace) -> dict[str, Any]:
    if not args.input_json:
        raise ValueError("--input-json 24K report is required unless --candidate-json is used")
    payload = load_candidate_json(args.input_json)
    candidates = select_two_stage_candidates_from_report(payload, limit=int(args.max_candidates))
    if not candidates:
        raise ValueError("No two-stage candidates with action/side model paths found in --input-json")
    ohlcv, source = load_ohlcv(args)
    evaluated: list[dict[str, Any]] = []
    for candidate in candidates:
        evaluated.append(evaluate_two_stage_candidate_with_regime_filters(ohlcv, candidate))
    return build_edge_meta_label_recovery_report(evaluated, source=source)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="4B.4.3.6.6.24L edge-aware meta-label/regime filter recovery")
    parser.add_argument("--symbol", default="ETHUSDT")
    parser.add_argument("--interval", default="1m")
    parser.add_argument("--days", type=int, default=90)
    parser.add_argument("--base-url", default="https://api.binance.com")
    parser.add_argument("--input-json", help="24K two-stage recovery JSON report")
    parser.add_argument("--candidate-json", help="Synthetic/precomputed candidate sample JSON for offline gate checks")
    parser.add_argument("--input-csv", help="Optional local OHLCV CSV")
    parser.add_argument("--max-candidates", type=int, default=3)
    parser.add_argument("--out-dir", default="reports")
    parser.add_argument("--promote", action="store_true", help="Copy PASS candidate model files only; never reload")
    parser.add_argument("--promote-prefix", default="")
    parser.add_argument("--review-ok", action="store_true", help="Required operator acknowledgement")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.review_ok:
        print("ERROR: --review-ok is required. This recovery tool is observation-only and must be explicitly reviewed.", file=sys.stderr)
        return 2
    if args.candidate_json:
        report = build_from_candidate_json(load_candidate_json(args.candidate_json))
    else:
        report = run_replay(args)
    report = maybe_promote(dict(report), args)
    json_path, md_path = write_reports(report, out_dir=args.out_dir)
    print(f"{PHASE} edge-aware meta-label / regime recovery {report.get('decision')}")
    print(f" - candidates: {report.get('candidate_count')}")
    print(f" - approved_for_training_candidate: {report.get('approved_for_training_candidate')}")
    print(f" - approved_for_paper_candidate: {report.get('approved_for_paper_candidate')}")
    print(f" - approved_for_live_real: {report.get('approved_for_live_real')}")
    print(f" - selected_filter: {report.get('selected_filter')}")
    print(f" - selected_mean_edge_bps: {report.get('selected_mean_edge_bps')}")
    print(f" - selected_good_action_pct: {report.get('selected_good_action_pct')}")
    print(f" - recommendation: {report.get('recommendation')}")
    print(f"report_json: {json_path.as_posix()}")
    print(f"report_md: {md_path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
