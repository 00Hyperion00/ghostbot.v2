from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Sequence

CONTRACT_VERSION = "4B.4.3.6.6.21"
DEFAULT_REPORT_PREFIX = "4B436621_acceptance"


@dataclass(frozen=True)
class TestGroup:
    name: str
    description: str
    command: tuple[str, ...]
    required_paths: tuple[str, ...] = ()
    timeout_sec: int = 300


@dataclass
class GroupResult:
    name: str
    description: str
    status: str
    returncode: int | None
    duration_sec: float
    command: list[str]
    missing_paths: list[str]
    stdout_tail: str
    log_path: str | None


DASHBOARD_ACCEPTANCE = (
    "tests/test_risk_plan_execution_contract.py",
    "tests/test_position_management_protective_exit_ux.py",
    "tests/test_dashboard_operator_ux_hardening.py",
    "tests/test_status_dashboard_payload.py",
    "tests/test_dashboard_audit_event_viewer_ux.py",
    "tests/test_dashboard_logic.py",
    "tests/test_dashboard_offline_fallback.py",
    "tests/test_model_retrain_reload_workflow.py",
)

DASHBOARD_FULL_GATE = (
    "tests/test_restart_recovery_persistent_reconciliation.py",
    "tests/test_risk_plan_execution_contract.py",
    "tests/test_position_management_protective_exit_ux.py",
    "tests/test_dashboard_operator_ux_hardening.py",
    "tests/test_status_dashboard_payload.py",
    "tests/test_dashboard_audit_event_viewer_ux.py",
    "tests/test_runtime_observability_event_audit.py",
    "tests/test_dashboard_backend_idempotency.py",
    "tests/test_engine_start_idempotent.py",
    "tests/test_dashboard_logic.py",
    "tests/test_dashboard_offline_fallback.py",
    "tests/test_dashboard_api_timeout.py",
    "tests/test_dashboard_navigation_layout.py",
    "tests/test_dashboard_backend_process_management.py",
    "tests/test_model_quality_monitoring.py",
    "tests/test_performance_analytics.py",
    "tests/test_config_profile_safety.py",
    "tests/test_desktop_launcher_packaging.py",
    "tests/test_operator_diagnostics.py",
    "tests/test_live_order_reconciliation_reliability.py",
    "tests/test_strategy_decision_audit.py",
    "tests/test_dashboard_operator_cockpit.py",
)

LIFECYCLE_RISK = (
    "tests/test_entry_lifecycle_guard.py",
    "tests/test_exit_lifecycle_guard.py",
    "tests/test_pending_reconciliation.py",
    "tests/test_execution_hygiene.py",
    "tests/test_risk_guards.py",
    "tests/test_live_demo_order_lifecycle_hardening.py",
)

AI_MODEL = (
    "tests/test_ai_provider_loading.py",
    "tests/test_strategy_ai_merge.py",
    "tests/test_api_ai_reload.py",
    "tests/test_dashboard_training_reload.py",
    "tests/test_ai_schema_validation.py",
    "tests/test_model_retrain_reload_workflow.py",
)

FEATURE_SCHEMA = (
    "tests/test_xgb_feature_schema.py",
    "tests/test_xgb_leakage_guard.py",
    "tests/test_xgb_feature_pack_4b3.py",
    "tests/test_xgb_regime_pack_4b32.py",
    "tests/test_xgb_vwap_pack_4b33.py",
    "tests/test_xgb_mtf_pack_4b34.py",
)

TRAINING_PIPELINE = (
    "tests/test_training_features.py",
    "tests/test_training_pipeline.py",
    "tests/test_xgb_labeling.py",
    "tests/test_xgb_class_balance.py",
    "tests/test_xgb_threshold_calibration.py",
    "tests/test_xgb_prediction_distribution.py",
    "tests/test_xgb_dataset_manifest.py",
)

API_COMPAT = (
    "tests/test_api_logs_compat.py",
    "tests/test_api_logs_market.py",
    "tests/test_api_start_stop.py",
    "tests/test_api_managed_app.py",
)

