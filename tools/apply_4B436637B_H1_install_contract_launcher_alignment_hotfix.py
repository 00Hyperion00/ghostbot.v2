from __future__ import annotations

import json
import py_compile
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

PATCH_ID = "4B436637B-H1"
PATCH_ID_COMPACT = "4B436637B_H1"
PATCH_VERSION = "4B.4.3.6.6.37B-H1"
PATCH_NAME = "Install Contract Launcher Alignment Hotfix"
ROOT = Path(__file__).resolve().parents[1]
PAYLOAD_ROOT = ROOT / "tools" / f"_patch_payload_{PATCH_ID_COMPACT}"
FILES = [
    "README_APPLY_4B436637B_H1.txt",
    "docs/INSTALL_CONTRACT_LAUNCHER_ALIGNMENT_HOTFIX_4B436637B_H1.md",
    "src/tradebot/install_contract_launcher_alignment_hotfix.py",
    "tests/test_install_contract_launcher_alignment_hotfix_4B436637B_H1.py",
    "tools/check_4B436637B_H1_install_contract_launcher_alignment_hotfix.py",
    "tools/run_4B436637B_H1_install_contract_launcher_alignment_hotfix.py",
    "tools/rollback_4B436637B_H1_install_contract_launcher_alignment_hotfix.py",
]
MUTATION_FILES = ["run_dashboard.bat", "start_dashboard.bat"]


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def copy_payload_file(rel: str) -> tuple[bool, bool]:
    src = PAYLOAD_ROOT / rel
    dst = ROOT / rel
    existed = dst.exists()
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return existed, True


def compile_file(path: Path) -> str | None:
    try:
        py_compile.compile(str(path), doraise=True)
    except Exception as exc:  # pragma: no cover
        return f"{type(exc).__name__}: {exc}"
    return None


def main() -> int:
    backup_root = ROOT / "tools" / f"_patch_backup_{PATCH_ID_COMPACT}_{utc_stamp()}"
    backed_up: list[str] = []
    modified: list[str] = []
    written: list[str] = []
    for rel in FILES:
        dst = ROOT / rel
        if dst.exists():
            backup_path = backup_root / rel
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dst, backup_path)
            backed_up.append(rel)
            modified.append(rel)
        copy_payload_file(rel)
        written.append(rel)

    sys.path.insert(0, str(ROOT / "src"))
    from tradebot.install_contract_launcher_alignment_hotfix import apply_bat_launcher_hotfix

    for rel in MUTATION_FILES:
        dst = ROOT / rel
        if dst.exists() and rel not in backed_up:
            backup_path = backup_root / rel
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dst, backup_path)
            backed_up.append(rel)

    mutation_result = apply_bat_launcher_hotfix(ROOT)
    modified.extend(mutation_result.get("bat_launcher_normalized_files", []))

    compile_errors: dict[str, str] = {}
    for rel in FILES:
        if rel.endswith(".py"):
            err = compile_file(ROOT / rel)
            if err:
                compile_errors[rel] = err

    result = {
        "applied": True,
        "patch_id": PATCH_ID_COMPACT,
        "patch_version": PATCH_VERSION,
        "patch_name": PATCH_NAME,
        "written_files": written,
        "modified_files": sorted(set(modified)),
        "backed_up_files": sorted(set(backed_up)),
        "backup_root": str(backup_root.relative_to(ROOT)) if backed_up else "",
        "compile_errors": compile_errors,
        "py_compile_ok": not compile_errors,
        **mutation_result,
        "install_contract_apply_performed": True,
        "install_contract_mutation_performed": bool(mutation_result.get("bat_launcher_normalization_performed")),
        "launcher_install_contract_mutation_performed": bool(mutation_result.get("bat_launcher_normalization_performed")),
        "requirements_alignment_mutation_performed": False,
        "readme_install_contract_mutation_performed": False,
        "approved_for_exchange_submit": False,
        "approved_for_live_real": False,
        "approved_for_paper_transition": False,
        "approved_for_runtime_overlay": False,
        "archive_execution_allowed": False,
        "archive_move_performed": False,
        "deduplication_action_performed": False,
        "destructive_cleanup_performed": False,
        "evidence_collection_started": False,
        "exchange_submit_performed": False,
        "file_delete_performed": False,
        "file_move_performed": False,
        "http_request_performed": False,
        "network_request_performed": False,
        "next_phase_unlock_performed": False,
        "order_submit_performed": False,
        "paper_transition_approval_performed": False,
        "paper_transition_unblocked": False,
        "public_market_data_collection_performed": False,
        "public_observation_execution_performed": False,
        "reload_performed": False,
        "report_delete_performed": False,
        "runtime_evidence_collection_performed": False,
        "runtime_health_probe_performed": False,
        "runtime_overlay_activated": False,
        "runtime_probe_performed": False,
        "runtime_readiness_unlock_performed": False,
        "signed_request_performed": False,
        "trading_action_performed": False,
        "training_performed": False,
        "transition_to_next_phase_performed": False,
    }
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if not compile_errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
