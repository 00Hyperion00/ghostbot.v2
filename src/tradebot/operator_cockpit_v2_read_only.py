from __future__ import annotations

import errno
import hashlib
import io
import json
import math
import os
import platform
import statistics
import subprocess
import urllib.error
import urllib.request
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence
from urllib.parse import urlparse

from .hyp005_r1_canonical_epoch_contract import (
    CANONICAL_R1_REPORTS_DIR,
    CANONICAL_R1_TASK_NAME,
    LEGACY_R1_REPORTS_DIR,
    LEGACY_R1_TASK_NAME,
    resolve_active_reports_dir,
)
from .risk_sizing_runtime_telemetry import (
    RISK_SIZING_EVIDENCE_EXPORT_FAIL_CLOSED,
    RISK_SIZING_OPERATOR_COCKPIT_AUDIT_PARITY,
    RISK_SIZING_RUNTIME_TELEMETRY_ENABLED,
    RISK_SIZING_RUNTIME_TELEMETRY_VERSION,
    RiskSizingEvidenceExportBlocked,
    assert_risk_sizing_evidence_export_ready,
    collect_risk_sizing_runtime_telemetry,
)

try:
    from .operator_cockpit_hyp006_binding import (
        OPERATOR_COCKPIT_HYP006_BINDING_VERSION,
        apply_hyp006_operator_cockpit_binding,
    )
except Exception:  # pragma: no cover - fail-closed legacy fallback
    OPERATOR_COCKPIT_HYP006_BINDING_VERSION = "UNAVAILABLE"

    def apply_hyp006_operator_cockpit_binding(snapshot: Mapping[str, Any], project_root: Path) -> dict[str, Any]:
        return dict(snapshot)

OPERATOR_COCKPIT_V2_CONTRACT_VERSION = "4B.4.3.6.6.26A"
OPERATOR_COCKPIT_V2_READ_ONLY = True
OPERATOR_COCKPIT_V2_VISUAL_UX_FOUNDATION = True
OPERATOR_COCKPIT_V2_HYP005_R1_AUDIT_INTEGRATION = True
OPERATOR_COCKPIT_V2_VISUALIZATION_PACK_VERSION = "4B.4.3.6.6.26B"
OPERATOR_COCKPIT_V2_SHADOW_AUDIT_VISUALIZATION_PACK = True
OPERATOR_COCKPIT_V2_SELF_CONTAINED_CHARTS = True
OPERATOR_COCKPIT_V2_MAE_MFE_SCATTER_HOTFIX_VERSION = "4B.4.3.6.6.26B-H1"
OPERATOR_COCKPIT_V2_SIGNED_MAE_MFE_DOMAIN = True
OPERATOR_COCKPIT_V2_ACCURATE_MAE_MFE_EMPTY_STATE = True
OPERATOR_COCKPIT_V2_WINDOWS_UTF8_CLIENT_DISCONNECT_HOTFIX_VERSION = "4B.4.3.6.6.26B-H2"
OPERATOR_COCKPIT_V2_WINDOWS_UTF8_EMPTY_STATE_ASSERTION = True
OPERATOR_COCKPIT_V2_CLIENT_DISCONNECT_NOISE_SUPPRESSION = True
OPERATOR_COCKPIT_V2_WINDOWS_MUTATION_BODY_DRAIN_HOTFIX_VERSION = "4B.4.3.6.6.26B-H3"
OPERATOR_COCKPIT_V2_MUTATION_REQUEST_BODY_DRAIN = True
OPERATOR_COCKPIT_V2_HTTP_405_CONTRACT_PRESERVATION = True
MAX_MUTATION_REQUEST_BODY_DRAIN_BYTES = 64 * 1024
OPERATOR_COCKPIT_V2_SAFE_ACTIONS_VERSION = "4B.4.3.6.6.26C"
OPERATOR_COCKPIT_V2_SAFE_OPERATOR_ACTIONS = True
OPERATOR_COCKPIT_V2_GET_ONLY_ACTIONS = True
OPERATOR_COCKPIT_V2_IN_MEMORY_EXPORTS_ONLY = True
MAX_OPERATOR_COCKPIT_EXPORT_FILE_BYTES = 5 * 1024 * 1024
MAX_OPERATOR_COCKPIT_EVIDENCE_PACK_BYTES = 12 * 1024 * 1024
OPERATOR_COCKPIT_V2_NO_CONFIG_MUTATION = True
OPERATOR_COCKPIT_V2_NO_SCHEDULER_MUTATION = True
OPERATOR_COCKPIT_V2_NO_TRADING_ACTION = True
OPERATOR_COCKPIT_V2_CANONICAL_EPOCH_HARDENING_VERSION = "4B.4.3.6.6.25AE-H5"
OPERATOR_COCKPIT_V2_CANONICAL_SOURCE_PREFERRED_WITH_LEGACY_FALLBACK = True
OPERATOR_COCKPIT_V2_RISK_SIZING_TELEMETRY_VERSION = RISK_SIZING_RUNTIME_TELEMETRY_VERSION
OPERATOR_COCKPIT_V2_RISK_SIZING_RUNTIME_TELEMETRY = RISK_SIZING_RUNTIME_TELEMETRY_ENABLED
OPERATOR_COCKPIT_V2_RISK_SIZING_AUDIT_PARITY = RISK_SIZING_OPERATOR_COCKPIT_AUDIT_PARITY
OPERATOR_COCKPIT_V2_RISK_SIZING_EVIDENCE_EXPORT_FAIL_CLOSED = RISK_SIZING_EVIDENCE_EXPORT_FAIL_CLOSED

DEFAULT_R1_REPORTS_DIR = LEGACY_R1_REPORTS_DIR
BASELINE_TASK_NAME = "TradeBot_HYP005_NoOrderShadowCollection"
R1_TASK_NAME = LEGACY_R1_TASK_NAME
DEFAULT_BACKEND_HEALTH_URL = "http://127.0.0.1:8000/health"

SAFE_EXPORT_SOURCE_PATTERNS: dict[str, tuple[str, str, str]] = {
    "logger": ("4B436625V_hyp005_shadow_observation_logger_*.json", "latest-25v-logger.json", "application/json; charset=utf-8"),
    "collection": ("4B436625X_hyp005_shadow_collection_orchestrator_*.json", "latest-25x-collection.json", "application/json; charset=utf-8"),
    "audit": ("4B436625Y_hyp005_shadow_operator_daily_audit_*.json", "latest-25y-audit.json", "application/json; charset=utf-8"),
    "ledger": ("4B436625X_hyp005_shadow_merged_ledger_*.jsonl", "latest-merged-ledger.jsonl", "application/x-ndjson; charset=utf-8"),
}

JsonObject = dict[str, Any]
TaskQuery = Callable[[str], Mapping[str, Any]]
BackendProbe = Callable[[str], Mapping[str, Any]]


@dataclass(frozen=True)
class SnapshotSource:
    latest_25v_logger: str | None
    latest_25x_collection: str | None
    latest_25y_audit: str | None
    latest_merged_ledger: str | None
    r1_reports_dir: str


@dataclass(frozen=True)
class PerformanceSummary:
    sample_count: int
    matured_count: int
    maturity_pending_count: int
    win_count: int
    loss_count: int
    win_rate_pct: float | None
    gross_profit_bps: float
    gross_loss_bps: float
    net_return_bps: float
    mean_return_bps: float | None
    median_return_bps: float | None
    profit_factor: float | None
    worst_return_bps: float | None
    best_return_bps: float | None


@dataclass(frozen=True)
class TimestampClusterSummary:
    timestamp_utc: str | None
    sample_count: int
    symbols: list[str]
    net_return_bps: float
    mean_return_bps: float | None
    gross_loss_share_pct: float | None


@dataclass(frozen=True)
class ModelSummary:
    status: str
    file_name: str | None
    relative_path: str | None
    sha256: str | None
    size_bytes: int | None
    modified_utc: str | None


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _round(value: float | None, digits: int = 6) -> float | None:
    if value is None or not math.isfinite(value):
        return None
    return round(value, digits)


def _as_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _as_int(value: Any, default: int = 0) -> int:
    if value in (None, ""):
        return default
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "ready", "enabled"}:
            return True
        if lowered in {"false", "0", "no", "disabled", "blocked"}:
            return False
    if value is None:
        return default
    return bool(value)


def _read_json(path: Path | None) -> JsonObject:
    if path is None or not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_jsonl(path: Path | None) -> list[JsonObject]:
    if path is None or not path.exists():
        return []
    rows: list[JsonObject] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return rows
    for line in lines:
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def _latest_file(directory: Path, pattern: str) -> Path | None:
    if not directory.exists():
        return None
    matches = [path for path in directory.glob(pattern) if path.is_file()]
    if not matches:
        return None
    return max(matches, key=lambda path: (path.stat().st_mtime_ns, path.name))


def _safe_latest_export_source(project_root: Path, kind: str) -> Path | None:
    """Resolve only a fixed, allowlisted isolated-R1 report source."""
    spec = SAFE_EXPORT_SOURCE_PATTERNS.get(kind)
    if spec is None:
        return None
    reports_dir = resolve_active_reports_dir(project_root)
    latest = _latest_file(reports_dir, spec[0])
    if latest is None:
        return None
    resolved = latest.resolve()
    try:
        resolved.relative_to(reports_dir)
    except ValueError:
        return None
    return resolved


def _read_bounded_export_bytes(path: Path, *, max_bytes: int = MAX_OPERATOR_COCKPIT_EXPORT_FILE_BYTES) -> bytes:
    """Read an allowlisted export source without permitting unbounded memory use."""
    size = path.stat().st_size
    if size > max_bytes:
        raise ValueError("OPERATOR_COCKPIT_EXPORT_FILE_TOO_LARGE")
    return path.read_bytes()


