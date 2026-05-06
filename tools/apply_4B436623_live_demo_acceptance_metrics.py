from pathlib import Path
import py_compile

PHASE = "4B.4.3.6.6.23"
FILES = [
    Path("tools/generate_live_demo_acceptance_metrics_4B436623.py"),
    Path("tests/test_live_demo_acceptance_metrics_4B436623.py"),
    Path("docs/LIVE_DEMO_ACCEPTANCE_METRICS_RUNBOOK_4B436623.md"),
]


def compile_ok(path: Path) -> bool:
    py_compile.compile(str(path), doraise=True)
    return True


def main() -> int:
    root = Path.cwd()
    (root / "reports").mkdir(exist_ok=True)
    checks: dict[str, bool] = {}
    for rel in FILES:
        path = root / rel
        checks[f"{rel.as_posix()}_exists"] = path.exists()
        if path.suffix == ".py" and path.exists():
            checks[f"{rel.as_posix()}_py_compile_ok"] = compile_ok(path)
    tool = root / "tools" / "generate_live_demo_acceptance_metrics_4B436623.py"
    text = tool.read_text(encoding="utf-8") if tool.exists() else ""
    checks["observation_only_present"] = "observation-only" in text.lower() or "observation_only" in text
    checks["get_only_http_present"] = "method=\"GET\"" in text
    checks["post_method_absent"] = "method=\"POST\"" not in text and "force-buy" not in text and "force-sell" not in text
    checks["soak_prefix_present"] = "4B436622_live_demo_soak" in text
    checks["report_prefix_present"] = "4B436623_live_demo_acceptance_metrics" in text
    print(f"{PHASE} live-demo acceptance metrics tooling applied")
    for key, value in checks.items():
        print(f" - {key}: {value}")
    if not all(checks.values()):
        raise RuntimeError(f"{PHASE} checks failed: {checks}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
