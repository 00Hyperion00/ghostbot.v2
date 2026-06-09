from __future__ import annotations

import py_compile
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = PROJECT_ROOT / "tools"
SRC_DIR = PROJECT_ROOT / "src" / "tradebot"
PAYLOAD_DIR = TOOLS_DIR / "_patch_payload"
TARGET_RUNNER = TOOLS_DIR / "run_hyp005_shadow_observation_logger_4B436625V.py"
LEGACY_RUNNER = TOOLS_DIR / "run_hyp005_shadow_observation_logger_4B436625V_legacy_ordinal_identity.py"
WRAPPER_PAYLOAD = PAYLOAD_DIR / "run_hyp005_shadow_observation_logger_4B436625V_stable_identity_wrapper.py"
IDENTITY_MODULE = SRC_DIR / "hyp005_shadow_observation_identity.py"
DRIFT_CHECKER = TOOLS_DIR / "check_hyp005_shadow_observation_identity_drift_4B436625VH1.py"
ROLLBACK_TOOL = TOOLS_DIR / "rollback_4B436625V_H1_hyp005_shadow_observation_stable_identity_hotfix.py"
TEST_FILE = PROJECT_ROOT / "tests" / "test_hyp005_shadow_observation_stable_identity_hotfix_4B436625VH1.py"
DOC_FILE = PROJECT_ROOT / "docs" / "HYP005_SHADOW_OBSERVATION_STABLE_IDENTITY_HOTFIX_4B436625VH1.md"


def _compile(path: Path) -> bool:
    try:
        py_compile.compile(str(path), doraise=True)
    except py_compile.PyCompileError:
        return False
    return True


def _contains(path: Path, marker: str) -> bool:
    return path.exists() and marker in path.read_text(encoding="utf-8")


def main() -> int:
    if not TARGET_RUNNER.exists():
        print(f"stable_identity_apply_error: target runner missing: {TARGET_RUNNER}")
        return 2
    if not WRAPPER_PAYLOAD.exists():
        print(f"stable_identity_apply_error: wrapper payload missing: {WRAPPER_PAYLOAD}")
        return 2
    if not IDENTITY_MODULE.exists():
        print(f"stable_identity_apply_error: identity module missing: {IDENTITY_MODULE}")
        return 2

    if not LEGACY_RUNNER.exists():
        if _contains(TARGET_RUNNER, "HYP005_25V_STABLE_IDENTITY_WRAPPER = True"):
            print("stable_identity_apply_error: wrapper installed but legacy runner backup missing")
            return 2
        shutil.copy2(TARGET_RUNNER, LEGACY_RUNNER)

    shutil.copy2(WRAPPER_PAYLOAD, TARGET_RUNNER)

    checks: list[tuple[str, bool]] = [
        ("config_mutation_performed", False),
        ("scheduler_mutation_performed", False),
        ("trading_action_performed", False),
        ("src/tradebot/hyp005_shadow_observation_identity.py_exists", IDENTITY_MODULE.exists()),
        ("tools/run_hyp005_shadow_observation_logger_4B436625V.py_exists", TARGET_RUNNER.exists()),
        ("legacy_runner_backup_exists", LEGACY_RUNNER.exists()),
        ("tools/check_hyp005_shadow_observation_identity_drift_4B436625VH1.py_exists", DRIFT_CHECKER.exists()),
        ("tools/rollback_4B436625V_H1_hyp005_shadow_observation_stable_identity_hotfix.py_exists", ROLLBACK_TOOL.exists()),
        ("tests/test_hyp005_shadow_observation_stable_identity_hotfix_4B436625VH1.py_exists", TEST_FILE.exists()),
        ("docs/HYP005_SHADOW_OBSERVATION_STABLE_IDENTITY_HOTFIX_4B436625VH1.md_exists", DOC_FILE.exists()),
        ("identity_module_py_compile_ok", _compile(IDENTITY_MODULE)),
        ("wrapper_py_compile_ok", _compile(TARGET_RUNNER)),
        ("legacy_runner_py_compile_ok", _compile(LEGACY_RUNNER)),
        ("drift_checker_py_compile_ok", _compile(DRIFT_CHECKER)),
        ("rollback_tool_py_compile_ok", _compile(ROLLBACK_TOOL)),
        ("test_file_py_compile_ok", _compile(TEST_FILE)),
        ("stable_identity_version_present", _contains(IDENTITY_MODULE, 'HYP005_SHADOW_OBSERVATION_STABLE_IDENTITY_VERSION = "4B.4.3.6.6.25V-H1"')),
        ("rolling_ordinal_disabled_present", _contains(IDENTITY_MODULE, "HYP005_SHADOW_OBSERVATION_ROLLING_ORDINAL_DISABLED = True")),
        ("stable_observation_id_present", _contains(IDENTITY_MODULE, "def stable_observation_id(")),
        ("legacy_id_preservation_present", _contains(IDENTITY_MODULE, 'normalized.setdefault("legacy_observation_id"')),
        ("atomic_replace_present", _contains(IDENTITY_MODULE, "temp_path.replace(resolved)")),
        ("wrapper_installed", _contains(TARGET_RUNNER, "HYP005_25V_STABLE_IDENTITY_WRAPPER = True")),
        ("paper_live_order_enablement_present", False),
    ]

    print("4B.4.3.6.6.25V-H1 HYP-005 shadow observation stable identity / rolling-ordinal drift hotfix applied")
    all_ok = True
    for name, value in checks:
        if name in {"config_mutation_performed", "scheduler_mutation_performed", "trading_action_performed", "paper_live_order_enablement_present"}:
            print(f" - {name}: {value}")
            all_ok = all_ok and (value is False)
        else:
            print(f" - {name}: {value}")
            all_ok = all_ok and value
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
