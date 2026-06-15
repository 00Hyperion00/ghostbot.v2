from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

OPERATOR_COCKPIT_HYP006_EXPORT_BINDING_VERSION = "4B.4.3.6.6.28F-H2"
HYP006_REPORTS_RELATIVE_DIR = Path("reports") / "hyp006_r1_canonical"

# kind -> (latest-file pattern, safe download name, content type)
HYP006_SAFE_EXPORT_SOURCE_PATTERNS: dict[str, tuple[str, str, str]] = {
    "logger": (
        "4B436628D_hyp006_r1_shadow_observation_logger_*.json",
        "latest-hyp006-shadow-logger.json",
        "application/json; charset=utf-8",
    ),
    "collection": (
        "4B436628G_hyp006_r1_shadow_sample_expansion_acceptance_tracking_*.json",
        "latest-hyp006-acceptance-tracking.json",
        "application/json; charset=utf-8",
    ),
    "audit": (
        "4B436628F_hyp006_r1_operator_cockpit_baseline_*.json",
        "latest-hyp006-operator-cockpit-baseline.json",
        "application/json; charset=utf-8",
    ),
    "ledger": (
        "4B436628D_hyp006_r1_shadow_ledger_*.jsonl",
        "latest-hyp006-shadow-ledger.jsonl",
        "application/x-ndjson; charset=utf-8",
    ),
}


def hyp006_reports_dir(project_root: Path) -> Path:
    return project_root.resolve() / HYP006_REPORTS_RELATIVE_DIR


def latest_file(directory: Path, pattern: str) -> Path | None:
    if not directory.exists():
        return None
    candidates = [path for path in directory.glob(pattern) if path.is_file()]
    if not candidates:
        return None
    return max(candidates, key=lambda path: (path.stat().st_mtime_ns, path.name))


def latest_hyp006_export_source(project_root: Path, kind: str) -> Path | None:
    spec = HYP006_SAFE_EXPORT_SOURCE_PATTERNS.get(kind)
    if spec is None:
        return None
    reports_dir = hyp006_reports_dir(project_root)
    source = latest_file(reports_dir, spec[0])
    if source is None:
        return None
    resolved = source.resolve()
    try:
        resolved.relative_to(reports_dir.resolve())
    except ValueError:
        return None
    return resolved


def relative_or_name(path: Path | None, root: Path) -> str | None:
    if path is None:
        return None
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def expected_export_manifest(project_root: Path) -> list[dict[str, Any]]:
    root = project_root.resolve()
    output: list[dict[str, Any]] = []
    for kind, (_, download_name, content_type) in HYP006_SAFE_EXPORT_SOURCE_PATTERNS.items():
        source = latest_hyp006_export_source(root, kind)
        output.append(
            {
                "kind": kind,
                "available": source is not None,
                "download_name": download_name,
                "content_type": content_type,
                "source": relative_or_name(source, root),
                "endpoint": f"/api/operator-cockpit-v2/export/latest-{kind}",
                "branch_id": "HYP-006-R1",
                "namespace": "HYP006_R1",
                "legacy_hyp005_source_suppressed": True,
            }
        )
    return output


def export_source_parity_ok(exports: Any) -> bool:
    if not isinstance(exports, list) or not exports:
        return False
    for item in exports:
        if not isinstance(item, Mapping):
            return False
        source = str(item.get("source") or "")
        download_name = str(item.get("download_name") or "")
        if item.get("available") is True:
            if "hyp006_r1_canonical" not in source.replace("\\", "/"):
                return False
            if "hyp005" in source.lower() or "25v" in download_name.lower() or "25x" in download_name.lower() or "25y" in download_name.lower():
                return False
    return True
