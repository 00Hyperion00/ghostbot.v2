import importlib.util
import sys
from pathlib import Path


def load_tool(name: str):
    path = Path(__file__).resolve().parents[1] / "tools" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_scanner_classifies_legacy_20_patch_as_high_risk(tmp_path: Path) -> None:
    root = tmp_path
    tools = root / "tools"
    tools.mkdir()
    (tools / "apply_4B436620t9_dashboard_api_post_class_guard.py").write_text("print('legacy')\n", encoding="utf-8")
    scanner = load_tool("check_patch_artifact_risk_4B436621")
    report = scanner.scan_legacy_patches(root)
    assert report["summary"]["high_risk_legacy"] == 1
    assert report["items"][0]["recommendation"] == "ARCHIVE"
    assert "LEGACY_4B436620_PATCH" in report["items"][0]["reason_codes"]


def test_scanner_keeps_current_21_tooling_low_risk(tmp_path: Path) -> None:
    tools = tmp_path / "tools"
    tools.mkdir()
    (tools / "apply_4B436621b2_runtime_smoke_optional_diagnostics.py").write_text("print('tooling')\n", encoding="utf-8")
    scanner = load_tool("check_patch_artifact_risk_4B436621")
    report = scanner.scan_legacy_patches(tmp_path)
    assert report["summary"]["low_current_tooling"] == 1
    assert report["items"][0]["recommendation"] == "KEEP"


def test_archive_tool_is_dry_run_by_default(tmp_path: Path) -> None:
    tools = tmp_path / "tools"
    tools.mkdir()
    legacy = tools / "apply_4B436620d_dashboard_full_compat_restore.py"
    legacy.write_text("print('legacy')\n", encoding="utf-8")
    archive = load_tool("archive_legacy_patch_scripts_4B436621")
    plan = archive.archive_plan(tmp_path)
    result = archive.execute_archive(tmp_path, plan, apply=False)
    assert legacy.exists()
    assert result["applied"] is False
    assert result["actions"][0]["status"] == "planned"


def test_archive_tool_moves_only_when_apply_true(tmp_path: Path) -> None:
    tools = tmp_path / "tools"
    tools.mkdir()
    legacy = tools / "apply_4B436620t8_dashboard_api_post_final_guard.py"
    legacy.write_text("print('legacy')\n", encoding="utf-8")
    archive = load_tool("archive_legacy_patch_scripts_4B436621")
    plan = archive.archive_plan(tmp_path)
    result = archive.execute_archive(tmp_path, plan, apply=True)
    assert not legacy.exists()
    assert (tools / "legacy_patches_4B436620" / legacy.name).exists()
    assert result["actions"][0]["status"] == "moved"
