from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APPLY_H1H1 = ROOT / "tools" / "apply_4B436627GH1H1_windows_utf8_git_root_detection.py"
CHECK_H1H1 = ROOT / "tools" / "check_4B436627GH1H1_windows_utf8_git_root_detection.py"
ROLLBACK_H1H1 = ROOT / "tools" / "rollback_4B436627GH1H1_windows_utf8_git_root_detection.py"
PAYLOAD = ROOT / "tools" / "_patch_payload_4B436627GH1H1"


def run(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=root, check=True, encoding="utf-8", errors="strict", stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def make_project(tmp_path: Path) -> Path:
    root = tmp_path / "Masaüstü ALKILIÇ" / "trade_botV2"
    (root / "tools" / "_patch_payload_4B436627GH1H1").mkdir(parents=True)
    (root / "tests").mkdir(parents=True)
    shutil.copy2(APPLY_H1H1, root / "tools" / APPLY_H1H1.name)
    shutil.copy2(CHECK_H1H1, root / "tools" / CHECK_H1H1.name)
    shutil.copy2(ROLLBACK_H1H1, root / "tools" / ROLLBACK_H1H1.name)
    for source in PAYLOAD.iterdir():
        if source.is_file():
            shutil.copy2(source, root / "tools" / "_patch_payload_4B436627GH1H1" / source.name)
    for name in (
        "apply_4B436627GH1_repository_hygiene_cleanup.py",
        "check_4B436627GH1_repository_hygiene_cleanup.py",
        "rollback_4B436627GH1_repository_hygiene_cleanup.py",
    ):
        (root / "tools" / name).write_text("# old\n", encoding="utf-8")
    (root / "tests" / "test_repository_hygiene_cleanup_4B436627GH1.py").write_text("# old\n", encoding="utf-8")
    return root


def test_h1h1_apply_installs_unicode_safe_git_subprocess_contract(tmp_path: Path) -> None:
    root = make_project(tmp_path)
    run(root, sys.executable, str(root / "tools" / APPLY_H1H1.name))
    for name in (
        "apply_4B436627GH1_repository_hygiene_cleanup.py",
        "check_4B436627GH1_repository_hygiene_cleanup.py",
        "rollback_4B436627GH1_repository_hygiene_cleanup.py",
    ):
        content = (root / "tools" / name).read_text(encoding="utf-8")
        assert 'encoding="utf-8"' in content
        assert 'errors="strict"' in content


def test_h1h1_checker_reports_clean_state(tmp_path: Path) -> None:
    root = make_project(tmp_path)
    run(root, sys.executable, str(root / "tools" / APPLY_H1H1.name))
    result = run(root, sys.executable, str(root / "tools" / CHECK_H1H1.name), "--once-json")
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["read_only"] is True
    assert payload["trading_action_performed"] is False


def test_payload_regression_test_contains_unicode_path_case() -> None:
    content = (PAYLOAD / "test_repository_hygiene_cleanup_4B436627GH1.py").read_text(encoding="utf-8")
    assert "Masaüstü ALKILIÇ" in content


def test_h1h1_apply_is_idempotent(tmp_path: Path) -> None:
    root = make_project(tmp_path)
    apply_path = root / "tools" / APPLY_H1H1.name
    run(root, sys.executable, str(apply_path))
    first = (root / "tools" / "apply_4B436627GH1_repository_hygiene_cleanup.py").read_text(encoding="utf-8")
    run(root, sys.executable, str(apply_path))
    second = (root / "tools" / "apply_4B436627GH1_repository_hygiene_cleanup.py").read_text(encoding="utf-8")
    assert first == second


def test_h1h1_rollback_restores_previous_scripts(tmp_path: Path) -> None:
    root = make_project(tmp_path)
    target = root / "tools" / "apply_4B436627GH1_repository_hygiene_cleanup.py"
    original = target.read_text(encoding="utf-8")
    run(root, sys.executable, str(root / "tools" / APPLY_H1H1.name))
    assert target.read_text(encoding="utf-8") != original
    run(root, sys.executable, str(root / "tools" / ROLLBACK_H1H1.name))
    assert target.read_text(encoding="utf-8") == original
