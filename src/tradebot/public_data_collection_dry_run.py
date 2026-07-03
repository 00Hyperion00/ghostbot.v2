from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PATCH_ID = "4B436635F"
PATCH_VERSION = "4B.4.3.6.6.35F"
PATCH_NAME = "Public Data Collection Dry-Run"
CHECK_NAME = "public_data_collection_dry_run"
READY_DECISION = "PUBLIC_DATA_COLLECTION_DRY_RUN_READY_NO_SUBMIT_COLLECTOR_GUARD_LOCKED"
NOT_READY_DECISION = "PUBLIC_DATA_COLLECTION_DRY_RUN_NOT_READY"
SOURCE_READY_DECISION = "DRY_RUN_COLLECTION_AUTHORIZATION_READY_NO_SUBMIT_COLLECTION_SEAL_LOCKED"
NEXT_PHASE = "4B.4.3.6.6.35G"

FALSE_SAFETY_FIELDS = (
    "approved_for_live_real",
    "approved_for_paper_transition",
    "approved_for_exchange_submit",
    "approved_for_runtime_overlay",
    "exchange_submit_allowed",
    "network_submit_allowed",
    "paper_submit_allowed",
    "live_real_submit_allowed",
    "runtime_overlay_allowed",
    "order_submit_performed",
    "exchange_submit_performed",
    "trading_action_performed",
    "training_performed",
    "reload_performed",
    "runtime_overlay_activated",
    "archive_execution_allowed",
    "archive_move_performed",
    "file_delete_performed",
    "file_move_performed",
    "report_delete_performed",
    "destructive_cleanup_performed",
    "deduplication_action_performed",
    "transition_to_next_phase_allowed",
    "transition_to_next_phase_performed",
    "next_phase_unlock_allowed",
    "next_phase_unlock_performed",
    "approval_performed",
    "simulated_approval_performed",
    "paper_transition_approval_performed",
    "paper_transition_unblocked",
    "paper_environment_enabled",
    "live_environment_enabled",
    "runtime_readiness_unlock_performed",
    "runtime_evidence_collection_performed",
    "evidence_collection_started",
    "public_market_data_collection_performed",
    "runtime_health_probe_performed",
    "runtime_probe_performed",
    "private_api_access_allowed",
    "private_account_read_performed",
    "collection_preflight_executed",
    "collection_runbook_executed",
    "collection_authorization_unlocked",
    "dry_run_collection_authorization_performed",
    "collection_seal_relaxed",
    "public_data_dry_run_authorized",
    "public_data_collection_allowed_now",
    "dry_run_collector_executed",
    "collector_guard_relaxed",
)

DEFAULT_SCOPE_FREEZE = (
    {
        "source_id": "public_klines",
        "source_type": "public_market_data",
        "access_class": "public_read_only",
        "allowed_in_future_collection": True,
        "execution_allowed_now": False,
        "scope_note": "OHLCV klines only; no order/account/private endpoints.",
    },
    {
        "source_id": "public_ticker_24h",
        "source_type": "public_market_data",
        "access_class": "public_read_only",
        "allowed_in_future_collection": True,
        "execution_allowed_now": False,
        "scope_note": "Ticker snapshot for diagnostics only; not executed by 35F.",
    },
    {
        "source_id": "public_book_ticker",
        "source_type": "public_market_data",
        "access_class": "public_read_only",
        "allowed_in_future_collection": True,
        "execution_allowed_now": False,
        "scope_note": "Best bid/ask public endpoint planning only.",
    },
    {
        "source_id": "runtime_health_readiness_probe",
        "source_type": "local_runtime_probe",
        "access_class": "local_read_only",
        "allowed_in_future_collection": True,
        "execution_allowed_now": False,
        "scope_note": "Local health/status probe dry-run scope; not executed by 35F.",
    },
    {
        "source_id": "recovery_report_ingestion",
        "source_type": "local_evidence_file",
        "access_class": "local_read_only",
        "allowed_in_future_collection": True,
        "execution_allowed_now": False,
        "scope_note": "Read-only report parsing only; no delete/move/dedup.",
    },
)


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"JSON object expected: {path}")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def repo_root_from(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists() or (candidate / "src").exists():
            return candidate
    return current


def git_value(args: list[str], repo_root: Path) -> str | None:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=repo_root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=5,
        )
    except Exception:
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


