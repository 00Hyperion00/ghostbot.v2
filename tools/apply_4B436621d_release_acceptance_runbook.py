import py_compile
from pathlib import Path

PHASE = "4B.4.3.6.6.21d"
FILES = [
    Path("tools/generate_4B436621_release_acceptance.py"),
    Path("tests/test_release_acceptance_4B436621.py"),
    Path("docs/OPERATOR_ACCEPTANCE_RUNBOOK_4B436621.md"),
]


def compile_file(path: Path) -> bool:
    try:
        py_compile.compile(str(path), doraise=True)
        return True
    except Exception:
        return False


def main() -> int:
    root = Path.cwd()
    (root / "reports").mkdir(exist_ok=True)
    (root / "docs").mkdir(exist_ok=True)
    checks: dict[str, bool] = {}
    for rel in FILES:
        path = root / rel
        checks[f"{rel.as_posix()}_exists"] = path.exists()
        if path.suffix == ".py":
            checks[f"{rel.as_posix()}_py_compile_ok"] = path.exists() and compile_file(path)
    generator = root / "tools" / "generate_4B436621_release_acceptance.py"
    text = generator.read_text(encoding="utf-8") if generator.exists() else ""
    checks["release_report_target_present"] = "RELEASE_ACCEPTANCE_4B436621" in text
    checks["runbook_target_present"] = "OPERATOR_ACCEPTANCE_RUNBOOK_4B436621.md" in text
    checks["no_runtime_imports"] = "tradebot.engine" not in text and "tradebot.api" not in text
    print(f"{PHASE} release acceptance final report / runbook tooling applied")
    for key, value in checks.items():
        print(f" - {key}: {value}")
    if not all(checks.values()):
        raise RuntimeError(f"{PHASE} checks failed: {checks}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
