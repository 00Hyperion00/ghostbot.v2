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


def seed_reports(root: Path) -> None:
    reports = root / "reports"
    write_json(reports / "4B436621_acceptance_20260101_000001.json", {"passed": True, "groups": [{"name": "compileall", "status": "PASS", "duration_sec": 0.1}]})
    write_json(reports / "4B436621_runtime_smoke_20260101_000001.json", {"passed": True, "checks": [{"name": "health", "status": "PASS", "reason": "OK"}]})
    write_json(reports / "4B436621_dashboard_contract_20260101_000001.json", {"passed": True, "checks": [{"name": "imports", "status": "PASS", "reason": "OK"}]})
    write_json(reports / "4B436621_legacy_patch_risk_20260101_000001.json", {"passed": True, "high_risk_legacy": 33, "medium_review": 22, "low_current_tooling": 5})
    write_json(reports / "4B436621_legacy_patch_archive_20260101_000001.json", {"passed": True, "moved": 33})


def test_release_generator_collects_latest_reports(tmp_path: Path) -> None:
    gen = load_generator()
    seed_reports(tmp_path)
    collected = gen.collect_reports(tmp_path)
    assert collected["acceptance_gate"]["exists"] is True
    assert collected["runtime_smoke"]["passed"] is True


def test_release_generator_writes_report_and_runbook(tmp_path: Path) -> None:
    gen = load_generator()
    seed_reports(tmp_path)
    payload = gen.generate(tmp_path, strict=True)
    assert payload["decision"] == "PASS"
    assert (tmp_path / "reports" / "RELEASE_ACCEPTANCE_4B436621.md").exists()
    assert (tmp_path / "reports" / "RELEASE_ACCEPTANCE_4B436621.json").exists()
    assert (tmp_path / "docs" / "OPERATOR_ACCEPTANCE_RUNBOOK_4B436621.md").exists()
    report = (tmp_path / "reports" / "RELEASE_ACCEPTANCE_4B436621.md").read_text(encoding="utf-8")
    assert "Release Decision" in report
    assert "4B.4.3.6.6.22" in report


def test_release_generator_marks_review_when_reports_missing(tmp_path: Path) -> None:
    gen = load_generator()
    payload = gen.generate(tmp_path, strict=False)
    assert payload["decision"] == "REVIEW"
    assert any("missing report" in reason for reason in payload["reasons"])


def test_runbook_contains_operator_guardrails() -> None:
    gen = load_generator()
    text = gen.build_runbook_markdown()
    assert "live_trading_armed" in text or "real live trading" in text
    assert "Do not rerun" in gen.build_release_markdown({k: {"exists": False, "passed": False, "path": None, "data": {}} for k in gen.REPORT_PATTERNS}, "REVIEW", ["x"])
