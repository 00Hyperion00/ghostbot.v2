from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradebot.model_quality_gate import ModelQualityGateConfig
from tradebot.training.retrain_recovery import (
    RETRAIN_RECOVERY_CONTRACT_VERSION,
    DatasetQualityConfig,
    build_candidate_matrix,
    evaluate_retrain_candidate,
    select_best_retrain_candidate,
)

REPORT_PREFIX = "4B436624D_model_retrain_recovery"


def _parse_csv_ints(value: str) -> list[int]:
    return [int(part.strip()) for part in str(value or "").split(",") if part.strip()]


def _parse_csv_strings(value: str) -> list[str]:
    return [str(part.strip()) for part in str(value or "").split(",") if part.strip()]


def _ts() -> str:
    return time.strftime("%Y%m%d_%H%M%S")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def _write_md(path: Path, payload: dict[str, Any]) -> None:
    selection = payload.get("selection") or {}
    candidates = payload.get("candidates") or []
    lines = [
        f"# 4B.4.3.6.6.24D Model Retrain Recovery Report",
        "",
        f"- contract_version: `{payload.get('contract_version')}`",
        f"- decision: **{payload.get('decision')}**",
        f"- approved: `{payload.get('approved')}`",
        f"- recommended_action: `{payload.get('recommended_action')}`",
        f"- candidate_count: `{len(candidates)}`",
        "",
        "## Selection",
        "",
        f"- decision: `{selection.get('decision')}`",
        f"- approved: `{selection.get('approved')}`",
        f"- reason_codes: `{selection.get('reason_codes')}`",
        "",
        "## Candidates",
        "",
        "| # | decision | score | days | class_weight | threshold | reload_allowed | reasons |",
        "|---:|---|---:|---:|---|---|---|---|",
    ]
    for idx, item in enumerate(candidates, start=1):
        spec = item.get("candidate_spec") or {}
        lines.append(
            "| {idx} | {decision} | {score:.4f} | {days} | {class_weight} | {threshold} | {reload_allowed} | {reasons} |".format(
                idx=idx,
                decision=item.get("decision"),
                score=float(item.get("score") or 0.0),
                days=spec.get("days"),
                class_weight=spec.get("class_weight_profile"),
                threshold=spec.get("threshold_profile"),
                reload_allowed=item.get("reload_allowed"),
                reasons=", ".join(str(x) for x in item.get("reason_codes") or []),
            )
        )
    lines.extend([
        "",
        "## Guardrail",
        "",
        "This report never reloads a candidate model by itself. Promotion copies files only when `--promote` is explicitly provided and the best candidate is PASS.",
        "Real live trading remains blocked by policy until later phases produce paper/live-demo evidence.",
    ])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _sidecar_candidates(model_path: str | None) -> list[Path]:
    if not model_path:
        return []
    path = Path(model_path)
    stem = path.with_suffix("")
    return [path, Path(f"{stem}.schema.json"), Path(f"{stem}.manifest.json")]


def _promote_candidate(candidate: dict[str, Any], promote_to: str) -> dict[str, Any]:
    model_path = candidate.get("model_path")
    if not model_path:
        return {"ok": False, "reason": "MODEL_PATH_MISSING"}
    source_paths = _sidecar_candidates(str(model_path))
    target_model = Path(promote_to)
    target_stem = target_model.with_suffix("")
    target_paths = [target_model, Path(f"{target_stem}.schema.json"), Path(f"{target_stem}.manifest.json")]
    copied: list[dict[str, str]] = []
    for src, dst in zip(source_paths, target_paths, strict=False):
        if not src.exists():
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied.append({"from": src.as_posix(), "to": dst.as_posix()})
    return {"ok": bool(copied), "copied": copied, "promote_to": target_model.as_posix()}


def _build_configs(args: argparse.Namespace) -> tuple[ModelQualityGateConfig, DatasetQualityConfig]:
    gate_config = ModelQualityGateConfig(
        min_clean_samples=int(args.min_clean_samples),
        min_action_coverage=float(args.min_action_coverage),
        max_hold_rate=float(args.max_hold_rate),
        max_low_margin_reject_rate=float(args.max_low_margin_reject_rate),
        min_calibrated_accuracy=float(args.min_calibrated_accuracy),
        min_target_action_rate=float(args.min_target_action_rate),
        max_target_hold_rate=float(args.max_target_hold_rate),
        min_present_target_classes=int(args.min_present_target_classes),
        block_synthetic_class_padding=True,
    )
    dataset_config = DatasetQualityConfig(
        min_clean_samples=int(args.min_clean_samples),
        min_target_action_rate=float(args.min_target_action_rate),
        max_target_hold_rate=float(args.max_target_hold_rate),
        min_present_target_classes=int(args.min_present_target_classes),
        block_synthetic_class_padding=True,
    )
    return gate_config, dataset_config


