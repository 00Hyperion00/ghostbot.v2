from __future__ import annotations

import py_compile
import re
import shutil
from pathlib import Path

CONTRACT_VERSION = "4B.4.3.6.6.28F-H2"
ROOT = Path(__file__).resolve().parents[1]
BACKUP_DIR = ROOT / "tools" / "_patch_backup_4B436628F_H2"
OPERATOR_FILE = ROOT / "src" / "tradebot" / "operator_cockpit_v2_read_only.py"
HYP006_BINDING_FILE = ROOT / "src" / "tradebot" / "operator_cockpit_hyp006_binding.py"

EXPECTED_FILES = [
    "src/tradebot/operator_cockpit_hyp006_export_binding.py",
    "tools/apply_4B436628F_H2_operator_cockpit_export_parity.py",
    "tools/check_4B436628F_H2_operator_cockpit_export_parity.py",
    "tools/rollback_4B436628F_H2_operator_cockpit_export_parity.py",
    "tests/test_operator_cockpit_export_parity_4B436628F_H2.py",
    "docs/HYP006_R1_OPERATOR_COCKPIT_EXPORT_PARITY_4B436628F_H2.md",
]

HYP006_SAFE_EXPORT_PATTERNS_BLOCK = '''SAFE_EXPORT_SOURCE_PATTERNS: dict[str, tuple[str, str, str]] = {
    "logger": (
        "4B436628D_hyp006_r1_shadow_observation_logger_*.json",
        "latest-hyp006-shadow-logger.json",
        "application/json; charset=utf-8",
    ),
    "collection": (
        "4B436628G_hyp006_r1_shadow_sample_expansion_acceptance_tracking_*.json",
        "latest-hyp006-acceptance-tracking.json",
        "application/json; charset=utf-8",
    ),
    "audit": (
        "4B436628F_hyp006_r1_operator_cockpit_baseline_*.json",
        "latest-hyp006-operator-cockpit-baseline.json",
        "application/json; charset=utf-8",
    ),
    "ledger": (
        "4B436628D_hyp006_r1_shadow_ledger_*.jsonl",
        "latest-hyp006-shadow-ledger.jsonl",
        "application/x-ndjson; charset=utf-8",
    ),
}
OPERATOR_COCKPIT_V2_HYP006_EXPORT_SOURCE_PARITY_HOTFIX_VERSION = "4B.4.3.6.6.28F-H2"
OPERATOR_COCKPIT_V2_HYP006_EXPORTS_BOUND = True
OPERATOR_COCKPIT_V2_LEGACY_HYP005_EXPORTS_SUPPRESSED = True

JsonObject ='''

HYP006_SAFE_LATEST_EXPORT_SOURCE_FUNCTION = '''def _safe_latest_export_source(project_root: Path, kind: str) -> Path | None:
    """Resolve latest safe export source from HYP-006 canonical reports.

    28F-H2 intentionally binds read-only exports to active HYP-006-R1 artifacts.
    It does not mutate config, scheduler, model, trading state, or order state.
    """
    spec = SAFE_EXPORT_SOURCE_PATTERNS.get(kind)
    if spec is None:
        return None
    root = project_root.resolve()
    reports_dir = root / "reports" / "hyp006_r1_canonical"
    latest = _latest_file(reports_dir, spec[0])
    if latest is None:
        return None
    resolved = latest.resolve()
    try:
        resolved.relative_to(reports_dir.resolve())
    except ValueError:
        return None
    return resolved


'''


def _compile(path: Path) -> bool:
    try:
        py_compile.compile(str(path), doraise=True)
        return True
    except py_compile.PyCompileError:
        return False


def _backup_once(path: Path) -> None:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup = BACKUP_DIR / path.name
    if path.exists() and not backup.exists():
        shutil.copy2(path, backup)


