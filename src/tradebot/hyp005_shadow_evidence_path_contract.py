from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

HYP005_SHADOW_EVIDENCE_PATH_UTF8_CONTRACT_VERSION = "4B.4.3.6.6.27G-H2"
UTF8_PATH_CONTRACT_VERSION = HYP005_SHADOW_EVIDENCE_PATH_UTF8_CONTRACT_VERSION
_MOJIBAKE_MARKERS = ("Ã", "Ä", "Å", "Â", "�")


def _mojibake_score(text: str) -> tuple[int, int]:
    return (sum(text.count(marker) for marker in _MOJIBAKE_MARKERS), len(text))


def repair_reversible_mojibake(value: str) -> str:
    text = str(value)
    candidates = [text]
    for encoding in ("latin-1", "cp1252"):
        try:
            candidates.append(text.encode(encoding).decode("utf-8"))
        except Exception:
            pass
    return min(dict.fromkeys(candidates), key=_mojibake_score)


def resolve_existing_evidence_path(
    value: str | os.PathLike[str],
    *,
    field: str = "path",
    expect_directory: bool = False,
    required: bool = True,
) -> Path | None:
    raw = os.fspath(value)
    for candidate in dict.fromkeys((raw, repair_reversible_mojibake(raw))):
        path = Path(candidate)
        try:
            valid = path.exists() and (path.is_dir() if expect_directory else path.is_file())
        except OSError:
            valid = False
        if valid:
            return path.resolve()
    if required:
        raise ValueError(f"HYP005_EVIDENCE_PATH_UNRESOLVED:{field}:{raw}")
    return None


def resolve_evidence_output_directory(
    value: str | os.PathLike[str] | None = None,
    *,
    field: str = "out_dir",
    create: bool = True,
    required: bool = True,
) -> Path | None:
    if value is None:
        if required:
            raise ValueError(f"HYP005_EVIDENCE_OUTPUT_DIRECTORY_MISSING:{field}")
        return None
    path = Path(repair_reversible_mojibake(os.fspath(value)))
    if create:
        path.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.is_dir():
        return path.resolve()
    if required:
        raise ValueError(f"HYP005_EVIDENCE_OUTPUT_DIRECTORY_UNRESOLVED:{field}:{value}")
    return None


def normalize_logger_report_evidence_paths(
    payload: dict[str, Any],
    *,
    require_exists: bool = False,
) -> dict[str, Any]:
    result = dict(payload)
    for key in ("ledger_json", "ledger_jsonl", "logger_json", "candidate_spec_json"):
        value = result.get(key)
        if value:
            resolved = resolve_existing_evidence_path(value, field=key, required=require_exists)
            result[key] = str(
                resolved
                if resolved is not None
                else Path(repair_reversible_mojibake(os.fspath(value)))
            )
    reports: list[str] = []
    for value in result.get("source_reports") or []:
        resolved = resolve_existing_evidence_path(
            value,
            field="source_reports",
            required=require_exists,
        )
        reports.append(
            str(
                resolved
                if resolved is not None
                else Path(repair_reversible_mojibake(os.fspath(value)))
            )
        )
    if "source_reports" in result:
        result["source_reports"] = reports
    result["utf8_path_contract_version"] = HYP005_SHADOW_EVIDENCE_PATH_UTF8_CONTRACT_VERSION
    result["evidence_paths_resolved"] = True
    result["powershell_safe_ascii_json"] = True
    return result


def write_json_ascii_atomic(path: str | os.PathLike[str], payload: Any) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(
        prefix=target.name + ".",
        suffix=".tmp",
        dir=str(target.parent),
    )
    temporary = Path(temp_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=True, sort_keys=True, indent=2)
            handle.write("\n")
        temporary.replace(target)
    finally:
        try:
            if temporary.exists():
                temporary.unlink()
        except OSError:
            pass
    return target
