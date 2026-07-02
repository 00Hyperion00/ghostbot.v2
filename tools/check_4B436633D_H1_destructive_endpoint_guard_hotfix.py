from __future__ import annotations

import argparse
import json
import os
import py_compile
import re
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

PATCH_ID = "4B436633D_H1"
PATCH_VERSION = "4B.4.3.6.6.33D-H1"
CHECK_NAME = "destructive_endpoint_guard_coverage_hotfix"
READY_DECISION = "DESTRUCTIVE_ENDPOINT_GUARD_COVERAGE_HOTFIX_READY"
NOT_READY_DECISION = "DESTRUCTIVE_ENDPOINT_GUARD_COVERAGE_HOTFIX_NOT_READY"
TARGET_API_PATH = Path("src/tradebot/api.py")
TARGET_ENDPOINTS: tuple[str, ...] = ("/balance-sync", "/risk-reset", "/safe-mode/toggle")
GUARD_CALL = "_require_33d_h1_legacy_destructive_endpoint_guard"


@dataclass(frozen=True)
class EndpointGuardRecord:
    endpoint: str
    present: bool
    guarded: bool
    line_number: int | None
    guard_line_number: int | None
    evidence: list[str]


def _now_ms() -> int:
    return int(time.time() * 1000)


def _compile_file(path: Path) -> str | None:
    if not path.exists():
        return f"missing: {path.as_posix()}"
    try:
        py_compile.compile(str(path), doraise=True)
        return None
    except Exception as exc:
        return f"{type(exc).__name__}: {exc}"


def _find_endpoint_guard(content: str, endpoint: str) -> EndpointGuardRecord:
    lines = content.splitlines()
    pattern = re.compile(r"^\s*@app\.post\(\s*([\'\"]){0}\1".format(re.escape(endpoint)))
    decorator_index: int | None = None
    for index, line in enumerate(lines):
        if pattern.search(line):
            decorator_index = index
            break
    if decorator_index is None:
        return EndpointGuardRecord(endpoint, False, False, None, None, [])

    block_end = len(lines)
    for index in range(decorator_index + 1, len(lines)):
        if index > decorator_index + 1 and re.match(r"^\s*@app\.(get|post|put|patch|delete)\(", lines[index]):
            block_end = index
            break
    guard_line_number: int | None = None
    evidence: list[str] = []
    for index in range(decorator_index + 1, block_end):
        lower = lines[index].lower()
        if GUARD_CALL.lower() in lower:
            guard_line_number = index + 1
            evidence.append("33d_h1_guard_call")
        if "fail-closed" in lower or "fail_closed" in lower:
            evidence.append("fail_closed")
        if "blocked" in lower:
            evidence.append("blocked")
        if "operator" in lower:
            evidence.append("operator")
        if "confirm" in lower:
            evidence.append("confirmation")
        if "guard" in lower:
            evidence.append("guard")
        if "httpexception" in lower or "raise" in lower:
            evidence.append("raise_httpexception")
    return EndpointGuardRecord(
        endpoint=endpoint,
        present=True,
        guarded=guard_line_number is not None,
        line_number=decorator_index + 1,
        guard_line_number=guard_line_number,
        evidence=sorted(set(evidence)),
    )


def scan_endpoint_guards(root: Path) -> dict[str, Any]:
    api_path = root / TARGET_API_PATH
    if not api_path.exists():
        records = [EndpointGuardRecord(endpoint, False, False, None, None, []) for endpoint in TARGET_ENDPOINTS]
    else:
        content = api_path.read_text(encoding="utf-8")
        records = [_find_endpoint_guard(content, endpoint) for endpoint in TARGET_ENDPOINTS]
    present_count = sum(1 for record in records if record.present)
    guarded_count = sum(1 for record in records if record.present and record.guarded)
    return {
        "api_path": TARGET_API_PATH.as_posix(),
        "api_exists": api_path.exists(),
        "records": [asdict(record) for record in records],
        "target_endpoint_count": len(TARGET_ENDPOINTS),
        "present_count": present_count,
        "guarded_count": guarded_count,
        "unguarded_target_endpoint_count": len(TARGET_ENDPOINTS) - guarded_count,
        "complete": present_count == len(TARGET_ENDPOINTS) and guarded_count == len(TARGET_ENDPOINTS),
    }


