import py_compile
from pathlib import Path

PHASE = "4B.4.3.6.6.22"
FILES = [
    Path("tools/run_live_demo_soak_4B436622.py"),
    Path("tests/test_live_demo_soak_4B436622.py"),
    Path("docs/LIVE_DEMO_SOAK_RUNBOOK_4B436622.md"),
]


def main() -> int:
    root = Path.cwd()
    (root / "reports").mkdir(exist_ok=True)
    checks: dict[str, bool] = {}
    for rel in FILES:
        path = root / rel
        checks[f"{rel.as_posix()}_exists"] = path.exists()
        if path.suffix == ".py" and path.exists():
            py_compile.compile(str(path), doraise=True)
            checks[f"{rel.as_posix()}_py_compile_ok"] = True
    tool = root / "tools" / "run_live_demo_soak_4B436622.py"
    text = tool.read_text(encoding="utf-8") if tool.exists() else ""
    checks["observation_only_present"] = "observation_only" in text
    checks["no_post_actions_present"] = "no_post_actions" in text
    checks["post_method_absent"] = 'method="POST"' not in text and "method='POST'" not in text
    checks["force_endpoint_absent"] = "/force" not in text and "/cancel" not in text and "/risk/reset" not in text
    checks["real_live_arming_guard_present"] = "REAL_LIVE_ARMED" in text and "LIVE_REAL_CONFIRM_ENABLED" in text
    print(f"{PHASE} live-demo supervised soak tooling applied")
    for key, value in checks.items():
        print(f" - {key}: {value}")
    if not all(checks.values()):
        raise RuntimeError(f"{PHASE} checks failed: {checks}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