def _safe_action_manifest(project_root: Path) -> JsonObject:
    """Describe safe GET-only actions and visibly locked control-plane operations."""
    root = project_root.resolve()
    telemetry = collect_risk_sizing_runtime_telemetry(root)
    exports: list[JsonObject] = []
    for kind, (_, download_name, content_type) in SAFE_EXPORT_SOURCE_PATTERNS.items():
        source = _safe_latest_export_source(root, kind)
        exports.append({
            "kind": kind,
            "available": source is not None,
            "download_name": download_name,
            "content_type": content_type,
            "source": _relative_or_name(source, root),
            "endpoint": f"/api/operator-cockpit-v2/export/latest-{kind}",
        })
    return {
        "version": OPERATOR_COCKPIT_V2_SAFE_ACTIONS_VERSION,
        "read_only": True,
        "get_only": True,
        "in_memory_exports_only": True,
        "enabled": [
            {"code": "REFRESH_SNAPSHOT", "label": "Snapshot yenile", "endpoint": "/api/operator-cockpit-v2/snapshot"},
            {"code": "RECHECK_BACKEND_HEALTH", "label": "Backend probe tekrarla", "endpoint": "/api/operator-cockpit-v2/actions/backend-probe"},
            {"code": "OPEN_ACTION_MANIFEST", "label": "Kaynak manifestini aç", "endpoint": "/api/operator-cockpit-v2/actions/manifest"},
            {"code": "DOWNLOAD_SNAPSHOT_JSON", "label": "Snapshot JSON indir", "endpoint": "/api/operator-cockpit-v2/export/snapshot.json"},
            {"code": "OPEN_LATEST_AUDIT_JSON", "label": "Son audit JSON aç", "endpoint": "/api/operator-cockpit-v2/view/latest-audit.json"},
            {"code": "DOWNLOAD_EVIDENCE_PACK_ZIP", "label": "Evidence pack indir", "endpoint": "/api/operator-cockpit-v2/export/evidence-pack.zip"},
            {"code": "OPEN_RISK_SIZING_RUNTIME_TELEMETRY_JSON", "label": "Risk-sizing telemetry JSON aç", "endpoint": "/api/operator-cockpit-v2/view/risk-sizing-runtime-telemetry.json"},
            {"code": "DOWNLOAD_RISK_SIZING_EVIDENCE_PACK_ZIP", "label": "Risk-sizing evidence pack indir", "endpoint": "/api/operator-cockpit-v2/export/risk-sizing-evidence-pack.zip", "available": telemetry["export_ready"]},
        ],
        "locked": [
            {"code": "EMERGENCY_STOP", "label": "Emergency stop", "reason": "Control-plane entegrasyonu ve ayrı risk incelemesi bekleniyor."},
            {"code": "PAPER_MODE_ENABLE", "label": "Paper mode aç", "reason": "Shadow acceptance gate onayı gerekli."},
            {"code": "LIVE_MODE_ENABLE", "label": "Live mode aç", "reason": "Paper acceptance ve canlı risk incelemesi gerekli."},
            {"code": "MODEL_RELOAD", "label": "Model reload", "reason": "Read-only cockpit model state değiştirmez."},
            {"code": "SCHEDULER_MUTATION", "label": "Scheduler değiştir", "reason": "Scheduler mutation bakım prosedürüne ayrılmıştır."},
            {"code": "SYMBOL_SET_MUTATION", "label": "Sembol seti değiştir", "reason": "Branch gate kararı ve ayrı patch gerektirir."},
        ],
        "exports": exports,
        "risk_sizing_evidence_export_gate": {
            "contract_version": telemetry["contract_version"],
            "available": telemetry["export_ready"],
            "fail_closed": True,
            "blockers": telemetry["export_blockers"],
        },
    }


def _build_in_memory_evidence_pack(
    project_root: Path,
    *,
    task_query: TaskQuery | None = None,
    backend_probe: BackendProbe | None = None,
) -> bytes:
    """Build a bounded evidence ZIP in memory; never write export artifacts to disk."""
    root = project_root.resolve()
    snapshot = collect_operator_cockpit_snapshot(root, task_query=task_query, backend_probe=backend_probe)
    manifest = _safe_action_manifest(root)
    output = io.BytesIO()
    source_total = 0
    with zipfile.ZipFile(output, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("operator-cockpit/snapshot.json", json.dumps(snapshot, ensure_ascii=False, indent=2).encode("utf-8"))
        archive.writestr("operator-cockpit/safe-actions-manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8"))
        for kind, (_, download_name, _) in SAFE_EXPORT_SOURCE_PATTERNS.items():
            source = _safe_latest_export_source(root, kind)
            if source is None:
                continue
            payload = _read_bounded_export_bytes(source)
            source_total += len(payload)
            if source_total > MAX_OPERATOR_COCKPIT_EVIDENCE_PACK_BYTES:
                raise ValueError("OPERATOR_COCKPIT_EVIDENCE_PACK_TOO_LARGE")
            archive.writestr(f"operator-cockpit/sources/{download_name}", payload)
    return output.getvalue()


def _build_risk_sizing_in_memory_evidence_pack(
    project_root: Path,
    *,
    task_query: TaskQuery | None = None,
    backend_probe: BackendProbe | None = None,
) -> bytes:
    """Build additive risk-sizing evidence only when runtime telemetry is audit-complete."""
    root = project_root.resolve()
    telemetry = collect_risk_sizing_runtime_telemetry(root)
    assert_risk_sizing_evidence_export_ready(telemetry)
    snapshot = collect_operator_cockpit_snapshot(root, task_query=task_query, backend_probe=backend_probe)
    manifest = _safe_action_manifest(root)
    output = io.BytesIO()
    with zipfile.ZipFile(output, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("operator-cockpit/snapshot.json", json.dumps(snapshot, ensure_ascii=False, indent=2).encode("utf-8"))
        archive.writestr("operator-cockpit/safe-actions-manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8"))
        archive.writestr("operator-cockpit/risk-sizing-runtime-telemetry.json", json.dumps(telemetry, ensure_ascii=False, indent=2).encode("utf-8"))
    payload = output.getvalue()
    if len(payload) > MAX_OPERATOR_COCKPIT_EVIDENCE_PACK_BYTES:
        raise ValueError("OPERATOR_COCKPIT_EVIDENCE_PACK_TOO_LARGE")
    return payload


def _relative_or_name(path: Path | None, root: Path) -> str | None:
    if path is None:
        return None
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _mtime_utc(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat(timespec="seconds")


def _scan_active_model(project_root: Path) -> ModelSummary:
    search_roots = (
        project_root / "models",
        project_root / "artifacts",
        project_root / "model",
    )
    candidates: list[Path] = []
    for search_root in search_roots:
        if search_root.exists():
            candidates.extend(path for path in search_root.rglob("*.ubj") if path.is_file())
    if not candidates:
        return ModelSummary("NOT_FOUND", None, None, None, None, None)
    latest = max(candidates, key=lambda path: (path.stat().st_mtime_ns, path.name))
    return ModelSummary(
        status="DISCOVERED_READ_ONLY",
        file_name=latest.name,
        relative_path=_relative_or_name(latest, project_root),
        sha256=_sha256(latest),
        size_bytes=latest.stat().st_size,
        modified_utc=_mtime_utc(latest),
    )


def _default_backend_probe(url: str) -> Mapping[str, Any]:
    request = urllib.request.Request(url=url, method="GET", headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=0.8) as response:
            payload = json.loads(response.read().decode("utf-8"))
            if isinstance(payload, dict):
                return {"reachable": True, "status_code": response.status, "payload": payload}
    except (OSError, urllib.error.URLError, json.JSONDecodeError):
        pass
    return {"reachable": False, "status_code": None, "payload": {}}


def _default_task_query(task_name: str) -> Mapping[str, Any]:
    if platform.system().lower() != "windows":
        return {"task_name": task_name, "state": "UNAVAILABLE", "read_only_probe": True}
    command = (
        "$ErrorActionPreference='Stop';"
        f"$task=Get-ScheduledTask -TaskName '{task_name}';"
        f"$info=Get-ScheduledTaskInfo -TaskName '{task_name}';"
        "[PSCustomObject]@{"
        "task_name=$task.TaskName;state=[string]$task.State;"
        "last_run_time=[string]$info.LastRunTime;last_task_result=$info.LastTaskResult;"
        "next_run_time=[string]$info.NextRunTime;number_of_missed_runs=$info.NumberOfMissedRuns"
        "}|ConvertTo-Json -Compress"
    )
    try:
        completed = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
            text=True,
            capture_output=True,
            timeout=3.0,
            check=False,
        )
        if completed.returncode == 0:
            payload = json.loads(completed.stdout.strip())
            if isinstance(payload, dict):
                payload["read_only_probe"] = True
                return payload
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
        pass
    return {"task_name": task_name, "state": "UNAVAILABLE", "read_only_probe": True}


def _performance(rows: Sequence[Mapping[str, Any]]) -> PerformanceSummary:
    values = [value for row in rows if (value := _as_float(row.get("forward_return_bps_final"))) is not None]
    wins = [value for value in values if value > 0]
    losses = [value for value in values if value < 0]
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    return PerformanceSummary(
        sample_count=len(rows),
        matured_count=len(values),
        maturity_pending_count=len(rows) - len(values),
        win_count=len(wins),
        loss_count=len(losses),
        win_rate_pct=_round((len(wins) / len(values)) * 100 if values else None, 2),
        gross_profit_bps=_round(gross_profit) or 0.0,
        gross_loss_bps=_round(gross_loss) or 0.0,
        net_return_bps=_round(gross_profit - gross_loss) or 0.0,
        mean_return_bps=_round(statistics.fmean(values) if values else None),
        median_return_bps=_round(statistics.median(values) if values else None),
        profit_factor=_round(gross_profit / gross_loss if gross_loss > 0 else None),
        worst_return_bps=_round(min(values) if values else None),
        best_return_bps=_round(max(values) if values else None),
    )


def _worst_cluster(rows: Sequence[Mapping[str, Any]], performance: PerformanceSummary) -> TimestampClusterSummary:
    grouped: dict[str, list[Mapping[str, Any]]] = {}
    for row in rows:
        timestamp = str(row.get("timestamp_utc") or "UNKNOWN")
        grouped.setdefault(timestamp, []).append(row)
    clusters: list[TimestampClusterSummary] = []
    for timestamp, cluster_rows in grouped.items():
        values = [value for row in cluster_rows if (value := _as_float(row.get("forward_return_bps_final"))) is not None]
        net_return = sum(values)
        loss = abs(sum(value for value in values if value < 0))
        clusters.append(
            TimestampClusterSummary(
                timestamp_utc=timestamp,
                sample_count=len(cluster_rows),
                symbols=sorted({str(row.get("symbol") or "UNKNOWN") for row in cluster_rows}),
                net_return_bps=_round(net_return) or 0.0,
                mean_return_bps=_round(statistics.fmean(values) if values else None),
                gross_loss_share_pct=_round((loss / performance.gross_loss_bps) * 100 if performance.gross_loss_bps else None, 2),
            )
        )
    if not clusters:
        return TimestampClusterSummary(None, 0, [], 0.0, None, None)
    return min(clusters, key=lambda cluster: cluster.net_return_bps)