TEST_GROUPS: dict[str, TestGroup] = {
    "compileall": TestGroup(
        name="compileall",
        description="Python syntax/import bytecode gate for src and tests",
        command=("-m", "compileall", "-q", "src", "tests"),
        required_paths=("src", "tests"),
        timeout_sec=300,
    ),
    "dashboard_acceptance": TestGroup(
        name="dashboard_acceptance",
        description="Dashboard/operator/audit short acceptance suite",
        command=("-m", "pytest", "-q", *DASHBOARD_ACCEPTANCE),
        required_paths=DASHBOARD_ACCEPTANCE,
        timeout_sec=300,
    ),
    "dashboard_full_gate": TestGroup(
        name="dashboard_full_gate",
        description="Full dashboard/status/audit/operator cockpit gate",
        command=("-m", "pytest", "-q", *DASHBOARD_FULL_GATE),
        required_paths=DASHBOARD_FULL_GATE,
        timeout_sec=420,
    ),
    "lifecycle_risk": TestGroup(
        name="lifecycle_risk",
        description="Order lifecycle, pending reconciliation and risk guard regression",
        command=("-m", "pytest", "-q", *LIFECYCLE_RISK),
        required_paths=LIFECYCLE_RISK,
        timeout_sec=300,
    ),
    "ai_model": TestGroup(
        name="ai_model",
        description="AI provider, reload, schema and dashboard training regression",
        command=("-m", "pytest", "-q", *AI_MODEL),
        required_paths=AI_MODEL,
        timeout_sec=360,
    ),
    "feature_schema": TestGroup(
        name="feature_schema",
        description="XGBoost feature/schema/leakage regression",
        command=("-m", "pytest", "-q", *FEATURE_SCHEMA),
        required_paths=FEATURE_SCHEMA,
        timeout_sec=360,
    ),
    "training_pipeline": TestGroup(
        name="training_pipeline",
        description="Training dataset/label/calibration/pipeline regression",
        command=("-m", "pytest", "-q", *TRAINING_PIPELINE),
        required_paths=TRAINING_PIPELINE,
        timeout_sec=420,
    ),
    "api": TestGroup(
        name="api",
        description="API compatibility/start-stop/log endpoints regression",
        command=("-m", "pytest", "-q", *API_COMPAT),
        required_paths=API_COMPAT,
        timeout_sec=300,
    ),
}

DEFAULT_GROUP_ORDER = (
    "compileall",
    "dashboard_acceptance",
    "dashboard_full_gate",
    "lifecycle_risk",
    "ai_model",
    "feature_schema",
    "training_pipeline",
    "api",
)


def tail_text(value: str, max_chars: int = 5000) -> str:
    if len(value) <= max_chars:
        return value
    return value[-max_chars:]


def now_stamp() -> str:
    return dt.datetime.now().strftime("%Y%m%d_%H%M%S")


def split_csv(values: Sequence[str] | None) -> list[str]:
    result: list[str] = []
    for value in values or []:
        for item in value.split(','):
            item = item.strip()
            if item:
                result.append(item)
    return result


def resolve_groups(only: Sequence[str] | None, skip: Sequence[str] | None) -> list[str]:
    selected = split_csv(only) or list(DEFAULT_GROUP_ORDER)
    skipped = set(split_csv(skip))
    unknown = [name for name in selected + list(skipped) if name not in TEST_GROUPS]
    if unknown:
        raise SystemExit(f"Unknown acceptance group(s): {', '.join(sorted(set(unknown)))}")
    return [name for name in selected if name not in skipped]


def build_env(root: Path) -> dict[str, str]:
    env = os.environ.copy()
    src_path = str(root / "src")
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = src_path if not existing else src_path + os.pathsep + existing
    env.setdefault("PYTHONUTF8", "1")
    return env


def missing_paths(root: Path, paths: Iterable[str]) -> list[str]:
    return [path for path in paths if not (root / path).exists()]


def ensure_report_dirs(root: Path) -> tuple[Path, Path]:
    reports = root / "reports"
    logs = reports / "acceptance_logs"
    logs.mkdir(parents=True, exist_ok=True)
    return reports, logs


def run_group(
    root: Path,
    group: TestGroup,
    *,
    timestamp: str,
    timeout_override: int | None = None,
    allow_missing: bool = False,
) -> GroupResult:
    missing = missing_paths(root, group.required_paths)
    command = [sys.executable, *group.command]
    reports_dir, logs_dir = ensure_report_dirs(root)
    log_path = logs_dir / f"{timestamp}_{group.name}.log"

    if missing and not allow_missing:
        output = "Missing required path(s):\n" + "\n".join(f" - {item}" for item in missing)
        log_path.write_text(output, encoding="utf-8")
        return GroupResult(
            name=group.name,
            description=group.description,
            status="MISSING",
            returncode=127,
            duration_sec=0.0,
            command=command,
            missing_paths=missing,
            stdout_tail=tail_text(output),
            log_path=str(log_path.relative_to(root)),
        )

    if missing and allow_missing:
        output = "Skipped due to missing required path(s):\n" + "\n".join(f" - {item}" for item in missing)
        log_path.write_text(output, encoding="utf-8")
        return GroupResult(
            name=group.name,
            description=group.description,
            status="SKIPPED",
            returncode=None,
            duration_sec=0.0,
            command=command,
            missing_paths=missing,
            stdout_tail=tail_text(output),
            log_path=str(log_path.relative_to(root)),
        )

    timeout_sec = int(timeout_override or group.timeout_sec)
    start = time.monotonic()
    try:
        completed = subprocess.run(
            command,
            cwd=str(root),
            env=build_env(root),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout_sec,
            check=False,
        )
        duration = time.monotonic() - start
        output = completed.stdout or ""
        log_path.write_text(output, encoding="utf-8", errors="replace")
        return GroupResult(
            name=group.name,
            description=group.description,
            status="PASS" if completed.returncode == 0 else "FAIL",
            returncode=completed.returncode,
            duration_sec=round(duration, 3),
            command=command,
            missing_paths=[],
            stdout_tail=tail_text(output),
            log_path=str(log_path.relative_to(root)),
        )
    except subprocess.TimeoutExpired as exc:
        duration = time.monotonic() - start
        output = (exc.stdout or "") + f"\nTIMEOUT after {timeout_sec} sec\n"
        log_path.write_text(output, encoding="utf-8", errors="replace")
        return GroupResult(
            name=group.name,
            description=group.description,
            status="TIMEOUT",
            returncode=None,
            duration_sec=round(duration, 3),
            command=command,
            missing_paths=[],
            stdout_tail=tail_text(output),
            log_path=str(log_path.relative_to(root)),
        )


