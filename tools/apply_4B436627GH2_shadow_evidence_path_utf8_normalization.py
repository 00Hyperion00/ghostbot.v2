from __future__ import annotations

import json
import py_compile
import shutil
import sys
from pathlib import Path

CONTRACT_VERSION = "4B.4.3.6.6.27G-H2"
ROOT = Path(__file__).resolve().parents[1]
BACKUP = ROOT / "tools" / "_patch_backup_4B436627GH2"
PAYLOAD = ROOT / "tools" / "_patch_payload_4B436627GH2"
CREATED = BACKUP / ".created_files.json"

LEGACY = ROOT / "tools" / "run_hyp005_shadow_observation_logger_4B436625V_legacy_ordinal_identity.py"
WRAPPER = ROOT / "tools" / "run_hyp005_shadow_observation_logger_4B436625V.py"
EPOCH_PS1 = ROOT / "tools" / "run_hyp005_r1_canonical_epoch_cycle_4B436625AEH5.ps1"
MODULE = ROOT / "src" / "tradebot" / "hyp005_shadow_evidence_path_contract.py"
CHECKER = ROOT / "tools" / "check_4B436627GH2_shadow_evidence_path_utf8_normalization.py"
ROLLBACK = ROOT / "tools" / "rollback_4B436627GH2_shadow_evidence_path_utf8_normalization.py"
TEST = ROOT / "tests" / "test_shadow_evidence_path_utf8_normalization_4B436627GH2.py"


def _replace_once(text: str, old: str, new: str, *, label: str) -> str:
    if new in text:
        return text
    if old not in text:
        raise RuntimeError(f"PATCH_ANCHOR_MISSING:{label}")
    return text.replace(old, new, 1)


def _backup(path: Path) -> None:
    if not path.exists():
        raise RuntimeError(f"REQUIRED_FILE_MISSING:{path.relative_to(ROOT)}")
    destination = BACKUP / path.relative_to(ROOT)
    if not destination.exists():
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _install_module() -> list[str]:
    source = PAYLOAD / "src" / "tradebot" / "hyp005_shadow_evidence_path_contract.py"
    if not source.exists():
        raise RuntimeError("PATCH_PAYLOAD_MISSING:hyp005_shadow_evidence_path_contract.py")
    created: list[str] = []
    if not MODULE.exists():
        created.append(str(MODULE.relative_to(ROOT)))
    MODULE.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, MODULE)
    return created


def _patch_legacy() -> None:
    _backup(LEGACY)
    text = LEGACY.read_text(encoding="utf-8")
    text = _replace_once(
        text,
        "from tradebot.hyp005_r1_canonical_epoch_contract import utc_artifact_stamp  # noqa: E402\n",
        "from tradebot.hyp005_r1_canonical_epoch_contract import utc_artifact_stamp  # noqa: E402\n"
        "from tradebot.hyp005_shadow_evidence_path_contract import (  # noqa: E402\n"
        "    HYP005_SHADOW_EVIDENCE_PATH_UTF8_CONTRACT_VERSION,\n"
        "    normalize_logger_report_evidence_paths,\n"
        "    resolve_evidence_output_directory,\n"
        "    resolve_existing_evidence_path,\n"
        "    serialize_evidence_path,\n"
        "    write_json_ascii_atomic,\n"
        ")\n",
        label="legacy_import_contract",
    )
    text = _replace_once(
        text,
        "        payload = load_json(candidate_spec_json)\n        source_paths.append(candidate_spec_json)\n",
        "        resolved_candidate_spec = resolve_existing_evidence_path(candidate_spec_json, field=\"candidate_spec_json\", expect_directory=False)\n"
        "        payload = load_json(resolved_candidate_spec)\n"
        "        source_paths.append(serialize_evidence_path(resolved_candidate_spec))\n",
        label="legacy_candidate_spec_resolution",
    )
    text = _replace_once(
        text,
        "        payload = load_json(item)\n        source_paths.append(item)\n",
        "        resolved_input = resolve_existing_evidence_path(item, field=\"input_json\", expect_directory=False)\n"
        "        payload = load_json(resolved_input)\n"
        "        source_paths.append(serialize_evidence_path(resolved_input))\n",
        label="legacy_input_json_resolution",
    )
    text = _replace_once(
        text,
        "            source_paths.append(str(path))\n",
        "            source_paths.append(serialize_evidence_path(path))\n",
        label="legacy_discovered_path_serialization",
    )
    text = _replace_once(
        text,
        "    out_dir = Path(args.out_dir)\n",
        "    out_dir = resolve_evidence_output_directory(args.out_dir, field=\"out_dir\")\n",
        label="legacy_out_dir_resolution",
    )
    text = _replace_once(
        text,
        "    report[\"ledger_json\"] = str(ledger_json)\n    report[\"ledger_jsonl\"] = str(ledger_jsonl)\n    write_json(json_path, report)\n",
        "    report[\"ledger_json\"] = serialize_evidence_path(ledger_json)\n"
        "    report[\"ledger_jsonl\"] = serialize_evidence_path(ledger_jsonl)\n"
        "    report = normalize_logger_report_evidence_paths(report, require_exists=True)\n"
        "    report[\"evidence_path_contract_version\"] = HYP005_SHADOW_EVIDENCE_PATH_UTF8_CONTRACT_VERSION\n"
        "    write_json_ascii_atomic(json_path, report)\n",
        label="legacy_ascii_report_write",
    )
    _write(LEGACY, text)