def git_snapshot(repo_root: Path) -> dict[str, Any]:
    branch = git_value(["branch", "--show-current"], repo_root)
    head = git_value(["rev-parse", "--short", "HEAD"], repo_root)
    tags = git_value(["tag", "--list", "4B.4.3.6.6.35*"], repo_root)
    return {
        "git_available": branch is not None or head is not None,
        "git_branch": branch or None,
        "git_head_short": head or None,
        "phase_35_tag_count_observed": len([line for line in (tags or "").splitlines() if line.strip()]),
    }


def latest_source_35e_report(reports_dir: Path) -> Path | None:
    patterns = (
        "4B436635E_dry_run_collection_authorization_*_ready.json",
        "**/4B436635E_dry_run_collection_authorization_*_ready.json",
    )
    matches: list[Path] = []
    for pattern in patterns:
        matches.extend(p for p in reports_dir.glob(pattern) if p.is_file())
    unique = sorted(set(matches), key=lambda p: (p.stat().st_mtime, str(p)))
    return unique[-1] if unique else None


def safety_violations(report: dict[str, Any]) -> list[str]:
    return [field for field in FALSE_SAFETY_FIELDS if bool(report.get(field, False))]


@dataclass(frozen=True)
class Source35E:
    path: Path | None
    data: dict[str, Any]
    complete: bool
    status: str
    decision: str | None
    safety_violations: tuple[str, ...]


def load_source_35e(reports_dir: Path) -> Source35E:
    path = latest_source_35e_report(reports_dir)
    if path is None:
        return Source35E(None, {}, False, "SOURCE_35E_REPORT_MISSING", None, tuple())
    try:
        data = read_json(path)
    except Exception as exc:
        return Source35E(path, {}, False, f"SOURCE_35E_REPORT_INVALID:{exc}", None, tuple())
    violations = tuple(safety_violations(data))
    complete = (
        data.get("status") == "READY"
        and data.get("decision") == SOURCE_READY_DECISION
        and bool(data.get("no_submit_collection_seal_complete"))
        and bool(data.get("no_submit_collection_seal_locked"))
        and bool(data.get("operator_collection_token_ledger_complete"))
        and bool(data.get("public_data_dry_run_authorization_complete"))
        and not violations
    )
    return Source35E(
        path=path,
        data=data,
        complete=complete,
        status="SOURCE_35E_READY" if complete else "SOURCE_35E_NOT_READY",
        decision=data.get("decision"),
        safety_violations=violations,
    )


def build_collection_token_template(source: Source35E) -> dict[str, Any]:
    template = {
        "token_type": "PUBLIC_DATA_COLLECTION_DRY_RUN_TEMPLATE_ONLY",
        "schema_version": PATCH_VERSION,
        "required_fields": [
            "patch_version",
            "operator_id",
            "authorized_scope_digest",
            "no_submit_collection_seal_digest",
            "created_at_utc",
            "operator_attestation",
        ],
        "forbidden_effects": [
            "exchange_submit",
            "network_submit_private_api",
            "paper_submit",
            "live_real_submit",
            "runtime_overlay_activation",
            "file_delete",
            "file_move",
        ],
        "template_is_not_authorization": True,
        "execution_allowed_now": False,
    }
    payload = {
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "source_35e_decision": source.decision,
        "source_35e_report": str(source.path) if source.path else None,
        "collection_token_template": template,
        "collection_token_template_complete": source.complete,
        "collection_token_template_is_not_authorization": True,
        "collection_token_present": False,
        "collection_token_valid": False,
        "collection_token_template_status": (
            "COLLECTION_TOKEN_TEMPLATE_READY_NOT_A_TOKEN" if source.complete else "COLLECTION_TOKEN_TEMPLATE_BLOCKED_SOURCE_35E_NOT_READY"
        ),
    }
    payload["collection_token_template_digest"] = digest(payload)
    return payload


