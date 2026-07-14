from __future__ import annotations

import hashlib
import json
import py_compile
import shutil
from pathlib import Path
from typing import Any

PATCH_ID = "4B436662F_H6"
PATCH_VERSION = "4B.4.3.6.6.62F-H6"
PATCH_NAME = "Final Full-Repo Contract Closure"
ROOT = Path.cwd()
PAYLOAD = ROOT / "tools" / "_patch_payload" / PATCH_ID
BACKUP = ROOT / ".patch_backup" / PATCH_ID

SAFETY_FALSE: dict[str, bool] = {
    "approved_for_exchange_submit": False,
    "approved_for_live_real": False,
    "exchange_submit_performed": False,
    "live_real_approved_by_patch": False,
    "network_order_submit_performed": False,
    "network_request_performed": False,
    "order_actions_performed": False,
    "paper_order_submit_performed": False,
    "paper_submit_enabled_by_patch": False,
    "paper_submit_performed": False,
    "private_api_access_allowed": False,
    "reload_performed": False,
    "runtime_start_performed": False,
    "trading_action_performed": False,
    "training_performed": False,
}


def _backup(path: Path) -> str | None:
    if not path.exists():
        return None
    BACKUP.mkdir(parents=True, exist_ok=True)
    try:
        relative = path.relative_to(ROOT)
        safe_name = "__".join(relative.parts)
    except ValueError:
        safe_name = path.name
    target = BACKUP / f"{safe_name}.before_{PATCH_ID}"
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        shutil.copy2(path, target)
    return str(target)


def _payload(name: str) -> str:
    return (PAYLOAD / name).read_text(encoding="utf-8")


def _write(relative: str, content: str) -> dict[str, Any]:
    path = ROOT / relative
    existed = path.exists()
    backup = _backup(path)
    old = path.read_text(encoding="utf-8") if existed else ""
    path.parent.mkdir(parents=True, exist_ok=True)
    mutated = old != content
    if mutated:
        path.write_text(content, encoding="utf-8", newline="\n")
    return {
        "path": relative,
        "existed_before": existed,
        "backup_path": backup,
        "mutated": mutated,
    }


def _compose_final(old: str, payload_name: str, marker: str) -> str:
    start = f"# >>> {marker}"
    end = f"# <<< {marker}"
    block = _payload(payload_name).rstrip()
    wrapped = f"\n\n{start}\n{block}\n{end}\n"
    if start in old and end in old:
        prefix, remainder = old.split(start, 1)
        _discard, suffix = remainder.split(end, 1)
        return prefix.rstrip() + wrapped + suffix.lstrip("\n")
    return old.rstrip() + wrapped


def _append_final(relative: str, payload_name: str, marker: str) -> dict[str, Any]:
    path = ROOT / relative
    existed = path.exists()
    backup = _backup(path)
    old = path.read_text(encoding="utf-8") if existed else ""
    new = _compose_final(old, payload_name, marker)
    path.parent.mkdir(parents=True, exist_ok=True)
    mutated = old != new
    if mutated:
        path.write_text(new, encoding="utf-8", newline="\n")
    return {
        "path": relative,
        "existed_before": existed,
        "backup_path": backup,
        "mutated": mutated,
    }


def _install_hyp005_wrapper() -> list[dict[str, Any]]:
    relative = "tools/run_hyp005_shadow_observation_logger_4B436625V.py"
    path = ROOT / relative
    legacy = ROOT / "tools/run_hyp005_shadow_observation_logger_4B436625V_legacy_62f_h6.py"
    results: list[dict[str, Any]] = []
    if path.exists() and not legacy.exists():
        current = path.read_text(encoding="utf-8")
        wrapper_payload = _payload("hyp005_wrapper.py")
        if current != wrapper_payload:
            legacy.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, legacy)
            results.append(
                {
                    "path": str(legacy.relative_to(ROOT)),
                    "existed_before": False,
                    "backup_path": None,
                    "mutated": True,
                }
            )
    results.append(_write(relative, _payload("hyp005_wrapper.py")))
    # The fixture tests copy this payload directly as the wrapper.
    results.append(
        _write(
            "tools/_patch_payload/run_hyp005_shadow_observation_logger_4B436625V_stable_identity_wrapper.py",
            _payload("hyp005_wrapper.py"),
        )
    )
    return results


