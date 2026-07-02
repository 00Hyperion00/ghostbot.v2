from __future__ import annotations

import json
import py_compile
import re
import shutil
import time
from pathlib import Path
from typing import Any

PATCH_ID = "4B436633D_H1"
PATCH_VERSION = "4B.4.3.6.6.33D-H1"
PATCH_NAME = "Destructive Endpoint Guard Coverage Hotfix"
TARGET_API_PATH = Path("src/tradebot/api.py")
TARGET_ENDPOINTS: tuple[str, ...] = ("/balance-sync", "/risk-reset", "/safe-mode/toggle")
GUARD_CALL = "_require_33d_h1_legacy_destructive_endpoint_guard"

PAYLOADS: dict[str, str] = {'README_APPLY_4B436633D_H1.txt': '4B.4.3.6.6.33D-H1 — Destructive Endpoint Guard Coverage Hotfix\n\nUygulama:\n\n  python tools/apply_4B436633D_H1_destructive_endpoint_guard_hotfix.py\n\nKontrol:\n\n  $env:PYTHONPATH="src"\n  python tools/check_4B436633D_H1_destructive_endpoint_guard_hotfix.py --once-json\n  python -m pytest -q tests/test_runtime_safety_lockdown_guard_h1_4B436633D_H1.py\n  python -m compileall -q -x \'(_patch_backup|_patch_payload|legacy_patches)\' src tools tests\n\nRapor üret:\n\n  $env:PYTHONPATH="src"\n  python tools/run_4B436633D_H1_destructive_endpoint_guard_hotfix.py --reports-dir .\\reports\\recovery --once-json\n\n33D tekrar doğrula:\n\n  $env:PYTHONPATH="src"\n  python tools/check_4B436633D_runtime_safety_lockdown.py --once-json\n  python tools/run_4B436633D_runtime_safety_lockdown.py --reports-dir .\\reports\\recovery --once-json\n\nBu hotfix emir, exchange submit, runtime overlay, training veya reload yapmaz.\n', 'docs/RUNTIME_SAFETY_LOCKDOWN_DESTRUCTIVE_ENDPOINT_GUARD_HOTFIX_4B436633D_H1.md': '# 4B.4.3.6.6.33D-H1 — Destructive Endpoint Guard Coverage Hotfix\n\nBu hotfix, 33D `Runtime Safety Lockdown` çıktısında unguarded görünen üç legacy FastAPI endpointini fail-closed guard ile kapatır:\n\n- `POST /balance-sync`\n- `POST /risk-reset`\n- `POST /safe-mode/toggle`\n\nBu endpointler `src/tradebot/api.py` içinde legacy yüzeydir. Cockpit tarafındaki `/api/...` endpointler zaten operator / confirmation / runtime-lock guard evidence ile korunmaktadır. Bu patch legacy destructive endpointleri doğrudan bloke eder.\n\n## Safety contract\n\n- Exchange submit yapmaz.\n- Trading action yapmaz.\n- Runtime overlay açmaz.\n- Training yapmaz.\n- Reload yapmaz.\n- Paper/live/live-real onayı vermez.\n- Destructive cleanup yapmaz.\n\nBeklenen 33D-H1 kararı:\n\n```text\nDESTRUCTIVE_ENDPOINT_GUARD_COVERAGE_HOTFIX_READY\n```\n\nBeklenen 33D rerun kararı:\n\n```text\nRUNTIME_SAFETY_LOCKDOWN_READY_ALL_RUNTIME_SUBMIT_PATHS_BLOCKED\n```\n', 'tools/check_4B436633D_H1_destructive_endpoint_guard_hotfix.py': 'from __future__ import annotations\n\nimport argparse\nimport json\nimport os\nimport py_compile\nimport re\nimport subprocess\nimport sys\nimport time\nfrom dataclasses import asdict, dataclass\nfrom pathlib import Path\nfrom typing import Any\n\nPATCH_ID = "4B436633D_H1"\nPATCH_VERSION = "4B.4.3.6.6.33D-H1"\nCHECK_NAME = "destructive_endpoint_guard_coverage_hotfix"\nREADY_DECISION = "DESTRUCTIVE_ENDPOINT_GUARD_COVERAGE_HOTFIX_READY"\nNOT_READY_DECISION = "DESTRUCTIVE_ENDPOINT_GUARD_COVERAGE_HOTFIX_NOT_READY"\nTARGET_API_PATH = Path("src/tradebot/api.py")\nTARGET_ENDPOINTS: tuple[str, ...] = ("/balance-sync", "/risk-reset", "/safe-mode/toggle")\nGUARD_CALL = "_require_33d_h1_legacy_destructive_endpoint_guard"\n\n\n@dataclass(frozen=True)\nclass EndpointGuardRecord:\n    endpoint: str\n    present: bool\n    guarded: bool\n    line_number: int | None\n    guard_line_number: int | None\n    evidence: list[str]\n\n\ndef _now_ms() -> int:\n    return int(time.time() * 1000)\n\n\ndef _compile_file(path: Path) -> str | None:\n    if not path.exists():\n        return f"missing: {path.as_posix()}"\n    try:\n        py_compile.compile(str(path), doraise=True)\n        return None\n    except Exception as exc:\n        return f"{type(exc).__name__}: {exc}"\n\n\ndef _find_endpoint_guard(content: str, endpoint: str) -> EndpointGuardRecord:\n    lines = content.splitlines()\n    pattern = re.compile(r"^\\s*@app\\.post\\(\\s*([\\\'\\"]){0}\\1".format(re.escape(endpoint)))\n    decorator_index: int | None = None\n    for index, line in enumerate(lines):\n        if pattern.search(line):\n            decorator_index = index\n            break\n    if decorator_index is None:\n        return EndpointGuardRecord(endpoint, False, False, None, None, [])\n\n    block_end = len(lines)\n    for index in range(decorator_index + 1, len(lines)):\n        if index > decorator_index + 1 and re.match(r"^\\s*@app\\.(get|post|put|patch|delete)\\(", lines[index]):\n            block_end = index\n            break\n    guard_line_number: int | None = None\n    evidence: list[str] = []\n    for index in range(decorator_index + 1, block_end):\n        lower = lines[index].lower()\n        if GUARD_CALL.lower() in lower:\n            guard_line_number = index + 1\n            evidence.append("33d_h1_guard_call")\n        if "fail-closed" in lower or "fail_closed" in lower:\n            evidence.append("fail_closed")\n        if "blocked" in lower:\n            evidence.append("blocked")\n        if "operator" in lower:\n            evidence.append("operator")\n        if "confirm" in lower:\n            evidence.append("confirmation")\n        if "guard" in lower:\n            evidence.append("guard")\n        if "httpexception" in lower or "raise" in lower:\n            evidence.append("raise_httpexception")\n    return EndpointGuardRecord(\n        endpoint=endpoint,\n        present=True,\n        guarded=guard_line_number is not None,\n        line_number=decorator_index + 1,\n        guard_line_number=guard_line_number,\n        evidence=sorted(set(evidence)),\n    )\n\n\ndef scan_endpoint_guards(root: Path) -> dict[str, Any]:\n    api_path = root / TARGET_API_PATH\n    if not api_path.exists():\n        records = [EndpointGuardRecord(endpoint, False, False, None, None, []) for endpoint in TARGET_ENDPOINTS]\n    else:\n        content = api_path.read_text(encoding="utf-8")\n        records = [_find_endpoint_guard(content, endpoint) for endpoint in TARGET_ENDPOINTS]\n    present_count = sum(1 for record in records if record.present)\n    guarded_count = sum(1 for record in records if record.present and record.guarded)\n    return {\n        "api_path": TARGET_API_PATH.as_posix(),\n        "api_exists": api_path.exists(),\n        "records": [asdict(record) for record in records],\n        "target_endpoint_count": len(TARGET_ENDPOINTS),\n        "present_count": present_count,\n        "guarded_count": guarded_count,\n        "unguarded_target_endpoint_count": len(TARGET_ENDPOINTS) - guarded_count,\n        "complete": present_count == len(TARGET_ENDPOINTS) and guarded_count == len(TARGET_ENDPOINTS),\n    }\n\n\ndef _run_33d_check(root: Path) -> dict[str, Any]:\n    check_path = root / "tools/check_4B436633D_runtime_safety_lockdown.py"\n    if not check_path.exists():\n        return {"available": False, "ok": None, "error": "33D check script missing"}\n    env = os.environ.copy()\n    src_path = str((root / "src").resolve())\n    env["PYTHONPATH"] = src_path + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")\n    try:\n        completed = subprocess.run(\n            [sys.executable, str(check_path), "--once-json"],\n            cwd=root,\n            env=env,\n            text=True,\n            capture_output=True,\n            timeout=60,\n            check=False,\n        )\n    except Exception as exc:\n        return {"available": True, "ok": False, "error": f"{type(exc).__name__}: {exc}"}\n    stdout = completed.stdout.strip()\n    parsed = None\n    if stdout:\n        try:\n            parsed = json.loads(stdout.splitlines()[-1])\n        except json.JSONDecodeError:\n            parsed = None\n    return {\n        "available": True,\n        "ok": completed.returncode == 0,\n        "returncode": completed.returncode,\n        "stdout_tail": stdout[-2000:],\n        "stderr_tail": completed.stderr.strip()[-2000:],\n        "parsed": parsed,\n    }\n\n\ndef build_report(root: Path, include_33d_check: bool = True) -> dict[str, Any]:\n    endpoint_guard = scan_endpoint_guards(root)\n    required_files = [\n        Path("README_APPLY_4B436633D_H1.txt"),\n        Path("docs/RUNTIME_SAFETY_LOCKDOWN_DESTRUCTIVE_ENDPOINT_GUARD_HOTFIX_4B436633D_H1.md"),\n        Path("tools/check_4B436633D_H1_destructive_endpoint_guard_hotfix.py"),\n        Path("tools/run_4B436633D_H1_destructive_endpoint_guard_hotfix.py"),\n        Path("tests/test_runtime_safety_lockdown_guard_h1_4B436633D_H1.py"),\n        TARGET_API_PATH,\n    ]\n    missing_files = [p.as_posix() for p in required_files if not (root / p).exists()]\n    compile_targets = [TARGET_API_PATH, Path("tools/check_4B436633D_H1_destructive_endpoint_guard_hotfix.py"), Path("tools/run_4B436633D_H1_destructive_endpoint_guard_hotfix.py"), Path("tests/test_runtime_safety_lockdown_guard_h1_4B436633D_H1.py")]\n    compile_errors = {p.as_posix(): err for p in compile_targets for err in [_compile_file(root / p)] if err is not None}\n    source_33d = _run_33d_check(root) if include_33d_check else {"available": False, "skipped": True}\n    parsed = source_33d.get("parsed") if isinstance(source_33d, dict) else None\n    source_33d_ready = bool(isinstance(parsed, dict) and parsed.get("status") == "READY" and parsed.get("destructive_endpoint_audit_complete") is True and int(parsed.get("unguarded_destructive_endpoint_count", 999999)) == 0)\n    h1_complete = bool(endpoint_guard["complete"] and not compile_errors and not missing_files)\n    return {\n        "patch_id": PATCH_ID,\n        "patch_version": PATCH_VERSION,\n        "check_name": CHECK_NAME,\n        "generated_at_epoch_ms": _now_ms(),\n        "ok": True,\n        "status": "READY" if h1_complete else "NOT_READY",\n        "decision": READY_DECISION if h1_complete else NOT_READY_DECISION,\n        "required_files_present": not missing_files,\n        "missing_files": missing_files,\n        "py_compile_ok": not compile_errors,\n        "compile_errors": compile_errors,\n        "endpoint_guard_coverage": endpoint_guard,\n        "endpoint_guard_coverage_complete": endpoint_guard["complete"],\n        "source_33d_check": source_33d,\n        "source_33d_ready_after_hotfix": source_33d_ready,\n        "destructive_endpoint_audit_expected_ready": endpoint_guard["complete"],\n        "runtime_safety_lockdown_expected_complete": endpoint_guard["complete"],\n        "approved_for_live_real": False,\n        "approved_for_paper_transition": False,\n        "approved_for_exchange_submit": False,\n        "approved_for_runtime_overlay": False,\n        "live_real_submit_allowed": False,\n        "paper_submit_allowed": False,\n        "network_submit_allowed": False,\n        "exchange_submit_allowed": False,\n        "runtime_overlay_allowed": False,\n        "trading_action_performed": False,\n        "exchange_submit_performed": False,\n        "training_performed": False,\n        "reload_performed": False,\n        "runtime_overlay_activated": False,\n        "destructive_cleanup_performed": False,\n    }\n\n\ndef main() -> int:\n    parser = argparse.ArgumentParser(description="Check 4B436633D-H1 destructive endpoint guard hotfix.")\n    parser.add_argument("--once-json", action="store_true")\n    parser.add_argument("--skip-33d-check", action="store_true")\n    args = parser.parse_args()\n    print(json.dumps(build_report(Path.cwd(), include_33d_check=not args.skip_33d_check), ensure_ascii=False, sort_keys=True))\n    return 0\n\n\nif __name__ == "__main__":\n    raise SystemExit(main())\n', 'tools/run_4B436633D_H1_destructive_endpoint_guard_hotfix.py': 'from __future__ import annotations\n\nimport argparse\nimport json\nimport time\nfrom pathlib import Path\n\nfrom check_4B436633D_H1_destructive_endpoint_guard_hotfix import build_report\n\nPATCH_ID = "4B436633D_H1"\nPATCH_VERSION = "4B.4.3.6.6.33D-H1"\n\n\ndef _timestamp() -> str:\n    return time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())\n\n\ndef main() -> int:\n    parser = argparse.ArgumentParser(description="Run 4B436633D-H1 destructive endpoint guard hotfix report.")\n    parser.add_argument("--reports-dir", default="reports/recovery")\n    parser.add_argument("--once-json", action="store_true")\n    parser.add_argument("--skip-33d-check", action="store_true")\n    args = parser.parse_args()\n    root = Path.cwd()\n    report = build_report(root, include_33d_check=not args.skip_33d_check)\n    reports_dir = root / args.reports_dir\n    reports_dir.mkdir(parents=True, exist_ok=True)\n    suffix = "ready" if report.get("status") == "READY" else "not_ready"\n    path = reports_dir / f"4B436633D_H1_destructive_endpoint_guard_hotfix_{_timestamp()}_{suffix}.json"\n    path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\\n", encoding="utf-8")\n    report["report_path"] = str(path)\n    print(json.dumps(report, ensure_ascii=False, sort_keys=True))\n    return 0\n\n\nif __name__ == "__main__":\n    raise SystemExit(main())\n', 'tests/test_runtime_safety_lockdown_guard_h1_4B436633D_H1.py': 'from __future__ import annotations\n\nimport importlib.util\nimport subprocess\nimport sys\nfrom pathlib import Path\n\n\ndef _load_apply_module(path: Path):\n    spec = importlib.util.spec_from_file_location("apply_33d_h1", path)\n    assert spec is not None and spec.loader is not None\n    module = importlib.util.module_from_spec(spec)\n    spec.loader.exec_module(module)\n    return module\n\n\ndef _write_sample_api(path: Path) -> None:\n    path.parent.mkdir(parents=True, exist_ok=True)\n    path.write_text(\n        "from fastapi import FastAPI\\n\\n"\n        "app = FastAPI()\\n\\n"\n        "@app.post(\'/balance-sync\')\\n"\n        "def balance_sync():\\n"\n        "    return {\'ok\': True}\\n\\n"\n        "@app.post(\'/risk-reset\')\\n"\n        "async def risk_reset():\\n"\n        "    return {\'ok\': True}\\n\\n"\n        "@app.post(\'/safe-mode/toggle\')\\n"\n        "def safe_mode_toggle():\\n"\n        "    \\"\\"\\"Toggle safe mode.\\"\\"\\"\\n"\n        "    return {\'ok\': True}\\n",\n        encoding="utf-8",\n    )\n\n\ndef test_patcher_injects_fail_closed_guard_for_three_legacy_endpoints(tmp_path: Path) -> None:\n    api_path = tmp_path / "src/tradebot/api.py"\n    _write_sample_api(api_path)\n    module = _load_apply_module(Path("tools/apply_4B436633D_H1_destructive_endpoint_guard_hotfix.py"))\n    result = module.patch_api_file(api_path)\n    assert result["api_guard_patch_performed"] is True\n    text = api_path.read_text(encoding="utf-8")\n    assert text.count("_require_33d_h1_legacy_destructive_endpoint_guard(") == 4\n    assert \'_require_33d_h1_legacy_destructive_endpoint_guard("/balance-sync")\' in text\n    assert \'_require_33d_h1_legacy_destructive_endpoint_guard("/risk-reset")\' in text\n    assert \'_require_33d_h1_legacy_destructive_endpoint_guard("/safe-mode/toggle")\' in text\n    compile(text, str(api_path), "exec")\n\n\ndef test_patcher_is_idempotent(tmp_path: Path) -> None:\n    api_path = tmp_path / "src/tradebot/api.py"\n    _write_sample_api(api_path)\n    module = _load_apply_module(Path("tools/apply_4B436633D_H1_destructive_endpoint_guard_hotfix.py"))\n    first = module.patch_api_file(api_path)\n    second = module.patch_api_file(api_path)\n    text = api_path.read_text(encoding="utf-8")\n    assert first["api_guard_patch_performed"] is True\n    assert second["api_guard_patch_performed"] is False\n    assert text.count("_require_33d_h1_legacy_destructive_endpoint_guard(") == 4\n\n\ndef test_check_script_detects_guard_coverage(tmp_path: Path) -> None:\n    api_path = tmp_path / "src/tradebot/api.py"\n    _write_sample_api(api_path)\n    module = _load_apply_module(Path("tools/apply_4B436633D_H1_destructive_endpoint_guard_hotfix.py"))\n    module.patch_api_file(api_path)\n    tools_dir = tmp_path / "tools"\n    docs_dir = tmp_path / "docs"\n    tests_dir = tmp_path / "tests"\n    tools_dir.mkdir(parents=True, exist_ok=True)\n    docs_dir.mkdir(parents=True, exist_ok=True)\n    tests_dir.mkdir(parents=True, exist_ok=True)\n    (tmp_path / "README_APPLY_4B436633D_H1.txt").write_text("ok\\n", encoding="utf-8")\n    (docs_dir / "RUNTIME_SAFETY_LOCKDOWN_DESTRUCTIVE_ENDPOINT_GUARD_HOTFIX_4B436633D_H1.md").write_text("ok\\n", encoding="utf-8")\n    (tests_dir / "test_runtime_safety_lockdown_guard_h1_4B436633D_H1.py").write_text("def test_placeholder():\\n    assert True\\n", encoding="utf-8")\n    check_src = Path("tools/check_4B436633D_H1_destructive_endpoint_guard_hotfix.py")\n    run_src = Path("tools/run_4B436633D_H1_destructive_endpoint_guard_hotfix.py")\n    check_dst = tools_dir / check_src.name\n    run_dst = tools_dir / run_src.name\n    check_dst.write_text(check_src.read_text(encoding="utf-8"), encoding="utf-8")\n    run_dst.write_text(run_src.read_text(encoding="utf-8"), encoding="utf-8")\n    completed = subprocess.run([sys.executable, str(check_dst), "--once-json", "--skip-33d-check"], cwd=tmp_path, text=True, capture_output=True, check=False)\n    assert completed.returncode == 0, completed.stderr\n    assert \'"status": "READY"\' in completed.stdout\n    assert \'"endpoint_guard_coverage_complete": true\' in completed.stdout\n'}
HELPER_BLOCK = '\n\n# 4B436633D-H1 Runtime Safety Lockdown: fail-closed legacy destructive endpoint guard.\ndef _require_33d_h1_legacy_destructive_endpoint_guard(endpoint_path: str) -> None:\n    """Fail closed for legacy destructive API endpoints until guarded cockpit flow is used."""\n    from fastapi import HTTPException as _HTTPException\n\n    raise _HTTPException(\n        status_code=423,\n        detail={\n            "ok": False,\n            "blocked": True,\n            "guard": "4B436633D-H1 legacy destructive endpoint guard",\n            "endpoint": endpoint_path,\n            "reason": "Legacy destructive endpoint is blocked; use guarded cockpit endpoint with operator confirmation.",\n            "approved_for_live_real": False,\n            "approved_for_exchange_submit": False,\n            "approved_for_runtime_overlay": False,\n            "live_real_submit_allowed": False,\n            "paper_submit_allowed": False,\n            "network_submit_allowed": False,\n            "exchange_submit_allowed": False,\n            "runtime_overlay_allowed": False,\n            "exchange_submit_performed": False,\n            "trading_action_performed": False,\n            "runtime_overlay_activated": False,\n        },\n    )\n'


