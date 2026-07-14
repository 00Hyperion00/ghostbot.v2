from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

HYP005_SHADOW_EVIDENCE_PATH_UTF8_CONTRACT_VERSION = "4B.4.3.6.6.27G-H2"
HYP005_SHADOW_EVIDENCE_PATH_UTF8_NORMALIZATION = True
HYP005_SHADOW_EVIDENCE_PATH_FAIL_CLOSED_RESOLUTION = True
HYP005_SHADOW_EVIDENCE_PATH_POWERSHELL_SAFE_ASCII_JSON = True

_PATH_FIELDS = ("ledger_json", "ledger_jsonl")
_PATH_LIST_FIELDS = ("source_reports",)


def _path_text(value: str | os.PathLike[str]) -> str:
    return os.fspath(value).strip()


def _repair_reversible_utf8_mojibake(text: str) -> str | None:
    """Return a reversible UTF-8 repair candidate, or None when no safe candidate exists."""
    try:
        repaired = text.encode("latin-1", errors="strict").decode("utf-8", errors="strict")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return None
    return repaired if repaired != text else None


def _candidate_paths(value: str | os.PathLike[str]) -> list[Path]:
    raw = _path_text(value)
    if not raw:
        return []
    values = [raw]
    repaired = _repair_reversible_utf8_mojibake(raw)
    if repaired and repaired not in values:
        values.append(repaired)
    return [Path(item).expanduser() for item in values]


def resolve_existing_evidence_path(
    value: str | os.PathLike[str],
    *,
    field: str,
    expect_directory: bool | None = None,
) -> Path:
    """Resolve an existing evidence path, preferring the exact input and repairing only when required."""
    candidates = _candidate_paths(value)
    for candidate in candidates:
        if not candidate.exists():
            continue
        resolved = candidate.resolve()
        if expect_directory is True and not resolved.is_dir():
            continue
        if expect_directory is False and not resolved.is_file():
            continue
        return resolved
    raise ValueError(f"HYP005_EVIDENCE_PATH_UNRESOLVED:{field}:{_path_text(value)}")


def resolve_existing_evidence_directory(value: str | os.PathLike[str], *, field: str) -> Path:
    return resolve_existing_evidence_path(value, field=field, expect_directory=True)


def resolve_evidence_output_directory(value: str | os.PathLike[str], *, field: str) -> Path:
    """Resolve or create an output directory without allowing a mojibake shadow directory."""
    candidates = _candidate_paths(value)
    for candidate in candidates:
        if candidate.exists() and candidate.is_dir():
            return candidate.resolve()
    for candidate in candidates:
        parent = candidate.parent
        if parent.exists() and parent.is_dir():
            candidate.mkdir(parents=True, exist_ok=True)
            return candidate.resolve()
    raise ValueError(f"HYP005_EVIDENCE_OUTPUT_DIR_UNRESOLVED:{field}:{_path_text(value)}")


def serialize_evidence_path(value: str | os.PathLike[str]) -> str:
    return str(Path(value).resolve())


def normalize_logger_report_evidence_paths(
    payload: Mapping[str, Any],
    *,
    require_exists: bool = True,
) -> dict[str, Any]:
    """Normalize logger evidence references and fail closed when mandatory artifacts cannot be resolved."""
    normalized = dict(payload)
    for field in _PATH_FIELDS:
        raw = normalized.get(field)
        if raw is None or str(raw).strip() == "":
            raise ValueError(f"HYP005_EVIDENCE_PATH_MISSING:{field}")
        if require_exists:
            normalized[field] = serialize_evidence_path(resolve_existing_evidence_path(str(raw), field=field, expect_directory=False))
        else:
            candidates = _candidate_paths(str(raw))
            normalized[field] = serialize_evidence_path(candidates[0]) if candidates else str(raw)

    for field in _PATH_LIST_FIELDS:
        raw_values = normalized.get(field)
        if not isinstance(raw_values, Sequence) or isinstance(raw_values, (str, bytes)) or not raw_values:
            raise ValueError(f"HYP005_EVIDENCE_PATH_LIST_MISSING:{field}")
        values: list[str] = []
        for index, raw in enumerate(raw_values):
            label = f"{field}[{index}]"
            if require_exists:
                values.append(serialize_evidence_path(resolve_existing_evidence_path(str(raw), field=label, expect_directory=False)))
            else:
                candidates = _candidate_paths(str(raw))
                values.append(serialize_evidence_path(candidates[0]) if candidates else str(raw))
        normalized[field] = values

    normalized["evidence_path_contract_version"] = HYP005_SHADOW_EVIDENCE_PATH_UTF8_CONTRACT_VERSION
    normalized["evidence_paths_resolved"] = True
    normalized["powershell_safe_ascii_json"] = True
    return normalized


def _atomic_write(path: Path, payload: bytes) -> None:
    resolved = path.resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="wb",
        prefix=f".{resolved.name}.",
        suffix=".tmp",
        dir=resolved.parent,
        delete=False,
    ) as handle:
        temp_path = Path(handle.name)
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        temp_path.replace(resolved)
    finally:
        temp_path.unlink(missing_ok=True)


def write_json_ascii_atomic(path: str | os.PathLike[str], payload: Any) -> None:
    """Write ASCII-escaped JSON so Windows PowerShell 5.1 default Get-Content cannot mojibake Unicode paths."""
    text = json.dumps(payload, ensure_ascii=True, sort_keys=True, indent=2) + "\n"
    _atomic_write(Path(path), text.encode("utf-8"))
