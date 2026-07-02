from __future__ import annotations

import json
import py_compile
from pathlib import Path

PATCH_VERSION = '4B.4.3.6.6.33J-H1'
PATCH_NAME = 'Operator Cockpit Recovery Plan Action Route Operator Identity Hotfix'
REPLACEMENTS = {'operator_id = require_operator_identity(context)\n        return await _execute_operator_action(request=request, action="engine_position_recovery.create_plan"': 'operator_id = require_operator_identity(context.get("operator_id"), action="engine_position_recovery.create_plan")\n        return await _execute_operator_action(request=request, action="engine_position_recovery.create_plan"', 'operator_id = require_operator_identity(context)\n        return await _execute_operator_action(request=request, action="engine_position_recovery.confirm_plan"': 'operator_id = require_operator_identity(context.get("operator_id"), action="engine_position_recovery.confirm_plan")\n        return await _execute_operator_action(request=request, action="engine_position_recovery.confirm_plan"', 'operator_id = require_operator_identity(context)\n        return await _execute_operator_action(request=request, action="engine_position_recovery.verify_completion"': 'operator_id = require_operator_identity(context.get("operator_id"), action="engine_position_recovery.verify_completion")\n        return await _execute_operator_action(request=request, action="engine_position_recovery.verify_completion"', 'operator_id = require_operator_identity(context)\n        return await _execute_operator_action(request=request, action="recovery_plan_apply.create_from_reviewed_candidate"': 'operator_id = require_operator_identity(context.get("operator_id"), action="recovery_plan_apply.create_from_reviewed_candidate")\n        return await _execute_operator_action(request=request, action="recovery_plan_apply.create_from_reviewed_candidate"', 'operator_id = require_operator_identity(context)\n        return await _execute_operator_action(request=request, action="recovery_plan_apply.confirm_manual_external_recovery"': 'operator_id = require_operator_identity(context.get("operator_id"), action="recovery_plan_apply.confirm_manual_external_recovery")\n        return await _execute_operator_action(request=request, action="recovery_plan_apply.confirm_manual_external_recovery"', 'operator_id = require_operator_identity(context)\n        return await _execute_operator_action(request=request, action="recovery_plan_apply.verify_no_mismatch"': 'operator_id = require_operator_identity(context.get("operator_id"), action="recovery_plan_apply.verify_no_mismatch")\n        return await _execute_operator_action(request=request, action="recovery_plan_apply.verify_no_mismatch"'}
COMPILE_HELPER = 'from __future__ import annotations\n\nimport json\nimport py_compile\nfrom pathlib import Path\n\nPATCH_VERSION = "4B.4.3.6.6.33J-H1"\n\n\ndef _root() -> Path:\n    return Path(__file__).resolve().parents[1]\n\n\ndef main() -> int:\n    root = _root()\n    targets = [\n        root / "src/tradebot/cockpit/__init__.py",\n        root / "src/tradebot/cockpit/app.py",\n        root / "src/tradebot/cockpit/broadcaster.py",\n        root / "src/tradebot/cockpit/orchestrator.py",\n        root / "src/tradebot/cockpit/schemas.py",\n        root / "src/tradebot/cockpit/security.py",\n        root / "src/tradebot/cli.py",\n        root / "tools/check_cockpit_runtime_4B436633J.py",\n        root / "tools/check_cockpit_runtime_4B436633J_H1.py",\n    ]\n    compiled: list[str] = []\n    errors: list[dict[str, str]] = []\n    for target in targets:\n        if not target.exists():\n            errors.append({"file": str(target.relative_to(root)), "error": "missing"})\n            continue\n        try:\n            py_compile.compile(str(target), doraise=True)\n            compiled.append(str(target.relative_to(root)))\n        except Exception as exc:\n            errors.append({"file": str(target.relative_to(root)), "error": str(exc)})\n    app_text = (root / "src/tradebot/cockpit/app.py").read_text(encoding="utf-8")\n    bad_signature_absent = "operator_id = require_operator_identity(context)" not in app_text\n    recovery_apply_action_identity_fixed = all(fragment in app_text for fragment in [\n        \'require_operator_identity(context.get("operator_id"), action="engine_position_recovery.create_plan")\',\n        \'require_operator_identity(context.get("operator_id"), action="engine_position_recovery.confirm_plan")\',\n        \'require_operator_identity(context.get("operator_id"), action="engine_position_recovery.verify_completion")\',\n        \'require_operator_identity(context.get("operator_id"), action="recovery_plan_apply.create_from_reviewed_candidate")\',\n        \'require_operator_identity(context.get("operator_id"), action="recovery_plan_apply.confirm_manual_external_recovery")\',\n        \'require_operator_identity(context.get("operator_id"), action="recovery_plan_apply.verify_no_mismatch")\',\n    ])\n    ok = not errors and bad_signature_absent and recovery_apply_action_identity_fixed\n    print(json.dumps({\n        "patch_version": PATCH_VERSION,\n        "ok": ok,\n        "compiled": compiled,\n        "errors": errors,\n        "bad_operator_identity_signature_absent": bad_signature_absent,\n        "recovery_apply_action_identity_fixed": recovery_apply_action_identity_fixed,\n        "runtime_mutation_performed": False,\n        "order_path_mutation_performed": False,\n        "live_real_enablement_performed": False,\n        "auth_policy_relaxation_performed": False,\n        "auto_position_mutation_performed": False,\n    }, indent=2, ensure_ascii=False))\n    return 0 if ok else 1\n\n\nif __name__ == "__main__":\n    raise SystemExit(main())\n'
RUNTIME_HELPER = 'from __future__ import annotations\n\nimport argparse\nimport json\nimport urllib.error\nimport urllib.request\nfrom typing import Any\n\nPATCH_VERSION = "4B.4.3.6.6.33J-H1"\n\n\ndef _request_json(url: str, token: str, operator: str) -> dict[str, Any]:\n    request = urllib.request.Request(url, headers={"X-TradeBot-Auth": token, "X-TradeBot-Operator": operator})\n    with urllib.request.urlopen(request, timeout=5.0) as response:\n        payload = response.read().decode("utf-8")\n    data = json.loads(payload)\n    return data if isinstance(data, dict) else {"raw": data}\n\n\ndef main() -> int:\n    parser = argparse.ArgumentParser(description="Check 33J-H1 recovery plan route hotfix runtime state.")\n    parser.add_argument("--base-url", default="http://127.0.0.1:8787")\n    parser.add_argument("--token", required=True)\n    parser.add_argument("--operator", required=True)\n    args = parser.parse_args()\n    base = args.base_url.rstrip("/")\n    result: dict[str, Any] = {"patch_version": PATCH_VERSION}\n    try:\n        health = _request_json(f"{base}/api/cockpit/health", args.token, args.operator)\n        snapshot = _request_json(f"{base}/api/cockpit/snapshot", args.token, args.operator)\n    except urllib.error.URLError as exc:\n        result.update({"ok": False, "server_reachable": False, "error": str(exc), "hint": "Start cockpit first in a separate PowerShell window."})\n        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))\n        return 1\n    except Exception as exc:\n        result.update({"ok": False, "server_reachable": True, "error": repr(exc), "hint": "Snapshot request failed; check cockpit terminal for traceback."})\n        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))\n        return 1\n    runtime_awareness = snapshot.get("runtime_awareness") or {}\n    runtime_lock = snapshot.get("runtime_lock") or {}\n    recovery_gate = snapshot.get("engine_position_recovery_gate") or runtime_awareness.get("engine_position_recovery_gate") or {}\n    apply_gate = snapshot.get("recovery_plan_apply_verification_gate") or recovery_gate.get("recovery_plan_apply_verification_gate") or {}\n    startup_error = (snapshot.get("cockpit") or {}).get("startup_error")\n    ok = bool(snapshot.get("ok")) and startup_error is None and bool(runtime_lock.get("held_by_current_process", False))\n    result.update({\n        "ok": ok,\n        "server_reachable": True,\n        "health_ok": health.get("ok"),\n        "startup_error": startup_error,\n        "runtime_lock_pid": runtime_lock.get("pid"),\n        "runtime_lock_held_by_current_process": runtime_lock.get("held_by_current_process"),\n        "risk_badge": runtime_awareness.get("risk_badge"),\n        "recovery_status": recovery_gate.get("status"),\n        "plan_present": recovery_gate.get("plan_present"),\n        "plan_confirmed": recovery_gate.get("plan_confirmed"),\n        "manual_external_recovery_confirmed": recovery_gate.get("manual_external_recovery_confirmed"),\n        "verified_no_mismatch": recovery_gate.get("verified_no_mismatch"),\n        "entry_guard_release_verified": recovery_gate.get("entry_guard_release_verified"),\n        "recovery_plan_apply_verification_gate": apply_gate,\n    })\n    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))\n    return 0 if ok else 1\n\n\nif __name__ == "__main__":\n    raise SystemExit(main())\n'
TEST_FILE = 'from __future__ import annotations\n\nimport py_compile\nfrom pathlib import Path\n\n\ndef _root() -> Path:\n    return Path(__file__).resolve().parents[1]\n\n\ndef test_33j_h1_operator_identity_signature_fixed() -> None:\n    text = (_root() / "src/tradebot/cockpit/app.py").read_text(encoding="utf-8")\n    assert "operator_id = require_operator_identity(context)" not in text\n    assert \'require_operator_identity(context.get("operator_id"), action="engine_position_recovery.create_plan")\' in text\n    assert \'require_operator_identity(context.get("operator_id"), action="engine_position_recovery.confirm_plan")\' in text\n    assert \'require_operator_identity(context.get("operator_id"), action="engine_position_recovery.verify_completion")\' in text\n    assert \'require_operator_identity(context.get("operator_id"), action="recovery_plan_apply.create_from_reviewed_candidate")\' in text\n    assert \'require_operator_identity(context.get("operator_id"), action="recovery_plan_apply.confirm_manual_external_recovery")\' in text\n    assert \'require_operator_identity(context.get("operator_id"), action="recovery_plan_apply.verify_no_mismatch")\' in text\n\n\ndef test_33j_h1_routes_still_present() -> None:\n    text = (_root() / "src/tradebot/cockpit/app.py").read_text(encoding="utf-8")\n    assert "/api/cockpit/recovery-plan-apply/create-from-reviewed-candidate" in text\n    assert "/api/cockpit/recovery-plan-apply/confirm-manual-external-recovery" in text\n    assert "/api/cockpit/recovery-plan-apply/verify-no-mismatch" in text\n    assert "CONFIRM_CREATE_RECOVERY_PLAN_FROM_REVIEWED_CANDIDATE" in (_root() / "src/tradebot/cockpit/security.py").read_text(encoding="utf-8")\n\n\ndef test_33j_h1_compile_contract() -> None:\n    for file_path in (_root() / "src/tradebot/cockpit").glob("*.py"):\n        py_compile.compile(str(file_path), doraise=True)\n    py_compile.compile(str(_root() / "tools/check_cockpit_runtime_4B436633J_H1.py"), doraise=True)\n'
README_DOC = '# 4B.4.3.6.6.33J-H1 — Operator Cockpit Recovery Plan Action Route Hotfix\n\nThis hotfix fixes a runtime-only 500 error in the 33J recovery-plan apply endpoints.\n\n## Root cause\n\nThe recovery action routes called `require_operator_identity(context)` although the current security contract requires `require_operator_identity(context.get("operator_id"), action="...")`.\n\n## Fixed endpoints\n\n- `/api/cockpit/engine-position-recovery/create-plan`\n- `/api/cockpit/engine-position-recovery/confirm-plan`\n- `/api/cockpit/engine-position-recovery/verify-completion`\n- `/api/cockpit/recovery-plan-apply/create-from-reviewed-candidate`\n- `/api/cockpit/recovery-plan-apply/confirm-manual-external-recovery`\n- `/api/cockpit/recovery-plan-apply/verify-no-mismatch`\n\n## Safety contract\n\n- No runtime position mutation.\n- No automatic position mutation.\n- No order-path change.\n- No live-real enablement.\n- No auth policy relaxation.\n- Entry guard release still requires verified no-mismatch.\n'
README_APPEND = '<!-- 4B436633J_H1_OPERATOR_COCKPIT_RECOVERY_PLAN_ACTION_ROUTE_HOTFIX -->\n## 33J-H1 Operator Cockpit Recovery Plan Action Route Hotfix\n\nFixes recovery-plan apply endpoint 500s caused by stale `require_operator_identity(context)` route calls. The hotfix only updates action-route operator identity binding; no order path, live-real, auth policy, or position mutation behavior is changed.\n'


