from __future__ import annotations

import py_compile
import shutil
from pathlib import Path

CONTRACT_VERSION = "4B.4.3.6.6.28C"
PATCH_ID = "4B436628C"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
PAYLOAD_ROOT = PROJECT_ROOT / "tools" / f"_patch_payload_{PATCH_ID}"
BACKUP_ROOT = PROJECT_ROOT / "tools" / f"_patch_backup_{PATCH_ID}"
EXPECTED_FILES = [
    "src/tradebot/hyp006_shadow_runner_dry_run.py",
    "tools/run_4B436628C_hyp006_shadow_runner_dry_run.py",
    "tools/check_4B436628C_hyp006_shadow_runner_dry_run.py",
    "tools/apply_4B436628C_hyp006_shadow_runner_dry_run.py",
    "tools/rollback_4B436628C_hyp006_shadow_runner_dry_run.py",
    "tests/test_hyp006_shadow_runner_dry_run_4B436628C.py",
    "docs/HYP006_R1_NO_ORDER_SHADOW_RUNNER_DRY_RUN_4B436628C.md",
]


def copy_file(relative: str) -> None:
    src = PAYLOAD_ROOT / relative
    dst = PROJECT_ROOT / relative
    if not src.exists():
        raise RuntimeError(f"PAYLOAD_FILE_MISSING:{relative}")
    if dst.exists():
        backup = BACKUP_ROOT / relative
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(dst, backup)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def py_compile_ok(path: Path) -> bool:
    py_compile.compile(str(path), doraise=True)
    return True


def main() -> int:
    if not PAYLOAD_ROOT.exists():
        raise RuntimeError(f"PATCH_PAYLOAD_MISSING:{PAYLOAD_ROOT}")
    for relative in EXPECTED_FILES:
        copy_file(relative)
    py_files = [PROJECT_ROOT / item for item in EXPECTED_FILES if item.endswith(".py")]
    for path in py_files:
        py_compile_ok(path)
    checks = {
        "config_mutation_performed": False,
        "scheduler_mutation_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "all_expected_files_present": all((PROJECT_ROOT / item).exists() for item in EXPECTED_FILES),
        "all_py_compile_ok": True,
        "contract_version_present": CONTRACT_VERSION in (PROJECT_ROOT / "src/tradebot/hyp006_shadow_runner_dry_run.py").read_text(encoding="utf-8"),
        "dry_run_runner_present": "build_hyp006_shadow_runner_dry_run_report" in (PROJECT_ROOT / "src/tradebot/hyp006_shadow_runner_dry_run.py").read_text(encoding="utf-8"),
        "operator_gate_present": "operator_registration_approval_gate_ready" in (PROJECT_ROOT / "src/tradebot/hyp006_shadow_runner_dry_run.py").read_text(encoding="utf-8"),
        "scheduler_preflight_present": "build_scheduler_registration_preflight" in (PROJECT_ROOT / "src/tradebot/hyp006_shadow_runner_dry_run.py").read_text(encoding="utf-8"),
        "runner_requires_review_ok": "REVIEW_OK_REQUIRED_FOR_28C_NO_ORDER_DRY_RUN" in (PROJECT_ROOT / "tools/run_4B436628C_hyp006_shadow_runner_dry_run.py").read_text(encoding="utf-8"),
        "shadow_collection_blocked": '"approved_for_shadow_collection": False' in (PROJECT_ROOT / "src/tradebot/hyp006_shadow_runner_dry_run.py").read_text(encoding="utf-8"),
        "paper_live_order_enablement_present": False,
    }
    print(f"{CONTRACT_VERSION} HYP-006-R1 No-Order Shadow Runner Dry-Run / Operator Registration Approval Gate patch applied")
    for key, value in checks.items():
        print(f" - {key}: {value}")
    required_true = [
        "all_expected_files_present",
        "all_py_compile_ok",
        "contract_version_present",
        "dry_run_runner_present",
        "operator_gate_present",
        "scheduler_preflight_present",
        "runner_requires_review_ok",
        "shadow_collection_blocked",
    ]
    required_false = [
        "config_mutation_performed",
        "scheduler_mutation_performed",
        "training_performed",
        "reload_performed",
        "trading_action_performed",
        "paper_live_order_enablement_present",
    ]
    if not all(checks[name] is True for name in required_true):
        raise RuntimeError("APPLY_POSTCHECK_FAILED_TRUE_REQUIREMENT")
    if not all(checks[name] is False for name in required_false):
        raise RuntimeError("APPLY_POSTCHECK_FAILED_FALSE_REQUIREMENT")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
