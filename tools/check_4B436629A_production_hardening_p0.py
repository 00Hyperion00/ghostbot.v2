from __future__ import annotations

import argparse
import json
import py_compile
from pathlib import Path

CONTRACT_VERSION = "4B.4.3.6.6.29A"
EXPECTED_FILES = [
    "requirements.txt",
    "src/tradebot/production_hardening.py",
    "src/tradebot/api_security.py",
    "tools/apply_4B436629A_production_hardening_p0.py",
    "tools/check_4B436629A_production_hardening_p0.py",
    "tools/run_4B436629A_production_hardening_p0.py",
    "tools/rollback_4B436629A_production_hardening_p0.py",
    "tests/test_production_hardening_p0_4B436629A.py",
    "docs/PRODUCTION_HARDENING_P0_4B436629A.md",
]
COMPILE_FILES = [
    "src/tradebot/production_hardening.py",
    "src/tradebot/api_security.py",
    "src/tradebot/config.py",
    "src/tradebot/persistence.py",
    "src/tradebot/api.py",
    "src/tradebot/training/labeling.py",
    "tools/apply_4B436629A_production_hardening_p0.py",
    "tools/check_4B436629A_production_hardening_p0.py",
    "tools/run_4B436629A_production_hardening_p0.py",
    "tools/rollback_4B436629A_production_hardening_p0.py",
    "tests/test_production_hardening_p0_4B436629A.py",
]


def _read(root: Path, rel: str) -> str:
    path = root / rel
    return path.read_text(encoding="utf-8") if path.exists() else ""


def compile_ok(path: Path) -> bool:
    try:
        py_compile.compile(str(path), doraise=True)
        return True
    except Exception:
        return False


def build_report(root: Path) -> dict[str, object]:
    expected = {name: (root / name).exists() for name in EXPECTED_FILES}
    compiled = {name: compile_ok(root / name) for name in COMPILE_FILES if (root / name).exists() and name.endswith(".py")}
    requirements = _read(root, "requirements.txt")
    config = _read(root, "src/tradebot/config.py")
    persistence = _read(root, "src/tradebot/persistence.py")
    api = _read(root, "src/tradebot/api.py")
    labeling = _read(root, "src/tradebot/training/labeling.py")
    hardening = _read(root, "src/tradebot/production_hardening.py")
    api_security = _read(root, "src/tradebot/api_security.py")
    gitignore = _read(root, ".gitignore")
    checks = {
        "all_expected_files_present": all(expected.values()),
        "all_py_compile_ok": all(compiled.values()) if compiled else False,
        "install_contract_requirements_present": "fastapi>=0.115" in requirements and "xgboost>=2.0" in requirements and "customtkinter>=5.2" in requirements,
        "strict_config_unknown_key_hard_error_present": "Unknown Settings yaml key(s)" in config and "strict_config_validation: bool = True" in config,
        "api_auth_fields_present": "api_auth_enabled" in config and "destructive_action_confirmation_required" in config,
        "api_security_module_present": "API_SECURITY_CONTRACT_VERSION" in api_security and "DESTRUCTIVE_CONFIRMATIONS" in api_security,
        "api_security_integrated": "install_api_security(app, engine.settings" in api and "from .api_security import install_api_security" in api,
        "sqlite_audit_baseline_present": "PRAGMA journal_mode = WAL" in persistence and "schema_meta" in persistence and "operator_actions" in persistence and "integrity_check" in persistence,
        "runtime_lock_present": "acquire_runtime_lock" in hardening and "RUNTIME_LOCK_ALREADY_HELD" in hardening,
        "fee_slippage_zero_defaults_removed": "entry_fee_bps: float = 0.0" not in labeling and "min_profit_bps: float = 24.0" in labeling,
        "promotion_gate_isolation_present": "evaluate_promotion_gate" in hardening and "HYPOTHESIS_PERFORMANCE_NOT_PRODUCTION_READINESS" in hardening,
        "repo_hygiene_ignore_policy_present": "BEGIN 4B.4.3.6.6.29A PRODUCTION HARDENING P0" in gitignore,
        "runtime_activation_blocked": '"runtime_overlay_activation_performed": False' in hardening,
        "paper_live_order_blocked": '"paper_live_order_enablement_performed": False' in hardening,
        "training_reload_blocked": '"training_performed": False' in hardening and '"reload_performed": False' in hardening,
    }
    return {
        "contract_version": CONTRACT_VERSION,
        "ok": all(checks.values()),
        "read_only": True,
        "checks": checks,
        "expected_files": expected,
        "compiled": compiled,
        "config_mutation_performed": False,
        "scheduler_mutation_performed": False,
        "strategy_parameter_mutation_performed": False,
        "runtime_overlay_activation_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "paper_live_order_enablement_present": False,
        "production_hardening_p0_track": True,
        "hyp006_strategy_threshold_mutation_performed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check 4B.4.3.6.6.29A Production Hardening P0 patch")
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    report = build_report(Path.cwd())
    if args.once_json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"{CONTRACT_VERSION} Production Hardening P0 check")
        for key, value in report["checks"].items():
            print(f" - {key}: {value}")
    return 0 if report.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