def _timestamp() -> str:
    return time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())


def _backup_existing(path: Path, backup_root: Path, backed_up: list[str]) -> None:
    if not path.exists():
        return
    try:
        relative = path.resolve().relative_to(Path.cwd().resolve())
    except ValueError:
        relative = Path(path.name)
    destination = backup_root / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, destination)
    backed_up.append(relative.as_posix())


def _find_insert_after_docstring(lines: list[str], def_index: int) -> int:
    insert_index = def_index + 1
    if insert_index >= len(lines):
        return insert_index
    stripped = lines[insert_index].strip()
    triple_double = chr(34) * 3
    triple_single = chr(39) * 3
    if not (stripped.startswith(triple_double) or stripped.startswith(triple_single)):
        return insert_index
    quote = triple_double if stripped.startswith(triple_double) else triple_single
    if stripped.count(quote) >= 2 and len(stripped) > 3:
        return insert_index + 1
    for index in range(insert_index + 1, len(lines)):
        if quote in lines[index]:
            return index + 1
    return insert_index


def _ensure_helper(content: str) -> tuple[str, bool]:
    if f"def {GUARD_CALL}" in content:
        return content, False
    marker_match = re.search(r"^\s*@app\.(get|post|put|patch|delete)\(", content, flags=re.MULTILINE)
    if marker_match:
        insert_at = marker_match.start()
        return content[:insert_at].rstrip() + HELPER_BLOCK + "\n" + content[insert_at:], True
    return content.rstrip() + HELPER_BLOCK + "\n", True


