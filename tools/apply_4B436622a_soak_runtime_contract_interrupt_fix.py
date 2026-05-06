import py_compile
from pathlib import Path

PHASE = "4B.4.3.6.6.22a"
FILES = [
    Path("tools/run_live_demo_soak_4B436622.py"),
    Path("tests/test_live_demo_soak_4B436622a.py"),
]


def main() -> int:
    root = Path.cwd()
    checks: dict[str, bool] = {}
    for rel in FILES:
        path = root / rel
        checks[f"{rel.as_posix()}_exists"] = path.exists()
        if path.suffix == ".py" and path.exists():
            py_compile.compile(str(path), doraise=True)
            checks[f"{rel.as_posix()}_py_compile_ok"] = True
    tool = (root / "tools" / "run_live_demo_soak_4B436622.py").read_text(encoding="utf-8")
    checks["runtime_engine_contract_minimum_present"] = 'RUNTIME_ENGINE_CONTRACT_MINIMUM = "4B.4.3.6.6.12"' in tool
    checks["release_candidate_warning_removed"] = "STATUS_CONTRACT_BELOW_RELEASE_CANDIDATE" not in tool
    checks["engine_minimum_warning_present"] = "STATUS_CONTRACT_BELOW_ENGINE_MINIMUM" in tool
    checks["keyboard_interrupt_handled"] = "except KeyboardInterrupt" in tool and "interrupted_by_operator" in tool
    checks["observation_only_still_present"] = '"observation_only": True' in tool
    checks["no_post_method_present"] = 'method="POST"' not in tool
    checks["force_endpoint_absent"] = "/force" not in tool
    print(f"{PHASE} soak runtime contract + interrupt handling hotfix applied")
    for key, value in checks.items():
        print(f" - {key}: {value}")
    if not all(checks.values()):
        raise RuntimeError(f"{PHASE} verification failed: {checks}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