def result_summary(results: Sequence[GroupResult]) -> dict[str, int]:
    summary: dict[str, int] = {"PASS": 0, "FAIL": 0, "MISSING": 0, "SKIPPED": 0, "TIMEOUT": 0}
    for result in results:
        summary[result.status] = summary.get(result.status, 0) + 1
    return summary


def gate_passed(results: Sequence[GroupResult]) -> bool:
    return all(result.status in {"PASS", "SKIPPED"} for result in results)


def write_reports(root: Path, results: Sequence[GroupResult], *, timestamp: str, prefix: str) -> tuple[Path, Path]:
    reports_dir, _ = ensure_report_dirs(root)
    summary = result_summary(results)
    passed = gate_passed(results)
    payload = {
        "contract_version": CONTRACT_VERSION,
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "project_root": str(root),
        "decision": "PASS" if passed else "FAIL",
        "summary": summary,
        "results": [asdict(result) for result in results],
    }
    json_path = reports_dir / f"{prefix}_{timestamp}.json"
    md_path = reports_dir / f"{prefix}_{timestamp}.md"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        f"# {CONTRACT_VERSION} Acceptance Gate",
        "",
        f"Generated at: `{payload['generated_at']}`",
        f"Project root: `{root}`",
        f"Decision: **{payload['decision']}**",
        "",
        "## Summary",
        "",
        "| Status | Count |",
        "|---|---:|",
    ]
    for key in ("PASS", "FAIL", "MISSING", "SKIPPED", "TIMEOUT"):
        lines.append(f"| {key} | {summary.get(key, 0)} |")
    lines.extend(["", "## Groups", ""])
    for result in results:
        lines.extend([
            f"### {result.name} — {result.status}",
            "",
            f"Description: {result.description}",
            f"Duration: `{result.duration_sec}` sec",
            f"Return code: `{result.returncode}`",
            f"Log: `{result.log_path}`",
            "",
            "Command:",
            "```text",
            " ".join(result.command),
            "```",
            "",
        ])
        if result.missing_paths:
            lines.extend(["Missing paths:", "```text", "\n".join(result.missing_paths), "```", ""])
        if result.stdout_tail:
            lines.extend(["Output tail:", "```text", result.stdout_tail.strip(), "```", ""])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def list_groups() -> None:
    for name in DEFAULT_GROUP_ORDER:
        group = TEST_GROUPS[name]
        print(f"{name}: {group.description}")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=f"{CONTRACT_VERSION} release acceptance test runner")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Project root. Default: current directory")
    parser.add_argument("--groups", action="append", help="Comma-separated group names to run. Default: all")
    parser.add_argument("--skip-groups", action="append", help="Comma-separated group names to skip")
    parser.add_argument("--timeout-sec", type=int, default=None, help="Override timeout for every group")
    parser.add_argument("--allow-missing", action="store_true", help="Skip groups with missing test files instead of failing")
    parser.add_argument("--fail-fast", action="store_true", help="Stop after first failed/missing/timed-out group")
    parser.add_argument("--report-prefix", default=DEFAULT_REPORT_PREFIX, help="Report filename prefix")
    parser.add_argument("--list-groups", action="store_true", help="List known groups and exit")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.list_groups:
        list_groups()
        return 0

    root = args.root.resolve()
    groups = resolve_groups(args.groups, args.skip_groups)
    timestamp = now_stamp()
    results: list[GroupResult] = []

    print(f"{CONTRACT_VERSION} acceptance gate started")
    print(f"Project root: {root}")
    print(f"Groups: {', '.join(groups)}")

    for name in groups:
        group = TEST_GROUPS[name]
        print(f"\n>>> RUN {name}: {group.description}")
        result = run_group(
            root,
            group,
            timestamp=timestamp,
            timeout_override=args.timeout_sec,
            allow_missing=args.allow_missing,
        )
        results.append(result)
        print(f"<<< {name}: {result.status} ({result.duration_sec}s)")
        if result.stdout_tail:
            print(result.stdout_tail.strip()[-1200:])
        if args.fail_fast and result.status not in {"PASS", "SKIPPED"}:
            break

    json_path, md_path = write_reports(root, results, timestamp=timestamp, prefix=args.report_prefix)
    decision = "PASSED" if gate_passed(results) else "FAILED"
    print(f"\n{CONTRACT_VERSION} acceptance gate {decision}")
    print(f"JSON report: {json_path}")
    print(f"Markdown report: {md_path}")
    return 0 if gate_passed(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