def _patch_endpoint(content: str, endpoint: str) -> tuple[str, bool]:
    lines = content.splitlines()
    pattern = re.compile(r"^\s*@app\.post\(\s*([\'\"])" + re.escape(endpoint) + r"\1")
    decorator_index: int | None = None
    for index, line in enumerate(lines):
        if pattern.search(line):
            decorator_index = index
            break
    if decorator_index is None:
        raise RuntimeError(f"Target endpoint decorator not found: {endpoint}")

    def_index: int | None = None
    for index in range(decorator_index + 1, min(len(lines), decorator_index + 10)):
        if re.match(r"^\s*(async\s+def|def)\s+", lines[index]):
            def_index = index
            break
    if def_index is None:
        raise RuntimeError(f"Target endpoint function not found after decorator: {endpoint}")

    block_end = len(lines)
    for index in range(def_index + 1, len(lines)):
        if re.match(r"^\s*@app\.(get|post|put|patch|delete)\(", lines[index]):
            block_end = index
            break
    block_text = "\n".join(lines[decorator_index:block_end])
    guard_line = f'{GUARD_CALL}("{endpoint}")'
    if guard_line in block_text:
        return content, False

    def_indent = lines[def_index][: len(lines[def_index]) - len(lines[def_index].lstrip())]
    body_indent = def_indent + "    "
    insert_index = _find_insert_after_docstring(lines, def_index)
    lines.insert(insert_index, f'{body_indent}{guard_line}')
    lines.insert(insert_index, f'{body_indent}# 4B436633D-H1: fail-closed operator/destructive endpoint guard.')
    return "\n".join(lines) + "\n", True


