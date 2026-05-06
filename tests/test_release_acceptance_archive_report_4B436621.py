import importlib.util
import json
from pathlib import Path


def load_generator():
    path = Path("tools/generate_4B436621_release_acceptance.py")
    spec = importlib.util.spec_from_file_location("generate_4B436621_release_acceptance", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def seed_pass_reports(root: Path) -> None:
    reports = root / "reports"
    write_json(reports / "4B436621_acceptance_20260101_000001.json", {"passed": True, "results": [{"name": "compileall", "status": "PASS"}]})
    write_json(reports / "4B436621_runtime_smoke_20260101_000001.json", {"passed": True, "checks": [{"name": "health", "status": "PASS"}]})
    write_json(reports / "4B436621_dashboard_contract_20260101_000001.json", {"passed": True, "checks": [{"name": "imports", "status": "PASS"}]})
    write_json(reports / "4B436621_legacy_patch_risk_20260101_000001.json", {"decision": "PASS", "summary": {"high_risk_legacy": 33, "medium_review": 22, "low_current_tooling": 5}})
    write_json(reports / "4B436621_legacy_patch_archive_20260101_000001.json", {
        "phase": "4B.4.3.6.6.21c",
        "applied": True,
        "archive_dir": "tools/legacy_patches_4B436620",
        "actions": [
            {"source": "tools/apply_4B436620a.py", "destination": "tools/legacy_patches_4B436620/apply_4B436620a.py", "status": "moved"},
            {"source": "tools/apply_4B436620b.py", "destination": "tools/legacy_patches_4B436620/apply_4B436620b.py", "status": "already_archived"},
        ],
    })


def test_archive_apply_report_counts_as_pass() -> None:
    gen = load_generator()
    data = {"applied": True, "actions": [{"status": "moved"}, {"status": "already_archived"}]}
    assert gen.archive_report_passed(data) is True
    assert gen.extract_result(data) is True
    assert gen.archive_moved_count(data) == 1


def test_archive_dry_run_or_missing_does_not_count_as_pass() -> None:
    gen = load_generator()
    assert gen.extract_result({"applied": False, "actions": [{"status": "planned"}]}) is False
    assert gen.extract_result({"applied": True, "actions": [{"status": "missing"}]}) is False


def test_strict_release_passes_with_archive_apply_report(tmp_path: Path) -> None:
    gen = load_generator()
    seed_pass_reports(tmp_path)
    payload = gen.generate(tmp_path, strict=True)
    assert payload["decision"] == "PASS"
    report = (tmp_path / "reports" / "RELEASE_ACCEPTANCE_4B436621.md").read_text(encoding="utf-8")
    assert "Archive moved: 1" in report
