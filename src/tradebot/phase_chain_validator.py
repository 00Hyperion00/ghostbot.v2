from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

PATCH_ID = "4B436633C"
PATCH_VERSION = "4B.4.3.6.6.33C"
PATCH_NAME = "Phase Chain Validator"
READY_DECISION = "PHASE_CHAIN_VALIDATOR_READY_SUBMIT_CAPABILITY_BLOCKED"
NOT_READY_DECISION = "PHASE_CHAIN_VALIDATOR_NOT_READY"

PHASE_TOKEN_PATTERN = re.compile(
    r"4B4366(?P<number>\d{2,3})(?P<letter>[A-Z])(?P<hotfix>(?:[_-]H\d+|[A-Z]\d+)?)",
    re.IGNORECASE,
)
TIMESTAMP_PATTERN = re.compile(r"20\d{6}T\d{6}Z")
STATUS_SUFFIX_PATTERN = re.compile(
    r"_(ready|not_ready|approval_required|execution_evidence_required)\.json$",
    re.IGNORECASE,
)

NOISE_MARKERS: tuple[str, ...] = (
    "__pycache__",
    ".pytest_cache",
    "_patch_backup",
    "_patch_payload",
    "legacy_patches",
)

ARTIFACT_ROOTS: tuple[str, ...] = (
    "tools",
    "tests",
    "docs",
    ".",
)

SAFE_FALSE_FIELDS: tuple[str, ...] = (
    "live_trading_armed",
    "live_real_double_confirm",
    "auto_trade_on_signal",
    "live_real_micro_canary_perform_network_submit",
    "paper_transition_operator_approved",
    "paper_sandbox_candidate_unlock_issued",
    "paper_sandbox_operator_final_approval_issued",
    "paper_sandbox_dry_run_execution_authorization_issued",
    "paper_sandbox_execution_preflight_authorization_issued",
)

SAFE_TRUE_FIELDS: tuple[str, ...] = (
    "strict_config_validation",
    "runtime_lock_enabled",
    "promotion_gate_isolation_enabled",
    "live_real_hard_block_required",
    "live_real_preflight_hard_submit_block_required",
    "live_real_final_hard_submit_block_required",
    "live_real_micro_canary_hard_caps_required",
    "second_micro_canary_submit_gate_no_live_submit_required",
    "paper_mode_runtime_guardrail_no_exchange_submit_required",
    "paper_mode_runtime_guardrail_no_live_real_required",
)

SUBMIT_CAPABILITY_FIELDS: tuple[str, ...] = (
    "execution_mode",
    "market_type",
    "live_trading_armed",
    "live_real_double_confirm",
    "auto_trade_on_signal",
    "live_real_micro_canary_perform_network_submit",
    "live_real_preflight_exchange_submit_cap",
    "live_real_preflight_network_submit_cap",
    "live_real_final_exchange_submit_cap",
    "live_real_final_network_submit_cap",
    "paper_mode_runtime_guardrail_exchange_submit_cap",
    "paper_mode_runtime_guardrail_network_submit_cap",
    "second_micro_canary_submit_gate_no_live_submit_required",
)


def default_required_phase_tokens() -> list[str]:
    tokens: list[str] = []
    for letter in "ABCDE":
        tokens.append(f"4B436629{letter}")
    for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        tokens.append(f"4B436630{letter}")
    for letter in "AB":
        tokens.append(f"4B436631{letter}")
    for letter in "AB":
        tokens.append(f"4B436632{letter}")
    for letter in "AB":
        tokens.append(f"4B436633{letter}")
    return tokens