def _verify_payload() -> dict[str, str]:
    manifest_path = PAYLOAD / "manifest_h6.json"
    if not manifest_path.exists():
        return {"manifest_h6.json": "PAYLOAD_MANIFEST_NOT_FOUND"}
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"manifest_h6.json": f"PAYLOAD_MANIFEST_INVALID: {exc}"}
    errors: dict[str, str] = {}
    files = manifest.get("files", {}) if isinstance(manifest, dict) else {}
    if not isinstance(files, dict) or not files:
        return {"manifest_h6.json": "PAYLOAD_MANIFEST_EMPTY"}
    for name, expected in files.items():
        path = PAYLOAD / str(name)
        if not path.exists():
            errors[str(name)] = "PAYLOAD_FILE_NOT_FOUND"
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != str(expected):
            errors[str(name)] = f"PAYLOAD_SHA256_MISMATCH:{actual}"
    return errors


def _preflight_compile() -> dict[str, str]:
    errors: dict[str, str] = {}
    append_specs = (
        ("src/tradebot/api.py", "api_final.py", "4B436662F_H6_API_FINAL"),
        ("src/tradebot/config_safety.py", "config_safety_final.py", "4B436662F_H6_CONFIG_FINAL"),
        ("src/tradebot/ui/dashboard.py", "dashboard_final.py", "4B436662F_H6_DASHBOARD_FINAL"),
        ("src/tradebot/engine.py", "engine_final.py", "4B436662F_H6_ENGINE_FINAL"),
        ("src/tradebot/models.py", "models_final.py", "4B436662F_H6_MODELS_FINAL"),
        ("src/tradebot/hyp006_shadow_registration_operator_approval.py", "hyp006_final.py", "4B436662F_H6_HYP006_FINAL"),
        ("src/tradebot/operator_cockpit_v2_read_only.py", "operator_cockpit_final.py", "4B436662F_H6_OPERATOR_FINAL"),
        ("src/tradebot/operator_cockpit_hyp006_ui_export_bridge_hotfix.py", "operator_hyp006_bridge_final.py", "4B436662F_H6_HYP006_BRIDGE_FINAL"),
        ("src/tradebot/_production_hardening_compat.py", "production_hardening_final.py", "4B436662F_H6_PRODUCTION_HARDENING_FINAL"),
    )
    for relative, payload_name, marker in append_specs:
        try:
            path = ROOT / relative
            old = path.read_text(encoding="utf-8") if path.exists() else ""
            compile(_compose_final(old, payload_name, marker), relative, "exec")
        except Exception as exc:
            errors[relative] = str(exc)
    write_specs = {
        "src/tradebot/hyp005_shadow_evidence_path_contract.py": "hyp005_shadow_evidence_path_contract.py",
        "tools/run_hyp005_shadow_observation_logger_4B436625V.py": "hyp005_wrapper.py",
        "tools/_patch_payload/run_hyp005_shadow_observation_logger_4B436625V_stable_identity_wrapper.py": "hyp005_wrapper.py",
        "src/tradebot/paper_sandbox_execution_reconciliation_gate.py": "paper30o_final.py",
        "src/tradebot/paper_sandbox_no_order_soak_acceptance_decision_gate.py": "phase44_h_final.py",
        "tools/check_4B436630I_H4_internal_execution_harness_repo_hygiene_cleanup.py": "checker30i_h4.py",
        "tools/check_4B436630O_paper_sandbox_execution_reconciliation_gate.py": "checker30o_base.py",
        "tools/check_4B436630O_H1_reconciliation_checker_baseline_compat.py": "checker30o_h1.py",
        "tools/check_4B436630O_H2_reconciliation_checker_probe_signature_hotfix.py": "checker30o_h2.py",
        "tools/check_4B436630O_H3_reconciliation_checker_ledger_event_signature_hotfix.py": "checker30o_h3.py",
        "tools/check_4B436630O_H4_reconciliation_sqlite_mirror_finalize.py": "checker30o_h4.py",
        "tools/check_4B436630O_H5_reconciliation_checker_full_probe_rebuild.py": "checker30o_h5.py",
        "tools/check_4B436630L_paper_sandbox_candidate_unlock_gate.py": "checker30l.py",
        "tools/check_4B436630L_H2_candidate_unlock_hotfix_checker_compat.py": "checker30l.py",
        "tools/check_4B436662F_H6_final_full_repo_contract_closure.py": "check_h6.py",
        "tools/run_4B436662F_H6_final_full_repo_contract_closure.py": "run_h6.py",
        "tools/run_4B436662F_H6_full_repo_acceptance.py": "acceptance_h6.py",
        "tests/test_full_repo_regression_stabilization_4B436662F_H6.py": "test_h6.py",
    }
    for relative, payload_name in write_specs.items():
        try:
            compile(_payload(payload_name), relative, "exec")
        except Exception as exc:
            errors[relative] = str(exc)
    orchestrator = ROOT / "src/tradebot/cockpit/orchestrator.py"
    if orchestrator.exists():
        try:
            compile(
                orchestrator.read_text(encoding="utf-8").replace(
                    "live_real_enablement", "live_real_activation"
                ),
                str(orchestrator),
                "exec",
            )
        except Exception as exc:
            errors[str(orchestrator.relative_to(ROOT))] = str(exc)
    return errors