def run(args: argparse.Namespace) -> dict[str, Any]:
    days = _parse_csv_ints(args.days)
    class_profiles = _parse_csv_strings(args.class_weight_profiles)
    threshold_profiles = _parse_csv_strings(args.threshold_profiles)
    gate_config, dataset_config = _build_configs(args)
    specs = build_candidate_matrix(
        days=days,
        class_weight_profiles=class_profiles,
        threshold_profiles=threshold_profiles,
        feature_lag=args.feature_lag,
        max_candidates=args.max_candidates,
    )

    candidates: list[dict[str, Any]] = []
    out_dir = Path(args.out_dir)
    for spec in specs:
        model_out = out_dir / f"{args.symbol.upper()}_{spec.slug()}.ubj"
        if args.dry_run:
            candidates.append({
                "contract_version": RETRAIN_RECOVERY_CONTRACT_VERSION,
                "report_type": "retrain_candidate_quality",
                "decision": "DRY_RUN",
                "ok": True,
                "reload_allowed": False,
                "candidate_spec": spec.to_dict(),
                "model_path": model_out.as_posix(),
                "reason_codes": ["DRY_RUN_NO_TRAINING_EXECUTED"],
                "warnings": [],
                "score": 0.0,
            })
            continue
        try:
            from tradebot.training.train_xgb import train as train_xgb_model

            result = train_xgb_model(
                args.symbol.upper(),
                args.interval,
                int(spec.days),
                model_out.as_posix(),
                base_url=args.base_url,
                class_weight_profile=spec.class_weight_profile,
                threshold_profile=spec.threshold_profile,
                feature_lag=spec.feature_lag,
            )
            evaluated = evaluate_retrain_candidate(
                result,
                gate_config=gate_config,
                dataset_config=dataset_config,
                candidate_spec=spec.to_dict(),
            )
            evaluated["training"] = result
            candidates.append(evaluated)
        except Exception as exc:
            candidates.append({
                "contract_version": RETRAIN_RECOVERY_CONTRACT_VERSION,
                "report_type": "retrain_candidate_quality",
                "decision": "BLOCK",
                "ok": False,
                "reload_allowed": False,
                "candidate_spec": spec.to_dict(),
                "model_path": model_out.as_posix(),
                "reason_codes": ["TRAINING_EXECUTION_FAILED"],
                "warnings": [],
                "error": str(exc),
                "score": -999.0,
            })
            if args.stop_on_error:
                break

    selection = select_best_retrain_candidate(candidates)
    promoted: dict[str, Any] | None = None
    if args.promote and bool(selection.get("approved")) and isinstance(selection.get("best_candidate"), dict):
        promoted = _promote_candidate(selection["best_candidate"], args.promote_to)

    decision = "PASS" if bool(selection.get("approved")) else ("PLAN" if args.dry_run else "BLOCK")
    payload = {
        "contract_version": RETRAIN_RECOVERY_CONTRACT_VERSION,
        "report_type": "model_retrain_recovery",
        "decision": decision,
        "approved": bool(selection.get("approved")),
        "dry_run": bool(args.dry_run),
        "recommended_action": "PROMOTE_APPROVED_CANDIDATE" if selection.get("approved") else ("RUN_WITHOUT_DRY_RUN" if args.dry_run else "KEEP_ACTIVE_MODEL_AND_REVIEW_DATASET"),
        "symbol": args.symbol.upper(),
        "interval": args.interval,
        "base_url": args.base_url,
        "candidate_count": len(candidates),
        "selection": selection,
        "candidates": candidates,
        "promoted": promoted,
        "guardrails": {
            "reload_performed": False,
            "promotion_requires_explicit_flag": True,
            "live_real_allowed": False,
        },
    }

    stamp = _ts()
    reports_dir = Path(args.reports_dir)
    json_path = reports_dir / f"{REPORT_PREFIX}_{stamp}.json"
    md_path = reports_dir / f"{REPORT_PREFIX}_{stamp}.md"
    _write_json(json_path, payload)
    _write_md(md_path, payload)
    payload["report_json"] = json_path.as_posix()
    payload["report_md"] = md_path.as_posix()
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="4B.4.3.6.6.24D model retrain recovery candidate sweep")
    parser.add_argument("--symbol", default="ETHUSDT")
    parser.add_argument("--interval", default="1m")
    parser.add_argument("--base-url", default="https://api.binance.com")
    parser.add_argument("--days", default="30,60,90")
    parser.add_argument("--class-weight-profiles", default="balanced,buy_sell_boost_light,buy_sell_boost_medium")
    parser.add_argument("--threshold-profiles", default="balanced,action_seek_light")
    parser.add_argument("--feature-lag", type=int, default=1)
    parser.add_argument("--max-candidates", type=int, default=6)
    parser.add_argument("--out-dir", default="models/candidates")
    parser.add_argument("--reports-dir", default="reports")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--stop-on-error", action="store_true")
    parser.add_argument("--promote", action="store_true")
    parser.add_argument("--promote-to", default="models/ETHUSDT_model_4b436624D.ubj")
    parser.add_argument("--min-clean-samples", type=int, default=1_000)
    parser.add_argument("--min-action-coverage", type=float, default=0.03)
    parser.add_argument("--max-hold-rate", type=float, default=0.97)
    parser.add_argument("--max-low-margin-reject-rate", type=float, default=0.75)
    parser.add_argument("--min-calibrated-accuracy", type=float, default=0.30)
    parser.add_argument("--min-target-action-rate", type=float, default=0.03)
    parser.add_argument("--max-target-hold-rate", type=float, default=0.97)
    parser.add_argument("--min-present-target-classes", type=int, default=2)
    args = parser.parse_args()
    payload = run(args)
    print(f"4B.4.3.6.6.24D model retrain recovery {payload['decision']}")
    print(f" - candidates: {payload['candidate_count']}")
    print(f" - approved: {payload['approved']}")
    print(f" - recommended_action: {payload['recommended_action']}")
    print(f"report_json: {payload['report_json']}")
    print(f"report_md: {payload['report_md']}")
    if payload["decision"] == "BLOCK":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
