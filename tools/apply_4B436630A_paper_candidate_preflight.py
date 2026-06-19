from __future__ import annotations

import json, shutil, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

CONTRACT_VERSION = "4B.4.3.6.6.30A"
FILES_TO_COPY = [
    "docs/PAPER_CANDIDATE_PREFLIGHT_4B436630A.md",
    "src/tradebot/paper_candidate_gate.py",
    "tests/test_paper_candidate_preflight_4B436630A.py",
    "tools/check_4B436630A_paper_candidate_preflight.py",
    "tools/run_4B436630A_paper_candidate_preflight.py",
    "tools/rollback_4B436630A_paper_candidate_preflight.py",
]
CONFIG_BLOCK = '''
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


def _copy_files(root: Path, payload: Path) -> None:
    for rel in FILES_TO_COPY:
        src = payload / rel
        dst = root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    src_self = payload / "tools/apply_4B436630A_paper_candidate_preflight.py"
    if src_self.exists():
        dst_self = root / "tools/apply_4B436630A_paper_candidate_preflight.py"
        dst_self.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_self, dst_self)


def _patch_config(root: Path) -> bool:
    path = root / "src/tradebot/config.py"
    text = path.read_text(encoding="utf-8")
    if "paper_candidate_preflight_enabled" in text:
        return False
    marker = "    # 4B.4.3.6.6.29C SQLite audit ledger upgrade\n"
    if marker not in text:
        marker = "    # 4B.4.3.6.6.29B API/operator security hardening controls\n"
    if marker not in text:
        raise RuntimeError("Config insertion marker not found")
    text = text.replace(marker, CONFIG_BLOCK + "\n" + marker, 1)
    path.write_text(text, encoding="utf-8", newline="\n")
    return True


def _backup(root: Path, rels: list[str]) -> Path:
    backup = root / "tools" / f"_patch_backup_{CONTRACT_VERSION.replace('.', '')}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    backup.mkdir(parents=True, exist_ok=True)
    for rel in rels:
        src = root / rel
        if src.exists():
            dst = backup / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            if src.is_dir():
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)
    return backup


def _run_check(root: Path) -> dict:
    result = subprocess.run([sys.executable, "tools/check_4B436630A_paper_candidate_preflight.py", "--once-json"], cwd=root, text=True, capture_output=True)
    if result.returncode not in (0, 2):
        raise RuntimeError(result.stderr or result.stdout)
    return json.loads(result.stdout)


def main() -> int:
    root = Path.cwd()
    payload = Path(__file__).resolve().parent / "_patch_payload" / CONTRACT_VERSION
    if not payload.exists():
        payload = Path(__file__).resolve().parent.parent
    rels = FILES_TO_COPY + ["tools/apply_4B436630A_paper_candidate_preflight.py", "src/tradebot/config.py"]
    _backup(root, rels)
    _copy_files(root, payload)
    patched_config = _patch_config(root)
    report = _run_check(root)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    print(f"{CONTRACT_VERSION} Paper Candidate Preflight patch applied")
    for key in ("all_expected_files_present","all_py_compile_ok","contract_version_ok","config_paper_preflight_fields_present","no_order_to_paper_transition_gate_present","exchange_sandbox_isolation_present","capital_cap_gate_present","kill_switch_gate_present","operator_approval_gate_present","module_probe_ok","operator_approval_required_blocks_transition","operator_approved_transition_candidate_review_only","live_real_hard_block_verified","runtime_activation_blocked","paper_live_order_blocked","training_reload_blocked"):
        print(f" - {key}: {report['checks'].get(key)}")
    print(f" - patched_config_paper_preflight_fields: {patched_config}")
    print(f" - runtime_overlay_activation_performed: {report.get('runtime_overlay_activation_performed')}")
    print(f" - training_performed: {report.get('training_performed')}")
    print(f" - reload_performed: {report.get('reload_performed')}")
    print(f" - trading_action_performed: {report.get('trading_action_performed')}")
    print(f" - paper_live_order_enablement_present: {report.get('paper_live_order_enablement_present')}")
    return 0 if report.get("ok") else 2

if __name__ == "__main__":
    raise SystemExit(main())