def _symbol_distribution(rows: Sequence[Mapping[str, Any]]) -> list[JsonObject]:
    counts: dict[str, int] = {}
    for row in rows:
        symbol = str(row.get("symbol") or "UNKNOWN")
        counts[symbol] = counts.get(symbol, 0) + 1
    return [
        {"symbol": symbol, "count": count}
        for symbol, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    ]


def _recent_observations(rows: Sequence[Mapping[str, Any]], limit: int = 8) -> list[JsonObject]:
    sorted_rows = sorted(rows, key=lambda row: str(row.get("timestamp_utc") or ""), reverse=True)
    return [
        {
            "symbol": row.get("symbol"),
            "timestamp_utc": row.get("timestamp_utc"),
            "observation_id": row.get("observation_id"),
            "spread_slippage_proxy_bps": _as_float(row.get("spread_slippage_proxy_bps")),
            "forward_return_bps_final": _as_float(row.get("forward_return_bps_final")),
        }
        for row in sorted_rows[:limit]
    ]


def _sample_timeline(rows: Sequence[Mapping[str, Any]]) -> list[JsonObject]:
    counts: dict[str, int] = {}
    for row in rows:
        timestamp = str(row.get("timestamp_utc") or "UNKNOWN")
        counts[timestamp] = counts.get(timestamp, 0) + 1
    cumulative = 0
    timeline: list[JsonObject] = []
    for timestamp, count in sorted(counts.items()):
        cumulative += count
        timeline.append({"timestamp_utc": timestamp, "new_samples": count, "cumulative_samples": cumulative})
    return timeline


def _return_distribution(rows: Sequence[Mapping[str, Any]]) -> list[JsonObject]:
    buckets: list[tuple[str, float | None, float | None]] = [
        ("< -500", None, -500.0),
        ("-500 / -250", -500.0, -250.0),
        ("-250 / -100", -250.0, -100.0),
        ("-100 / 0", -100.0, 0.0),
        ("0 / 100", 0.0, 100.0),
        ("100 / 250", 100.0, 250.0),
        ("250 / 500", 250.0, 500.0),
        (">= 500", 500.0, None),
    ]
    counts = {label: 0 for label, _, _ in buckets}
    for row in rows:
        value = _as_float(row.get("forward_return_bps_final"))
        if value is None:
            continue
        for label, lower, upper in buckets:
            if (lower is None or value >= lower) and (upper is None or value < upper):
                counts[label] += 1
                break
    return [{"bucket": label, "count": counts[label]} for label, _, _ in buckets]


def _symbol_performance(rows: Sequence[Mapping[str, Any]]) -> list[JsonObject]:
    grouped: dict[str, list[Mapping[str, Any]]] = {}
    for row in rows:
        symbol = str(row.get("symbol") or "UNKNOWN")
        grouped.setdefault(symbol, []).append(row)
    output: list[JsonObject] = []
    for symbol, symbol_rows in grouped.items():
        performance = _performance(symbol_rows)
        slippage_values = [
            value
            for row in symbol_rows
            if (value := _as_float(row.get("spread_slippage_proxy_bps"))) is not None
        ]
        output.append({
            "symbol": symbol,
            "sample_count": len(symbol_rows),
            "matured_count": performance.matured_count,
            "win_rate_pct": performance.win_rate_pct,
            "net_return_bps": performance.net_return_bps,
            "mean_return_bps": performance.mean_return_bps,
            "profit_factor": performance.profit_factor,
            "avg_slippage_proxy_bps": _round(statistics.fmean(slippage_values) if slippage_values else None),
        })
    return sorted(output, key=lambda item: (item["mean_return_bps"] is None, item["mean_return_bps"] or 0.0, item["symbol"]))


def _timestamp_clusters(rows: Sequence[Mapping[str, Any]], performance: PerformanceSummary) -> list[JsonObject]:
    grouped: dict[str, list[Mapping[str, Any]]] = {}
    for row in rows:
        timestamp = str(row.get("timestamp_utc") or "UNKNOWN")
        grouped.setdefault(timestamp, []).append(row)
    clusters: list[JsonObject] = []
    for timestamp, cluster_rows in grouped.items():
        values = [
            value
            for row in cluster_rows
            if (value := _as_float(row.get("forward_return_bps_final"))) is not None
        ]
        gross_loss = abs(sum(value for value in values if value < 0))
        clusters.append({
            "timestamp_utc": timestamp,
            "sample_count": len(cluster_rows),
            "matured_count": len(values),
            "symbols": sorted({str(row.get("symbol") or "UNKNOWN") for row in cluster_rows}),
            "net_return_bps": _round(sum(values)) or 0.0,
            "mean_return_bps": _round(statistics.fmean(values) if values else None),
            "gross_loss_bps": _round(gross_loss) or 0.0,
            "gross_loss_share_pct": _round((gross_loss / performance.gross_loss_bps) * 100 if performance.gross_loss_bps else None, 2),
        })
    return sorted(clusters, key=lambda item: (item["net_return_bps"], item["timestamp_utc"]))


def _slippage_observations(rows: Sequence[Mapping[str, Any]], limit: int = 24) -> list[JsonObject]:
    observations = [
        {
            "symbol": row.get("symbol"),
            "timestamp_utc": row.get("timestamp_utc"),
            "spread_slippage_proxy_bps": _as_float(row.get("spread_slippage_proxy_bps")),
            "forward_return_bps_final": _as_float(row.get("forward_return_bps_final")),
        }
        for row in rows
        if _as_float(row.get("spread_slippage_proxy_bps")) is not None
    ]
    observations.sort(key=lambda item: (item["spread_slippage_proxy_bps"] or 0.0), reverse=True)
    return observations[:limit]


def _mae_mfe_scatter(rows: Sequence[Mapping[str, Any]], limit: int = 80) -> list[JsonObject]:
    points = [
        {
            "symbol": row.get("symbol"),
            "timestamp_utc": row.get("timestamp_utc"),
            "mae_bps": _as_float(row.get("mae_bps")),
            "mfe_bps": _as_float(row.get("mfe_bps")),
            "forward_return_bps_final": _as_float(row.get("forward_return_bps_final")),
        }
        for row in rows
        if _as_float(row.get("mae_bps")) is not None and _as_float(row.get("mfe_bps")) is not None
    ]
    return points[:limit]


def _performance_comparison(rows: Sequence[Mapping[str, Any]], cluster: TimestampClusterSummary) -> list[JsonObject]:
    scenarios: list[tuple[str, list[Mapping[str, Any]]]] = [("Tüm R1", list(rows))]
    if cluster.timestamp_utc:
        scenarios.append((
            "Worst cluster hariç",
            [row for row in rows if str(row.get("timestamp_utc") or "") != cluster.timestamp_utc],
        ))
    scenarios.append((
        "Slippage < 15 bps",
        [
            row
            for row in rows
            if (value := _as_float(row.get("spread_slippage_proxy_bps"))) is None or value < 15.0
        ],
    ))
    output: list[JsonObject] = []
    for scenario, scenario_rows in scenarios:
        performance = _performance(scenario_rows)
        output.append({
            "scenario": scenario,
            "sample_count": performance.sample_count,
            "matured_count": performance.matured_count,
            "win_rate_pct": performance.win_rate_pct,
            "net_return_bps": performance.net_return_bps,
            "mean_return_bps": performance.mean_return_bps,
            "profit_factor": performance.profit_factor,
        })
    return output


def _visualizations(rows: Sequence[Mapping[str, Any]], performance: PerformanceSummary, cluster: TimestampClusterSummary) -> JsonObject:
    return {
        "sample_timeline": _sample_timeline(rows),
        "return_distribution": _return_distribution(rows),
        "symbol_performance": _symbol_performance(rows),
        "timestamp_clusters": _timestamp_clusters(rows, performance),
        "slippage_observations": _slippage_observations(rows),
        "mae_mfe_scatter": _mae_mfe_scatter(rows),
        "performance_comparison": _performance_comparison(rows, cluster),
    }

def _build_risk_items(
    audit: Mapping[str, Any],
    performance: PerformanceSummary,
    cluster: TimestampClusterSummary,
    rows: Sequence[Mapping[str, Any]],
    baseline_task: Mapping[str, Any],
    r1_task: Mapping[str, Any],
) -> list[JsonObject]:
    items: list[JsonObject] = []
    sample_target = _as_int(audit.get("shadow_sample_target"), 30)
    sample_count = _as_int(audit.get("shadow_observation_count"), performance.sample_count)
    if str(baseline_task.get("state", "")).upper() not in {"DISABLED", "UNAVAILABLE"}:
        items.append({"level": "critical", "code": "BASELINE_TASK_ENABLED", "title": "Baseline scheduler açık", "detail": "R1 izolasyonu için baseline scheduler Disabled kalmalı."})
    if str(r1_task.get("state", "")).upper() not in {"READY", "RUNNING", "UNAVAILABLE"}:
        items.append({"level": "warning", "code": "R1_TASK_NOT_READY", "title": "R1 scheduler hazır değil", "detail": "Görev durumu operatör tarafından kontrol edilmeli."})
    if sample_count < sample_target:
        items.append({"level": "info", "code": "SHADOW_SAMPLE_TARGET_INCOMPLETE", "title": "Shadow sample toplama devam ediyor", "detail": f"{sample_count} / {sample_target} unique sample tamamlandı."})
    if performance.profit_factor is not None and performance.profit_factor < 1.0:
        items.append({"level": "warning", "code": "PROFIT_FACTOR_BELOW_ONE", "title": "Profit factor takip edilmeli", "detail": f"Erken PF değeri {performance.profit_factor:.3f}. Paper geçişi kapalı tutulmalı."})
    if cluster.gross_loss_share_pct is not None and cluster.gross_loss_share_pct >= 50.0:
        items.append({"level": "warning", "code": "TIMESTAMP_CLUSTER_TAIL_LOSS_HIGH", "title": "Timestamp-cluster tail risk", "detail": f"En kötü küme gross loss'un %{cluster.gross_loss_share_pct:.2f} kısmını taşıyor."})
    slippage_values = [value for row in rows if (value := _as_float(row.get("spread_slippage_proxy_bps"))) is not None]
    max_slippage = max(slippage_values) if slippage_values else None
    if max_slippage is not None and max_slippage >= 15.0:
        items.append({"level": "warning", "code": "SLIPPAGE_PROXY_HIGH", "title": "Slippage proxy yüksek gözlem", "detail": f"Maksimum spread/slippage proxy {max_slippage:.3f} bps."})
    if _as_bool(audit.get("approved_for_live_real")) or _as_bool(audit.get("post_requests_allowed")):
        items.append({"level": "critical", "code": "UNSAFE_APPROVAL_DETECTED", "title": "Beklenmeyen işlem izni", "detail": "Read-only cockpit güvenlik kontrolü işlem izni bayrağı tespit etti."})
    if not items:
        items.append({"level": "healthy", "code": "NO_ACTIVE_RISK_WARNING", "title": "Aktif risk uyarısı yok", "detail": "Read-only kontroller kritik bir bulgu üretmedi."})
    return items


