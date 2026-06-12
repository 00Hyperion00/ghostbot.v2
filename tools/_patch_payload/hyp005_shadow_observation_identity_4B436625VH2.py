from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Iterable, Mapping, MutableMapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HYP005_SHADOW_OBSERVATION_STABLE_IDENTITY_VERSION = "4B.4.3.6.6.25V-H1"
HYP005_SHADOW_OBSERVATION_END_TO_END_IDENTITY_VERSION = "4B.4.3.6.6.25V-H2"
HYP005_SHADOW_OBSERVATION_STABLE_IDENTITY = True
HYP005_SHADOW_OBSERVATION_END_TO_END_CANONICAL_IDENTITY = True
HYP005_SHADOW_OBSERVATION_ROLLING_ORDINAL_DISABLED = True
HYP005_SHADOW_OBSERVATION_LEGACY_ID_PRESERVED = True

JsonObject = dict[str, Any]


def _non_empty_text(value: object, *, field: str) -> str:
    text = str(value).strip() if value is not None else ""
    if not text:
        raise ValueError(f"HYP005_STABLE_IDENTITY_MISSING_FIELD:{field}")
    return text


def _parse_timestamp_utc(value: object) -> datetime:
    text = _non_empty_text(value, field="timestamp_utc")
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as error:
        raise ValueError("HYP005_STABLE_IDENTITY_INVALID_TIMESTAMP") from error
    if parsed.tzinfo is None:
        raise ValueError("HYP005_STABLE_IDENTITY_TIMESTAMP_MUST_BE_TIMEZONE_AWARE")
    return parsed.astimezone(timezone.utc)


def canonical_timestamp_token(value: object) -> str:
    """Return a stable compact UTC timestamp token for observation IDs."""
    return _parse_timestamp_utc(value).strftime("%Y-%m-%dT%H%M%SZ")


def canonical_event_key(observation: Mapping[str, Any]) -> str:
    """Build a stable event key independent from rolling-window ordinal position."""
    hypothesis_id = _non_empty_text(observation.get("hypothesis_id", "HYP-005"), field="hypothesis_id")
    symbol = _non_empty_text(observation.get("symbol"), field="symbol").upper()
    timeframe = _non_empty_text(
        observation.get("timeframe", observation.get("interval", "4h")),
        field="timeframe",
    )
    timestamp_token = canonical_timestamp_token(
        observation.get("timestamp_utc", observation.get("timestamp", observation.get("open_time")))
    )
    return "|".join((hypothesis_id, symbol, timeframe, timestamp_token))


def stable_observation_id(observation: Mapping[str, Any]) -> str:
    """Build an immutable identity from hypothesis, symbol, timeframe and UTC candle timestamp."""
    hypothesis_id, symbol, timeframe, timestamp_token = canonical_event_key(observation).split("|", maxsplit=3)
    return f"{hypothesis_id}-{symbol}-{timeframe}-{timestamp_token}"


def normalize_observation_identity(observation: Mapping[str, Any]) -> JsonObject:
    """Return a copy with canonical identity while retaining the former ID for auditability."""
    normalized: JsonObject = dict(observation)
    new_id = stable_observation_id(normalized)
    previous_id = normalized.get("observation_id")
    if previous_id and str(previous_id) != new_id:
        normalized.setdefault("legacy_observation_id", str(previous_id))
    normalized["observation_id"] = new_id
    normalized["identity_contract_version"] = HYP005_SHADOW_OBSERVATION_STABLE_IDENTITY_VERSION
    normalized["identity_chain_contract_version"] = HYP005_SHADOW_OBSERVATION_END_TO_END_IDENTITY_VERSION
    normalized["identity_event_key"] = canonical_event_key(normalized)
    return normalized


def normalize_observation_rows(rows: Iterable[Mapping[str, Any]]) -> list[JsonObject]:
    """Normalize rows at an artifact or ingestion boundary and reject non-object rows."""
    normalized: list[JsonObject] = []
    for row in rows:
        if not isinstance(row, Mapping):
            raise ValueError("HYP005_STABLE_IDENTITY_ROW_MUST_BE_OBJECT")
        normalized.append(normalize_observation_identity(row))
    return normalized


def canonical_identity_ids(rows: Iterable[Mapping[str, Any]]) -> list[str]:
    return [stable_observation_id(row) for row in rows]


def assert_artifact_equivalence(*artifacts: Sequence[Mapping[str, Any]]) -> None:
    """Fail closed unless JSON, JSONL and report observations contain the same canonical sequence."""
    if len(artifacts) < 2:
        return
    expected = canonical_identity_ids(artifacts[0])
    for rows in artifacts[1:]:
        if canonical_identity_ids(rows) != expected:
            raise ValueError("HYP005_IDENTITY_ARTIFACT_EQUIVALENCE_FAILED")


def normalize_jsonl_lines(lines: Iterable[str]) -> tuple[list[str], int]:
    """Normalize non-empty JSONL lines and return serialized lines plus changed-row count."""
    serialized: list[str] = []
    changed = 0
    for line in lines:
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, MutableMapping):
            raise ValueError("HYP005_STABLE_IDENTITY_JSONL_ROW_MUST_BE_OBJECT")
        normalized = normalize_observation_identity(row)
        if normalized != row:
            changed += 1
        serialized.append(json.dumps(normalized, ensure_ascii=False, sort_keys=True))
    return serialized, changed


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


def write_json_atomic(path: Path, payload: Any) -> None:
    _atomic_write(path, (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8"))


def write_jsonl_atomic(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    payload = "".join(json.dumps(dict(row), ensure_ascii=False, sort_keys=True) + "\n" for row in rows).encode("utf-8")
    _atomic_write(path, payload)


def normalize_jsonl_file(path: Path) -> int:
    """Atomically normalize one newly emitted 25V JSONL ledger in place."""
    resolved = path.resolve()
    lines = resolved.read_text(encoding="utf-8").splitlines()
    serialized, changed = normalize_jsonl_lines(lines)
    _atomic_write(resolved, ("\n".join(serialized) + ("\n" if serialized else "")).encode("utf-8"))
    return changed