def _run_33d_check(root: Path) -> dict[str, Any]:
    check_path = root / "tools/check_4B436633D_runtime_safety_lockdown.py"
    if not check_path.exists():
        return {"available": False, "ok": None, "error": "33D check script missing"}
    env = os.environ.copy()
    src_path = str((root / "src").resolve())
    env["PYTHONPATH"] = src_path + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    try:
        completed = subprocess.run(
            [sys.executable, str(check_path), "--once-json"],
            cwd=root,
            env=env,
            text=True,
            capture_output=True,
            timeout=60,
            check=False,
        )
    except Exception as exc:
        return {"available": True, "ok": False, "error": f"{type(exc).__name__}: {exc}"}
    stdout = completed.stdout.strip()
    parsed = None
    if stdout:
        try:
            parsed = json.loads(stdout.splitlines()[-1])
        except json.JSONDecodeError:
            parsed = None
    return {
        "available": True,
        "ok": completed.returncode == 0,
        "returncode": completed.returncode,
        "stdout_tail": stdout[-2000:],
        "stderr_tail": completed.stderr.strip()[-2000:],
        "parsed": parsed,
    }


def build_report(root: Path, include_33d_check: bool = True) -> dict[str, Any]:
    endpoint_guard = scan_endpoint_guards(root)
    required_files = [
        Path("README_APPLY_4B436633D_H1.txt"),
        Path("docs/RUNTIME_SAFETY_LOCKDOWN_DESTRUCTIVE_ENDPOINT_GUARD_HOTFIX_4B436633D_H1.md"),
        Path("tools/check_4B436633D_H1_destructive_endpoint_guard_hotfix.py"),
        Path("tools/run_4B436633D_H1_destructive_endpoint_guard_hotfix.py"),
        Path("tests/test_runtime_safety_lockdown_guard_h1_4B436633D_H1.py"),
        TARGET_API_PATH,
    ]
    missing_files = [p.as_posix() for p in required_files if not (root / p).exists()]
    compile_targets = [TARGET_API_PATH, Path("tools/check_4B436633D_H1_destructive_endpoint_guard_hotfix.py"), Path("tools/run_4B436633D_H1_destructive_endpoint_guard_hotfix.py"), Path("tests/test_runtime_safety_lockdown_guard_h1_4B436633D_H1.py")]
    compile_errors = {p.as_posix(): err for p in compile_targets for err in [_compile_file(root / p)] if err is not None}
    source_33d = _run_33d_check(root) if include_33d_check else {"available": False, "skipped": True}
    parsed = source_33d.get("parsed") if isinstance(source_33d, dict) else None
    source_33d_ready = bool(isinstance(parsed, dict) and parsed.get("status") == "READY" and parsed.get("destructive_endpoint_audit_complete") is True and int(parsed.get("unguarded_destructive_endpoint_count", 999999)) == 0)
    h1_complete = bool(endpoint_guard["complete"] and not compile_errors and not missing_files)
    return {
        "patch_id": PATCH_ID,
        "patch_version": PATCH_VERSION,
        "check_name": CHECK_NAME,
        "generated_at_epoch_ms": _now_ms(),
        "ok": True,
        "status": "READY" if h1_complete else "NOT_READY",
        "decision": READY_DECISION if h1_complete else NOT_READY_DECISION,
        "required_files_present": not missing_files,
        "missing_files": missing_files,
        "py_compile_ok": not compile_errors,
        "compile_errors": compile_errors,
        "endpoint_guard_coverage": endpoint_guard,
        "endpoint_guard_coverage_complete": endpoint_guard["complete"],
        "source_33d_check": source_33d,
        "source_33d_ready_after_hotfix": source_33d_ready,
        "destructive_endpoint_audit_expected_ready": endpoint_guard["complete"],
        "runtime_safety_lockdown_expected_complete": endpoint_guard["complete"],
        "approved_for_live_real": False,
        "approved_for_paper_transition": False,
        "approved_for_exchange_submit": False,
        "approved_for_runtime_overlay": False,
        "live_real_submit_allowed": False,
        "paper_submit_allowed": False,
        "network_submit_allowed": False,
        "exchange_submit_allowed": False,
        "runtime_overlay_allowed": False,
        "trading_action_performed": False,
        "exchange_submit_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "runtime_overlay_activated": False,
        "destructive_cleanup_performed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check 4B436633D-H1 destructive endpoint guard hotfix.")
    parser.add_argument("--once-json", action="store_true")
    parser.add_argument("--skip-33d-check", action="store_true")
    args = parser.parse_args()
    print(json.dumps(build_report(Path.cwd(), include_33d_check=not args.skip_33d_check), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