def build_public_market_data_scope_freeze(source: Source35E) -> dict[str, Any]:
    scope = [dict(item) for item in DEFAULT_SCOPE_FREEZE]
    payload = {
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "source_35e_decision": source.decision,
        "source_35e_report": str(source.path) if source.path else None,
        "public_market_data_scope": scope,
        "public_market_data_scope_freeze_complete": source.complete,
        "public_market_data_scope_frozen": bool(source.complete),
        "public_market_data_scope_count": len(scope),
        "public_market_data_scope_status": (
            "PUBLIC_MARKET_DATA_SCOPE_FROZEN_DRY_RUN_ONLY" if source.complete else "PUBLIC_MARKET_DATA_SCOPE_FREEZE_BLOCKED_SOURCE_35E_NOT_READY"
        ),
        "public_data_collection_allowed_now": False,
        "public_market_data_collection_performed": False,
    }
    payload["public_market_data_scope_freeze_digest"] = digest(payload)
    return payload


def build_no_submit_dry_run_collector_guard(source: Source35E) -> dict[str, Any]:
    guard = {
        "guard_name": "NO_SUBMIT_DRY_RUN_COLLECTOR_GUARD",
        "locked": True,
        "collector_executable_now": False,
        "collector_execution_performed": False,
        "private_api_access_allowed": False,
        "order_submit_allowed": False,
        "paper_submit_allowed": False,
        "live_real_submit_allowed": False,
        "runtime_overlay_allowed": False,
        "boundary_relax_allowed": False,
    }
    payload = {
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "source_35e_decision": source.decision,
        "source_35e_report": str(source.path) if source.path else None,
        "collector_guard": guard,
        "no_submit_dry_run_collector_guard_complete": source.complete,
        "no_submit_dry_run_collector_guard_locked": True,
        "no_submit_dry_run_collector_guard_status": (
            "NO_SUBMIT_DRY_RUN_COLLECTOR_GUARD_LOCKED" if source.complete else "NO_SUBMIT_DRY_RUN_COLLECTOR_GUARD_BLOCKED_SOURCE_35E_NOT_READY"
        ),
        "dry_run_collector_executable_now": False,
        "dry_run_collector_executed": False,
        "collector_guard_relaxed": False,
    }
    payload["no_submit_dry_run_collector_guard_digest"] = digest(payload)
    return payload


