from __future__ import annotations

import importlib.util
from pathlib import Path


def _checker_module():
    root = Path(__file__).resolve().parents[1]
    path = root / "tools" / "check_apply_conflict_resolution.py"
    spec = importlib.util.spec_from_file_location("check_apply_conflict_resolution", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_apply_conflict_resolution_checker_reports_current_repo_ready() -> None:
    root = Path(__file__).resolve().parents[1]
    report = _checker_module().build_report(root)

    assert report["status"] == "READY"
    assert report["ready_file_count"] == report["conflict_file_count"] == 4
    assert {item["path"] for item in report["files"]} == {
        "README.md",
        "docs/ARCHITECTURE.md",
        "src/tradebot/strategy.py",
        "tests/test_strategy_ai_merge.py",
    }
    assert all(not item["conflict_markers_present"] for item in report["files"])
    assert all(not item["missing_tokens"] for item in report["files"])
