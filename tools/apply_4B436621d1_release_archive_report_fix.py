from pathlib import Path
import py_compile

PHASE = "4B.4.3.6.6.21d1"
GENERATOR = Path("tools/generate_4B436621_release_acceptance.py")
SELF_TEST = Path("tests/test_release_acceptance_archive_report_4B436621.py")

HELPER = r'''

def archive_report_passed(data: dict[str, Any]) -> bool:
    """Return True for 21c archive reports produced by archive_legacy_patch_scripts.

    21c archive reports do not contain a generic `passed/status/decision` field.
    Their source of truth is:
      - applied: True
      - actions: [{status: moved|already_archived|missing}, ...]

    `missing` is not a PASS state because it means the scanner planned a move but
    the file was not found during apply. Dry-run/planned reports are also not PASS.
    """
    if not isinstance(data, dict):
        return False
    if data.get("applied") is not True:
        return False
    actions = data.get("actions")
    if not isinstance(actions, list):
        return False
    allowed = {"moved", "already_archived"}
    return all(isinstance(item, dict) and item.get("status") in allowed for item in actions)


def archive_moved_count(data: dict[str, Any]) -> int | str:
    actions = data.get("actions") if isinstance(data, dict) else None
    if not isinstance(actions, list):
        return "-"
    return sum(1 for item in actions if isinstance(item, dict) and item.get("status") == "moved")
'''

TEST_CODE = r'''import importlib.util
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
'''


def replace_once(text: str, old: str, new: str) -> tuple[str, bool]:
    if old not in text:
        return text, False
    return text.replace(old, new, 1), True


def patch_generator(path: Path) -> dict[str, bool]:
    text = path.read_text(encoding="utf-8")
    checks: dict[str, bool] = {}

    if "def archive_report_passed" not in text:
        marker = "def extract_result(data: dict[str, Any], *, default: bool = False) -> bool:\n"
        text, ok = replace_once(text, marker, HELPER + "\n" + marker)
        checks["archive_helper_inserted"] = ok
    else:
        checks["archive_helper_inserted"] = True

    old = 'def extract_result(data: dict[str, Any], *, default: bool = False) -> bool:\n    for key in ("passed", "ok", "success", "gate_passed", "all_passed"):'
    new = 'def extract_result(data: dict[str, Any], *, default: bool = False) -> bool:\n    if archive_report_passed(data):\n        return True\n    for key in ("passed", "ok", "success", "gate_passed", "all_passed"):'
    if "if archive_report_passed(data):" not in text:
        text, ok = replace_once(text, old, new)
        checks["extract_result_archive_branch_inserted"] = ok
    else:
        checks["extract_result_archive_branch_inserted"] = True

    old = 'f"- Archive moved: {archive.get(\'moved\', archive.get(\'summary\', {}).get(\'moved\', \'-\'))}",'
    new = 'f"- Archive moved: {archive_moved_count(archive)}",'
    if "archive_moved_count(archive)" not in text:
        text, ok = replace_once(text, old, new)
        checks["archive_moved_summary_fixed"] = ok
    else:
        checks["archive_moved_summary_fixed"] = True

    path.write_text(text, encoding="utf-8")
    return checks


def main() -> int:
    root = Path.cwd()
    generator = root / GENERATOR
    self_test = root / SELF_TEST
    if not generator.exists():
        raise RuntimeError(f"Missing generator: {generator}")

    checks = patch_generator(generator)
    self_test.write_text(TEST_CODE, encoding="utf-8")

    py_compile.compile(str(generator), doraise=True)
    py_compile.compile(str(self_test), doraise=True)
    checks["generator_py_compile_ok"] = True
    checks["self_test_exists"] = self_test.exists()
    checks["self_test_py_compile_ok"] = True
    checks["archive_report_passed_symbol"] = "def archive_report_passed" in generator.read_text(encoding="utf-8")
    checks["archive_moved_count_symbol"] = "def archive_moved_count" in generator.read_text(encoding="utf-8")

    print(f"{PHASE} release archive report decision hotfix applied")
    for key, value in checks.items():
        print(f" - {key}: {value}")
    if not all(checks.values()):
        raise RuntimeError(f"{PHASE} checks failed: {checks}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