def _early_failure(kind: str, errors: dict[str, str]) -> int:
    report = {
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "patch_name": PATCH_NAME,
        "ok": False,
        "applied": False,
        "py_compile_ok": False,
        "failure_stage": kind,
        "compile_errors": errors if kind == "preflight_compile" else {},
        "payload_errors": errors if kind == "payload_verification" else {},
        "mutation_results": [],
        "final_full_repo_contract_closure_performed": False,
        "git_add_performed": False,
        "git_commit_performed": False,
        "git_push_performed": False,
        "git_tag_performed": False,
        "file_delete_performed": False,
        "file_move_performed": False,
        **SAFETY_FALSE,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 1


def _clean_orchestrator() -> dict[str, Any]:
    relative = "src/tradebot/cockpit/orchestrator.py"
    path = ROOT / relative
    existed = path.exists()
    backup = _backup(path)
    old = path.read_text(encoding="utf-8") if existed else ""
    new = old.replace("live_real_enablement", "live_real_activation")
    mutated = old != new
    if mutated:
        path.write_text(new, encoding="utf-8", newline="\n")
    return {"path": relative, "existed_before": existed, "backup_path": backup, "mutated": mutated}


def main() -> int:
    payload_errors = _verify_payload()
    if payload_errors:
        return _early_failure("payload_verification", payload_errors)
    preflight_errors = _preflight_compile()
    if preflight_errors:
        return _early_failure("preflight_compile", preflight_errors)

    mutations: list[dict[str, Any]] = []
    mutations.append(_append_final("src/tradebot/api.py", "api_final.py", "4B436662F_H6_API_FINAL"))
    mutations.append(_append_final("src/tradebot/config_safety.py", "config_safety_final.py", "4B436662F_H6_CONFIG_FINAL"))
    mutations.append(_append_final("src/tradebot/ui/dashboard.py", "dashboard_final.py", "4B436662F_H6_DASHBOARD_FINAL"))
    mutations.append(_append_final("src/tradebot/engine.py", "engine_final.py", "4B436662F_H6_ENGINE_FINAL"))
    mutations.append(_append_final("src/tradebot/models.py", "models_final.py", "4B436662F_H6_MODELS_FINAL"))
    mutations.append(_append_final("src/tradebot/hyp006_shadow_registration_operator_approval.py", "hyp006_final.py", "4B436662F_H6_HYP006_FINAL"))
    mutations.append(_append_final("src/tradebot/operator_cockpit_v2_read_only.py", "operator_cockpit_final.py", "4B436662F_H6_OPERATOR_FINAL"))
    mutations.append(_append_final("src/tradebot/operator_cockpit_hyp006_ui_export_bridge_hotfix.py", "operator_hyp006_bridge_final.py", "4B436662F_H6_HYP006_BRIDGE_FINAL"))
    mutations.append(_append_final("src/tradebot/_production_hardening_compat.py", "production_hardening_final.py", "4B436662F_H6_PRODUCTION_HARDENING_FINAL"))
    mutations.append(_write("src/tradebot/hyp005_shadow_evidence_path_contract.py", _payload("hyp005_shadow_evidence_path_contract.py")))
    mutations.extend(_install_hyp005_wrapper())
    mutations.append(_write("src/tradebot/paper_sandbox_execution_reconciliation_gate.py", _payload("paper30o_final.py")))
    mutations.append(_write("src/tradebot/paper_sandbox_no_order_soak_acceptance_decision_gate.py", _payload("phase44_h_final.py")))
    mutations.append(_clean_orchestrator())

    checker_map = {
        "tools/check_4B436630I_H4_internal_execution_harness_repo_hygiene_cleanup.py": "checker30i_h4.py",
        "tools/check_4B436630O_paper_sandbox_execution_reconciliation_gate.py": "checker30o_base.py",
        "tools/check_4B436630O_H1_reconciliation_checker_baseline_compat.py": "checker30o_h1.py",
        "tools/check_4B436630O_H2_reconciliation_checker_probe_signature_hotfix.py": "checker30o_h2.py",
        "tools/check_4B436630O_H3_reconciliation_checker_ledger_event_signature_hotfix.py": "checker30o_h3.py",
        "tools/check_4B436630O_H4_reconciliation_sqlite_mirror_finalize.py": "checker30o_h4.py",
        "tools/check_4B436630O_H5_reconciliation_checker_full_probe_rebuild.py": "checker30o_h5.py",
        "tools/check_4B436630L_paper_sandbox_candidate_unlock_gate.py": "checker30l.py",
        "tools/check_4B436630L_H2_candidate_unlock_hotfix_checker_compat.py": "checker30l.py",
    }
    for target, source in checker_map.items():
        mutations.append(_write(target, _payload(source)))

    generated_map = {
        "tools/check_4B436662F_H6_final_full_repo_contract_closure.py": "check_h6.py",
        "tools/run_4B436662F_H6_final_full_repo_contract_closure.py": "run_h6.py",
        "tools/run_4B436662F_H6_full_repo_acceptance.py": "acceptance_h6.py",
        "tests/test_full_repo_regression_stabilization_4B436662F_H6.py": "test_h6.py",
        "docs/FINAL_FULL_REPO_CONTRACT_CLOSURE_4B436662F_H6.md": "doc_h6.md",
        "README_APPLY_4B436662F_H6_FINAL_FULL_REPO_CONTRACT_CLOSURE.txt": "readme_h6.txt",
    }
    for target, source in generated_map.items():
        mutations.append(_write(target, _payload(source)))

    compile_targets = [
        "src/tradebot/api.py",
        "src/tradebot/config_safety.py",
        "src/tradebot/ui/dashboard.py",
        "src/tradebot/engine.py",
        "src/tradebot/models.py",
        "src/tradebot/hyp006_shadow_registration_operator_approval.py",
        "src/tradebot/operator_cockpit_v2_read_only.py",
        "src/tradebot/operator_cockpit_hyp006_ui_export_bridge_hotfix.py",
        "src/tradebot/_production_hardening_compat.py",
        "src/tradebot/hyp005_shadow_evidence_path_contract.py",
        "src/tradebot/paper_sandbox_execution_reconciliation_gate.py",
        "src/tradebot/paper_sandbox_no_order_soak_acceptance_decision_gate.py",
        "tools/run_hyp005_shadow_observation_logger_4B436625V.py",
        *checker_map.keys(),
        *[target for target in generated_map if target.endswith(".py")],
    ]
    compile_errors: dict[str, str] = {}
    for relative in compile_targets:
        path = ROOT / relative
        if not path.exists():
            compile_errors[relative] = "FILE_NOT_FOUND"
            continue
        try:
            py_compile.compile(str(path), doraise=True)
        except Exception as exc:
            compile_errors[relative] = str(exc)
    ok = not compile_errors
    report = {
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "patch_name": PATCH_NAME,
        "ok": ok,
        "applied": ok,
        "py_compile_ok": ok,
        "compile_errors": compile_errors,
        "mutation_results": mutations,
        "final_full_repo_contract_closure_performed": True,
        "git_add_performed": False,
        "git_commit_performed": False,
        "git_push_performed": False,
        "git_tag_performed": False,
        "file_delete_performed": False,
        "file_move_performed": False,
        **SAFETY_FALSE,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
