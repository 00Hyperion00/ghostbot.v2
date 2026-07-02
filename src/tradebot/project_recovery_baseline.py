from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable

PATCH_ID = "4B436633A"
PATCH_VERSION = "4B.4.3.6.6.33A"
PATCH_NAME = "Project Recovery Baseline"
READY_DECISION = "PROJECT_RECOVERY_BASELINE_READY_NO_TRADING_ACTIONS"
NOT_READY_DECISION = "PROJECT_RECOVERY_BASELINE_NOT_READY"

CORE_ROOT_PATHS: tuple[str, ...] = (
    "src",
    "tools",
    "tests",
    "docs",
    "reports",
    "examples",
    "models",
)

SAFETY_FALSE_KEYS: tuple[str, ...] = (
    "live_trading_armed",
    "live_real_double_confirm",
    "auto_trade_on_signal",
    "paper_transition_operator_approved",
    "paper_transition_runtime_envelope_frozen",
    "paper_sandbox_dry_run_operator_lock_issued",
    "paper_sandbox_operator_final_approval_issued",
    "paper_sandbox_candidate_unlock_issued",
    "paper_sandbox_execution_preflight_authorization_issued",
    "paper_sandbox_dry_run_execution_authorization_issued",
    "first_paper_sandbox_canary_operator_approval_issued",
    "live_real_micro_canary_perform_network_submit",
)

SAFETY_TRUE_KEYS: tuple[str, ...] = (
    "strict_config_validation",
    "runtime_lock_enabled",
    "sqlite_wal_enabled",
    "promotion_gate_isolation_enabled",
    "paper_kill_switch_enabled",
    "paper_mode_runtime_guardrail_kill_switch_enabled",
    "paper_soak_evidence_window_kill_switch_enabled",
    "live_real_preflight_hard_submit_block_required",
    "live_real_final_hard_submit_block_required",
    "live_real_micro_canary_kill_switch_armed",
    "live_real_micro_canary_hard_caps_required",
    "live_real_micro_canary_reconciliation_emergency_stop_armed",
    "live_real_micro_canary_reconciliation_kill_switch_armed",
    "live_real_hard_block_required",
)

SENSITIVE_KEY_PATTERN = re.compile(r"(secret|token|api_key|password|credential)", re.IGNORECASE)
PHASE_PATTERN = re.compile(r"4B4366(?P<suffix>[0-9A-Z_]+)", re.IGNORECASE)
REPORT_STATUS_PATTERN = re.compile(
    r"_(ready|not_ready|approval_required|execution_evidence_required)\.json$",
    re.IGNORECASE,
)


@dataclass(slots=True)
class DirectoryInventory:
    path: str
    exists: bool
    file_count: int = 0
    dir_count: int = 0


@dataclass(slots=True)
class RepoInventory:
    root: str
    generated_at_epoch_ms: int
    root_exists: bool
    directories: list[DirectoryInventory]
    total_files: int
    total_dirs: int
    has_pyproject: bool
    has_requirements: bool
    has_readme: bool
    complete: bool


@dataclass(slots=True)
class PhaseRecord:
    phase_key: str
    apply_files: list[str] = field(default_factory=list)
    check_files: list[str] = field(default_factory=list)
    run_files: list[str] = field(default_factory=list)
    rollback_files: list[str] = field(default_factory=list)
    test_files: list[str] = field(default_factory=list)
    doc_files: list[str] = field(default_factory=list)
    readme_apply_files: list[str] = field(default_factory=list)

    @property
    def artifact_count(self) -> int:
        return (
            len(self.apply_files)
            + len(self.check_files)
            + len(self.run_files)
            + len(self.rollback_files)
            + len(self.test_files)
            + len(self.doc_files)
            + len(self.readme_apply_files)
        )

    @property
    def has_core_artifact(self) -> bool:
        return bool(self.apply_files or self.run_files or self.check_files or self.doc_files)


@dataclass(slots=True)
class PhaseInventory:
    complete: bool
    phase_count: int
    phases: list[PhaseRecord]
    orphan_like_files: list[str]
    latest_phase_key: str | None


@dataclass(slots=True)
class EvidenceInventory:
    complete: bool
    reports_dir_exists: bool
    report_count: int
    ready_count: int
    not_ready_count: int
    approval_required_count: int
    execution_evidence_required_count: int
    unknown_status_count: int
    newest_reports: list[str]


@dataclass(slots=True)
class ConfigInventory:
    complete: bool
    config_file_exists: bool
    settings_field_count: int
    safety_false_keys: dict[str, bool | None]
    safety_true_keys: dict[str, bool | None]
    redacted_settings_hash: str | None
    redacted_settings_snapshot: dict[str, Any]


