from __future__ import annotations

import py_compile
import shutil
import sys
from pathlib import Path

CONTRACT_VERSION = "4B.4.3.6.6.27G-H1-H1"
BACKUP_DIRNAME = "_patch_backup_4B436627GH1H1"
PAYLOAD_DIRNAME = "_patch_payload_4B436627GH1H1"
TARGETS = (
    "tools/apply_4B436627GH1_repository_hygiene_cleanup.py",
    "tools/check_4B436627GH1_repository_hygiene_cleanup.py",
    "tools/rollback_4B436627GH1_repository_hygiene_cleanup.py",
    "tests/test_repository_hygiene_cleanup_4B436627GH1.py",
)


def _copy_payload(root: Path, relative: str) -> None:
    payload = root / "tools" / PAYLOAD_DIRNAME / Path(relative).name
    target = root / relative
    backup = root / "tools" / BACKUP_DIRNAME / relative
    if not payload.exists():
        raise RuntimeError(f"PAYLOAD_NOT_FOUND:{payload}")
    if target.exists() and not backup.exists():
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target, backup)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(payload, target)


def _compile(root: Path, relative: str) -> bool:
    try:
        py_compile.compile(str(root / relative), doraise=True)
    except py_compile.PyCompileError:
        return False
    return True


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    for relative in TARGETS:
        _copy_payload(root, relative)

    apply_text = (root / TARGETS[0]).read_text(encoding="utf-8")
    checker_text = (root / TARGETS[1]).read_text(encoding="utf-8")
    rollback_text = (root / TARGETS[2]).read_text(encoding="utf-8")
    test_text = (root / TARGETS[3]).read_text(encoding="utf-8")
    checks = {
        "config_mutation_performed": False,
        "scheduler_mutation_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "paper_live_order_enablement_present": False,
        "gh1_apply_py_compile_ok": _compile(root, TARGETS[0]),
        "gh1_checker_py_compile_ok": _compile(root, TARGETS[1]),
        "gh1_rollback_py_compile_ok": _compile(root, TARGETS[2]),
        "gh1_test_py_compile_ok": _compile(root, TARGETS[3]),
        "gh1_apply_explicit_utf8_present": 'encoding="utf-8"' in apply_text and 'errors="strict"' in apply_text,
        "gh1_checker_explicit_utf8_present": 'encoding="utf-8"' in checker_text and 'errors="strict"' in checker_text,
        "gh1_rollback_explicit_utf8_present": 'encoding="utf-8"' in rollback_text and 'errors="strict"' in rollback_text,
        "unicode_path_regression_test_present": 'Masaüstü ALKILIÇ' in test_text,
    }
    ok = (
        checks["gh1_apply_py_compile_ok"]
        and checks["gh1_checker_py_compile_ok"]
        and checks["gh1_rollback_py_compile_ok"]
        and checks["gh1_test_py_compile_ok"]
        and checks["gh1_apply_explicit_utf8_present"]
        and checks["gh1_checker_explicit_utf8_present"]
        and checks["gh1_rollback_explicit_utf8_present"]
        and checks["unicode_path_regression_test_present"]
        and not checks["config_mutation_performed"]
        and not checks["scheduler_mutation_performed"]
        and not checks["training_performed"]
        and not checks["reload_performed"]
        and not checks["trading_action_performed"]
        and not checks["paper_live_order_enablement_present"]
    )
    print(f"{CONTRACT_VERSION} Windows UTF-8 Git-root detection / Unicode-safe subprocess contract hotfix applied")
    for key, value in checks.items():
        print(f" - {key}: {value}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
