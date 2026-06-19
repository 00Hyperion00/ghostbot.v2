from __future__ import annotations

import argparse
import json
import py_compile
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "4B.4.3.6.6.29B"

EXPECTED_FILES = [
    "src/tradebot/api_security.py",
    "tests/test_api_operator_security_hardening_4B436629B.py",
    "tools/apply_4B436629B_api_operator_security_hardening.py",
    "tools/check_4B436629B_api_operator_security_hardening.py",
    "tools/rollback_4B436629B_api_operator_security_hardening.py",
    "tools/run_4B436629B_api_operator_security_hardening.py",
    "docs/API_OPERATOR_SECURITY_HARDENING_4B436629B.md",
]

COMPILE_TARGETS = [
    "src/tradebot/api_security.py",
    "src/tradebot/config.py",
    "tests/test_api_operator_security_hardening_4B436629B.py",
    "tools/apply_4B436629B_api_operator_security_hardening.py",
    "tools/check_4B436629B_api_operator_security_hardening.py",
    "tools/rollback_4B436629B_api_operator_security_hardening.py",
    "tools/run_4B436629B_api_operator_security_hardening.py",
]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _compile(path: Path) -> bool:
    try:
        py_compile.compile(str(path), doraise=True)
        return True
    except Exception:
        return False


def build_report(root: Path) -> dict[str, Any]:
    api_security = _read(root / "src/tradebot/api_security.py")
    config = _read(root / "src/tradebot/config.py")
    api = _read(root / "src/tradebot/api.py")
    expected_files = {path: (root / path).exists() for path in EXPECTED_FILES}
    compiled = {path: _compile(root / path) for path in COMPILE_TARGETS if (root / path).exists()}
    checks = {
        "all_expected_files_present": all(expected_files.values()),
        "all_py_compile_ok": all(compiled.values()) if compiled else False,
        "contract_version_ok": f'API_SECURITY_CONTRACT_VERSION = "{CONTRACT_VERSION}"' in api_security,
        "constant_time_token_compare_present": "hmac.compare_digest" in api_security,
        "token_ttl_guard_present": "API_AUTH_TOKEN_EXPIRED" in api_security and "api_auth_token_ttl_sec" in config,
        "token_issued_at_guard_present": "API_AUTH_TOKEN_ISSUED_AT_MISSING" in api_security and "api_auth_token_issued_at_ms" in config,
        "typed_confirmation_guard_present": "DESTRUCTIVE_ACTION_CONFIRMATION_REQUIRED" in api_security and "CONFIRM_FORCE_BUY" in api_security,
        "live_arm_ttl_guard_present": "LIVE_REAL_ARM_EXPIRED" in api_security and "live_real_arm_ttl_sec" in config,
        "live_arm_confirmation_guard_present": "LIVE_REAL_ARM_CONFIRMATION_REQUIRED" in api_security and "CONFIRM_LIVE_REAL_START" in api_security,
        "operator_audit_baseline_present": "OPERATOR_API_ACTION_ALLOWED" in api_security and "OPERATOR_API_ACTION_BLOCKED" in api_security,
        "local_only_guard_present": "API_LOCAL_ONLY_REQUIRED" in api_security and "api_local_only_required" in config,
        "api_security_integrated": "install_api_security(app, engine.settings" in api,
        "runtime_activation_blocked": "runtime_overlay_activation_performed" in api_security,
        "paper_live_order_blocked": "paper_live_order_enablement_present" in api_security,
        "training_reload_blocked": "training_reload_performed_by_guard" in api_security,
    }
    checks["all_security_controls_present"] = all(
        checks[key]
        for key in (
            "contract_version_ok",
            "constant_time_token_compare_present",
            "token_ttl_guard_present",
            "typed_confirmation_guard_present",
            "live_arm_ttl_guard_present",
            "operator_audit_baseline_present",
            "local_only_guard_present",
            "api_security_integrated",
        )
    )
    return {
        "ok": all(checks.values()),
        "contract_version": CONTRACT_VERSION,
        "read_only": True,
        "api_operator_security_hardening": True,
        "checks": checks,
        "expected_files": expected_files,
        "compiled": compiled,
        "config_mutation_performed": False,
        "scheduler_mutation_performed": False,
        "strategy_parameter_mutation_performed": False,
        "runtime_overlay_activation_performed": False,
        "training_performed": False,
        "reload_performed": False,
        "trading_action_performed": False,
        "paper_live_order_enablement_present": False,
        "hyp006_strategy_threshold_mutation_performed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check 4B.4.3.6.6.29B API operator security hardening")
    parser.add_argument("--once-json", action="store_true")
    args = parser.parse_args()
    report = build_report(Path.cwd())
    if args.once_json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"{CONTRACT_VERSION} API operator security hardening check ok={report['ok']}")
        for key, value in report["checks"].items():
            print(f" - {key}: {value}")
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