@dataclass(slots=True)
class SafetySnapshot:
    complete: bool
    live_real_allowed: bool
    paper_transition_allowed: bool
    exchange_submit_allowed: bool
    runtime_overlay_allowed: bool
    trading_action_performed: bool
    training_performed: bool
    reload_performed: bool
    blockers: list[str]


@dataclass(slots=True)
class RecoveryBaselineReport:
    patch_id: str
    patch_version: str
    patch_name: str
    decision: str
    status: str
    generated_at_epoch_ms: int
    repo_inventory: RepoInventory
    phase_inventory: PhaseInventory
    evidence_inventory: EvidenceInventory
    config_inventory: ConfigInventory
    safety_snapshot: SafetySnapshot
    approved_for_live_real: bool
    approved_for_paper_transition: bool
    approved_for_exchange_submit: bool
    approved_for_runtime_overlay: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# -----------------------------
# filesystem helpers
# -----------------------------

def now_epoch_ms() -> int:
    return int(time.time() * 1000)


def iter_files(root: Path, relative_roots: Iterable[str] = CORE_ROOT_PATHS) -> Iterable[Path]:
    for relative_root in relative_roots:
        base = root / relative_root
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.is_file():
                yield path


def safe_relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


# -----------------------------
# inventory builders
# -----------------------------

def build_repo_inventory(root: Path) -> RepoInventory:
    directories: list[DirectoryInventory] = []
    total_files = 0
    total_dirs = 0

    for relative in CORE_ROOT_PATHS:
        path = root / relative
        exists = path.exists() and path.is_dir()
        file_count = 0
        dir_count = 0
        if exists:
            for child in path.rglob("*"):
                if child.is_file():
                    file_count += 1
                elif child.is_dir():
                    dir_count += 1
            total_files += file_count
            total_dirs += dir_count
        directories.append(
            DirectoryInventory(
                path=relative,
                exists=exists,
                file_count=file_count,
                dir_count=dir_count,
            )
        )

    has_pyproject = (root / "pyproject.toml").is_file()
    has_requirements = (root / "requirements.txt").is_file()
    has_readme = (root / "README.md").is_file()
    root_exists = root.exists() and root.is_dir()
    complete = root_exists and has_pyproject and has_readme and any(d.path == "src" and d.exists for d in directories)

    return RepoInventory(
        root=str(root.resolve()),
        generated_at_epoch_ms=now_epoch_ms(),
        root_exists=root_exists,
        directories=directories,
        total_files=total_files,
        total_dirs=total_dirs,
        has_pyproject=has_pyproject,
        has_requirements=has_requirements,
        has_readme=has_readme,
        complete=complete,
    )


def _phase_key_from_path(relative_path: str) -> str | None:
    match = PHASE_PATTERN.search(relative_path)
    if not match:
        return None
    return "4B4366" + match.group("suffix").upper()


def build_phase_inventory(root: Path) -> PhaseInventory:
    records: dict[str, PhaseRecord] = {}
    orphan_like_files: list[str] = []

    for path in iter_files(root, ("tools", "tests", "docs")):
        relative = safe_relative(path, root)
        phase_key = _phase_key_from_path(relative)
        if phase_key is None:
            if any(token in path.name.lower() for token in ("apply_4b", "run_4b", "check_4b", "rollback_4b")):
                orphan_like_files.append(relative)
            continue

        record = records.setdefault(phase_key, PhaseRecord(phase_key=phase_key))
        name_lower = path.name.lower()
        if relative.startswith("tools/apply_"):
            record.apply_files.append(relative)
        elif relative.startswith("tools/check_"):
            record.check_files.append(relative)
        elif relative.startswith("tools/run_"):
            record.run_files.append(relative)
        elif relative.startswith("tools/rollback_"):
            record.rollback_files.append(relative)
        elif relative.startswith("tests/test_"):
            record.test_files.append(relative)
        elif relative.startswith("docs/"):
            record.doc_files.append(relative)
        elif name_lower.startswith("readme_apply_"):
            record.readme_apply_files.append(relative)
        else:
            orphan_like_files.append(relative)

    phases = sorted(records.values(), key=lambda item: item.phase_key)
    latest_phase_key = phases[-1].phase_key if phases else None
    complete = bool(phases) and not orphan_like_files

    return PhaseInventory(
        complete=complete,
        phase_count=len(phases),
        phases=phases,
        orphan_like_files=sorted(orphan_like_files),
        latest_phase_key=latest_phase_key,
    )


