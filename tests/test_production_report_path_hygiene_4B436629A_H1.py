from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_run_module():
    root = Path(__file__).resolve().parents[1]
    tools = root / "tools"
    if str(tools) not in sys.path:
        sys.path.insert(0, str(tools))
    path = tools / "run_4B436629A_production_hardening_p0.py"
    spec = importlib.util.spec_from_file_location("run_4B436629A_production_hardening_p0_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_29a_run_tool_rejects_shell_contaminated_reports_dir() -> None:
    module = _load_run_module()
    root = Path.cwd()
    bad = ".\\reports\\production_hardeninsrc=src"
    try:
        module._resolve_canonical_reports_dir(root, bad)
    except ValueError as exc:
        assert "REPORTS_DIR_NOT_CANONICAL_PRODUCTION_HARDENING" in str(exc)
    else:
        raise AssertionError("bad reports-dir path was not rejected")


def test_29a_run_tool_accepts_only_canonical_reports_dir() -> None:
    module = _load_run_module()
    root = Path.cwd()
    resolved = module._resolve_canonical_reports_dir(root, "reports/production_hardening")
    assert resolved == (root / "reports" / "production_hardening").resolve()


def test_29a_h1_patch_files_present() -> None:
    root = Path.cwd()
    assert (root / "tools" / "check_4B436629A_H1_production_report_path_hygiene.py").exists()
    assert (root / "docs" / "PRODUCTION_REPORT_PATH_HYGIENE_4B436629A_H1.md").exists()
