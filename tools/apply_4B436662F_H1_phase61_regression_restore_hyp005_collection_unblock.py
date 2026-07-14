from __future__ import annotations
import json, py_compile, shutil, sys
from pathlib import Path

PATCH_ID = "4B436662F_H1"
PATCH_VERSION = "4B.4.3.6.6.62F-H1"
PATCH_NAME = "Phase61 Regression Restore / HYP005 Collection Unblock Hotfix"
PAYLOAD = Path("tools/_patch_payload/4B436662F_H1")
BACKUP = Path(".patch_backup") / PATCH_ID
SAFETY_FALSE = {
    "paper_submit_enabled_by_patch": False,
    "paper_submit_performed": False,
    "paper_order_submit_performed": False,
    "network_request_performed": False,
    "network_order_submit_performed": False,
    "approved_for_live_real": False,
    "live_real_approved_by_patch": False,
    "approved_for_exchange_submit": False,
    "exchange_submit_performed": False,
    "runtime_start_performed": False,
    "training_performed": False,
    "reload_performed": False,
    "private_api_access_allowed": False,
    "trading_action_performed": False,
    "order_actions_performed": False,
}

def _backup_path(path: Path) -> str | None:
    if not path.exists():
        return None
    BACKUP.mkdir(parents=True, exist_ok=True)
    target = BACKUP / (str(path).replace("\\", "/").replace("/", "__") + ".before_4B436662F_H1")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, target)
    return str(target)

def _write(rel: str, text: str) -> dict[str, object]:
    path = Path(rel)
    existed = path.exists()
    backup = _backup_path(path)
    old = path.read_text(encoding="utf-8") if existed else None
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return {"path": rel, "existed_before": existed, "backup_path": backup, "mutated": old != text}

def _append_once(rel: str, marker: str, text: str) -> dict[str, object]:
    path = Path(rel)
    existed = path.exists()
    backup = _backup_path(path)
    old = path.read_text(encoding="utf-8") if existed else ""
    if marker in old:
        return {"path": rel, "existed_before": existed, "backup_path": backup, "mutated": False}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(old.rstrip() + "\n\n" + text.strip() + "\n", encoding="utf-8", newline="\n")
    return {"path": rel, "existed_before": existed, "backup_path": backup, "mutated": True}

def _payload(name: str) -> str:
    return (PAYLOAD / name).read_text(encoding="utf-8")

def main() -> int:
    mutations: list[dict[str, object]] = []
    written: list[str] = []
    mutations.append(_append_once("src/tradebot/operator_cockpit_v2_read_only.py", "4B.4.3.6.6.62F-H1 Phase61 public constant compatibility overlay", _payload("operator_cockpit_62f_h1_overlay.py")))
    mutations.append(_write("src/tradebot/hyp005_shadow_evidence_path_contract.py", _payload("hyp005_shadow_evidence_path_contract.py")))
    for rel in [
        "src/tradebot/release_audit_legacy_api_drift_compatibility_h4.py",
        "src/tradebot/release_audit_legacy_api_drift_compatibility_h5.py",
        "src/tradebot/release_audit_legacy_api_drift_compatibility_h6.py",
        "src/tradebot/release_audit_legacy_api_drift_compatibility_h7.py",
    ]:
        mutations.append(_write(rel, _payload("phase61_report_module.py")))
    mutations.append(_write("src/tradebot/full_repo_regression_stabilization_62F_H1.py", _payload("full_repo_regression_stabilization_62F_H1.py")))
    written.extend([
        "src/tradebot/hyp005_shadow_evidence_path_contract.py",
        "src/tradebot/full_repo_regression_stabilization_62F_H1.py",
        "src/tradebot/release_audit_legacy_api_drift_compatibility_h4.py",
        "src/tradebot/release_audit_legacy_api_drift_compatibility_h5.py",
        "src/tradebot/release_audit_legacy_api_drift_compatibility_h6.py",
        "src/tradebot/release_audit_legacy_api_drift_compatibility_h7.py",
    ])
    compile_errors: dict[str, str] = {}
    for rel in written + [
        "tools/check_4B436662F_H1_phase61_regression_restore_hyp005_collection_unblock.py",
        "tools/run_4B436662F_H1_phase61_regression_restore_hyp005_collection_unblock.py",
        "tools/rollback_4B436662F_H1_phase61_regression_restore_hyp005_collection_unblock.py",
        "tests/test_full_repo_regression_stabilization_4B436662F_H1.py",
    ]:
        try:
            py_compile.compile(rel, doraise=True)
        except Exception as exc:
            compile_errors[rel] = str(exc)
    payload = {
        "ok": not compile_errors,
        "applied": not compile_errors,
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "patch_name": PATCH_NAME,
        "phase_62f_h1_phase61_regression_restore_performed": True,
        "mutation_results": mutations,
        "written_files": written,
        "compile_errors": compile_errors,
        "py_compile_ok": not compile_errors,
        "git_add_performed": False,
        "git_commit_performed": False,
        "git_push_performed": False,
        "git_tag_performed": False,
        "file_delete_performed": False,
        "file_move_performed": False,
        **SAFETY_FALSE,
    }
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if payload["ok"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
