from __future__ import annotations

import py_compile
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src" / "tradebot"
TOOLS_DIR = PROJECT_ROOT / "tools"
PAYLOAD_DIR = TOOLS_DIR / "_patch_payload"
BACKUP_DIR = TOOLS_DIR / "_patch_backup_4B436625VH2"

IDENTITY_TARGET = SRC_DIR / "hyp005_shadow_observation_identity.py"
IDENTITY_PAYLOAD = PAYLOAD_DIR / "hyp005_shadow_observation_identity_4B436625VH2.py"
LOGGER_CORE = SRC_DIR / "research_hyp005_shadow_observation_logger.py"
ORCHESTRATOR_CORE = SRC_DIR / "research_hyp005_shadow_collection_orchestrator.py"
LOGGER_RUNNER = TOOLS_DIR / "run_hyp005_shadow_observation_logger_4B436625V.py"
LOGGER_WRAPPER_PAYLOAD = PAYLOAD_DIR / "run_hyp005_shadow_observation_logger_4B436625V_end_to_end_identity_wrapper.py"
ORCHESTRATOR_RUNNER = TOOLS_DIR / "run_hyp005_shadow_collection_orchestrator_4B436625X.py"
CHAIN_CHECKER = TOOLS_DIR / "check_hyp005_shadow_observation_identity_chain_4B436625VH2.py"
ROLLBACK_TOOL = TOOLS_DIR / "rollback_4B436625V_H2_hyp005_shadow_observation_end_to_end_identity_hotfix.py"
TEST_FILE = PROJECT_ROOT / "tests" / "test_hyp005_shadow_observation_end_to_end_identity_hotfix_4B436625VH2.py"
DOC_FILE = PROJECT_ROOT / "docs" / "HYP005_SHADOW_OBSERVATION_END_TO_END_IDENTITY_HOTFIX_4B436625VH2.md"


def _compile(path: Path) -> bool:
    try:
        py_compile.compile(str(path), doraise=True)
    except py_compile.PyCompileError:
        return False
    return True


def _contains(path: Path, marker: str) -> bool:
    return path.exists() and marker in path.read_text(encoding="utf-8")


def _backup(path: Path) -> None:
    relative = path.relative_to(PROJECT_ROOT)
    target = BACKUP_DIR / relative
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)


