from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "4B.4.3.6.6.30A-H1"

MISSING_CONFIG_BLOCK = '''
    # 4B.4.3.6.6.30A-H1 paper candidate preflight missing fields repair
    paper_transition_operator_approval_required: bool = True
    paper_transition_operator_approved: bool = False
    paper_transition_confirmation_phrase: str = "CONFIRM_PAPER_TRANSITION_CANDIDATE"
    paper_transition_confirmation_token: str = ""
    paper_exchange_sandbox_required: bool = True
    paper_sandbox_allowed_market_types: str = "spot_demo,spot_testnet"
    paper_transition_capital_cap_usd: float = 100.0
    paper_order_notional_cap_usd: float = 25.0
    paper_max_daily_loss_usd: float = 5.0
    paper_max_daily_trades_cap: int = 5
    paper_kill_switch_required: bool = True
    paper_kill_switch_enabled: bool = True
'''

ALL_30A_FIELDS_BLOCK = '''
    # 4B.4.3.6.6.30A paper candidate preflight controls
    paper_candidate_preflight_enabled: bool = True
    paper_transition_operator_approval_required: bool = True
    paper_transition_operator_approved: bool = False
    paper_transition_confirmation_phrase: str = "CONFIRM_PAPER_TRANSITION_CANDIDATE"
    paper_transition_confirmation_token: str = ""
    paper_exchange_sandbox_required: bool = True
    paper_sandbox_allowed_market_types: str = "spot_demo,spot_testnet"
    paper_transition_capital_cap_usd: float = 100.0
    paper_order_notional_cap_usd: float = 25.0
    paper_max_daily_loss_usd: float = 5.0
    paper_max_daily_trades_cap: int = 5
    paper_kill_switch_required: bool = True
    paper_kill_switch_enabled: bool = True
'''

REQUIRED_FIELDS = [
    "paper_candidate_preflight_enabled",
    "paper_transition_operator_approval_required",
    "paper_transition_operator_approved",
    "paper_transition_confirmation_phrase",
    "paper_transition_confirmation_token",
    "paper_exchange_sandbox_required",
    "paper_sandbox_allowed_market_types",
    "paper_transition_capital_cap_usd",
    "paper_order_notional_cap_usd",
    "paper_max_daily_loss_usd",
    "paper_max_daily_trades_cap",
    "paper_kill_switch_required",
    "paper_kill_switch_enabled",
]

BACKUP_RELS = [
    "src/tradebot/config.py",
    "tools/apply_4B436630A_paper_candidate_preflight.py",
]


def _backup(root: Path) -> Path:
    backup = root / "tools" / f"_patch_backup_{CONTRACT_VERSION.replace('.', '')}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    backup.mkdir(parents=True, exist_ok=True)
    for rel in BACKUP_RELS:
        src = root / rel
        if src.exists():
            dst = backup / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    return backup


def _patch_config(root: Path) -> dict[str, Any]:
    path = root / "src/tradebot/config.py"
    text = path.read_text(encoding="utf-8")
    before_missing = [field for field in REQUIRED_FIELDS if field not in text]
    if not before_missing:
        return {"patched": False, "before_missing": [], "after_missing": []}

    # 29E already introduced paper_candidate_preflight_enabled. The original 30A apply exited early
    # when it saw this field, so insert only the missing operator/cap/kill-switch fields after it.
    if "paper_candidate_preflight_enabled" in text and "paper_transition_operator_approval_required" not in text:
        anchor = "    paper_candidate_preflight_enabled: bool = True\n"
        if anchor in text:
            text = text.replace(anchor, anchor + MISSING_CONFIG_BLOCK, 1)
        else:
            raise RuntimeError("paper_candidate_preflight_enabled field exists but exact insertion anchor was not found")
    else:
        marker = "    # 4B.4.3.6.6.29E production readiness consolidation gate controls\n"
        if marker not in text:
            marker = "    # 4B.4.3.6.6.29D replay/backtest/walk-forward gate controls\n"
        if marker not in text:
            marker = "    @classmethod\n"
        if marker not in text:
            raise RuntimeError("Config insertion marker not found")
        text = text.replace(marker, ALL_30A_FIELDS_BLOCK + "\n" + marker, 1)

    path.write_text(text, encoding="utf-8", newline="\n")
    after = path.read_text(encoding="utf-8")
    after_missing = [field for field in REQUIRED_FIELDS if field not in after]
    return {"patched": True, "before_missing": before_missing, "after_missing": after_missing}


def _load_checker(root: Path) -> Any:
    checker_path = root / "tools/check_4B436630A_H1_paper_preflight_config_fields.py"
    spec = importlib.util.spec_from_file_location("check_4B436630A_H1_paper_preflight_config_fields", checker_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("H1 checker import spec failed")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    root = Path.cwd()
    _backup(root)
    patch_result = _patch_config(root)
    checker = _load_checker(root)
    report = checker.build_report(root)
    report["patch_result"] = patch_result
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    print(f"{CONTRACT_VERSION} Paper preflight config fields hotfix applied")
    for key in (
        "all_expected_files_present",
        "all_py_compile_ok",
        "base_30a_checker_ok",
        "config_paper_preflight_fields_present",
        "module_probe_ok",
        "operator_approval_required_blocks_transition",
        "operator_approved_transition_candidate_review_only",
        "invalid_risk_caps_block_preflight",
        "live_real_hard_block_verified",
        "runtime_activation_blocked",
        "paper_live_order_blocked",
        "training_reload_blocked",
    ):
        print(f" - {key}: {report['checks'].get(key)}")
    print(f" - patched_config_paper_preflight_missing_fields: {patch_result.get('patched')}")
    print(f" - runtime_overlay_activation_performed: {report.get('runtime_overlay_activation_performed')}")
    print(f" - training_performed: {report.get('training_performed')}")
    print(f" - reload_performed: {report.get('reload_performed')}")
    print(f" - trading_action_performed: {report.get('trading_action_performed')}")
    print(f" - paper_live_order_enablement_present: {report.get('paper_live_order_enablement_present')}")
    return 0 if report.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