def _patch_wrapper() -> None:
    _backup(WRAPPER)
    text = WRAPPER.read_text(encoding="utf-8")
    text = _replace_once(
        text,
        "from tradebot.hyp005_shadow_observation_identity import (  # noqa: E402\n",
        "from tradebot.hyp005_shadow_evidence_path_contract import (  # noqa: E402\n"
        "    normalize_logger_report_evidence_paths,\n"
        "    resolve_evidence_output_directory,\n"
        "    write_json_ascii_atomic,\n"
        ")\n"
        "from tradebot.hyp005_shadow_observation_identity import (  # noqa: E402\n",
        label="wrapper_import_contract",
    )
    text = _replace_once(
        text,
        "    return args.out_dir.resolve()\n",
        "    return resolve_evidence_output_directory(args.out_dir, field=\"out_dir\")\n",
        label="wrapper_out_dir_resolution",
    )
    text = _replace_once(
        text,
        "    report_payload[\"shadow_observations\"] = report_rows\n",
        "    report_payload[\"shadow_observations\"] = report_rows\n"
        "    report_payload = normalize_logger_report_evidence_paths(report_payload, require_exists=True)\n",
        label="wrapper_report_path_normalization",
    )
    text = _replace_once(
        text,
        "    write_json_atomic(report_json, report_payload)\n",
        "    write_json_ascii_atomic(report_json, report_payload)\n",
        label="wrapper_ascii_report_write",
    )
    _write(WRAPPER, text)


def _patch_epoch_ps1() -> None:
    _backup(EPOCH_PS1)
    text = EPOCH_PS1.read_text(encoding="utf-8")
    text = _replace_once(
        text,
        "$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = \"1\"\n",
        "$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = \"1\"\n"
        "$env:PYTHONUTF8 = \"1\"\n"
        "$env:PYTHONIOENCODING = \"utf-8\"\n"
        "$OutputEncoding = [System.Text.UTF8Encoding]::new($false)\n"
        "[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)\n"
        "# 4B.4.3.6.6.27G-H2 Windows Unicode serialization parity\n",
        label="epoch_powershell_utf8_contract",
    )
    _write(EPOCH_PS1, text)


def _compile(path: Path) -> bool:
    py_compile.compile(str(path), doraise=True)
    return True


def main() -> int:
    BACKUP.mkdir(parents=True, exist_ok=True)
    created = _install_module()
    _patch_legacy()
    _patch_wrapper()
    _patch_epoch_ps1()
    if not CREATED.exists():
        CREATED.write_text(json.dumps(created, indent=2), encoding="utf-8")

    checks = {
        "config_mutation_performed": False,
        "scheduler_mutation_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "paper_live_order_enablement_present": False,
        "path_contract_module_py_compile_ok": _compile(MODULE),
        "legacy_logger_py_compile_ok": _compile(LEGACY),
        "identity_wrapper_py_compile_ok": _compile(WRAPPER),
        "checker_py_compile_ok": _compile(CHECKER),
        "rollback_py_compile_ok": _compile(ROLLBACK),
        "test_file_py_compile_ok": _compile(TEST),
        "powershell_utf8_contract_present": "PYTHONIOENCODING = \"utf-8\"" in EPOCH_PS1.read_text(encoding="utf-8"),
        "ascii_escaped_logger_json_writer_present": "write_json_ascii_atomic(json_path, report)" in LEGACY.read_text(encoding="utf-8"),
        "fail_closed_evidence_resolution_present": "normalize_logger_report_evidence_paths(report_payload, require_exists=True)" in WRAPPER.read_text(encoding="utf-8"),
    }
    print(f"{CONTRACT_VERSION} Canonical shadow evidence path UTF-8 normalization / Windows Unicode serialization parity / fail-closed evidence path resolution hotfix applied")
    for key, value in checks.items():
        print(f" - {key}: {value}")
    return 0 if all(value is True for key, value in checks.items() if not key.endswith("_performed") and key != "paper_live_order_enablement_present") else 1


if __name__ == "__main__":
    raise SystemExit(main())