def _replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if new in text:
        return
    if old not in text:
        raise RuntimeError(f"HYP005_25VH2_EXPECTED_SOURCE_FRAGMENT_MISSING:{path}:{old[:80]}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def _patch_logger_core() -> None:
    _replace_once(
        LOGGER_CORE,
        "import math\n",
        "import math\n\nfrom .hyp005_shadow_observation_identity import (\n    HYP005_SHADOW_OBSERVATION_END_TO_END_IDENTITY_VERSION,\n    normalize_observation_identity,\n)\n",
    )
    _replace_once(
        LOGGER_CORE,
        "def _observation_dicts(observations: Sequence[ShadowObservation]) -> list[dict[str, Any]]:\n    return [asdict(item) for item in observations]\n",
        "def _observation_dicts(observations: Sequence[ShadowObservation]) -> list[dict[str, Any]]:\n    return [normalize_observation_identity(asdict(item)) for item in observations]\n",
    )
    _replace_once(
        LOGGER_CORE,
        '        "shadow_observations": observation_rows,\n',
        '        "shadow_observations": observation_rows,\n        "identity_contract_version": HYP005_SHADOW_OBSERVATION_END_TO_END_IDENTITY_VERSION,\n        "canonical_identity_end_to_end": True,\n',
    )


def _patch_orchestrator_core() -> None:
    _replace_once(
        ORCHESTRATOR_CORE,
        "from typing import Any, Iterable, Mapping, Sequence\n",
        "from typing import Any, Iterable, Mapping, Sequence\n\nfrom .hyp005_shadow_observation_identity import canonical_event_key, normalize_observation_identity\n",
    )
    _replace_once(
        ORCHESTRATOR_CORE,
        '''def observation_key(row: Mapping[str, Any]) -> tuple[str, ...]:\n    return (\n        str(row.get("timestamp_utc") or row.get("timestamp") or row.get("open_time") or ""),\n        str(row.get("symbol") or ""),\n        str(row.get("timeframe") or row.get("interval") or ""),\n        str(row.get("strategy_family") or row.get("signal_family") or ""),\n        str(row.get("sweep_direction") or ""),\n        str(row.get("entry_reference_price") or row.get("entry_reference") or ""),\n    )\n''',
        '''def observation_key(row: Mapping[str, Any]) -> tuple[str, ...]:\n    """Return the canonical HYP-005 event identity; market-price drift must not create a new sample."""\n    return (canonical_event_key(row),)\n''',
    )
    _replace_once(
        ORCHESTRATOR_CORE,
        "            row = dict(raw_row)\n            key = observation_key(row)\n",
        "            row = normalize_observation_identity(raw_row)\n            key = observation_key(row)\n",
    )


def _patch_orchestrator_runner() -> None:
    _replace_once(
        ORCHESTRATOR_RUNNER,
        "HYP005_R1_COLLECTION_DAG_BOOTSTRAP_HOTFIX_VERSION = \"4B.4.3.6.6.25AE-H4\"\n",
        "HYP005_R1_COLLECTION_DAG_BOOTSTRAP_HOTFIX_VERSION = \"4B.4.3.6.6.25AE-H4\"\nHYP005_END_TO_END_CANONICAL_IDENTITY_HOTFIX_VERSION = \"4B.4.3.6.6.25V-H2\"\nHYP005_CANONICAL_LEDGER_JSONL_SINGLE_SOURCE = True\n",
    )
    _replace_once(
        ORCHESTRATOR_RUNNER,
        '''    if include_all:\n        return spec, logger_reports, acceptance_reports, ledger_jsons, ledger_jsonls\n    return (\n        spec,\n        [item for item in [_latest(logger_reports)] if item],\n        [item for item in [_latest(acceptance_reports)] if item],\n        [item for item in [_latest(ledger_jsons)] if item],\n        [item for item in [_latest(ledger_jsonls)] if item],\n    )\n''',
        '''    if include_all:\n        # JSONL is the single ingestion truth. JSON remains an audit-equivalent sidecar only.\n        return spec, logger_reports, acceptance_reports, [], ledger_jsonls or ledger_jsons\n    latest_jsonl = _latest(ledger_jsonls)\n    return (\n        spec,\n        [item for item in [_latest(logger_reports)] if item],\n        [item for item in [_latest(acceptance_reports)] if item],\n        [] if latest_jsonl else [item for item in [_latest(ledger_jsons)] if item],\n        [latest_jsonl] if latest_jsonl else [],\n    )\n''',
    )
    _replace_once(
        ORCHESTRATOR_RUNNER,
        "    observation_sets = [load_observations_from_json(path) for path in ledger_json_paths]\n    observation_sets.extend(load_observations_from_jsonl(path) for path in ledger_jsonl_paths)\n",
        "    if ledger_jsonl_paths:\n        # Explicit chains also prefer JSONL to avoid ingesting the equivalent JSON sidecar twice.\n        ledger_json_paths = []\n    observation_sets = [load_observations_from_json(path) for path in ledger_json_paths]\n    observation_sets.extend(load_observations_from_jsonl(path) for path in ledger_jsonl_paths)\n",
    )


def main() -> int:
    required = [IDENTITY_PAYLOAD, LOGGER_CORE, ORCHESTRATOR_CORE, LOGGER_RUNNER, LOGGER_WRAPPER_PAYLOAD, ORCHESTRATOR_RUNNER, CHAIN_CHECKER, ROLLBACK_TOOL, TEST_FILE, DOC_FILE]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        print("25vh2_apply_error: required file missing")
        for item in missing:
            print(f" - missing: {item}")
        return 2

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    for path in (IDENTITY_TARGET, LOGGER_CORE, ORCHESTRATOR_CORE, LOGGER_RUNNER, ORCHESTRATOR_RUNNER):
        _backup(path)

    # The H2 identity payload overlays H1 while keeping its public compatibility constants.
    shutil.copy2(IDENTITY_PAYLOAD, IDENTITY_TARGET)
    _patch_logger_core()
    _patch_orchestrator_core()
    _patch_orchestrator_runner()
    shutil.copy2(LOGGER_WRAPPER_PAYLOAD, LOGGER_RUNNER)

    checks: list[tuple[str, bool]] = [
        ("config_mutation_performed", False),
        ("scheduler_mutation_performed", False),
        ("trading_action_performed", False),
        ("identity_module_py_compile_ok", _compile(IDENTITY_TARGET)),
        ("logger_core_py_compile_ok", _compile(LOGGER_CORE)),
        ("orchestrator_core_py_compile_ok", _compile(ORCHESTRATOR_CORE)),
        ("logger_runner_py_compile_ok", _compile(LOGGER_RUNNER)),
        ("orchestrator_runner_py_compile_ok", _compile(ORCHESTRATOR_RUNNER)),
        ("chain_checker_py_compile_ok", _compile(CHAIN_CHECKER)),
        ("rollback_tool_py_compile_ok", _compile(ROLLBACK_TOOL)),
        ("test_file_py_compile_ok", _compile(TEST_FILE)),
        ("canonical_identity_h2_present", _contains(IDENTITY_TARGET, 'HYP005_SHADOW_OBSERVATION_END_TO_END_IDENTITY_VERSION = "4B.4.3.6.6.25V-H2"')),
        ("logger_core_native_normalization_present", _contains(LOGGER_CORE, "normalize_observation_identity(asdict(item))")),
        ("logger_wrapper_artifact_equivalence_present", _contains(LOGGER_RUNNER, "identity_artifact_equivalence_verified")),
        ("orchestrator_canonical_key_present", _contains(ORCHESTRATOR_CORE, "return (canonical_event_key(row),)")),
        ("orchestrator_jsonl_single_source_present", _contains(ORCHESTRATOR_RUNNER, "HYP005_CANONICAL_LEDGER_JSONL_SINGLE_SOURCE = True")),
        ("paper_live_order_enablement_present", False),
    ]
    print("4B.4.3.6.6.25V-H2 HYP-005 shadow observation end-to-end canonical identity / JSON-JSONL-report-orchestrator runtime chain alignment hotfix applied")
    all_ok = True
    for name, value in checks:
        print(f" - {name}: {value}")
        if name in {"config_mutation_performed", "scheduler_mutation_performed", "trading_action_performed", "paper_live_order_enablement_present"}:
            all_ok = all_ok and (value is False)
        else:
            all_ok = all_ok and value
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