def patch_api_file(api_path: Path) -> dict[str, Any]:
    if not api_path.exists():
        raise FileNotFoundError(f"missing target api file: {api_path.as_posix()}")
    original = api_path.read_text(encoding="utf-8")
    content, helper_changed = _ensure_helper(original)
    endpoint_changes: dict[str, bool] = {}
    for endpoint in TARGET_ENDPOINTS:
        content, changed = _patch_endpoint(content, endpoint)
        endpoint_changes[endpoint] = changed
    changed = content != original
    if changed:
        api_path.write_text(content, encoding="utf-8")
    return {"api_path": api_path.as_posix(), "helper_inserted": helper_changed, "endpoint_changes": endpoint_changes, "api_guard_patch_performed": changed}


def _compile_file(path: Path) -> str | None:
    try:
        py_compile.compile(str(path), doraise=True)
        return None
    except Exception as exc:
        return f"{type(exc).__name__}: {exc}"


def main() -> int:
    root = Path.cwd()
    backup_root = root / "tools" / f"_patch_backup_{PATCH_ID}_{_timestamp()}"
    backed_up: list[str] = []
    written_files: list[str] = []
    api_patch_result = None
    try:
        _backup_existing(root / TARGET_API_PATH, backup_root, backed_up)
        api_patch_result = patch_api_file(root / TARGET_API_PATH)
        for relative, payload in PAYLOADS.items():
            path = root / relative
            _backup_existing(path, backup_root, backed_up)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(payload, encoding="utf-8")
            written_files.append(relative)
        compile_targets = [root / TARGET_API_PATH, root / "tools/check_4B436633D_H1_destructive_endpoint_guard_hotfix.py", root / "tools/run_4B436633D_H1_destructive_endpoint_guard_hotfix.py", root / "tests/test_runtime_safety_lockdown_guard_h1_4B436633D_H1.py"]
        compile_errors = {str(p.relative_to(root)): err for p in compile_targets for err in [_compile_file(p)] if err is not None}
        result = {
            "applied": not compile_errors,
            "patch_id": PATCH_ID,
            "patch_version": PATCH_VERSION,
            "patch_name": PATCH_NAME,
            "backup_root": str(backup_root.relative_to(root)) if backed_up else "",
            "backed_up_files": backed_up,
            "written_files": written_files,
            "modified_files": [TARGET_API_PATH.as_posix()],
            "api_patch_result": api_patch_result,
            "compile_errors": compile_errors,
            "py_compile_ok": not compile_errors,
            "approved_for_live_real": False,
            "approved_for_paper_transition": False,
            "approved_for_exchange_submit": False,
            "approved_for_runtime_overlay": False,
            "trading_action_performed": False,
            "exchange_submit_performed": False,
            "training_performed": False,
            "reload_performed": False,
            "runtime_overlay_activated": False,
            "destructive_cleanup_performed": False,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if not compile_errors else 1
    except Exception as exc:
        result = {
            "applied": False,
            "patch_id": PATCH_ID,
            "patch_version": PATCH_VERSION,
            "error": f"{type(exc).__name__}: {exc}",
            "backup_root": str(backup_root.relative_to(root)) if backed_up else "",
            "backed_up_files": backed_up,
            "written_files": written_files,
            "api_patch_result": api_patch_result,
            "approved_for_live_real": False,
            "approved_for_paper_transition": False,
            "approved_for_exchange_submit": False,
            "approved_for_runtime_overlay": False,
            "trading_action_performed": False,
            "exchange_submit_performed": False,
            "training_performed": False,
            "reload_performed": False,
            "runtime_overlay_activated": False,
            "destructive_cleanup_performed": False,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
