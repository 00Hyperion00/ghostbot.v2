from __future__ import annotations
import json
import py_compile
import re
import shutil
from pathlib import Path

PATCH_ID = "4B436662F_H3"
PATCH_VERSION = "4B.4.3.6.6.62F-H3"
PAYLOAD = Path("tools/_patch_payload/4B436662F_H3")
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


def _backup(path: Path) -> str | None:
    if not path.exists():
        return None
    BACKUP.mkdir(parents=True, exist_ok=True)
    target = BACKUP / (str(path).replace("\\", "/").replace("/", "__") + ".before_" + PATCH_ID)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, target)
    return str(target)


def _payload(name: str) -> str:
    return (PAYLOAD / name).read_text(encoding="utf-8")


def _write(rel: str, text: str) -> dict[str, object]:
    path = Path(rel)
    existed = path.exists()
    backup = _backup(path)
    old = path.read_text(encoding="utf-8") if existed else ""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return {"path": rel, "existed_before": existed, "backup_path": backup, "mutated": old != text}


def _append_once(rel: str, marker: str, text: str) -> dict[str, object]:
    path = Path(rel)
    existed = path.exists()
    backup = _backup(path)
    old = path.read_text(encoding="utf-8") if existed else ""
    if marker in old:
        return {"path": rel, "existed_before": existed, "backup_path": backup, "mutated": False}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(old.rstrip() + "\n\n" + text.strip() + "\n", encoding="utf-8", newline="\n")
    return {"path": rel, "existed_before": existed, "backup_path": backup, "mutated": True}


def _repair_hyp006() -> dict[str, object]:
    rel = "src/tradebot/hyp006_shadow_registration_operator_approval.py"
    path = Path(rel)
    existed = path.exists()
    backup = _backup(path)
    old = path.read_text(encoding="utf-8") if existed else ""
    text = old
    # Remove the malformed 62F-H2 tail that produced an unterminated string literal.
    marker = "62F-H2 hyp006 stdout"
    idx = text.find(marker)
    if idx >= 0:
        line_start = text.rfind("\n", 0, idx)
        text = text[: max(line_start, 0)].rstrip() + "\n"
    # If another malformed t+' tail exists, truncate from that block conservatively.
    bad = "return t if 'hyp006_scheduler_stdout.log' in t else t+'"
    idx = text.find(bad)
    if idx >= 0:
        line_start = text.rfind("\n", 0, idx)
        text = text[: max(line_start, 0)].rstrip() + "\n"
    text = text.rstrip() + "\n\n" + _payload("hyp006_fix.py").strip() + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return {"path": rel, "existed_before": existed, "backup_path": backup, "mutated": text != old}


def main() -> int:
    mutations: list[dict[str, object]] = []
    mutations.append(_write("src/tradebot/_production_hardening_compat.py", _payload("prod.py")))
    mutations.append(_write("src/tradebot/production_hardening/__init__.py", "from tradebot._production_hardening_compat import *\n"))
    mutations.append(_append_once("src/tradebot/operator_cockpit_v2_read_only.py", "62F-H3 phase61 prod risk sizing restore", _payload("operator_fix.py")))
    mutations.append(_repair_hyp006())
    mutations.append(_write("src/tradebot/full_repo_regression_stabilization_62F_H3.py", _payload("full.py")))
    mutations.append(_write("tools/check_4B436662F_H3_hyp006_syntax_production_hardening_risk_sizing_restore.py", _payload("check.py")))
    mutations.append(_write("tools/run_4B436662F_H3_hyp006_syntax_production_hardening_risk_sizing_restore.py", _payload("run.py")))
    mutations.append(_write("tests/test_full_repo_regression_stabilization_4B436662F_H3.py", _payload("test.py")))
    mutations.append(_write("docs/HYP006_SYNTAX_PRODUCTION_HARDENING_RISK_SIZING_RESTORE_4B436662F_H3.md", _payload("doc.md")))
    mutations.append(_write("README_APPLY_4B436662F_H3_HYP006_SYNTAX_PRODUCTION_HARDENING_RISK_SIZING_RESTORE.txt", _payload("readme.txt")))

    compile_targets = [
        "src/tradebot/hyp006_shadow_registration_operator_approval.py",
        "src/tradebot/_production_hardening_compat.py",
        "src/tradebot/full_repo_regression_stabilization_62F_H3.py",
        "tools/check_4B436662F_H3_hyp006_syntax_production_hardening_risk_sizing_restore.py",
        "tools/run_4B436662F_H3_hyp006_syntax_production_hardening_risk_sizing_restore.py",
        "tests/test_full_repo_regression_stabilization_4B436662F_H3.py",
    ]
    errors: dict[str, str] = {}
    for rel in compile_targets:
        try:
            py_compile.compile(rel, doraise=True)
        except Exception as exc:
            errors[rel] = str(exc)
    payload = {
        "ok": not errors,
        "applied": not errors,
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "patch_name": "HYP006 Syntax / Production Hardening / Risk-Sizing Builder Restore",
        "phase_62f_h3_restore_performed": True,
        "mutation_results": mutations,
        "compile_errors": errors,
        "py_compile_ok": not errors,
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