def build_evidence_inventory(root: Path) -> EvidenceInventory:
    reports_dir = root / "reports"
    report_paths = sorted(reports_dir.rglob("*.json")) if reports_dir.exists() else []
    ready_count = 0
    not_ready_count = 0
    approval_required_count = 0
    execution_evidence_required_count = 0
    unknown_status_count = 0

    newest = sorted(report_paths, key=lambda item: item.stat().st_mtime, reverse=True)[:25]

    for path in report_paths:
        name = path.name.lower()
        if name.endswith("_ready.json") and not name.endswith("_not_ready.json"):
            ready_count += 1
        elif name.endswith("_not_ready.json"):
            not_ready_count += 1
        elif name.endswith("_approval_required.json"):
            approval_required_count += 1
        elif name.endswith("_execution_evidence_required.json"):
            execution_evidence_required_count += 1
        elif REPORT_STATUS_PATTERN.search(name):
            # Defensive fallback; all known patterns above should classify first.
            pass
        else:
            unknown_status_count += 1

    complete = reports_dir.exists()
    return EvidenceInventory(
        complete=complete,
        reports_dir_exists=reports_dir.exists(),
        report_count=len(report_paths),
        ready_count=ready_count,
        not_ready_count=not_ready_count,
        approval_required_count=approval_required_count,
        execution_evidence_required_count=execution_evidence_required_count,
        unknown_status_count=unknown_status_count,
        newest_reports=[safe_relative(path, root) for path in newest],
    )


def _redact_value(key: str, value: Any) -> Any:
    if SENSITIVE_KEY_PATTERN.search(key):
        if value in (None, "", False):
            return ""
        return "[REDACTED]"
    return value


def _settings_to_redacted_dict(settings: Any) -> dict[str, Any]:
    if hasattr(settings, "to_dict"):
        try:
            raw = settings.to_dict(include_secrets=False)
            if isinstance(raw, dict):
                return {str(key): _redact_value(str(key), value) for key, value in raw.items()}
        except Exception:
            pass
    if hasattr(settings, "__dataclass_fields__"):
        return {
            str(key): _redact_value(str(key), getattr(settings, str(key)))
            for key in settings.__dataclass_fields__
        }
    return {}


def _load_default_settings(root: Path) -> Any | None:
    config_path = root / "src" / "tradebot" / "config.py"
    if not config_path.is_file():
        return None

    import importlib

    src_path = root / "src"
    src_path_str = str(src_path.resolve())
    added_to_path = False
    if src_path.exists() and src_path_str not in os.sys.path:
        os.sys.path.insert(0, src_path_str)
        added_to_path = True

    previous_tradebot_module = os.sys.modules.pop("tradebot", None)
    previous_config_module = os.sys.modules.pop("tradebot.config", None)
    try:
        importlib.invalidate_caches()
        module = importlib.import_module("tradebot.config")
        settings_cls = getattr(module, "Settings", None)
        if settings_cls is None:
            return None
        return settings_cls()
    except Exception:
        return None
    finally:
        os.sys.modules.pop("tradebot.config", None)
        os.sys.modules.pop("tradebot", None)
        if previous_tradebot_module is not None:
            os.sys.modules["tradebot"] = previous_tradebot_module
        if previous_config_module is not None:
            os.sys.modules["tradebot.config"] = previous_config_module
        if added_to_path:
            try:
                os.sys.path.remove(src_path_str)
            except ValueError:
                pass


def build_config_inventory(root: Path) -> ConfigInventory:
    config_file = root / "src" / "tradebot" / "config.py"
    settings = _load_default_settings(root)
    redacted_snapshot = _settings_to_redacted_dict(settings) if settings is not None else {}

    safety_false = {
        key: (bool(redacted_snapshot[key]) if key in redacted_snapshot else None)
        for key in SAFETY_FALSE_KEYS
    }
    safety_true = {
        key: (bool(redacted_snapshot[key]) if key in redacted_snapshot else None)
        for key in SAFETY_TRUE_KEYS
    }
    snapshot_json = json.dumps(redacted_snapshot, sort_keys=True, ensure_ascii=False, default=str)
    snapshot_hash = hashlib.sha256(snapshot_json.encode("utf-8")).hexdigest() if redacted_snapshot else None

    complete = config_file.is_file() and settings is not None and bool(redacted_snapshot)
    return ConfigInventory(
        complete=complete,
        config_file_exists=config_file.is_file(),
        settings_field_count=len(redacted_snapshot),
        safety_false_keys=safety_false,
        safety_true_keys=safety_true,
        redacted_settings_hash=snapshot_hash,
        redacted_settings_snapshot=redacted_snapshot,
    )


