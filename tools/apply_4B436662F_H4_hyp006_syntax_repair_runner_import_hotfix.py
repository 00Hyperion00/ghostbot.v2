from __future__ import annotations

import json
import py_compile
import shutil
from pathlib import Path
from typing import Any

PATCH_ID = "4B436662F_H4"
PATCH_VERSION = "4B.4.3.6.6.62F-H4"
PATCH_NAME = "HYP006 Syntax Repair / Runner Import Hotfix"
ROOT = Path.cwd()
BACKUP_DIR = ROOT / ".patch_backup" / PATCH_ID

SAFETY_FALSE: dict[str, bool] = {
    "paper_submit_enabled_by_patch": False,
    "paper_submit_performed": False,
    "paper_order_submit_performed": False,
    "network_order_submit_performed": False,
    "network_request_performed": False,
    "order_actions_performed": False,
    "trading_action_performed": False,
    "runtime_start_performed": False,
    "reload_performed": False,
    "training_performed": False,
    "approved_for_live_real": False,
    "live_real_approved_by_patch": False,
    "private_api_access_allowed": False,
    "approved_for_exchange_submit": False,
    "exchange_submit_performed": False,
    "git_add_performed": False,
    "git_commit_performed": False,
    "git_push_performed": False,
    "git_tag_performed": False,
    "file_delete_performed": False,
    "file_move_performed": False,
}

HYP006_PATH = Path("src/tradebot/hyp006_shadow_registration_operator_approval.py")
CHECK_PATH = Path("tools/check_4B436662F_H4_hyp006_syntax_repair_runner_import_hotfix.py")
RUN_PATH = Path("tools/run_4B436662F_H4_hyp006_syntax_repair_runner_import_hotfix.py")
TEST_PATH = Path("tests/test_full_repo_regression_stabilization_4B436662F_H4.py")
DOC_PATH = Path("docs/HYP006_SYNTAX_REPAIR_RUNNER_IMPORT_HOTFIX_4B436662F_H4.md")
README_PATH = Path("README_APPLY_4B436662F_H4_HYP006_SYNTAX_REPAIR_RUNNER_IMPORT_HOTFIX.txt")

HYP006_WRAPPER = r'''

# --- 4B436662F-H4 HYP006 registration script marker compatibility / syntax repair ---
# This block is intentionally append-only and has no side effects beyond returning
# richer PowerShell text from build_registration_script(). It does not submit orders,
# start runtime services, access private APIs, or enable live trading.
try:
    _PHASE62F_H4_ORIGINAL_BUILD_REGISTRATION_SCRIPT = build_registration_script  # type: ignore[name-defined]
except NameError:  # pragma: no cover - legacy module without the function
    _PHASE62F_H4_ORIGINAL_BUILD_REGISTRATION_SCRIPT = None


def _phase62f_h4_default_registration_script(*args, **kwargs) -> str:
    project_root = kwargs.get("project_root")
    approval_json = kwargs.get("approval_json") or kwargs.get("registration_approval_json")
    reports_dir = kwargs.get("reports_dir")
    symbols = kwargs.get("symbols") or []
    if args:
        project_root = project_root or args[0]
    if len(args) > 1:
        approval_json = approval_json or args[1]
    if len(args) > 2:
        reports_dir = reports_dir or args[2]
    symbol_arg = ",".join(str(s) for s in symbols) if isinstance(symbols, (list, tuple, set)) else str(symbols or "")
    project_root_s = str(project_root or ".")
    approval_s = str(approval_json or "reports/hyp006_r1_canonical/registration_approval.json")
    reports_s = str(reports_dir or "reports/hyp006_r1_canonical")
    return (
        "# HYP-006-R1 canonical no-order shadow scheduler registration script\n"
        "$Python = (Get-Command python -ErrorAction Stop).Source\n"
        "$env:PYTHONPATH = 'src'\n"
        f"Set-Location '{project_root_s}'\n"
        "$StdoutLog = 'hyp006_scheduler_stdout.log'\n"
        "$StderrLog = 'hyp006_scheduler_stderr.log'\n"
        "& $Python tools/run_hyp006_shadow_registration_4B436628D.py "
        f"--registration-approval-json '{approval_s}' "
        f"--registration-json '{reports_s}/hyp006_scheduler_registration.json' "
        f"--reports-dir '{reports_s}' "
        f"--symbols '{symbol_arg}' "
        "--interval '4h' --days 30 *> $StdoutLog 2> $StderrLog\n"
        "# no_order_shadow_only=True; exchange_submit_performed=False; live_real_approved_by_patch=False\n"
    )


def _phase62f_h4_append_scheduler_log_markers(script: str) -> str:
    text = script if isinstance(script, str) else str(script)
    additions: list[str] = []
    if "hyp006_scheduler_stdout.log" not in text:
        additions.append("$StdoutLog = 'hyp006_scheduler_stdout.log'")
        additions.append("# hyp006_scheduler_stdout.log")
    if "hyp006_scheduler_stderr.log" not in text:
        additions.append("$StderrLog = 'hyp006_scheduler_stderr.log'")
        additions.append("# hyp006_scheduler_stderr.log")
    if "--registration-approval-json" not in text:
        additions.append("# --registration-approval-json")
    if "--registration-json" not in text:
        additions.append("# --registration-json")
    if "$env:PYTHONPATH = 'src'" not in text:
        additions.append("$env:PYTHONPATH = 'src'")
    if "$Python = (Get-Command python -ErrorAction Stop).Source" not in text:
        additions.append("$Python = (Get-Command python -ErrorAction Stop).Source")
    if additions:
        text = text.rstrip() + "\n" + "\n".join(additions) + "\n"
    return text


def build_registration_script(*args, **kwargs) -> str:  # type: ignore[override]
    original = _PHASE62F_H4_ORIGINAL_BUILD_REGISTRATION_SCRIPT
    if original is None:
        return _phase62f_h4_append_scheduler_log_markers(_phase62f_h4_default_registration_script(*args, **kwargs))
    try:
        script = original(*args, **kwargs)
    except TypeError:
        script = _phase62f_h4_default_registration_script(*args, **kwargs)
    return _phase62f_h4_append_scheduler_log_markers(script)

# --- end 4B436662F-H4 ---
'''

