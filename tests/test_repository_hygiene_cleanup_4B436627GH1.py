from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
APPLY = ROOT / "tools" / "apply_4B436627GH1_repository_hygiene_cleanup.py"
CHECKER = ROOT / "tools" / "check_4B436627GH1_repository_hygiene_cleanup.py"
ROLLBACK = ROOT / "tools" / "rollback_4B436627GH1_repository_hygiene_cleanup.py"


def run(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=repo, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "Masaüstü ALKILIÇ" / "repo"
    (repo / "tools").mkdir(parents=True)
    (repo / "reports" / "hyp005_r1_canonical").mkdir(parents=True)
    (repo / "tools" / "_patch_backup_4B436627G").mkdir(parents=True)
    (repo / "tools" / "_patch_payload_4B436627G").mkdir(parents=True)
    (repo / "src").mkdir(parents=True)
    shutil.copy2(APPLY, repo / "tools" / APPLY.name)
    shutil.copy2(CHECKER, repo / "tools" / CHECKER.name)
    shutil.copy2(ROLLBACK, repo / "tools" / ROLLBACK.name)
    (repo / ".gitignore").write_text("__pycache__/\n", encoding="utf-8")
    (repo / "reports" / "hyp005_r1_canonical" / "runtime.json").write_text("{}\n", encoding="utf-8")
    (repo / "tools" / "_patch_backup_4B436627G" / "old.py").write_text("x = 1\n", encoding="utf-8")
    (repo / "tools" / "_patch_payload_4B436627G" / "payload.py").write_text("x = 2\n", encoding="utf-8")
    (repo / "src" / "stable.py").write_text("STABLE = True\n", encoding="utf-8")
    run(repo, "git", "init", "-q")
    run(repo, "git", "config", "user.email", "test@example.com")
    run(repo, "git", "config", "user.name", "Test")
    run(repo, "git", "add", ".")
    run(repo, "git", "commit", "-qm", "baseline")
    return repo


def tracked(repo: Path) -> list[str]:
    return [path for path in run(repo, "git", "ls-files", "-z").stdout.split("\0") if path]


def test_apply_untracks_runtime_and_patch_workdirs_without_deleting_local_files(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    run(repo, sys.executable, str(repo / "tools" / APPLY.name))
    files = tracked(repo)
    assert "reports/hyp005_r1_canonical/runtime.json" not in files
    assert "tools/_patch_backup_4B436627G/old.py" not in files
    assert "tools/_patch_payload_4B436627G/payload.py" not in files
    assert (repo / "reports" / "hyp005_r1_canonical" / "runtime.json").exists()
    assert (repo / "tools" / "_patch_backup_4B436627G" / "old.py").exists()
    assert (repo / "tools" / "_patch_payload_4B436627G" / "payload.py").exists()
    assert (repo / "src" / "stable.py").read_text(encoding="utf-8") == "STABLE = True\n"


def test_apply_is_idempotent(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    apply_path = repo / "tools" / APPLY.name
    run(repo, sys.executable, str(apply_path))
    first = (repo / ".gitignore").read_text(encoding="utf-8")
    run(repo, sys.executable, str(apply_path))
    second = (repo / ".gitignore").read_text(encoding="utf-8")
    assert first == second
    assert second.count("# BEGIN 4B.4.3.6.6.27G-H1 REPOSITORY HYGIENE") == 1


def test_checker_reports_read_only_clean_state(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    run(repo, sys.executable, str(repo / "tools" / APPLY.name))
    result = run(repo, sys.executable, str(repo / "tools" / CHECKER.name), "--once-json")
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["read_only"] is True
    assert payload["trading_action_performed"] is False
    assert payload["tracked_hygiene_paths_remaining"] == []


def test_rollback_restores_gitignore_and_restages_previous_paths(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    original = (repo / ".gitignore").read_text(encoding="utf-8")
    run(repo, sys.executable, str(repo / "tools" / APPLY.name))
    run(repo, sys.executable, str(repo / "tools" / ROLLBACK.name))
    assert (repo / ".gitignore").read_text(encoding="utf-8") == original
    files = tracked(repo)
    assert "reports/hyp005_r1_canonical/runtime.json" in files
    assert "tools/_patch_backup_4B436627G/old.py" in files
    assert "tools/_patch_payload_4B436627G/payload.py" in files


def test_git_subprocess_boundaries_use_explicit_utf8() -> None:
    for script in (APPLY, CHECKER, ROLLBACK):
        content = script.read_text(encoding="utf-8")
        assert 'encoding="utf-8"' in content
        assert 'errors="strict"' in content