@dataclass(slots=True)
class ArtifactPresence:
    apply_files: list[str] = field(default_factory=list)
    check_files: list[str] = field(default_factory=list)
    run_files: list[str] = field(default_factory=list)
    rollback_files: list[str] = field(default_factory=list)
    test_files: list[str] = field(default_factory=list)
    doc_files: list[str] = field(default_factory=list)
    readme_apply_files: list[str] = field(default_factory=list)
    report_files: list[str] = field(default_factory=list)
    other_files: list[str] = field(default_factory=list)

    @property
    def operational_count(self) -> int:
        return (
            len(self.apply_files)
            + len(self.check_files)
            + len(self.run_files)
            + len(self.test_files)
            + len(self.doc_files)
            + len(self.readme_apply_files)
            + len(self.report_files)
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ArtifactMatrixRow:
    phase_token: str
    required: bool
    discovered: bool
    artifact_presence: ArtifactPresence
    missing_required_artifacts: list[str]
    warnings: list[str]


@dataclass(slots=True)
class DagNode:
    phase_token: str
    required: bool
    discovered: bool
    has_evidence: bool
    status: str


@dataclass(slots=True)
class DagEdge:
    source: str
    target: str
    relation: str


@dataclass(slots=True)
class PhaseDag:
    complete: bool
    node_count: int
    edge_count: int
    latest_discovered_phase_token: str | None
    required_phase_count: int
    required_missing_count: int
    forward_phase_count: int
    forward_phase_tokens: list[str]
    nodes: list[DagNode]
    edges: list[DagEdge]


@dataclass(slots=True)
class EvidenceRecord:
    path: str
    phase_token: str | None
    status: str
    status_source: str
    timestamp_token: str | None
    modified_epoch_ms: int
    sha256: str | None
    parse_error: str | None = None


@dataclass(slots=True)
class EvidenceResolutionRecord:
    phase_token: str
    selected_evidence: EvidenceRecord | None
    candidate_count: int
    missing: bool
    warnings: list[str]


@dataclass(slots=True)
class EvidenceSourceResolution:
    complete: bool
    source_33b_report: str | None
    total_report_count: int
    resolved_required_count: int
    missing_required_count: int
    malformed_count: int
    unknown_count: int
    status_conflict_count: int
    records: list[EvidenceResolutionRecord]


@dataclass(slots=True)
class SubmitCapabilityAssertion:
    passed: bool
    approved_for_live_real: bool
    approved_for_paper_transition: bool
    approved_for_exchange_submit: bool
    approved_for_runtime_overlay: bool
    live_real_submit_allowed: bool
    paper_submit_allowed: bool
    network_submit_allowed: bool
    exchange_submit_allowed: bool
    runtime_overlay_allowed: bool
    execution_mode: str | None
    market_type: str | None
    checked_fields: dict[str, Any]
    violations: list[str]


@dataclass(slots=True)
class PhaseChainValidatorSafetySnapshot:
    trading_action_performed: bool
    training_performed: bool
    reload_performed: bool
    runtime_overlay_activated: bool
    exchange_submit_performed: bool


@dataclass(slots=True)
class PhaseChainValidatorReport:
    patch_id: str
    patch_version: str
    patch_name: str
    decision: str
    status: str
    generated_at_epoch_ms: int
    canonical_phase_dag: PhaseDag
    required_artifact_matrix: list[ArtifactMatrixRow]
    evidence_source_resolution: EvidenceSourceResolution
    submit_capability_assertion: SubmitCapabilityAssertion
    safety_snapshot: PhaseChainValidatorSafetySnapshot
    recommended_next_phase: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# -----------------------------
# Basic helpers
# -----------------------------

def now_epoch_ms() -> int:
    return int(time.time() * 1000)


def safe_relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def normalize_phase_token(token: str | None) -> str | None:
    if not token:
        return None
    return token.upper().replace("-", "_")


def extract_phase_token(text: str) -> str | None:
    match = PHASE_TOKEN_PATTERN.search(text.upper().replace("-", "_"))
    if not match:
        return None
    token = match.group(0).upper().replace("-", "_")
    return token


def phase_sort_key(token: str) -> tuple[int, int, int, int, str]:
    token = token.upper().replace("-", "_")
    match = PHASE_TOKEN_PATTERN.search(token)
    if not match:
        return (9999, 9999, 9999, 9999, token)
    number = int(match.group("number"))
    letter = ord(match.group("letter")) - ord("A")
    hotfix = match.group("hotfix") or ""
    hotfix_rank = 0
    if hotfix.startswith("_H"):
        try:
            hotfix_rank = int(hotfix[2:])
        except ValueError:
            hotfix_rank = 999
    elif hotfix:
        hotfix_rank = 500
    return (number, letter, hotfix_rank, len(token), token)


def base_phase_token(token: str) -> str:
    token = token.upper().replace("-", "_")
    return re.sub(r"_H\d+$", "", token)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iter_project_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if path.is_dir():
            continue
        rel = safe_relative(path, root)
        parts = set(Path(rel).parts)
        if parts.intersection(NOISE_MARKERS):
            continue
        yield path


def read_json_object(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:  # noqa: BLE001 - evidence scanners must not crash the gate
        return None, f"{type(exc).__name__}: {exc}"
    if not isinstance(payload, dict):
        return None, "JSON root is not an object"
    return payload, None


def classify_status_from_payload(payload: Mapping[str, Any]) -> str | None:
    for key in ("status", "decision", "baseline_status", "baseline_decision", "result"):
        value = payload.get(key)
        if isinstance(value, str):
            lowered = value.lower()
            if "execution_evidence_required" in lowered:
                return "execution_evidence_required"
            if "approval_required" in lowered or "operator_required" in lowered or "authorization_required" in lowered:
                return "approval_required"
            if "not_ready" in lowered or "blocked" in lowered or "fail" in lowered:
                return "not_ready"
            if "ready" in lowered or "pass" in lowered or "accepted" in lowered:
                return "ready"
    for key in ("ok", "complete", "ready"):
        value = payload.get(key)
        if value is True:
            return "ready"
        if value is False:
            return "not_ready"
    return None


def classify_report_status(path: Path, payload: Mapping[str, Any] | None, parse_error: str | None) -> tuple[str, str, bool]:
    if parse_error:
        return "malformed_json", "json_parse_error", False

    suffix_match = STATUS_SUFFIX_PATTERN.search(path.name)
    payload_status = classify_status_from_payload(payload or {})
    if suffix_match:
        suffix_status = suffix_match.group(1).lower()
        if payload_status and payload_status != suffix_status:
            return suffix_status, f"filename_suffix_over_payload_{payload_status}", True
        return suffix_status, "filename_suffix", False

    lower_name = path.name.lower()
    if "manifest" in lower_name:
        return "manifest", "filename_token", False
    if "snapshot" in lower_name:
        return "snapshot", "filename_token", False
    if payload_status:
        return payload_status, "json_payload", False
    return "unknown", "unclassified", False


def timestamp_token_for(path: Path) -> str | None:
    match = TIMESTAMP_PATTERN.search(path.name)
    return match.group(0) if match else None


# -----------------------------
# Artifact matrix
# -----------------------------

def add_artifact(record: ArtifactPresence, rel: str) -> None:
    name = Path(rel).name.lower()
    parent = Path(rel).parent.as_posix().lower()
    if name.startswith("apply_") and name.endswith(".py"):
        record.apply_files.append(rel)
    elif name.startswith("check_") and name.endswith(".py"):
        record.check_files.append(rel)
    elif name.startswith("run_") and name.endswith(".py"):
        record.run_files.append(rel)
    elif name.startswith("rollback_") and name.endswith(".py"):
        record.rollback_files.append(rel)
    elif parent == "tests" and name.startswith("test_") and name.endswith(".py"):
        record.test_files.append(rel)
    elif parent == "docs" and name.endswith((".md", ".txt")):
        record.doc_files.append(rel)
    elif name.startswith("readme_apply_") and name.endswith(".txt"):
        record.readme_apply_files.append(rel)
    elif rel.startswith("reports/") and name.endswith(".json"):
        record.report_files.append(rel)
    else:
        record.other_files.append(rel)


def collect_artifact_matrix(root: Path, required_tokens: Sequence[str]) -> tuple[list[ArtifactMatrixRow], dict[str, ArtifactPresence]]:
    required_set = {normalize_phase_token(t) for t in required_tokens}
    artifacts_by_phase: dict[str, ArtifactPresence] = {t: ArtifactPresence() for t in required_set if t}

    for path in iter_project_files(root):
        rel = safe_relative(path, root)
        token = extract_phase_token(rel)
        if not token:
            continue
        artifacts_by_phase.setdefault(token, ArtifactPresence())
        add_artifact(artifacts_by_phase[token], rel)

    rows: list[ArtifactMatrixRow] = []
    for token in sorted(artifacts_by_phase, key=phase_sort_key):
        presence = artifacts_by_phase[token]
        required = token in required_set
        missing: list[str] = []
        warnings: list[str] = []

        if required and presence.operational_count == 0:
            missing.append("any_operational_artifact")
        if required and not presence.report_files:
            warnings.append("no_report_evidence_found")
        if required and not (presence.apply_files or presence.check_files or presence.run_files):
            warnings.append("no_apply_check_or_run_script_found")
        if required and not presence.test_files:
            warnings.append("no_test_file_found")
        if required and not presence.doc_files:
            warnings.append("no_doc_file_found")

        rows.append(
            ArtifactMatrixRow(
                phase_token=token,
                required=required,
                discovered=presence.operational_count > 0 or bool(presence.other_files),
                artifact_presence=presence,
                missing_required_artifacts=missing,
                warnings=warnings,
            )
        )
    return rows, artifacts_by_phase


# -----------------------------
# Evidence resolution
# -----------------------------

def scan_evidence_records(root: Path) -> tuple[list[EvidenceRecord], int, int, int]:
    reports_dir = root / "reports"
    records: list[EvidenceRecord] = []
    malformed = 0
    unknown = 0
    conflicts = 0
    if not reports_dir.exists():
        return records, malformed, unknown, conflicts

    for path in reports_dir.rglob("*.json"):
        rel = safe_relative(path, root)
        parts = set(Path(rel).parts)
        if parts.intersection(NOISE_MARKERS):
            continue
        payload, parse_error = read_json_object(path)
        status, source, conflict = classify_report_status(path, payload, parse_error)
        if status == "malformed_json":
            malformed += 1
        if status == "unknown":
            unknown += 1
        if conflict:
            conflicts += 1
        records.append(
            EvidenceRecord(
                path=rel,
                phase_token=extract_phase_token(rel),
                status=status,
                status_source=source,
                timestamp_token=timestamp_token_for(path),
                modified_epoch_ms=int(path.stat().st_mtime * 1000),
                sha256=None if parse_error else file_sha256(path),
                parse_error=parse_error,
            )
        )
    return records, malformed, unknown, conflicts


def status_rank(status: str) -> int:
    return {
        "ready": 100,
        "not_ready": 90,
        "approval_required": 80,
        "execution_evidence_required": 70,
        "snapshot": 50,
        "manifest": 40,
        "unknown": 10,
        "malformed_json": 0,
    }.get(status, 0)


def evidence_sort_key(record: EvidenceRecord) -> tuple[int, int, str]:
    return (status_rank(record.status), record.modified_epoch_ms, record.path)


def find_latest_33b_report(root: Path) -> str | None:
    reports_dir = root / "reports" / "recovery"
    if not reports_dir.exists():
        return None
    candidates = sorted(
        reports_dir.glob("4B436633B_canonical_evidence_phase_hygiene_*_ready.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if candidates:
        return safe_relative(candidates[0], root)
    return None


def build_evidence_source_resolution(root: Path, required_tokens: Sequence[str]) -> EvidenceSourceResolution:
    all_records, malformed_count, unknown_count, conflict_count = scan_evidence_records(root)
    source_33b = find_latest_33b_report(root)
    records_by_token: dict[str, list[EvidenceRecord]] = {}
    for record in all_records:
        if not record.phase_token:
            continue
        records_by_token.setdefault(record.phase_token, []).append(record)

    resolution_records: list[EvidenceResolutionRecord] = []
    missing_count = 0
    resolved_count = 0
    for token in required_tokens:
        token = normalize_phase_token(token) or token
        candidates = records_by_token.get(token, [])
        selected = sorted(candidates, key=evidence_sort_key, reverse=True)[0] if candidates else None
        warnings: list[str] = []
        if not selected:
            missing_count += 1
            warnings.append("missing_required_phase_evidence")
        else:
            resolved_count += 1
            if selected.status != "ready":
                warnings.append(f"selected_evidence_status_{selected.status}")
        resolution_records.append(
            EvidenceResolutionRecord(
                phase_token=token,
                selected_evidence=selected,
                candidate_count=len(candidates),
                missing=selected is None,
                warnings=warnings,
            )
        )

    complete = source_33b is not None and missing_count == 0
    return EvidenceSourceResolution(
        complete=complete,
        source_33b_report=source_33b,
        total_report_count=len(all_records),
        resolved_required_count=resolved_count,
        missing_required_count=missing_count,
        malformed_count=malformed_count,
        unknown_count=unknown_count,
        status_conflict_count=conflict_count,
        records=resolution_records,
    )


# -----------------------------
# DAG
# -----------------------------

def build_phase_dag(
    required_tokens: Sequence[str],
    artifact_rows: Sequence[ArtifactMatrixRow],
    evidence_resolution: EvidenceSourceResolution,
) -> PhaseDag:
    required_set = {normalize_phase_token(t) for t in required_tokens}
    discovered_set = {row.phase_token for row in artifact_rows if row.discovered}
    evidence_tokens = {record.phase_token for record in evidence_resolution.records if record.selected_evidence is not None}
    all_tokens = sorted({t for t in required_set.union(discovered_set) if t}, key=phase_sort_key)

    latest = all_tokens[-1] if all_tokens else None
    required_missing = sorted([t for t in required_set if t not in discovered_set and t not in evidence_tokens], key=phase_sort_key)
    required_max = max((phase_sort_key(t) for t in required_set if t), default=(0, 0, 0, 0, ""))
    forward_tokens = sorted(
        [t for t in all_tokens if phase_sort_key(t) > required_max and t not in required_set],
        key=phase_sort_key,
    )

    status_by_token: dict[str, str] = {}
    for record in evidence_resolution.records:
        if record.selected_evidence is not None:
            status_by_token[record.phase_token] = record.selected_evidence.status

    nodes = [
        DagNode(
            phase_token=token,
            required=token in required_set,
            discovered=token in discovered_set,
            has_evidence=token in evidence_tokens,
            status=status_by_token.get(token, "unknown"),
        )
        for token in all_tokens
    ]

    edges: list[DagEdge] = []
    required_sorted = sorted([t for t in required_set if t], key=phase_sort_key)
    for source, target in zip(required_sorted, required_sorted[1:]):
        edges.append(DagEdge(source=source, target=target, relation="required_serial_predecessor"))
    for token in all_tokens:
        parent = base_phase_token(token)
        if parent != token and parent in all_tokens:
            edges.append(DagEdge(source=parent, target=token, relation="hotfix_parent"))

    complete = len(required_missing) == 0 and bool(required_sorted)
    return PhaseDag(
        complete=complete,
        node_count=len(nodes),
        edge_count=len(edges),
        latest_discovered_phase_token=latest,
        required_phase_count=len(required_set),
        required_missing_count=len(required_missing),
        forward_phase_count=len(forward_tokens),
        forward_phase_tokens=forward_tokens[:50],
        nodes=nodes,
        edges=edges,
    )


# -----------------------------
# Config / submit capability assertion
# -----------------------------

def settings_to_dict(settings: Any) -> dict[str, Any]:
    if hasattr(settings, "to_dict"):
        try:
            return dict(settings.to_dict(include_secrets=False))
        except TypeError:
            return dict(settings.to_dict())
    if hasattr(settings, "__dict__"):
        return dict(settings.__dict__)
    return {}


def load_settings_snapshot(root: Path) -> dict[str, Any]:
    src = root / "src"
    original_sys_path = list(sys.path)
    try:
        if src.exists():
            sys.path.insert(0, str(src))
        module = importlib.import_module("tradebot.config")
        settings_cls = getattr(module, "Settings")
        return settings_to_dict(settings_cls())
    except Exception:  # noqa: BLE001 - fallback scanner must not crash the safety gate
        return {}
    finally:
        sys.path[:] = original_sys_path


def build_submit_capability_assertion(root: Path) -> SubmitCapabilityAssertion:
    settings = load_settings_snapshot(root)
    checked = {key: settings.get(key) for key in SUBMIT_CAPABILITY_FIELDS if key in settings}
    violations: list[str] = []

    for key in SAFE_FALSE_FIELDS:
        value = settings.get(key)
        if value is True:
            violations.append(f"{key}=true")

    for key in SAFE_TRUE_FIELDS:
        value = settings.get(key)
        if value is False:
            violations.append(f"{key}=false")

    execution_mode = settings.get("execution_mode")
    market_type = settings.get("market_type")

    live_real_submit_allowed = bool(
        settings.get("live_trading_armed")
        or settings.get("live_real_double_confirm")
        or settings.get("live_real_micro_canary_perform_network_submit")
    )
    paper_submit_allowed = bool(
        settings.get("paper_transition_operator_approved")
        or settings.get("paper_sandbox_candidate_unlock_issued")
        or settings.get("paper_sandbox_operator_final_approval_issued")
    )
    network_submit_allowed = bool(
        settings.get("live_real_micro_canary_perform_network_submit")
        or int(settings.get("live_real_preflight_network_submit_cap") or 0) > 0 and not settings.get("live_real_preflight_hard_submit_block_required", True)
        or int(settings.get("live_real_final_network_submit_cap") or 0) > 0 and not settings.get("live_real_final_hard_submit_block_required", True)
    )
    exchange_submit_allowed = bool(
        settings.get("auto_trade_on_signal")
        or int(settings.get("paper_mode_runtime_guardrail_exchange_submit_cap") or 0) > 0 and not settings.get("paper_mode_runtime_guardrail_no_exchange_submit_required", True)
        or int(settings.get("live_real_final_exchange_submit_cap") or 0) > 0 and not settings.get("live_real_final_hard_submit_block_required", True)
    )
    runtime_overlay_allowed = bool(settings.get("runtime_overlay_activation_candidate") or False)

    if execution_mode not in (None, "dry_run", "DRY_RUN"):
        violations.append(f"execution_mode={execution_mode!r}")
    if live_real_submit_allowed:
        violations.append("live_real_submit_allowed")
    if network_submit_allowed:
        violations.append("network_submit_allowed")
    if exchange_submit_allowed:
        violations.append("exchange_submit_allowed")
    if runtime_overlay_allowed:
        violations.append("runtime_overlay_allowed")

    passed = not violations
    return SubmitCapabilityAssertion(
        passed=passed,
        approved_for_live_real=False,
        approved_for_paper_transition=False,
        approved_for_exchange_submit=False,
        approved_for_runtime_overlay=False,
        live_real_submit_allowed=live_real_submit_allowed,
        paper_submit_allowed=paper_submit_allowed,
        network_submit_allowed=network_submit_allowed,
        exchange_submit_allowed=exchange_submit_allowed,
        runtime_overlay_allowed=runtime_overlay_allowed,
        execution_mode=str(execution_mode) if execution_mode is not None else None,
        market_type=str(market_type) if market_type is not None else None,
        checked_fields=checked,
        violations=violations,
    )


# -----------------------------
# Public builder / writer
# -----------------------------

def build_phase_chain_validator_report(
    repo_root: str | Path = ".",
    *,
    required_phase_tokens: Sequence[str] | None = None,
) -> PhaseChainValidatorReport:
    root = Path(repo_root).resolve()
    required_tokens = list(required_phase_tokens or default_required_phase_tokens())
    required_tokens = [normalize_phase_token(t) or t for t in required_tokens]

    matrix, _ = collect_artifact_matrix(root, required_tokens)
    evidence_resolution = build_evidence_source_resolution(root, required_tokens)
    dag = build_phase_dag(required_tokens, matrix, evidence_resolution)
    submit_assertion = build_submit_capability_assertion(root)
    safety_snapshot = PhaseChainValidatorSafetySnapshot(
        trading_action_performed=False,
        training_performed=False,
        reload_performed=False,
        runtime_overlay_activated=False,
        exchange_submit_performed=False,
    )

    critical_missing = [row.phase_token for row in matrix if row.required and row.missing_required_artifacts]
    artifact_matrix_complete = len(critical_missing) == 0
    status = "READY" if dag.complete and artifact_matrix_complete and evidence_resolution.complete and submit_assertion.passed else "NOT_READY"
    decision = READY_DECISION if status == "READY" else NOT_READY_DECISION

    return PhaseChainValidatorReport(
        patch_id=PATCH_ID,
        patch_version=PATCH_VERSION,
        patch_name=PATCH_NAME,
        decision=decision,
        status=status,
        generated_at_epoch_ms=now_epoch_ms(),
        canonical_phase_dag=dag,
        required_artifact_matrix=list(matrix),
        evidence_source_resolution=evidence_resolution,
        submit_capability_assertion=submit_assertion,
        safety_snapshot=safety_snapshot,
        recommended_next_phase="4B.4.3.6.6.33D Runtime Safety Lockdown" if status == "READY" else "Resolve 33C blockers before 33D",
    )


def utc_timestamp() -> str:
    return time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())


def write_phase_chain_validator_report(
    repo_root: str | Path = ".",
    *,
    reports_dir: str | Path | None = None,
    required_phase_tokens: Sequence[str] | None = None,
) -> Path:
    root = Path(repo_root).resolve()
    report = build_phase_chain_validator_report(root, required_phase_tokens=required_phase_tokens)
    out_dir = Path(reports_dir).resolve() if reports_dir else root / "reports" / "recovery"
    out_dir.mkdir(parents=True, exist_ok=True)
    suffix = "ready" if report.status == "READY" else "not_ready"
    out_path = out_dir / f"{PATCH_ID}_phase_chain_validator_{utc_timestamp()}_{suffix}.json"
    out_path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return out_path


def summarize_report(report: PhaseChainValidatorReport) -> dict[str, Any]:
    return {
        "ok": report.status == "READY",
        "patch_id": report.patch_id,
        "patch_version": report.patch_version,
        "check_name": "phase_chain_validator",
        "status": report.status,
        "decision": report.decision,
        "canonical_dag_complete": report.canonical_phase_dag.complete,
        "required_phase_count": report.canonical_phase_dag.required_phase_count,
        "required_missing_count": report.canonical_phase_dag.required_missing_count,
        "node_count": report.canonical_phase_dag.node_count,
        "edge_count": report.canonical_phase_dag.edge_count,
        "latest_discovered_phase_token": report.canonical_phase_dag.latest_discovered_phase_token,
        "forward_phase_count": report.canonical_phase_dag.forward_phase_count,
        "evidence_resolution_complete": report.evidence_source_resolution.complete,
        "source_33b_report": report.evidence_source_resolution.source_33b_report,
        "missing_required_evidence_count": report.evidence_source_resolution.missing_required_count,
        "total_report_count": report.evidence_source_resolution.total_report_count,
        "malformed_count": report.evidence_source_resolution.malformed_count,
        "unknown_count": report.evidence_source_resolution.unknown_count,
        "status_conflict_count": report.evidence_source_resolution.status_conflict_count,
        "submit_capability_assertion_passed": report.submit_capability_assertion.passed,
        "approved_for_live_real": report.submit_capability_assertion.approved_for_live_real,
        "approved_for_paper_transition": report.submit_capability_assertion.approved_for_paper_transition,
        "approved_for_exchange_submit": report.submit_capability_assertion.approved_for_exchange_submit,
        "approved_for_runtime_overlay": report.submit_capability_assertion.approved_for_runtime_overlay,
        "live_real_submit_allowed": report.submit_capability_assertion.live_real_submit_allowed,
        "paper_submit_allowed": report.submit_capability_assertion.paper_submit_allowed,
        "network_submit_allowed": report.submit_capability_assertion.network_submit_allowed,
        "exchange_submit_allowed": report.submit_capability_assertion.exchange_submit_allowed,
        "runtime_overlay_allowed": report.submit_capability_assertion.runtime_overlay_allowed,
        "submit_violations": report.submit_capability_assertion.violations,
        "trading_action_performed": report.safety_snapshot.trading_action_performed,
        "training_performed": report.safety_snapshot.training_performed,
        "reload_performed": report.safety_snapshot.reload_performed,
        "runtime_overlay_activated": report.safety_snapshot.runtime_overlay_activated,
        "exchange_submit_performed": report.safety_snapshot.exchange_submit_performed,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=PATCH_NAME)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--reports-dir", default=None)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args(argv)

    if args.write:
        path = write_phase_chain_validator_report(args.repo_root, reports_dir=args.reports_dir)
        report = build_phase_chain_validator_report(args.repo_root)
        summary = summarize_report(report)
        summary["report_path"] = str(path)
    else:
        report = build_phase_chain_validator_report(args.repo_root)
        summary = summarize_report(report)

    if args.once_json:
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    else:
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if summary.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
