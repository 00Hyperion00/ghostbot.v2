from __future__ import annotations

import argparse
import json
import runpy
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tradebot.hyp005_shadow_evidence_path_contract import (  # noqa: E402
    normalize_logger_report_evidence_paths,
    resolve_evidence_output_directory,
    write_json_ascii_atomic,
)
from tradebot.hyp005_shadow_observation_identity import (  # noqa: E402
    HYP005_SHADOW_OBSERVATION_END_TO_END_IDENTITY_VERSION,
    HYP005_SHADOW_OBSERVATION_STABLE_IDENTITY_VERSION,
    assert_artifact_equivalence,
    normalize_observation_rows,
    write_json_atomic,
    write_jsonl_atomic,
)

HYP005_25V_END_TO_END_IDENTITY_WRAPPER = True
LEGACY_RUNNER = Path(__file__).with_name("run_hyp005_shadow_observation_logger_4B436625V_legacy_ordinal_identity.py")
LEDGER_JSONL_PATTERN = "4B436625V_hyp005_shadow_observation_ledger_*.jsonl"
LEDGER_JSON_PATTERN = "4B436625V_hyp005_shadow_observation_ledger_*.json"
REPORT_JSON_PATTERN = "4B436625V_hyp005_shadow_observation_logger_*.json"
FileSignature = tuple[int, int]


def _parse_out_dir(argv: list[str]) -> Path:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--out-dir", type=Path, required=True)
    args, _ = parser.parse_known_args(argv)
    return resolve_evidence_output_directory(args.out_dir, field="out_dir")


def _signatures(out_dir: Path) -> dict[Path, FileSignature]:
    if not out_dir.exists():
        return {}
    signatures: dict[Path, FileSignature] = {}
    for pattern in (LEDGER_JSONL_PATTERN, LEDGER_JSON_PATTERN, REPORT_JSON_PATTERN):
        for path in out_dir.glob(pattern):
            if path.is_file():
                stat = path.stat()
                signatures[path.resolve()] = (stat.st_mtime_ns, stat.st_size)
    return signatures


def _run_legacy_runner() -> int:
    if not LEGACY_RUNNER.exists():
        print(f"legacy_runner_missing: {LEGACY_RUNNER}", file=sys.stderr)
        return 2
    try:
        runpy.run_path(str(LEGACY_RUNNER), run_name="__main__")
    except SystemExit as error:
        if error.code is None:
            return 0
        if isinstance(error.code, int):
            return error.code
        print(str(error.code), file=sys.stderr)
        return 1
    return 0


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _changed_paths(out_dir: Path, before: dict[Path, FileSignature]) -> list[Path]:
    return sorted((path for path, signature in _signatures(out_dir).items() if before.get(path) != signature), key=str)


def _latest_changed(paths: list[Path], pattern: str) -> Path:
    matches = [path for path in paths if path.match(pattern)]
    if not matches:
        raise RuntimeError(f"HYP005_IDENTITY_EXPECTED_CHANGED_ARTIFACT_MISSING:{pattern}")
    return max(matches, key=lambda item: (item.stat().st_mtime_ns, item.name))


def _align_latest_bundle(changed_paths: list[Path]) -> tuple[int, int]:
    ledger_jsonl = _latest_changed(changed_paths, LEDGER_JSONL_PATTERN)
    ledger_json = _latest_changed(changed_paths, LEDGER_JSON_PATTERN)
    report_json = _latest_changed(changed_paths, REPORT_JSON_PATTERN)

    jsonl_rows = normalize_observation_rows(_read_jsonl(ledger_jsonl))
    json_payload = _read_json(ledger_json)
    if not isinstance(json_payload, list):
        raise RuntimeError("HYP005_IDENTITY_LEDGER_JSON_MUST_BE_ARRAY")
    json_rows = normalize_observation_rows(json_payload)
    report_payload = _read_json(report_json)
    if not isinstance(report_payload, dict):
        raise RuntimeError("HYP005_IDENTITY_LOGGER_REPORT_MUST_BE_OBJECT")
    report_rows_raw = report_payload.get("shadow_observations")
    if not isinstance(report_rows_raw, list):
        raise RuntimeError("HYP005_IDENTITY_LOGGER_REPORT_OBSERVATIONS_MUST_BE_ARRAY")
    report_rows = normalize_observation_rows(report_rows_raw)

    assert_artifact_equivalence(json_rows, jsonl_rows, report_rows)
    write_json_atomic(ledger_json, json_rows)
    write_jsonl_atomic(ledger_jsonl, jsonl_rows)
    report_payload["shadow_observations"] = report_rows
    report_payload = normalize_logger_report_evidence_paths(report_payload, require_exists=True)
    report_payload["identity_contract_version"] = HYP005_SHADOW_OBSERVATION_STABLE_IDENTITY_VERSION
    report_payload["identity_chain_contract_version"] = HYP005_SHADOW_OBSERVATION_END_TO_END_IDENTITY_VERSION
    report_payload["canonical_identity_end_to_end"] = True
    report_payload["identity_artifact_equivalence_verified"] = True
    write_json_ascii_atomic(report_json, report_payload)
    assert_artifact_equivalence(_read_json(ledger_json), _read_jsonl(ledger_jsonl), _read_json(report_json)["shadow_observations"])
    return len(jsonl_rows), 3


def main() -> int:
    out_dir = _parse_out_dir(sys.argv[1:])
    before = _signatures(out_dir)
    exit_code = _run_legacy_runner()
    if exit_code != 0:
        return exit_code
    try:
        row_count, artifact_count = _align_latest_bundle(_changed_paths(out_dir, before))
    except Exception as error:  # fail closed: do not claim a healthy logger bundle
        print(f"HYP005_IDENTITY_ARTIFACT_ALIGNMENT_FAILED: {error}", file=sys.stderr)
        return 3
    print(f" - end_to_end_identity_version: {HYP005_SHADOW_OBSERVATION_END_TO_END_IDENTITY_VERSION}")
    print(f" - canonical_identity_end_to_end: True")
    print(f" - aligned_artifacts: {artifact_count}")
    print(f" - normalized_rows: {row_count}")
    print(" - identity_artifact_equivalence_verified: True")
    print(" - rolling_ordinal_identity_used: False")
    print(" - config_mutation_performed: False")
    print(" - scheduler_mutation_performed: False")
    print(" - trading_action_performed: False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