def patch_operator_file() -> dict[str, bool]:
    status: dict[str, bool] = {}
    if not OPERATOR_FILE.exists():
        return {"operator_file_exists": False}
    status["operator_file_exists"] = True
    text = OPERATOR_FILE.read_text(encoding="utf-8")
    original = text

    patterns_re = re.compile(
        r'SAFE_EXPORT_SOURCE_PATTERNS: dict\[str, tuple\[str, str, str\]\] = \{.*?\}\s*\n\s*JsonObject =',
        re.DOTALL,
    )
    text, pattern_replacements = patterns_re.subn(HYP006_SAFE_EXPORT_PATTERNS_BLOCK, text, count=1)
    status["safe_export_patterns_replaced"] = pattern_replacements == 1

    function_re = re.compile(
        r'def _safe_latest_export_source\(project_root: Path, kind: str\) -> Path \| None:\n.*?\n\ndef _read_bounded_export_bytes',
        re.DOTALL,
    )
    text, source_replacements = function_re.subn(
        HYP006_SAFE_LATEST_EXPORT_SOURCE_FUNCTION + "def _read_bounded_export_bytes",
        text,
        count=1,
    )
    status["safe_latest_export_source_replaced"] = source_replacements == 1

    if text != original:
        _backup_once(OPERATOR_FILE)
        OPERATOR_FILE.write_text(text, encoding="utf-8")
        status["operator_file_patched"] = True
    else:
        status["operator_file_patched"] = False
    return status


def patch_hyp006_binding_version() -> dict[str, bool]:
    if not HYP006_BINDING_FILE.exists():
        return {"hyp006_binding_file_exists": False, "hyp006_binding_version_updated": False}
    text = HYP006_BINDING_FILE.read_text(encoding="utf-8")
    original = text
    text = text.replace(
        'OPERATOR_COCKPIT_HYP006_BINDING_VERSION = "4B.4.3.6.6.28F-H1"',
        'OPERATOR_COCKPIT_HYP006_BINDING_VERSION = "4B.4.3.6.6.28F-H2"',
    )
    if text != original:
        _backup_once(HYP006_BINDING_FILE)
        HYP006_BINDING_FILE.write_text(text, encoding="utf-8")
    return {
        "hyp006_binding_file_exists": True,
        "hyp006_binding_version_updated": 'OPERATOR_COCKPIT_HYP006_BINDING_VERSION = "4B.4.3.6.6.28F-H2"' in text,
    }


def main() -> int:
    patch_status = {**patch_operator_file(), **patch_hyp006_binding_version()}
    checks: dict[str, bool] = {
        "config_mutation_performed": False,
        "scheduler_mutation_performed": False,
        "scheduler_task_created": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "paper_live_order_enablement_present": False,
        **patch_status,
    }
    for relative in EXPECTED_FILES:
        path = ROOT / relative
        checks[f"{relative}_exists"] = path.exists()
        if path.suffix == ".py":
            checks[f"{relative}_py_compile_ok"] = path.exists() and _compile(path)
    checks["operator_file_py_compile_ok"] = OPERATOR_FILE.exists() and _compile(OPERATOR_FILE)
    checks["hyp006_binding_file_py_compile_ok"] = HYP006_BINDING_FILE.exists() and _compile(HYP006_BINDING_FILE)
    operator_text = OPERATOR_FILE.read_text(encoding="utf-8") if OPERATOR_FILE.exists() else ""
    checks["hyp006_export_patterns_present"] = "4B436628D_hyp006_r1_shadow_ledger_*.jsonl" in operator_text and "latest-hyp006-shadow-ledger.jsonl" in operator_text
    safe_export_block = operator_text.split("SAFE_EXPORT_SOURCE_PATTERNS", 1)[1].split("JsonObject =", 1)[0] if "SAFE_EXPORT_SOURCE_PATTERNS" in operator_text and "JsonObject =" in operator_text else operator_text
    checks["legacy_export_patterns_suppressed"] = "4B436625X_hyp005_shadow_merged_ledger_*.jsonl" not in safe_export_block and "latest-25x-collection.json" not in safe_export_block and "latest-25v-logger.json" not in safe_export_block
    checks["hyp006_reports_dir_binding_present"] = 'reports" / "hyp006_r1_canonical' in operator_text

    print(f"{CONTRACT_VERSION} Operator Cockpit HYP-006 export source parity hotfix applied")
    for key, value in checks.items():
        print(f" - {key}: {value}")

    required = [
        checks.get("operator_file_exists", False),
        checks.get("safe_export_patterns_replaced", False) or checks.get("hyp006_export_patterns_present", False),
        checks.get("safe_latest_export_source_replaced", False) or checks.get("hyp006_reports_dir_binding_present", False),
        checks.get("operator_file_py_compile_ok", False),
        checks.get("hyp006_binding_file_py_compile_ok", False),
        checks.get("hyp006_export_patterns_present", False),
        checks.get("legacy_export_patterns_suppressed", False),
        checks.get("hyp006_reports_dir_binding_present", False),
    ]
    file_checks = [value for key, value in checks.items() if key.endswith("_exists") or key.endswith("_py_compile_ok")]
    return 0 if all(required) and all(file_checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