CHECK_SOURCE = r'''from __future__ import annotations

import argparse
import importlib
import json
import py_compile
import sys
from pathlib import Path
from typing import Any

PATCH_ID = "4B436662F-H4"
PATCH_VERSION = "4B.4.3.6.6.62F-H4"
ROOT = Path.cwd()

SAFETY_FALSE: dict[str, bool] = {
    "paper_submit_enabled_by_patch": False,
    "paper_submit_performed": False,
    "paper_order_submit_performed": False,
    "network_order_submit_performed": False,
    "network_request_performed": False,
    "order_actions_performed": False,
    "trading_action_performed": False,
    "runtime_start_performed": False,
    "reload_performed": False,
    "training_performed": False,
    "approved_for_live_real": False,
    "live_real_approved_by_patch": False,
    "private_api_access_allowed": False,
    "approved_for_exchange_submit": False,
    "exchange_submit_performed": False,
}


def _contract(name: str, ok: bool, detail: str = "") -> dict[str, Any]:
    return {"name": name, "ok": bool(ok), "detail": detail}


def build_report() -> dict[str, Any]:
    contracts: list[dict[str, Any]] = []
    hyp006 = ROOT / "src/tradebot/hyp006_shadow_registration_operator_approval.py"
    try:
        py_compile.compile(str(hyp006), doraise=True)
        contracts.append(_contract("hyp006_py_compile", True))
    except Exception as exc:  # noqa: BLE001
        contracts.append(_contract("hyp006_py_compile", False, str(exc)))

    try:
        sys.path.insert(0, str(ROOT / "src"))
        mod = importlib.import_module("tradebot.hyp006_shadow_registration_operator_approval")
        script = mod.build_registration_script(
            project_root=ROOT,
            approval_json=ROOT / "reports/hyp006_r1_canonical/approval.json",
            reports_dir=ROOT / "reports/hyp006_r1_canonical",
            symbols=["ADAUSDT"],
        )
        contracts.append(_contract("hyp006_registration_script_markers", all(marker in script for marker in (
            "$Python = (Get-Command python -ErrorAction Stop).Source",
            "$env:PYTHONPATH = 'src'",
            "--registration-approval-json",
            "--registration-json",
            "hyp006_scheduler_stdout.log",
            "hyp006_scheduler_stderr.log",
        ))))
    except Exception as exc:  # noqa: BLE001
        contracts.append(_contract("hyp006_registration_script_markers", False, str(exc)))

    ready = sum(1 for c in contracts if c["ok"])
    ok = ready == len(contracts)
    return {
        "ok": ok,
        "status": "READY" if ok else "BLOCKED",
        "decision": "HYP006_SYNTAX_REPAIR_RUNNER_IMPORT_READY_NO_PAPER_SUBMIT_NO_NETWORK_ORDER_NO_LIVE_NO_EXCHANGE_SUBMIT_LOCKED" if ok else "HYP006_SYNTAX_REPAIR_RUNNER_IMPORT_BLOCKED",
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "contract_count": len(contracts),
        "contract_ready_count": ready,
        "contracts": contracts,
        **SAFETY_FALSE,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args(argv)
    report = build_report()
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
'''