def _system_status(risks: Sequence[Mapping[str, Any]]) -> str:
    levels = {str(item.get("level", "")).lower() for item in risks}
    if "critical" in levels:
        return "CRITICAL"
    if "warning" in levels:
        return "WATCH"
    return "HEALTHY"


def _activity_feed(audit: Mapping[str, Any], rows: Sequence[Mapping[str, Any]], limit: int = 6) -> list[JsonObject]:
    activities: list[JsonObject] = []
    latest_timestamp = max((str(row.get("timestamp_utc") or "") for row in rows), default=None)
    if latest_timestamp:
        latest_rows = [row for row in rows if str(row.get("timestamp_utc") or "") == latest_timestamp]
        symbols = ", ".join(sorted({str(row.get("symbol") or "UNKNOWN") for row in latest_rows}))
        activities.append({"kind": "sample", "timestamp": latest_timestamp, "title": "Son observation kümesi", "detail": symbols})
    activities.append({"kind": "audit", "timestamp": None, "title": "Audit durumu", "detail": str(audit.get("dashboard_status") or "AUDIT_NOT_AVAILABLE")})
    activities.append({"kind": "risk", "timestamp": None, "title": "Paper geçişi", "detail": "Açık" if _as_bool(audit.get("paper_transition_ready")) else "Kapalı — risk gate onayı gerekli"})
    return activities[:limit]


def collect_operator_cockpit_snapshot(
    project_root: Path,
    *,
    task_query: TaskQuery | None = None,
    backend_probe: BackendProbe | None = None,
    backend_health_url: str = DEFAULT_BACKEND_HEALTH_URL,
) -> JsonObject:
    """Build a read-only operator snapshot without changing config, scheduler or trading state."""
    root = project_root.resolve()
    reports_dir = resolve_active_reports_dir(root)
    latest_25v = _latest_file(reports_dir, "4B436625V_hyp005_shadow_observation_logger_*.json")
    latest_25x = _latest_file(reports_dir, "4B436625X_hyp005_shadow_collection_orchestrator_*.json")
    latest_25y = _latest_file(reports_dir, "4B436625Y_hyp005_shadow_operator_daily_audit_*.json")
    latest_merged = _latest_file(reports_dir, "4B436625X_hyp005_shadow_merged_ledger_*.jsonl")
    logger_report = _read_json(latest_25v)
    collection_report = _read_json(latest_25x)
    audit = _read_json(latest_25y)
    rows = _read_jsonl(latest_merged)
    query = task_query or _default_task_query
    baseline_task = dict(query(BASELINE_TASK_NAME))
    active_r1_task_name = CANONICAL_R1_TASK_NAME if reports_dir == (root / CANONICAL_R1_REPORTS_DIR).resolve() else R1_TASK_NAME
    r1_task = dict(query(active_r1_task_name))
    backend = dict((backend_probe or _default_backend_probe)(backend_health_url))
    performance = _performance(rows)
    cluster = _worst_cluster(rows, performance)
    model = _scan_active_model(root)
    risks = _build_risk_items(audit, performance, cluster, rows, baseline_task, r1_task)
    sample_count = _as_int(audit.get("shadow_observation_count"), performance.sample_count)
    sample_target = max(_as_int(audit.get("shadow_sample_target"), 30), 1)
    progress_pct = _as_float(audit.get("progress_pct"))
    if progress_pct is None:
        progress_pct = round(min(sample_count / sample_target, 1.0) * 100, 6)
    risk_sizing_telemetry = collect_risk_sizing_runtime_telemetry(root)
    snapshot = {
        "contract_version": OPERATOR_COCKPIT_V2_CONTRACT_VERSION,
        "visualization_pack_version": OPERATOR_COCKPIT_V2_VISUALIZATION_PACK_VERSION,
        "read_only": True,
        "generated_at_utc": _utc_now_iso(),
        "system_status": _system_status(risks),
        "mode": "SHADOW",
        "branch_id": "HYP-005-R1",
        "fresh_ledger_namespace": "HYP005_R1",
        "sources": asdict(SnapshotSource(
            latest_25v_logger=_relative_or_name(latest_25v, root),
            latest_25x_collection=_relative_or_name(latest_25x, root),
            latest_25y_audit=_relative_or_name(latest_25y, root),
            latest_merged_ledger=_relative_or_name(latest_merged, root),
            r1_reports_dir=_relative_or_name(reports_dir, root) or str(DEFAULT_R1_REPORTS_DIR),
        )),
        "backend": backend,
        "scheduler": {"baseline_task": baseline_task, "r1_task": r1_task},
        "audit": {
            "decision": audit.get("decision"),
            "dashboard_status": audit.get("dashboard_status"),
            "latest_logger_decision": audit.get("latest_logger_decision") or logger_report.get("decision"),
            "latest_collection_decision": audit.get("latest_collection_decision") or collection_report.get("decision"),
            "latest_acceptance_decision": audit.get("latest_acceptance_decision"),
            "shadow_observation_count": sample_count,
            "shadow_sample_target": sample_target,
            "progress_pct": _round(progress_pct),
            "paper_transition_ready": _as_bool(audit.get("paper_transition_ready")),
            "approved_for_paper_candidate": _as_bool(audit.get("approved_for_paper_candidate")),
            "approved_for_live_real": _as_bool(audit.get("approved_for_live_real")),
            "post_requests_allowed": _as_bool(audit.get("post_requests_allowed")),
            "order_actions_performed": _as_bool(audit.get("order_actions_performed")),
            "source_ledgers": _as_int(audit.get("source_ledgers")),
            "source_reports": _as_int(audit.get("source_reports")),
        },
        "performance": asdict(performance),
        "worst_timestamp_cluster": asdict(cluster),
        "symbol_distribution": _symbol_distribution(rows),
        "recent_observations": _recent_observations(rows),
        "risk_items": risks,
        "activity_feed": _activity_feed(audit, rows),
        "model": asdict(model),
        "visualizations": _visualizations(rows, performance, cluster),
        "safe_operator_actions": _safe_action_manifest(root),
        "risk_sizing_runtime_telemetry": risk_sizing_telemetry,
        "operator_guidance": "Müdahale gerekmez. No-order shadow collection otomatik devam ediyor." if sample_count < sample_target else "Shadow hedefi tamamlandı. Bir sonraki audit gate değerlendirilmelidir.",
    }
    return apply_hyp006_operator_cockpit_binding(snapshot, root)