def evaluate(repo_root: Path | None = None, reports_dir: Path | None = None, write_reports: bool = False) -> dict[str, Any]:
    repo_root = repo_root_from(repo_root)
    reports_dir = (reports_dir or (repo_root / "reports" / "recovery")).resolve()
    source = load_source_35e(reports_dir)
    token_template = build_collection_token_template(source)
    scope_freeze = build_public_market_data_scope_freeze(source)
    collector_guard = build_no_submit_dry_run_collector_guard(source)

    errors: list[str] = []
    if not source.complete:
        errors.append(source.status)
    if source.safety_violations:
        errors.append("SOURCE_35E_SAFETY_VIOLATIONS:" + ",".join(source.safety_violations))

    ready = not errors and all(
        [
            token_template["collection_token_template_complete"],
            scope_freeze["public_market_data_scope_freeze_complete"],
            collector_guard["no_submit_dry_run_collector_guard_complete"],
            collector_guard["no_submit_dry_run_collector_guard_locked"],
        ]
    )
    stamp = utc_stamp()

    report: dict[str, Any] = {
        "ok": ready,
        "status": "READY" if ready else "NOT_READY",
        "decision": READY_DECISION if ready else NOT_READY_DECISION,
        "check_name": CHECK_NAME,
        "patch_id": PATCH_ID,
        "patch_name": PATCH_NAME,
        "patch_version": PATCH_VERSION,
        "errors": errors,
        **git_snapshot(repo_root),
        "source_35e_complete": source.complete,
        "source_35e_status": source.status,
        "source_35e_decision": source.decision,
        "source_35e_report": str(source.path) if source.path else None,
        "source_35e_safety_violation_count": len(source.safety_violations),
        "source_35e_safety_violations": list(source.safety_violations),
        "source_35e_no_submit_collection_seal_digest": source.data.get("no_submit_collection_seal_digest"),
        "source_35e_public_data_dry_run_authorization_digest": source.data.get("public_data_dry_run_authorization_digest"),
        "source_35e_operator_collection_token_ledger_digest": source.data.get("operator_collection_token_ledger_digest"),
        "phase_34_closed": bool(source.data.get("phase_34_closed", True)),
        "phase_35_planning_only": True,
        "accepted_for_public_data_collection_dry_run": ready,
        "collection_token_template_complete": token_template["collection_token_template_complete"],
        "collection_token_template_status": token_template["collection_token_template_status"],
        "collection_token_template_digest": token_template["collection_token_template_digest"],
        "collection_token_template_is_not_authorization": True,
        "collection_token_present": False,
        "collection_token_valid": False,
        "public_market_data_scope_freeze_complete": scope_freeze["public_market_data_scope_freeze_complete"],
        "public_market_data_scope_frozen": scope_freeze["public_market_data_scope_frozen"],
        "public_market_data_scope_count": scope_freeze["public_market_data_scope_count"],
        "public_market_data_scope_status": scope_freeze["public_market_data_scope_status"],
        "public_market_data_scope_freeze_digest": scope_freeze["public_market_data_scope_freeze_digest"],
        "no_submit_dry_run_collector_guard_complete": collector_guard["no_submit_dry_run_collector_guard_complete"],
        "no_submit_dry_run_collector_guard_locked": collector_guard["no_submit_dry_run_collector_guard_locked"],
        "no_submit_dry_run_collector_guard_status": collector_guard["no_submit_dry_run_collector_guard_status"],
        "no_submit_dry_run_collector_guard_digest": collector_guard["no_submit_dry_run_collector_guard_digest"],
        "public_data_collection_scope_ready": ready,
        "public_data_collection_allowed_now": False,
        "dry_run_collector_executable_now": False,
        "dry_run_collector_executed": False,
        "collector_guard_relaxed": False,
        "collection_authorization_unlocked": False,
        "dry_run_collection_authorization_performed": False,
        "collection_seal_relaxed": False,
        "collection_preflight_executable_now": False,
        "collection_preflight_executed": False,
        "collection_runbook_executed": False,
        "runtime_evidence_collection_performed": False,
        "evidence_collection_started": False,
        "public_market_data_collection_performed": False,
        "runtime_probe_performed": False,
        "runtime_health_probe_performed": False,
        "private_api_access_allowed": False,
        "private_account_read_performed": False,
        "paper_transition_blocked": True,
        "paper_transition_ready": False,
        "paper_transition_unblocked": False,
        "paper_transition_approval_performed": False,
        "paper_environment_enabled": False,
        "live_environment_enabled": False,
        "paper_transition_status": "PAPER_TRANSITION_BLOCKED_PUBLIC_DATA_DRY_RUN_ONLY_NO_SUBMIT",
        "runtime_readiness_status": "PUBLIC_DATA_COLLECTION_DRY_RUN_READY_PLANNING_ONLY_NO_SUBMIT" if ready else "PUBLIC_DATA_COLLECTION_DRY_RUN_NOT_READY",
        "next_phase": NEXT_PHASE,
        "next_phase_unlock_allowed": False,
        "next_phase_unlock_performed": False,
        "transition_to_next_phase_allowed": False,
        "transition_to_next_phase_performed": False,
    }
    for field in FALSE_SAFETY_FIELDS:
        report.setdefault(field, False)

    if write_reports:
        reports_dir.mkdir(parents=True, exist_ok=True)
        token_path = reports_dir / f"{PATCH_ID}_collection_token_template_{stamp}.json"
        scope_path = reports_dir / f"{PATCH_ID}_public_market_data_scope_freeze_{stamp}.json"
        guard_path = reports_dir / f"{PATCH_ID}_no_submit_dry_run_collector_guard_{stamp}.json"
        report_path = reports_dir / f"{PATCH_ID}_public_data_collection_dry_run_{stamp}_{'ready' if ready else 'not_ready'}.json"
        write_json(token_path, token_template)
        write_json(scope_path, scope_freeze)
        write_json(guard_path, collector_guard)
        report.update(
            {
                "collection_token_template_path": str(token_path),
                "public_market_data_scope_freeze_path": str(scope_path),
                "no_submit_dry_run_collector_guard_path": str(guard_path),
                "report_path": str(report_path),
            }
        )
        write_json(report_path, report)
    else:
        report.update(
            {
                "collection_token_template_path": None,
                "public_market_data_scope_freeze_path": None,
                "no_submit_dry_run_collector_guard_path": None,
                "report_path": None,
            }
        )
    return report


def main(argv: list[str] | None = None, *, write_reports: bool = False) -> int:
    parser = argparse.ArgumentParser(description=f"{PATCH_VERSION} {PATCH_NAME}")
    parser.add_argument("--reports-dir", type=Path, default=None)
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args(argv)
    report = evaluate(reports_dir=args.reports_dir, write_reports=write_reports)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