def build_safety_snapshot(config_inventory: ConfigInventory) -> SafetySnapshot:
    blockers: list[str] = []

    false_violations = [key for key, value in config_inventory.safety_false_keys.items() if value is True]
    true_violations = [key for key, value in config_inventory.safety_true_keys.items() if value is False]
    missing_false_keys = [key for key, value in config_inventory.safety_false_keys.items() if value is None]
    missing_true_keys = [key for key, value in config_inventory.safety_true_keys.items() if value is None]

    if false_violations:
        blockers.append("SAFETY_FALSE_KEY_ENABLED:" + ",".join(false_violations))
    if true_violations:
        blockers.append("SAFETY_TRUE_KEY_DISABLED:" + ",".join(true_violations))
    if missing_false_keys:
        blockers.append("SAFETY_FALSE_KEY_MISSING:" + ",".join(missing_false_keys))
    if missing_true_keys:
        blockers.append("SAFETY_TRUE_KEY_MISSING:" + ",".join(missing_true_keys))
    if not config_inventory.complete:
        blockers.append("CONFIG_INVENTORY_INCOMPLETE")

    live_real_allowed = bool(config_inventory.safety_false_keys.get("live_real_micro_canary_perform_network_submit"))
    paper_transition_allowed = bool(config_inventory.safety_false_keys.get("paper_transition_operator_approved"))
    exchange_submit_allowed = live_real_allowed
    runtime_overlay_allowed = False

    complete = not blockers and not live_real_allowed and not paper_transition_allowed and not exchange_submit_allowed

    return SafetySnapshot(
        complete=complete,
        live_real_allowed=live_real_allowed,
        paper_transition_allowed=paper_transition_allowed,
        exchange_submit_allowed=exchange_submit_allowed,
        runtime_overlay_allowed=runtime_overlay_allowed,
        trading_action_performed=False,
        training_performed=False,
        reload_performed=False,
        blockers=blockers,
    )


def build_recovery_baseline(root: Path) -> RecoveryBaselineReport:
    generated_at = now_epoch_ms()
    repo_inventory = build_repo_inventory(root)
    phase_inventory = build_phase_inventory(root)
    evidence_inventory = build_evidence_inventory(root)
    config_inventory = build_config_inventory(root)
    safety_snapshot = build_safety_snapshot(config_inventory)

    ready = (
        repo_inventory.complete
        and phase_inventory.complete
        and evidence_inventory.complete
        and config_inventory.complete
        and safety_snapshot.complete
    )

    return RecoveryBaselineReport(
        patch_id=PATCH_ID,
        patch_version=PATCH_VERSION,
        patch_name=PATCH_NAME,
        decision=READY_DECISION if ready else NOT_READY_DECISION,
        status="READY" if ready else "NOT_READY",
        generated_at_epoch_ms=generated_at,
        repo_inventory=repo_inventory,
        phase_inventory=phase_inventory,
        evidence_inventory=evidence_inventory,
        config_inventory=config_inventory,
        safety_snapshot=safety_snapshot,
        approved_for_live_real=False,
        approved_for_paper_transition=False,
        approved_for_exchange_submit=False,
        approved_for_runtime_overlay=False,
    )


def write_report(report: RecoveryBaselineReport, reports_dir: Path) -> Path:
    reports_dir.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime(report.generated_at_epoch_ms / 1000))
    suffix = "ready" if report.status == "READY" else "not_ready"
    path = reports_dir / f"{PATCH_ID}_project_recovery_baseline_{timestamp}_{suffix}.json"
    path.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    return path


def run_project_recovery_baseline(root: Path, reports_dir: Path) -> tuple[RecoveryBaselineReport, Path]:
    report = build_recovery_baseline(root)
    path = write_report(report, reports_dir)
    return report, path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=f"{PATCH_VERSION} {PATCH_NAME}")
    parser.add_argument("--repo-root", default=".", help="Repository root. Defaults to current directory.")
    parser.add_argument("--reports-dir", default="reports/recovery", help="Output report directory.")
    parser.add_argument("--once-json", action="store_true", help="Print compact JSON to stdout.")
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    reports_dir = Path(args.reports_dir)
    if not reports_dir.is_absolute():
        reports_dir = repo_root / reports_dir

    report, report_path = run_project_recovery_baseline(repo_root, reports_dir)
    payload = report.to_dict()
    payload["report_path"] = str(report_path)

    if args.once_json:
        print(json.dumps(payload, sort_keys=True, ensure_ascii=False))
    else:
        print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))

    return 0 if report.status == "READY" else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
