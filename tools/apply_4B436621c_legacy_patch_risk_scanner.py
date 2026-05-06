from pathlib import Path
import py_compile

PHASE = "4B.4.3.6.6.21c"
REQUIRED = [
    Path("tools/check_patch_artifact_risk_4B436621.py"),
    Path("tools/archive_legacy_patch_scripts_4B436621.py"),
    Path("tests/test_legacy_patch_risk_scanner_4B436621.py"),
    Path("docs/LEGACY_PATCH_POLICY_4B436621.md"),
]


def compile_ok(path: Path) -> bool:
    py_compile.compile(str(path), doraise=True)
    return True


def main() -> int:
    root = Path.cwd()
    checks: dict[str, bool] = {}
    (root / "reports").mkdir(exist_ok=True)
    for rel in REQUIRED:
        path = root / rel
        checks[f"{rel.as_posix()}_exists"] = path.exists()
        if path.suffix == ".py" and path.exists():
            checks[f"{rel.as_posix()}_py_compile_ok"] = compile_ok(path)
    checks["reports_dir_exists"] = (root / "reports").exists()
    checks["scanner_has_no_delete_behavior"] = "unlink(" not in (root / REQUIRED[0]).read_text(encoding="utf-8")
    checks["archive_tool_default_dry_run"] = "Default mode is dry-run" in (root / REQUIRED[1]).read_text(encoding="utf-8")
    print(f"{PHASE} legacy patch risk scanner / archive plan tooling applied")
    for key, value in checks.items():
        print(f" - {key}: {value}")
    if not all(checks.values()):
        raise RuntimeError(f"{PHASE} apply verification failed: {checks}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