def _repo_root() -> Path:
    return Path.cwd()


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.replace("\r\n", "\n"), encoding="utf-8")


def _append_once(path: Path, marker: str, block: str) -> bool:
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    if marker in text:
        return False
    with path.open("a", encoding="utf-8") as fh:
        if text and not text.endswith("\n"):
            fh.write("\n")
        fh.write("\n" + block.strip() + "\n")
    return True


def apply() -> dict[str, object]:
    root = _repo_root()
    app_path = root / "src/tradebot/cockpit/app.py"
    security_path = root / "src/tradebot/cockpit/security.py"
    if not app_path.exists():
        raise RuntimeError("src/tradebot/cockpit/app.py not found")
    if not security_path.exists():
        raise RuntimeError("src/tradebot/cockpit/security.py not found")
    text = app_path.read_text(encoding="utf-8")
    if "recovery_plan_apply.create_from_reviewed_candidate" not in text:
        raise RuntimeError("33J recovery plan apply baseline not found; apply 33J first")
    changed = False
    replacements_applied: list[str] = []
    for old, new in REPLACEMENTS.items():
        if old in text:
            text = text.replace(old, new)
            changed = True
            replacements_applied.append(new.split('action="', 1)[1].split('"', 1)[0])
    app_path.write_text(text, encoding="utf-8")

    _write_text(root / "tools/compile_operator_cockpit_4B436633J_H1.py", COMPILE_HELPER)
    _write_text(root / "tools/check_cockpit_runtime_4B436633J_H1.py", RUNTIME_HELPER)
    _write_text(root / "tests/test_operator_cockpit_4B436633J_H1.py", TEST_FILE)
    _write_text(root / "docs/OPERATOR_COCKPIT_RECOVERY_PLAN_ACTION_ROUTE_HOTFIX_4B436633J_H1.md", README_DOC)
    readme_changed = _append_once(root / "README.md", "<!-- 4B436633J_H1_OPERATOR_COCKPIT_RECOVERY_PLAN_ACTION_ROUTE_HOTFIX -->", README_APPEND)

    try:
        py_compile.compile(str(app_path), doraise=True)
    except Exception as exc:
        raise RuntimeError(f"app.py compile failed after 33J-H1 hotfix: {exc}") from exc

    return {
        "patch_version": PATCH_VERSION,
        "patch_name": PATCH_NAME,
        "written": [
            "src/tradebot/cockpit/app.py",
            "tools/compile_operator_cockpit_4B436633J_H1.py",
            "tools/check_cockpit_runtime_4B436633J_H1.py",
            "tests/test_operator_cockpit_4B436633J_H1.py",
            "docs/OPERATOR_COCKPIT_RECOVERY_PLAN_ACTION_ROUTE_HOTFIX_4B436633J_H1.md",
            "README.md",
        ],
        "app_py_changed": changed,
        "readme_changed": readme_changed,
        "operator_identity_route_signature_hotfix_added": True,
        "recovery_plan_apply_endpoint_500_hotfix_added": True,
        "fixed_actions": replacements_applied,
        "runtime_mutation_performed": False,
        "order_path_mutation_performed": False,
        "live_real_enablement_performed": False,
        "auth_policy_relaxation_performed": False,
        "auto_position_mutation_performed": False,
        "entry_guard_release_policy_changed": False,
    }


if __name__ == "__main__":
    print(json.dumps(apply(), ensure_ascii=False, indent=2))
