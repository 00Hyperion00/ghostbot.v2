from __future__ import annotations

import json
import py_compile
import shutil
from pathlib import Path

PATCH_ID = "4B436661"
PATCH_VERSION = "4B.4.3.6.6.61"
PATCH_NAME = "Release Audit / Repository Hygiene / Pytest Collection Isolation"

PYTEST_INI_CONTENT = """[pytest]
testpaths =
    tests
python_files =
    test_*.py
norecursedirs =
    .git
    .hg
    .svn
    .tox
    .venv
    venv
    env
    build
    dist
    .eggs
    *.egg
    _patch_backup*
    _patch_payload*
    legacy_patches
addopts =
    -ra
    --import-mode=importlib
    --ignore-glob=tools/_patch_backup_*
    --ignore-glob=tools/_patch_payload_*
    --ignore=legacy_patches
    --ignore-glob=**/_patch_backup_*
    --ignore-glob=**/_patch_payload_*
    --ignore-glob=**/legacy_patches
"""

REQUIRED_FILES = [
    "README_APPLY_4B436661_RELEASE_AUDIT_PYTEST_COLLECTION_HYGIENE.txt",
    "docs/RELEASE_AUDIT_REPOSITORY_HYGIENE_PYTEST_COLLECTION_ISOLATION_4B436661.md",
    "src/tradebot/release_audit_pytest_collection_hygiene.py",
    "tests/test_release_audit_pytest_collection_hygiene_4B436661.py",
    "tools/apply_4B436661_release_audit_pytest_collection_hygiene.py",
    "tools/check_4B436661_release_audit_pytest_collection_hygiene.py",
    "tools/run_4B436661_release_audit_pytest_collection_hygiene.py",
    "tools/rollback_4B436661_release_audit_pytest_collection_hygiene.py",
]

PYTHON_FILES = [path for path in REQUIRED_FILES if path.endswith(".py")]


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _write_pytest_ini(root: Path) -> dict[str, object]:
    pytest_ini = root / "pytest.ini"
    backup_dir = root / ".patch_backup" / PATCH_ID
    backup_path = backup_dir / "pytest.ini.before_4B436661"
    backup_created = False
    previous_content = pytest_ini.read_text(encoding="utf-8") if pytest_ini.exists() else None
    if previous_content != PYTEST_INI_CONTENT:
        backup_dir.mkdir(parents=True, exist_ok=True)
        if previous_content is not None and not backup_path.exists():
            backup_path.write_text(previous_content, encoding="utf-8")
            backup_created = True
        pytest_ini.write_text(PYTEST_INI_CONTENT, encoding="utf-8")
        mutated = True
    else:
        mutated = False
    return {
        "pytest_ini_mutation_performed": mutated,
        "pytest_ini_backup_created": backup_created,
        "pytest_ini_backup_path": str(backup_path) if backup_path.exists() else None,
    }


def main() -> int:
    root = _root()
    pytest_result = _write_pytest_ini(root)

    missing = [path for path in REQUIRED_FILES if not (root / path).exists()]
    compile_errors: dict[str, str] = {}
    for relative in PYTHON_FILES:
        path = root / relative
        if not path.exists():
            continue
        try:
            py_compile.compile(str(path), doraise=True)
        except py_compile.PyCompileError as exc:
            compile_errors[relative] = str(exc)

    result = {
        "applied": not missing and not compile_errors,
        "ok": not missing and not compile_errors,
        "patch_id": PATCH_ID,
        "patch_name": PATCH_NAME,
        "patch_version": PATCH_VERSION,
        "phase_61_source_mutation_performed": True,
        "missing_files": missing,
        "compile_errors": compile_errors,
        "py_compile_ok": not compile_errors,
        "written_files": ["pytest.ini", *REQUIRED_FILES],
        "file_delete_performed": False,
        "file_move_performed": False,
        "destructive_cleanup_performed": False,
        "git_add_performed": False,
        "git_commit_performed": False,
        "git_push_performed": False,
        "git_tag_performed": False,
        "actual_evidence_accepted_by_patch": False,
        "actual_evidence_ingested_by_patch": False,
        "paper_submit_enabled_by_patch": False,
        "paper_submit_performed": False,
        "paper_order_submit_performed": False,
        "network_order_submit_performed": False,
        "network_request_performed": False,
        "approved_for_live_real": False,
        "live_real_approved_by_patch": False,
        "approved_for_exchange_submit": False,
        "exchange_submit_performed": False,
        "private_api_access_allowed": False,
        "runtime_start_performed": False,
        "runtime_start_command_executed": False,
        "runtime_process_start_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "runtime_overlay_activated": False,
        "signed_request_performed": False,
        "transition_to_next_phase_performed": False,
        **pytest_result,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