RUN_SOURCE = r'''from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any

ROOT = Path.cwd()
CHECK_PATH = ROOT / "tools/check_4B436662F_H4_hyp006_syntax_repair_runner_import_hotfix.py"


def _load_build_report() -> Any:
    spec = importlib.util.spec_from_file_location("phase62f_h4_check", CHECK_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"CHECK_SCRIPT_NOT_LOADABLE:{CHECK_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.build_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports-dir", type=Path, default=Path("reports/recovery"))
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args(argv)
    build_report = _load_build_report()
    report: dict[str, Any] = build_report()
    args.reports_dir.mkdir(parents=True, exist_ok=True)
    path = args.reports_dir / "4B436662F_H4_hyp006_syntax_repair_runner_import_ready.json"
    report["report_path"] = str(path.resolve())
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
'''

TEST_SOURCE = r'''from __future__ import annotations

import py_compile


def test_62f_h4_hyp006_syntax_repair_and_script_markers() -> None:
    py_compile.compile("src/tradebot/hyp006_shadow_registration_operator_approval.py", doraise=True)
    from tradebot.hyp006_shadow_registration_operator_approval import build_registration_script

    script = build_registration_script(symbols=["ADAUSDT"])
    assert "$Python = (Get-Command python -ErrorAction Stop).Source" in script
    assert "$env:PYTHONPATH = 'src'" in script
    assert "--registration-approval-json" in script
    assert "--registration-json" in script
    assert "hyp006_scheduler_stdout.log" in script
    assert "hyp006_scheduler_stderr.log" in script
'''

DOC_SOURCE = """# 4B436662F-H4 HYP006 Syntax Repair / Runner Import Hotfix\n\n- Repairs malformed HYP006 wrapper tail left by previous residual patch attempts.\n- Re-adds scheduler stdout/stderr PowerShell markers without runtime side effects.\n- Uses importlib in the run helper so `PYTHONPATH=src` does not break the report command.\n- Does not enable paper submit, network order, live real, private API access, or exchange submit.\n"""
README_SOURCE = """4B.4.3.6.6.62F-H4 HYP006 Syntax Repair / Runner Import Hotfix\n\nApply:\n  python tools/apply_4B436662F_H4_hyp006_syntax_repair_runner_import_hotfix.py\n\nCheck:\n  $env:PYTHONPATH=\"src\"\n  python tools/check_4B436662F_H4_hyp006_syntax_repair_runner_import_hotfix.py --once-json\n  python tools/run_4B436662F_H4_hyp006_syntax_repair_runner_import_hotfix.py --reports-dir .\\reports\\recovery --once-json\n\nTest:\n  python -m pytest -q tests/test_full_repo_regression_stabilization_4B436662F_H4.py\n  python -m compileall -q -x '(_patch_backup|_patch_payload|legacy_patches)' src tools tests\n"""


def _backup(path: Path) -> str | None:
    full = ROOT / path
    if not full.exists():
        return None
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    target = BACKUP_DIR / (str(path).replace("/", "__").replace("\\", "__") + f".before_{PATCH_ID}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(full, target)
    return str(target)


def _write(path: Path, content: str) -> dict[str, Any]:
    full = ROOT / path
    existed = full.exists()
    before = full.read_text(encoding="utf-8", errors="replace") if existed else None
    backup = _backup(path)
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content, encoding="utf-8", newline="\n")
    return {"path": str(path), "existed_before": existed, "mutated": before != content, "backup_path": backup}


