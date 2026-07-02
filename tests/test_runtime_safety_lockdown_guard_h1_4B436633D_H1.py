from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path


def _load_apply_module(path: Path):
    spec = importlib.util.spec_from_file_location("apply_33d_h1", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_sample_api(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "from fastapi import FastAPI\n\n"
        "app = FastAPI()\n\n"
        "@app.post('/balance-sync')\n"
        "def balance_sync():\n"
        "    return {'ok': True}\n\n"
        "@app.post('/risk-reset')\n"
        "async def risk_reset():\n"
        "    return {'ok': True}\n\n"
        "@app.post('/safe-mode/toggle')\n"
        "def safe_mode_toggle():\n"
        "    \"\"\"Toggle safe mode.\"\"\"\n"
        "    return {'ok': True}\n",
        encoding="utf-8",
    )


def test_patcher_injects_fail_closed_guard_for_three_legacy_endpoints(tmp_path: Path) -> None:
    api_path = tmp_path / "src/tradebot/api.py"
    _write_sample_api(api_path)
    module = _load_apply_module(Path("tools/apply_4B436633D_H1_destructive_endpoint_guard_hotfix.py"))
    result = module.patch_api_file(api_path)
    assert result["api_guard_patch_performed"] is True
    text = api_path.read_text(encoding="utf-8")
    assert text.count("_require_33d_h1_legacy_destructive_endpoint_guard(") == 4
    assert '_require_33d_h1_legacy_destructive_endpoint_guard("/balance-sync")' in text
    assert '_require_33d_h1_legacy_destructive_endpoint_guard("/risk-reset")' in text
    assert '_require_33d_h1_legacy_destructive_endpoint_guard("/safe-mode/toggle")' in text
    compile(text, str(api_path), "exec")


def test_patcher_is_idempotent(tmp_path: Path) -> None:
    api_path = tmp_path / "src/tradebot/api.py"
    _write_sample_api(api_path)
    module = _load_apply_module(Path("tools/apply_4B436633D_H1_destructive_endpoint_guard_hotfix.py"))
    first = module.patch_api_file(api_path)
    second = module.patch_api_file(api_path)
    text = api_path.read_text(encoding="utf-8")
    assert first["api_guard_patch_performed"] is True
    assert second["api_guard_patch_performed"] is False
    assert text.count("_require_33d_h1_legacy_destructive_endpoint_guard(") == 4


def test_check_script_detects_guard_coverage(tmp_path: Path) -> None:
    api_path = tmp_path / "src/tradebot/api.py"
    _write_sample_api(api_path)
    module = _load_apply_module(Path("tools/apply_4B436633D_H1_destructive_endpoint_guard_hotfix.py"))
    module.patch_api_file(api_path)
    tools_dir = tmp_path / "tools"
    docs_dir = tmp_path / "docs"
    tests_dir = tmp_path / "tests"
    tools_dir.mkdir(parents=True, exist_ok=True)
    docs_dir.mkdir(parents=True, exist_ok=True)
    tests_dir.mkdir(parents=True, exist_ok=True)
    (tmp_path / "README_APPLY_4B436633D_H1.txt").write_text("ok\n", encoding="utf-8")
    (docs_dir / "RUNTIME_SAFETY_LOCKDOWN_DESTRUCTIVE_ENDPOINT_GUARD_HOTFIX_4B436633D_H1.md").write_text("ok\n", encoding="utf-8")
    (tests_dir / "test_runtime_safety_lockdown_guard_h1_4B436633D_H1.py").write_text("def test_placeholder():\n    assert True\n", encoding="utf-8")
    check_src = Path("tools/check_4B436633D_H1_destructive_endpoint_guard_hotfix.py")
    run_src = Path("tools/run_4B436633D_H1_destructive_endpoint_guard_hotfix.py")
    check_dst = tools_dir / check_src.name
    run_dst = tools_dir / run_src.name
    check_dst.write_text(check_src.read_text(encoding="utf-8"), encoding="utf-8")
    run_dst.write_text(run_src.read_text(encoding="utf-8"), encoding="utf-8")
    completed = subprocess.run([sys.executable, str(check_dst), "--once-json", "--skip-33d-check"], cwd=tmp_path, text=True, capture_output=True, check=False)
    assert completed.returncode == 0, completed.stderr
    assert '"status": "READY"' in completed.stdout
    assert '"endpoint_guard_coverage_complete": true' in completed.stdout
