from __future__ import annotations

import argparse
import json
import platform
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradebot.hyp005_r1_canonical_epoch_contract import (  # noqa: E402
    BASELINE_TASK_NAME,
    CANONICAL_R1_REPORTS_DIR,
    CANONICAL_R1_TASK_NAME,
    HYP005_R1_CANONICAL_EPOCH_HARDENING_VERSION,
    LEGACY_R1_TASK_NAME,
    is_utc_artifact_filename,
)


def _latest(directory: Path, pattern: str) -> Path | None:
    matches = sorted(directory.glob(pattern), key=lambda item: (item.stat().st_mtime_ns, item.name), reverse=True)
    return matches[0] if matches else None


def _read_json(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _task_state(task_name: str) -> str:
    if platform.system().lower() != "windows":
        return "UNAVAILABLE"
    command = f"(Get-ScheduledTask -TaskName '{task_name}' -ErrorAction SilentlyContinue).State"
    try:
        completed = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
            capture_output=True,
            text=True,
            timeout=4.0,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return "UNAVAILABLE"
    text = completed.stdout.strip()
    return text.upper() if text else "NOT_FOUND"


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only 25AE-H5 canonical epoch audit")
    parser.add_argument("--project-root", type=Path, default=ROOT)
    parser.add_argument("--reports-dir", type=Path)
    parser.add_argument("--require-task-registration", action="store_true")
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()

    project_root = args.project_root.resolve()
    reports_dir = (args.reports_dir or (project_root / CANONICAL_R1_REPORTS_DIR)).resolve()
    latest_25v = _latest(reports_dir, "4B436625V_hyp005_shadow_observation_logger_*.json")
    latest_25x = _latest(reports_dir, "4B436625X_hyp005_shadow_collection_orchestrator_*.json")
    latest_25w = _latest(reports_dir, "4B436625W_hyp005_shadow_observation_acceptance_*.json")
    latest_25y = _latest(reports_dir, "4B436625Y_hyp005_shadow_operator_daily_audit_*.json")
    latest_merged = _latest(reports_dir, "4B436625X_hyp005_shadow_merged_ledger_*.jsonl")

    artifacts = [path for path in (latest_25v, latest_25x, latest_25w, latest_25y, latest_merged) if path is not None]
    utc_stamp_artifacts_ready = len(artifacts) == 5 and all(is_utc_artifact_filename(path) for path in artifacts)

    acceptance = _read_json(latest_25w)
    audit = _read_json(latest_25y)
    ledger_input_paths = _as_list(acceptance.get("ledger_input_paths"))
    collection_report_paths = _as_list(acceptance.get("collection_report_paths"))
    acceptance_source_ledgers = _as_list(acceptance.get("source_ledgers"))
    source_collection_reports = int(acceptance.get("source_collection_reports") or 0)

    acceptance_source_attribution_ready = (
        len(ledger_input_paths) == 1
        and len(collection_report_paths) == 1
        and len(acceptance_source_ledgers) == 1
        and source_collection_reports == 1
    )
    audit_source_attribution_ready = int(audit.get("source_ledgers") or 0) == 1 and int(audit.get("source_reports") or 0) == 3

    cockpit_path = project_root / "src" / "tradebot" / "operator_cockpit_v2_read_only.py"
    cockpit_text = cockpit_path.read_text(encoding="utf-8") if cockpit_path.exists() else ""
    dashboard_source_alignment_ready = (
        "OPERATOR_COCKPIT_V2_CANONICAL_EPOCH_HARDENING_VERSION" in cockpit_text
        and "CANONICAL_R1_REPORTS_DIR" in cockpit_text
        and "resolve_active_reports_dir" in cockpit_text
        and "CANONICAL_R1_TASK_NAME" in cockpit_text
    )

    baseline_state = _task_state(BASELINE_TASK_NAME)
    legacy_state = _task_state(LEGACY_R1_TASK_NAME)
    canonical_state = _task_state(CANONICAL_R1_TASK_NAME)
    task_registration_ready = (
        baseline_state in {"DISABLED", "NOT_FOUND", "UNAVAILABLE"}
        and legacy_state in {"DISABLED", "UNAVAILABLE"}
        and canonical_state in {"READY", "RUNNING", "UNAVAILABLE"}
    )

    active_runtime_chain_ready = (
        utc_stamp_artifacts_ready
        and acceptance_source_attribution_ready
        and audit_source_attribution_ready
        and dashboard_source_alignment_ready
        and (task_registration_ready if args.require_task_registration else True)
    )
    payload = {
        "ok": active_runtime_chain_ready,
        "read_only": True,
        "contract_version": HYP005_R1_CANONICAL_EPOCH_HARDENING_VERSION,
        "reports_dir": str(reports_dir),
        "artifacts": [str(path) for path in artifacts],
        "utc_stamp_artifacts_ready": utc_stamp_artifacts_ready,
        "acceptance_source_attribution_ready": acceptance_source_attribution_ready,
        "audit_source_attribution_ready": audit_source_attribution_ready,
        "dashboard_source_alignment_ready": dashboard_source_alignment_ready,
        "task_registration_required": bool(args.require_task_registration),
        "task_registration_ready": task_registration_ready,
        "scheduler": {
            "baseline_task": {"task_name": BASELINE_TASK_NAME, "state": baseline_state},
            "legacy_r1_task": {"task_name": LEGACY_R1_TASK_NAME, "state": legacy_state},
            "canonical_r1_task": {"task_name": CANONICAL_R1_TASK_NAME, "state": canonical_state},
        },
        "source_attribution": {
            "ledger_input_paths": ledger_input_paths,
            "collection_report_paths": collection_report_paths,
            "acceptance_source_ledgers": acceptance_source_ledgers,
            "source_collection_reports": source_collection_reports,
            "audit_source_ledgers": audit.get("source_ledgers"),
            "audit_source_reports": audit.get("source_reports"),
        },
        "config_mutation_performed": False,
        "scheduler_mutation_performed": False,
        "trading_action_performed": False,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