DASHBOARD_HTML = r'''<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>TradeBot V2 · Operator Cockpit</title>
<style>
:root{--bg:#07101d;--panel:#0e1a2b;--panel2:#122137;--line:rgba(255,255,255,.08);--text:#e8f0fb;--muted:#8ea4bf;--accent:#55b7ff;--green:#61d89a;--amber:#ffcb72;--red:#ff7588;--blue:#79c8ff;--shadow:0 18px 45px rgba(0,0,0,.22)}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:radial-gradient(circle at top right,#112c4a 0,#07101d 36%,#050b14 100%);color:var(--text);font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;min-height:100vh}.app{display:grid;grid-template-columns:248px minmax(0,1fr);min-height:100vh}.sidebar{padding:22px 16px;border-right:1px solid var(--line);background:rgba(5,12,22,.86);backdrop-filter:blur(18px);position:sticky;top:0;height:100vh}.brand{display:flex;gap:12px;align-items:center;padding:4px 8px 22px}.logo{width:38px;height:38px;border-radius:13px;background:linear-gradient(135deg,#5fc7ff,#7d8dff);display:grid;place-items:center;color:#04111f;font-weight:900;box-shadow:0 8px 26px rgba(85,183,255,.35)}.brand strong{display:block;font-size:15px}.brand small{color:var(--muted)}.nav-label{font-size:10px;letter-spacing:.16em;color:#6f87a4;text-transform:uppercase;padding:18px 10px 7px}.nav a{display:flex;gap:10px;padding:10px 11px;border-radius:10px;text-decoration:none;color:#b8c9dc;font-size:13px;margin:2px 0}.nav a.active,.nav a:hover{background:rgba(121,200,255,.11);color:white}.read-only{margin-top:24px;padding:12px;border:1px solid rgba(97,216,154,.22);border-radius:12px;background:rgba(97,216,154,.08);font-size:12px;color:#bdebd1}.main{padding:24px 28px 42px;max-width:1700px;width:100%;margin:auto}.topbar{display:flex;justify-content:space-between;align-items:center;gap:16px;margin-bottom:20px}.title h1{font-size:24px;margin:0 0 5px}.title p{margin:0;color:var(--muted);font-size:13px}.top-actions{display:flex;gap:9px;align-items:center}.pill,.btn{border:1px solid var(--line);border-radius:999px;padding:8px 12px;font-size:12px;background:rgba(255,255,255,.04);color:#d7e4f2}.btn{cursor:pointer}.btn:hover{background:rgba(255,255,255,.09)}.grid{display:grid;gap:14px}.cards{grid-template-columns:repeat(5,minmax(0,1fr));margin-bottom:14px}.card,.section{background:linear-gradient(145deg,rgba(18,33,55,.94),rgba(11,22,38,.94));border:1px solid var(--line);border-radius:16px;box-shadow:var(--shadow)}.card{padding:16px;min-height:112px}.label{color:var(--muted);font-size:11px;letter-spacing:.09em;text-transform:uppercase}.value{font-size:22px;font-weight:750;margin-top:12px}.hint{font-size:12px;color:#9db1c8;margin-top:7px}.status-dot{width:9px;height:9px;display:inline-block;border-radius:50%;margin-right:7px}.healthy{color:var(--green)}.warning{color:var(--amber)}.critical{color:var(--red)}.info{color:var(--blue)}.dot-healthy{background:var(--green)}.dot-warning{background:var(--amber)}.dot-critical{background:var(--red)}.layout{grid-template-columns:minmax(0,1.55fr) minmax(320px,.75fr);align-items:start}.section{padding:17px;margin-bottom:14px}.section-head{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:15px}.section h2{font-size:15px;margin:0}.section small{color:var(--muted)}.progress-shell{background:rgba(255,255,255,.055);height:12px;border-radius:999px;overflow:hidden;margin:15px 0 8px}.progress{height:100%;width:0;border-radius:999px;background:linear-gradient(90deg,#50b9ff,#6fe4bc);transition:width .35s ease}.progress-row{display:flex;justify-content:space-between;color:#c6d6e7;font-size:13px}.metric-row{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin-top:15px}.metric{padding:12px;border-radius:12px;background:rgba(255,255,255,.035);border:1px solid rgba(255,255,255,.05)}.metric strong{display:block;margin-top:7px;font-size:16px}.risk-list,.activity-list{display:grid;gap:9px}.risk{padding:12px;border-radius:12px;background:rgba(255,255,255,.035);border-left:3px solid var(--blue)}.risk.warning{border-left-color:var(--amber)}.risk.critical{border-left-color:var(--red)}.risk.healthy{border-left-color:var(--green)}.risk strong{display:block;font-size:13px;color:#ecf5ff}.risk span{display:block;color:#a9bad0;font-size:12px;margin-top:5px;line-height:1.45}.table-wrap{overflow:auto;border:1px solid rgba(255,255,255,.055);border-radius:12px}table{width:100%;border-collapse:collapse;font-size:12px;min-width:720px}th,td{text-align:left;padding:11px 12px;border-bottom:1px solid rgba(255,255,255,.055);white-space:nowrap}th{color:#8fa6c1;font-weight:650;background:rgba(255,255,255,.025)}td{color:#d4e0ef}.activity{display:flex;gap:10px;align-items:flex-start;padding:10px 0;border-bottom:1px solid rgba(255,255,255,.055)}.activity:last-child{border-bottom:0}.activity-icon{width:28px;height:28px;border-radius:9px;background:rgba(121,200,255,.12);display:grid;place-items:center;font-size:12px;color:#8dd4ff}.activity strong{font-size:13px;display:block}.activity span{font-size:12px;color:var(--muted);display:block;margin-top:4px}.scheduler{display:grid;gap:8px}.scheduler-line{display:flex;justify-content:space-between;gap:12px;font-size:12px;border-bottom:1px solid rgba(255,255,255,.05);padding:8px 0}.scheduler-line span{color:var(--muted)}.scheduler-line strong{font-weight:650;text-align:right}.placeholder{padding:20px;border:1px dashed rgba(255,255,255,.16);border-radius:12px;color:#8da3bd;font-size:12px;line-height:1.6}.footer{font-size:11px;color:#6e86a3;padding-top:6px}.empty{color:#8da3bd;font-size:12px}.overview-badge{display:inline-flex;align-items:center;gap:6px;padding:6px 10px;background:rgba(255,255,255,.04);border:1px solid var(--line);border-radius:999px;font-size:11px;color:#cfe0f2}.visual-shell{padding:0;overflow:hidden}.visual-head{padding:17px 17px 0}.tabs{display:flex;gap:8px;flex-wrap:wrap;padding:14px 17px;border-bottom:1px solid var(--line)}.tab{border:1px solid var(--line);background:rgba(255,255,255,.025);color:#9fb3ca;border-radius:999px;padding:8px 12px;font-size:12px;cursor:pointer}.tab.active,.tab:hover{background:rgba(121,200,255,.13);color:#eef8ff;border-color:rgba(121,200,255,.25)}.tab-panel{display:none;padding:16px}.tab-panel.active{display:block}.chart-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.chart-card{min-height:260px;padding:13px;border:1px solid rgba(255,255,255,.055);border-radius:13px;background:rgba(255,255,255,.025)}.chart-card.wide{grid-column:1/-1}.chart-title{font-size:13px;font-weight:750}.chart-note{font-size:11px;color:var(--muted);margin-top:4px}.chart{height:205px;margin-top:10px}.chart svg{width:100%;height:100%;overflow:visible}.chart text{fill:#8fa6c1;font-size:10px}.chart .gridline{stroke:rgba(255,255,255,.07);stroke-width:1}.chart .axis{stroke:rgba(255,255,255,.14);stroke-width:1}.chart .line{fill:none;stroke:#68caff;stroke-width:3;stroke-linecap:round;stroke-linejoin:round}.chart .point{fill:#75e0bf}.chart .bar{fill:#5cbcff}.chart .bar-negative{fill:#ff8b9a}.chart .bar-positive{fill:#68d99e}.chart .scatter{fill:#79c8ff;opacity:.78}.legend{display:flex;gap:13px;flex-wrap:wrap;color:#9fb3ca;font-size:11px;margin-top:8px}.legend i{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:5px}.scenario-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:9px}.scenario{padding:12px;border-radius:12px;background:rgba(255,255,255,.035);border:1px solid rgba(255,255,255,.055)}.scenario strong{display:block;font-size:13px}.scenario span{display:block;color:var(--muted);font-size:11px;margin-top:7px}.action-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.action-btn{display:flex;align-items:center;justify-content:center;min-height:38px;padding:9px 10px;border:1px solid rgba(121,200,255,.2);border-radius:10px;background:rgba(121,200,255,.08);color:#d8edff;text-decoration:none;font-size:12px;cursor:pointer;text-align:center}.action-btn:hover{background:rgba(121,200,255,.15)}.action-feedback{margin-top:10px;padding:10px;border-radius:10px;background:rgba(255,255,255,.035);color:#9fb3ca;font-size:11px;line-height:1.45}.locked-actions{display:grid;gap:7px;margin-top:12px}.locked-action{padding:9px 10px;border:1px solid rgba(255,203,114,.15);border-radius:10px;background:rgba(255,203,114,.045)}.locked-action strong{display:block;font-size:12px;color:#ffd98f}.locked-action span{display:block;color:#9fb3ca;font-size:11px;margin-top:4px;line-height:1.4}.hide{display:none}@media(max-width:1220px){.cards{grid-template-columns:repeat(3,1fr)}.layout{grid-template-columns:1fr}}@media(max-width:900px){.chart-grid{grid-template-columns:1fr}.scenario-grid{grid-template-columns:1fr}}@media(max-width:820px){.app{grid-template-columns:1fr}.sidebar{position:relative;height:auto;display:none}.main{padding:18px}.cards{grid-template-columns:repeat(2,1fr)}.metric-row{grid-template-columns:repeat(2,1fr)}.topbar{align-items:flex-start;flex-direction:column}}@media(max-width:480px){.cards{grid-template-columns:1fr}.main{padding:14px}}
</style>
</head>
<body>
<div class="app">
<aside class="sidebar">
  <div class="brand"><div class="logo">T</div><div><strong>TradeBot V2</strong><small>Operator Cockpit</small></div></div>
  <div class="nav-label">Operasyon</div><nav class="nav"><a class="active" href="#overview">◈ Genel Durum</a><a href="#shadow">◌ Shadow Audit</a><a href="#risk">△ Risk Merkezi</a><a href="#actions">◎ Güvenli Aksiyonlar</a><a href="#scheduler">◷ Scheduler</a></nav>
  <div class="nav-label">Analiz</div><nav class="nav"><a href="#visuals">▤ Quant Görseller</a><a href="#observations">◎ Observation Akışı</a><a href="#model">◇ Model ve Strateji</a><a href="#logs">≡ Loglar</a></nav>
  <div class="read-only"><strong>Read-only foundation · Safe actions</strong><br>GET-only aksiyonlar rapor okur ve dışa aktarır; trading state değiştirmez.</div>
</aside>
<main class="main">
<header class="topbar"><div class="title"><h1>Operator Cockpit V2</h1><p>Gelişmiş görünürlük · Katmanlı quant analiz · Kontrollü operasyon</p></div><div class="top-actions"><span class="pill" id="generated">Güncelleniyor…</span><button class="btn" id="refresh">Yenile</button></div></header>
<section id="overview" class="grid cards">
  <article class="card"><div class="label">Sistem Durumu</div><div class="value" id="system-status">—</div><div class="hint" id="operator-guidance">Snapshot bekleniyor</div></article>
  <article class="card"><div class="label">Çalışma Modu</div><div class="value info" id="mode">SHADOW</div><div class="hint">No-order validation branch</div></article>
  <article class="card"><div class="label">R1 İlerlemesi</div><div class="value" id="sample-count">— / —</div><div class="hint" id="progress-hint">Unique shadow sample</div></article>
  <article class="card"><div class="label">Paper Gate</div><div class="value" id="paper-gate">—</div><div class="hint">Kontrollü geçiş kapısı</div></article>
  <article class="card"><div class="label">Backend</div><div class="value" id="backend-status">—</div><div class="hint">Local health probe</div></article>
</section>
<div class="grid layout"><div>
<section id="shadow" class="section"><div class="section-head"><div><h2>HYP-005-R1 Shadow Validation</h2><small>Fresh isolated ledger · 8 sembol · 4 saatlik tarama</small></div><span class="overview-badge" id="branch">HYP-005-R1</span></div><div class="progress-shell"><div class="progress" id="progress"></div></div><div class="progress-row"><span id="progress-text">—</span><span id="progress-percent">—%</span></div><div class="metric-row"><div class="metric"><div class="label">Matured</div><strong id="matured">—</strong></div><div class="metric"><div class="label">Profit Factor</div><strong id="pf">—</strong></div><div class="metric"><div class="label">Mean Edge</div><strong id="mean-edge">—</strong></div><div class="metric"><div class="label">Win Rate</div><strong id="win-rate">—</strong></div></div></section>
<section id="visuals" class="section visual-shell"><div class="visual-head"><div class="section-head"><div><h2>Shadow Audit Visualization</h2><small>Quant detaylar sekmeli yapı içinde; ana ekranın bilgi hiyerarşisi korunur.</small></div><!-- 26B-H1 · READ ONLY --><!-- 26B-H2 · READ ONLY --><span class="overview-badge">26B-H3 · READ ONLY</span></div></div><div class="tabs"><button class="tab active" data-tab="progress-panel">İlerleme</button><button class="tab" data-tab="returns-panel">Edge ve Dağılım</button><button class="tab" data-tab="risk-panel">Cluster ve Slippage</button><button class="tab" data-tab="execution-panel">MAE / MFE</button></div>
<div id="progress-panel" class="tab-panel active"><div class="chart-grid"><div class="chart-card wide"><div class="chart-title">Unique sample zaman çizgisi</div><div class="chart-note">R1 isolated ledger içindeki kümülatif observation ilerlemesi</div><div class="chart" id="sample-timeline-chart"></div></div><div class="chart-card"><div class="chart-title">Sembol yoğunluğu</div><div class="chart-note">Unique sample dağılımı</div><div class="chart" id="symbol-count-chart"></div></div><div class="chart-card"><div class="chart-title">Senaryo özeti</div><div class="chart-note">Risk filtreleri yalnızca analiz amaçlıdır; config değiştirmez.</div><div class="scenario-grid" id="scenario-grid"></div></div></div></div>
<div id="returns-panel" class="tab-panel"><div class="chart-grid"><div class="chart-card"><div class="chart-title">Forward return dağılımı</div><div class="chart-note">Final edge değerlerinin bps kovaları</div><div class="chart" id="return-distribution-chart"></div></div><div class="chart-card"><div class="chart-title">Sembol bazlı mean edge</div><div class="chart-note">Negatif ve pozitif sembol katkıları</div><div class="chart" id="symbol-edge-chart"></div></div><div class="chart-card wide"><div class="chart-title">Sembol performans tablosu</div><div class="table-wrap"><table style="min-width:640px"><thead><tr><th>Sembol</th><th>Sample</th><th>Matured</th><th>Mean Edge</th><th>Net Edge</th><th>Win Rate</th><th>Ort. Slippage</th></tr></thead><tbody id="symbol-performance-body"></tbody></table></div></div></div></div>
<div id="risk-panel" class="tab-panel"><div class="chart-grid"><div class="chart-card"><div class="chart-title">Timestamp-cluster net edge</div><div class="chart-note">En kötü cluster üstte görünür</div><div class="chart" id="cluster-loss-chart"></div></div><div class="chart-card"><div class="chart-title">Slippage proxy sıralaması</div><div class="chart-note">Yüksek proxy gözlemleri ayrı görünür</div><div class="chart" id="slippage-chart"></div></div><div class="chart-card wide"><div class="chart-title">Timestamp cluster tablosu</div><div class="table-wrap"><table style="min-width:760px"><thead><tr><th>Timestamp</th><th>Sembol</th><th>Sample</th><th>Matured</th><th>Net Edge</th><th>Mean Edge</th><th>Gross Loss Payı</th></tr></thead><tbody id="cluster-body"></tbody></table></div></div></div></div>
<div id="execution-panel" class="tab-panel"><div class="chart-grid"><div class="chart-card wide"><div class="chart-title">MAE / MFE execution görünümü</div><div class="chart-note">Ledger alanları mevcutsa observation bazlı scatter çizilir.</div><div class="chart" id="mae-mfe-chart"></div></div></div></div></section>
<section id="observations" class="section"><div class="section-head"><div><h2>Son Observation Akışı</h2><small>Teknik detaylar gerektiğinde görünür; ana ekranı kalabalıklaştırmaz.</small></div></div><div class="table-wrap"><table><thead><tr><th>Sembol</th><th>Zaman (UTC)</th><th>Slippage Proxy</th><th>Final Edge</th><th>Observation ID</th></tr></thead><tbody id="observations-body"></tbody></table></div></section>
<section class="section"><div class="section-head"><div><h2>Sembol Dağılımı</h2><small>R1 unique sample yoğunluğu</small></div></div><div class="table-wrap"><table style="min-width:420px"><thead><tr><th>Sembol</th><th>Sample</th><th>Yoğunluk</th></tr></thead><tbody id="symbols-body"></tbody></table></div></section>
<section id="logs" class="section"><div class="section-head"><div><h2>Audit Kaynakları</h2><small>Developer detayları ayrı tutulur.</small></div></div><details><summary class="btn">Kaynak yollarını göster</summary><pre id="sources" class="placeholder"></pre></details></section>
</div><div>
<section id="risk" class="section"><div class="section-head"><div><h2>Risk Merkezi</h2><small>Kritik bilgi önce; ayrıntı gerektiğinde.</small></div></div><div class="risk-list" id="risk-list"></div></section>
<section id="actions" class="section"><div class="section-head"><div><h2>Güvenli Operatör Aksiyonları</h2><small>Yalnızca GET tabanlı görünürlük ve dışa aktarma.</small></div><span class="overview-badge">26C · GET ONLY</span></div><div class="action-grid"><button class="action-btn" id="action-backend-probe" type="button">Backend Probe Tekrarla</button><a class="action-btn" href="/api/operator-cockpit-v2/export/snapshot.json">Snapshot JSON İndir</a><a class="action-btn" href="/api/operator-cockpit-v2/view/latest-audit.json" target="_blank" rel="noopener">Son Audit JSON Aç</a><a class="action-btn" href="/api/operator-cockpit-v2/actions/manifest" target="_blank" rel="noopener">Kaynak Manifestini Aç</a><a class="action-btn" href="/api/operator-cockpit-v2/export/evidence-pack.zip">Evidence Pack ZIP İndir</a><a class="action-btn" href="/api/operator-cockpit-v2/view/risk-sizing-runtime-telemetry.json" target="_blank" rel="noopener">Risk-Sizing Telemetry JSON Aç</a><a class="action-btn" href="/api/operator-cockpit-v2/export/risk-sizing-evidence-pack.zip">Risk-Sizing Evidence ZIP İndir</a><a class="action-btn" href="/api/operator-cockpit-v2/export/latest-ledger">Merged Ledger İndir</a></div><div class="action-feedback" id="action-feedback">Aksiyonlar yalnızca local GET istekleridir; config, scheduler ve trading state değiştirilmez.</div><div class="locked-actions" id="locked-actions"></div></section>
<section id="scheduler" class="section"><div class="section-head"><div><h2>Scheduler</h2><small>Baseline kapalı, R1 aktif kalmalı.</small></div></div><div class="scheduler" id="scheduler-lines"></div></section>
<section class="section"><div class="section-head"><div><h2>Worst Timestamp Cluster</h2><small>Market-wide tail risk erken görünümü</small></div></div><div class="metric-row" style="grid-template-columns:repeat(2,1fr)"><div class="metric"><div class="label">Timestamp</div><strong id="cluster-time">—</strong></div><div class="metric"><div class="label">Gross Loss Payı</div><strong id="cluster-share">—</strong></div></div><p class="hint" id="cluster-detail">—</p></section>
<section id="model" class="section"><div class="section-head"><div><h2>Model ve Strateji</h2><small>Model yalnızca okunur; reload aksiyonu yoktur.</small></div></div><div class="scheduler" id="model-lines"></div></section>
<section class="section"><div class="section-head"><div><h2>Son Aktiviteler</h2><small>Operatör için kısa ve anlamlı özet</small></div></div><div class="activity-list" id="activity-list"></div></section>
</div></div>
<footer class="footer">4B.4.3.6.6.26C · Operator Cockpit V2 Safe Operator Actions · GET-only read-only operations</footer>
</main></div>
<script>
const $=id=>document.getElementById(id);const esc=v=>String(v??'—').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));const fmt=(v,d=2)=>v===null||v===undefined?'—':Number(v).toLocaleString('tr-TR',{maximumFractionDigits:d,minimumFractionDigits:0});const svg=(body)=>`<svg viewBox="0 0 760 210" preserveAspectRatio="none">${body}</svg>`;const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
function tone(v){v=String(v||'').toLowerCase();return v.includes('critical')?'critical':v.includes('watch')||v.includes('block')||v.includes('warning')?'warning':'healthy'}function line(k,v){return `<div class="scheduler-line"><span>${esc(k)}</span><strong>${esc(v??'—')}</strong></div>`}function empty(msg){return `<div class="placeholder">${esc(msg)}</div>`}
function lineChart(el,data,xKey,yKey){if(!data.length){$(el).innerHTML=empty('Grafik için veri bulunamadı.');return}const vals=data.map(x=>Number(x[yKey]||0)),max=Math.max(...vals,1),min=Math.min(...vals,0),span=Math.max(max-min,1);const px=i=>40+(i*Math.max(0,680/(Math.max(data.length-1,1)))),py=v=>175-((v-min)/span)*140;let body='<line class="axis" x1="40" y1="175" x2="730" y2="175"/><line class="axis" x1="40" y1="25" x2="40" y2="175"/>';for(let i=0;i<4;i++){const y=35+i*42;body+=`<line class="gridline" x1="40" y1="${y}" x2="730" y2="${y}"/>`}const points=data.map((x,i)=>`${px(i)},${py(Number(x[yKey]||0))}`).join(' ');body+=`<polyline class="line" points="${points}"/>`;data.forEach((x,i)=>{body+=`<circle class="point" cx="${px(i)}" cy="${py(Number(x[yKey]||0))}" r="4"><title>${esc(x[xKey])}: ${fmt(x[yKey],2)}</title></circle>`});body+=`<text x="40" y="198">${esc(String(data[0][xKey]).slice(0,10))}</text><text x="650" y="198">${esc(String(data[data.length-1][xKey]).slice(0,10))}</text>`;$(el).innerHTML=svg(body)}
function barChart(el,data,labelKey,valueKey){if(!data.length){$(el).innerHTML=empty('Grafik için veri bulunamadı.');return}const values=data.map(x=>Number(x[valueKey]||0)),max=Math.max(...values.map(Math.abs),1),n=data.length,gap=8,w=Math.max(18,(670/n)-gap),zero=112;let body='<line class="axis" x1="42" y1="112" x2="730" y2="112"/>';data.forEach((x,i)=>{const value=Number(x[valueKey]||0),h=(Math.abs(value)/max)*75,y=value>=0?zero-h:zero,cls=value>=0?'bar-positive':'bar-negative',xx=48+i*(670/n);body+=`<rect class="${cls}" x="${xx}" y="${y}" width="${w}" height="${Math.max(h,1)}" rx="4"><title>${esc(x[labelKey])}: ${fmt(value,2)}</title></rect><text transform="translate(${xx+w/2},198) rotate(-35)" text-anchor="end">${esc(String(x[labelKey]).slice(0,14))}</text>`});$(el).innerHTML=svg(body)}
function positiveBarChart(el,data,labelKey,valueKey){if(!data.length){$(el).innerHTML=empty('Grafik için veri bulunamadı.');return}const max=Math.max(...data.map(x=>Number(x[valueKey]||0)),1),n=data.length,w=Math.max(18,650/n-8);let body='<line class="axis" x1="42" y1="175" x2="730" y2="175"/>';data.forEach((x,i)=>{const v=Number(x[valueKey]||0),h=(v/max)*135,xx=52+i*(650/n);body+=`<rect class="bar" x="${xx}" y="${175-h}" width="${w}" height="${Math.max(h,1)}" rx="4"><title>${esc(x[labelKey])}: ${fmt(v,2)}</title></rect><text transform="translate(${xx+w/2},198) rotate(-35)" text-anchor="end">${esc(String(x[labelKey]).slice(0,14))}</text>`});$(el).innerHTML=svg(body)}
function finiteChartNumber(value){const parsed=Number(value);return Number.isFinite(parsed)?parsed:null}
function signedDomain(values){const finite=values.map(finiteChartNumber).filter(value=>value!==null);if(!finite.length)return null;let min=Math.min(...finite,0),max=Math.max(...finite,0);const span=Math.max(max-min,1),padding=Math.max(span*.08,1);min-=padding;max+=padding;return{min,max,span:Math.max(max-min,1)}}
function scaleSigned(value,domain,start,end){return start+((value-domain.min)/domain.span)*(end-start)}
function scatterChart(el,data,xKey,yKey){const points=data.map(record=>({record,x:finiteChartNumber(record[xKey]),y:finiteChartNumber(record[yKey])})).filter(point=>point.x!==null&&point.y!==null);if(!points.length){$(el).innerHTML=empty('MAE / MFE verisi henüz oluşmadı.');return}const xDomain=signedDomain(points.map(point=>point.x)),yDomain=signedDomain(points.map(point=>point.y)),left=58,right=730,top=28,bottom=176,xZero=scaleSigned(0,xDomain,left,right),yZero=scaleSigned(0,yDomain,bottom,top);let body='';for(let i=0;i<5;i++){const x=left+((right-left)/4)*i,y=top+((bottom-top)/4)*i;body+=`<line class="gridline" x1="${x}" y1="${top}" x2="${x}" y2="${bottom}"/><line class="gridline" x1="${left}" y1="${y}" x2="${right}" y2="${y}"/>`}body+=`<line class="axis" x1="${left}" y1="${yZero}" x2="${right}" y2="${yZero}"/><line class="axis" x1="${xZero}" y1="${top}" x2="${xZero}" y2="${bottom}"/><text x="${right-72}" y="202">MAE bps</text><text x="${left}" y="18">MFE bps</text><text x="${left}" y="202">${fmt(xDomain.min,1)}</text><text x="${right-38}" y="202">${fmt(xDomain.max,1)}</text><text x="${left+5}" y="${top+10}">${fmt(yDomain.max,1)}</text><text x="${left+5}" y="${bottom-5}">${fmt(yDomain.min,1)}</text>`;points.forEach(point=>{const record=point.record,xx=scaleSigned(point.x,xDomain,left,right),yy=scaleSigned(point.y,yDomain,bottom,top);body+=`<circle class="scatter" cx="${xx}" cy="${yy}" r="5"><title>${esc(record.symbol)} · ${esc(record.timestamp_utc)} · MAE ${fmt(point.x,2)} · MFE ${fmt(point.y,2)} · Final Edge ${fmt(record.forward_return_bps_final,2)}</title></circle>`});$(el).innerHTML=svg(body)}
function renderVisuals(v){const timeline=v.sample_timeline||[],sym=v.symbol_performance||[],dist=v.return_distribution||[],clusters=(v.timestamp_clusters||[]).slice(0,12),slip=(v.slippage_observations||[]).slice(0,12),scatter=v.mae_mfe_scatter||[],scenarios=v.performance_comparison||[];lineChart('sample-timeline-chart',timeline,'timestamp_utc','cumulative_samples');positiveBarChart('symbol-count-chart',sym,'symbol','sample_count');positiveBarChart('return-distribution-chart',dist,'bucket','count');barChart('symbol-edge-chart',sym,'symbol','mean_return_bps');barChart('cluster-loss-chart',clusters,'timestamp_utc','net_return_bps');positiveBarChart('slippage-chart',slip.map((x,i)=>({...x,label:(x.symbol||'—')+' '+(i+1)})),'label','spread_slippage_proxy_bps');scatterChart('mae-mfe-chart',scatter,'mae_bps','mfe_bps');$('scenario-grid').innerHTML=scenarios.map(x=>`<div class="scenario"><strong>${esc(x.scenario)}</strong><span>Sample ${esc(x.sample_count)} · Matured ${esc(x.matured_count)}</span><span>PF ${fmt(x.profit_factor,3)} · Mean ${fmt(x.mean_return_bps,2)} bps</span><span>Net ${fmt(x.net_return_bps,2)} bps · Win ${fmt(x.win_rate_pct,2)}%</span></div>`).join('')||empty('Senaryo verisi yok.');$('symbol-performance-body').innerHTML=sym.map(x=>`<tr><td>${esc(x.symbol)}</td><td>${esc(x.sample_count)}</td><td>${esc(x.matured_count)}</td><td>${fmt(x.mean_return_bps,2)} bps</td><td>${fmt(x.net_return_bps,2)} bps</td><td>${fmt(x.win_rate_pct,2)}%</td><td>${fmt(x.avg_slippage_proxy_bps,2)} bps</td></tr>`).join('')||'<tr><td colspan="7" class="empty">Sembol performansı yok.</td></tr>';$('cluster-body').innerHTML=clusters.map(x=>`<tr><td>${esc(x.timestamp_utc)}</td><td>${esc((x.symbols||[]).join(', '))}</td><td>${esc(x.sample_count)}</td><td>${esc(x.matured_count)}</td><td>${fmt(x.net_return_bps,2)} bps</td><td>${fmt(x.mean_return_bps,2)} bps</td><td>${fmt(x.gross_loss_share_pct,2)}%</td></tr>`).join('')||'<tr><td colspan="7" class="empty">Cluster verisi yok.</td></tr>'}
function render(s){const a=s.audit||{},p=s.performance||{},c=s.worst_timestamp_cluster||{},sch=s.scheduler||{},model=s.model||{};$('generated').textContent='Güncel · '+(s.generated_at_utc||'—');const st=s.system_status||'—';$('system-status').innerHTML=`<span class="status-dot dot-${tone(st)}"></span><span class="${tone(st)}">${esc(st)}</span>`;$('operator-guidance').textContent=s.operator_guidance||'—';$('mode').textContent=s.mode||'—';$('sample-count').textContent=`${a.shadow_observation_count??0} / ${a.shadow_sample_target??30}`;$('paper-gate').innerHTML=`<span class="${a.paper_transition_ready?'healthy':'warning'}">${a.paper_transition_ready?'READY':'BLOCKED'}</span>`;$('backend-status').innerHTML=`<span class="${s.backend&&s.backend.reachable?'healthy':'warning'}">${s.backend&&s.backend.reachable?'BAĞLI':'ERİŞİLEMİYOR'}</span>`;$('branch').textContent=s.branch_id||'—';const pct=Math.min(Number(a.progress_pct||0),100);$('progress').style.width=pct+'%';$('progress-text').textContent=`${a.shadow_observation_count??0} / ${a.shadow_sample_target??30} unique sample`;$('progress-percent').textContent=fmt(a.progress_pct,2)+'%';$('matured').textContent=`${p.matured_count??0} / ${p.sample_count??0}`;$('pf').textContent=fmt(p.profit_factor,3);$('mean-edge').textContent=fmt(p.mean_return_bps,2)+' bps';$('win-rate').textContent=fmt(p.win_rate_pct,2)+'%';$('risk-list').innerHTML=(s.risk_items||[]).map(r=>`<div class="risk ${esc(r.level)}"><strong>${esc(r.title)}</strong><span>${esc(r.detail)}</span></div>`).join('')||'<div class="empty">Risk kaydı yok.</div>';const base=sch.baseline_task||{},r1=sch.r1_task||{};$('scheduler-lines').innerHTML=line('Baseline task',base.state||'—')+line('R1 task',r1.state||'—')+line('Son çalışma',r1.last_run_time||'—')+line('Sonuç',r1.last_task_result??'—')+line('Sonraki çalışma',r1.next_run_time||'—')+line('Kaçırılan çalışma',r1.number_of_missed_runs??'—');$('cluster-time').textContent=c.timestamp_utc||'—';$('cluster-share').textContent=fmt(c.gross_loss_share_pct,2)+'%';$('cluster-detail').textContent=(c.symbols||[]).length?`${(c.symbols||[]).join(', ')} · Net ${fmt(c.net_return_bps,2)} bps`:'Cluster verisi bulunamadı.';$('model-lines').innerHTML=line('Durum',model.status||'—')+line('Model',model.file_name||'Model henüz seçilmedi')+line('SHA-256',model.sha256?model.sha256.slice(0,16)+'…':'—')+line('Branch',s.branch_id||'—')+line('Namespace',s.fresh_ledger_namespace||'—');$('observations-body').innerHTML=(s.recent_observations||[]).map(o=>`<tr><td>${esc(o.symbol)}</td><td>${esc(o.timestamp_utc)}</td><td>${fmt(o.spread_slippage_proxy_bps,3)} bps</td><td>${fmt(o.forward_return_bps_final,2)} bps</td><td>${esc(o.observation_id)}</td></tr>`).join('')||'<tr><td colspan="5" class="empty">Observation bulunamadı.</td></tr>';const total=Math.max(Number(p.sample_count||0),1);$('symbols-body').innerHTML=(s.symbol_distribution||[]).map(x=>`<tr><td>${esc(x.symbol)}</td><td>${esc(x.count)}</td><td>${fmt((Number(x.count)/total)*100,1)}%</td></tr>`).join('')||'<tr><td colspan="3" class="empty">Sembol verisi yok.</td></tr>';$('activity-list').innerHTML=(s.activity_feed||[]).map(x=>`<div class="activity"><div class="activity-icon">●</div><div><strong>${esc(x.title)}</strong><span>${esc(x.detail)}</span></div></div>`).join('')||'<div class="empty">Aktivite bulunamadı.</div>';$('sources').textContent=JSON.stringify(s.sources||{},null,2);renderVisuals(s.visualizations||{});renderSafeActions(s.safe_operator_actions||{})}
function renderSafeActions(actions){const locked=actions.locked||[];$('locked-actions').innerHTML=locked.map(x=>`<div class="locked-action"><strong>🔒 ${esc(x.label)}</strong><span>${esc(x.reason)}</span></div>`).join('')||'<div class="empty">Kilitli aksiyon yok.</div>'}
async function backendProbe(){const feedback=$('action-feedback');feedback.textContent='Backend health probe çalışıyor…';try{const res=await fetch('/api/operator-cockpit-v2/actions/backend-probe',{cache:'no-store'});const payload=await res.json();feedback.textContent=payload.reachable?'Backend health probe başarılı. Local backend erişilebilir.':'Backend health probe tamamlandı. Local backend şu anda erişilemiyor.';await refresh()}catch(e){feedback.textContent='Backend health probe okunamadı.'}}
async function refresh(){try{const res=await fetch('/api/operator-cockpit-v2/snapshot',{cache:'no-store'});render(await res.json())}catch(e){$('system-status').innerHTML='<span class="critical">SNAPSHOT HATASI</span>';$('operator-guidance').textContent='Local dashboard snapshot okunamadı.'}}$('refresh').addEventListener('click',refresh);$('action-backend-probe').addEventListener('click',backendProbe);document.querySelectorAll('.tab').forEach(btn=>btn.addEventListener('click',()=>{document.querySelectorAll('.tab').forEach(x=>x.classList.remove('active'));document.querySelectorAll('.tab-panel').forEach(x=>x.classList.remove('active'));btn.classList.add('active');$(btn.dataset.tab).classList.add('active')}));refresh();setInterval(refresh,15000);
</script>
</body></html>'''