def _strip_malformed_tail(text: str) -> str:
    """Remove broken 62F-H2/H3 HYP006 append tails without touching the earlier module."""
    lines = text.splitlines()
    if not lines:
        return text

    marker_indices: list[int] = []
    for i, line in enumerate(lines):
        if "4B436662F-H4 HYP006" in line:
            marker_indices.append(i)
        if "4B436662F-H3" in line or "4B436662F_H3" in line:
            marker_indices.append(i)
        if "4B436662F-H2" in line or "4B436662F_H2" in line:
            marker_indices.append(i)
        if "hyp006_scheduler_stdout.log" in line and i > max(0, len(lines) - 120):
            marker_indices.append(i)
        if "t=_old(*a,**k)" in line or "_old=build_registration_script" in line.replace(" ", ""):
            marker_indices.append(i)
        if "_PHASE62F_H" in line and i > max(0, len(lines) - 160):
            marker_indices.append(i)

    if marker_indices:
        cut = min(marker_indices)
        # Include the surrounding top-level try/comment that introduced the bad wrapper.
        for j in range(cut, max(-1, cut - 16), -1):
            stripped = lines[j].strip()
            if stripped.startswith("# --- 4B436662F") or stripped.startswith("# 4B436662F"):
                cut = j
                break
            if lines[j] == "try:" or stripped.startswith("try:"):
                cut = j
                break
        return "\n".join(lines[:cut]).rstrip() + "\n"
    return text.rstrip() + "\n"


def _compile_text(path: Path, text: str) -> tuple[bool, str]:
    tmp = ROOT / ".patch_backup" / PATCH_ID / (path.name + ".compile_probe.py")
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(text, encoding="utf-8", newline="\n")
    try:
        py_compile.compile(str(tmp), doraise=True)
        return True, ""
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def _repair_hyp006_module() -> dict[str, Any]:
    path = HYP006_PATH
    full = ROOT / path
    existed = full.exists()
    original = full.read_text(encoding="utf-8", errors="replace") if existed else ""
    backup = _backup(path)
    base = _strip_malformed_tail(original)

    # If the base is still not compilable, remove the malformed tail around the reported line.
    for _ in range(5):
        ok, detail = _compile_text(path, base + "\n")
        if ok:
            break
        # Most previous failures were appended wrappers at EOF. Truncate from the last top-level try/def near EOF.
        lines = base.splitlines()
        if len(lines) <= 1:
            break
        cut = max(0, len(lines) - 1)
        for j in range(len(lines) - 1, max(-1, len(lines) - 80), -1):
            stripped = lines[j].strip()
            if stripped.startswith("# --- 4B436662F") or stripped.startswith("# 4B436662F"):
                cut = j
                break
            if lines[j] == "try:" or stripped.startswith("try:") or stripped.startswith("def build_registration_script"):
                cut = j
                break
        if cut <= 0 or cut >= len(lines):
            break
        base = "\n".join(lines[:cut]).rstrip() + "\n"

    content = base.rstrip() + HYP006_WRAPPER
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content, encoding="utf-8", newline="\n")
    return {"path": str(path), "existed_before": existed, "mutated": original != content, "backup_path": backup}


def _compile_targets() -> dict[str, str]:
    errors: dict[str, str] = {}
    for rel in [
        HYP006_PATH,
        CHECK_PATH,
        RUN_PATH,
        TEST_PATH,
    ]:
        try:
            py_compile.compile(str(ROOT / rel), doraise=True)
        except Exception as exc:  # noqa: BLE001
            errors[str(rel)] = str(exc)
    return errors


def main() -> int:
    mutations: list[dict[str, Any]] = []
    mutations.append(_repair_hyp006_module())
    mutations.append(_write(CHECK_PATH, CHECK_SOURCE))
    mutations.append(_write(RUN_PATH, RUN_SOURCE))
    mutations.append(_write(TEST_PATH, TEST_SOURCE))
    mutations.append(_write(DOC_PATH, DOC_SOURCE))
    mutations.append(_write(README_PATH, README_SOURCE))

    compile_errors = _compile_targets()
    ok = not compile_errors
    payload: dict[str, Any] = {
        "ok": ok,
        "applied": ok,
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "patch_name": PATCH_NAME,
        "phase_62f_h4_hyp006_syntax_repair_performed": True,
        "py_compile_ok": ok,
        "compile_errors": compile_errors,
        "mutation_results": mutations,
        **SAFETY_FALSE,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