_CLIENT_DISCONNECT_WINERRORS = frozenset({10053, 10054, 10058})
_CLIENT_DISCONNECT_ERRNOS = frozenset({errno.EPIPE, errno.ECONNABORTED, errno.ECONNRESET})


def _is_client_disconnect_error(error: BaseException) -> bool:
    """Return True only for expected client-side socket disconnect conditions."""
    if isinstance(error, (BrokenPipeError, ConnectionAbortedError, ConnectionResetError)):
        return True
    if not isinstance(error, OSError):
        return False
    if error.errno in _CLIENT_DISCONNECT_ERRNOS:
        return True
    return getattr(error, "winerror", None) in _CLIENT_DISCONNECT_WINERRORS


def _parse_content_length(raw_value: str | None) -> int | None:
    """Parse Content-Length without trusting malformed or negative values."""
    if raw_value is None:
        return 0
    stripped = raw_value.strip()
    if not stripped:
        return 0
    try:
        parsed = int(stripped, 10)
    except ValueError:
        return None
    return parsed if parsed >= 0 else None


def _attachment_headers(filename: str) -> dict[str, str]:
    """Return a fixed safe attachment header for allowlisted exports."""
    safe_name = "".join(character for character in filename if character.isalnum() or character in {"-", "_", "."})
    return {"Content-Disposition": f'attachment; filename="{safe_name or "operator-cockpit-export.bin"}"'}


class OperatorCockpitRequestHandler(BaseHTTPRequestHandler):
    project_root: Path = Path.cwd()
    task_query: TaskQuery | None = None
    backend_probe: BackendProbe | None = None

    def _write(self, status: HTTPStatus, body: bytes, content_type: str, *, extra_headers: Mapping[str, str] | None = None) -> None:
        try:
            self.send_response(status.value)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Operator-Cockpit-Mode", "read-only")
            for name, value in (extra_headers or {}).items():
                self.send_header(name, value)
            if getattr(self, "close_connection", False):
                self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(body)
            flush = getattr(self.wfile, "flush", None)
            if callable(flush):
                flush()
        except OSError as error:
            if _is_client_disconnect_error(error):
                return
            raise

    def _json(self, status: HTTPStatus, payload: Mapping[str, Any]) -> None:
        self._write(status, json.dumps(payload, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path in {"/", "/dashboard", "/operator-cockpit-v2"}:
            self._write(HTTPStatus.OK, DASHBOARD_HTML.encode("utf-8"), "text/html; charset=utf-8")
            return
        if path == "/api/operator-cockpit-v2/health":
            self._json(HTTPStatus.OK, {"ok": True, "read_only": True, "contract_version": OPERATOR_COCKPIT_V2_CONTRACT_VERSION})
            return
        if path == "/api/operator-cockpit-v2/snapshot":
            self._json(HTTPStatus.OK, collect_operator_cockpit_snapshot(self.project_root, task_query=self.task_query, backend_probe=self.backend_probe))
            return
        if path == "/api/operator-cockpit-v2/actions/manifest":
            self._json(HTTPStatus.OK, _safe_action_manifest(self.project_root))
            return
        if path == "/api/operator-cockpit-v2/actions/backend-probe":
            probe = dict((self.backend_probe or _default_backend_probe)(DEFAULT_BACKEND_HEALTH_URL))
            probe.update({"read_only": True, "action": "RECHECK_BACKEND_HEALTH"})
            self._json(HTTPStatus.OK, probe)
            return
        if path == "/api/operator-cockpit-v2/export/snapshot.json":
            payload = collect_operator_cockpit_snapshot(self.project_root, task_query=self.task_query, backend_probe=self.backend_probe)
            self._write(HTTPStatus.OK, json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"), "application/json; charset=utf-8", extra_headers=_attachment_headers("operator-cockpit-snapshot.json"))
            return
        if path == "/api/operator-cockpit-v2/view/risk-sizing-runtime-telemetry.json":
            telemetry = collect_risk_sizing_runtime_telemetry(self.project_root)
            self._json(HTTPStatus.OK, telemetry)
            return
        if path == "/api/operator-cockpit-v2/export/risk-sizing-evidence-pack.zip":
            try:
                body = _build_risk_sizing_in_memory_evidence_pack(self.project_root, task_query=self.task_query, backend_probe=self.backend_probe)
            except RiskSizingEvidenceExportBlocked as error:
                self._json(HTTPStatus.PRECONDITION_FAILED, {"ok": False, "error": str(error), "blockers": error.blockers, "read_only": True})
                return
            except ValueError as error:
                self._json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"ok": False, "error": str(error), "read_only": True})
                return
            self._write(HTTPStatus.OK, body, "application/zip", extra_headers=_attachment_headers("operator-cockpit-risk-sizing-evidence-pack.zip"))
            return
        if path == "/api/operator-cockpit-v2/export/evidence-pack.zip":
            try:
                body = _build_in_memory_evidence_pack(self.project_root, task_query=self.task_query, backend_probe=self.backend_probe)
            except ValueError as error:
                self._json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"ok": False, "error": str(error), "read_only": True})
                return
            self._write(HTTPStatus.OK, body, "application/zip", extra_headers=_attachment_headers("operator-cockpit-evidence-pack.zip"))
            return
        if path == "/api/operator-cockpit-v2/view/latest-audit.json":
            source = _safe_latest_export_source(self.project_root, "audit")
            if source is None:
                self._json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "LATEST_AUDIT_NOT_FOUND", "read_only": True})
                return
            try:
                body = _read_bounded_export_bytes(source)
            except ValueError as error:
                self._json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"ok": False, "error": str(error), "read_only": True})
                return
            self._write(HTTPStatus.OK, body, "application/json; charset=utf-8")
            return
        export_routes = {
            "/api/operator-cockpit-v2/export/latest-logger": "logger",
            "/api/operator-cockpit-v2/export/latest-collection": "collection",
            "/api/operator-cockpit-v2/export/latest-audit": "audit",
            "/api/operator-cockpit-v2/export/latest-ledger": "ledger",
        }
        kind = export_routes.get(path)
        if kind is not None:
            spec = SAFE_EXPORT_SOURCE_PATTERNS[kind]
            source = _safe_latest_export_source(self.project_root, kind)
            if source is None:
                self._json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "EXPORT_SOURCE_NOT_FOUND", "kind": kind, "read_only": True})
                return
            try:
                body = _read_bounded_export_bytes(source)
            except ValueError as error:
                self._json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"ok": False, "error": str(error), "read_only": True})
                return
            self._write(HTTPStatus.OK, body, spec[2], extra_headers=_attachment_headers(spec[1]))
            return
        self._json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "NOT_FOUND", "read_only": True})

    def _drain_mutation_request_body(self) -> int:
        """Consume a bounded mutation payload so Windows can deliver the HTTP 405 response cleanly."""
        transfer_encoding = (self.headers.get("Transfer-Encoding") or "").strip().lower()
        if transfer_encoding and transfer_encoding != "identity":
            self.close_connection = True
            return 0

        content_length = _parse_content_length(self.headers.get("Content-Length"))
        if content_length is None:
            self.close_connection = True
            return 0
        if content_length == 0:
            return 0

        drain_target = min(content_length, MAX_MUTATION_REQUEST_BODY_DRAIN_BYTES)
        drained = 0
        try:
            while drained < drain_target:
                chunk = self.rfile.read(min(8192, drain_target - drained))
                if not chunk:
                    self.close_connection = True
                    break
                drained += len(chunk)
        except OSError as error:
            if _is_client_disconnect_error(error):
                self.close_connection = True
                return drained
            raise

        if content_length > MAX_MUTATION_REQUEST_BODY_DRAIN_BYTES:
            self.close_connection = True
        return drained

    def _block_mutation(self) -> None:
        self._drain_mutation_request_body()
        self._json(HTTPStatus.METHOD_NOT_ALLOWED, {"ok": False, "error": "READ_ONLY_DASHBOARD_MUTATION_BLOCKED", "read_only": True})

    def do_POST(self) -> None:  # noqa: N802
        self._block_mutation()

    def do_PUT(self) -> None:  # noqa: N802
        self._block_mutation()

    def do_PATCH(self) -> None:  # noqa: N802
        self._block_mutation()

    def do_DELETE(self) -> None:  # noqa: N802
        self._block_mutation()

    def log_message(self, format: str, *args: object) -> None:
        return


def make_operator_cockpit_server(
    project_root: Path,
    *,
    host: str = "127.0.0.1",
    port: int = 8090,
    task_query: TaskQuery | None = None,
    backend_probe: BackendProbe | None = None,
) -> ThreadingHTTPServer:
    handler = type("BoundOperatorCockpitRequestHandler", (OperatorCockpitRequestHandler,), {})
    handler.project_root = project_root.resolve()
    handler.task_query = staticmethod(task_query) if task_query is not None else None
    handler.backend_probe = staticmethod(backend_probe) if backend_probe is not None else None
    return ThreadingHTTPServer((host, port), handler)
