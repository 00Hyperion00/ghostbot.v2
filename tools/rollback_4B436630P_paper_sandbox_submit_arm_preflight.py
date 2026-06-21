from __future__ import annotations

from pathlib import Path

FILES = [
    "README_APPLY_4B436630P.txt",
    "docs/PAPER_SANDBOX_SUBMIT_ARM_PREFLIGHT_4B436630P.md",
    "src/tradebot/paper_sandbox_submit_arm_preflight.py",
    "tests/test_paper_sandbox_submit_arm_preflight_4B436630P.py",
    "tools/apply_4B436630P_paper_sandbox_submit_arm_preflight.py",
    "tools/check_4B436630P_paper_sandbox_submit_arm_preflight.py",
    "tools/rollback_4B436630P_paper_sandbox_submit_arm_preflight.py",
    "tools/run_4B436630P_paper_sandbox_submit_arm_preflight.py",
]
CONFIG_FIELDS = [
    "paper_sandbox_submit_arm_preflight_enabled",
    "paper_sandbox_submit_arm_consume_30o_required",
    "paper_sandbox_submit_arm_api_mode",
    "paper_sandbox_submit_arm_base_url",
    "paper_sandbox_submit_arm_min_notional_usd",
    "paper_sandbox_submit_arm_lot_size_step_qty",
    "paper_sandbox_submit_arm_min_qty",
    "paper_sandbox_submit_arm_simulated_price_usd",
    "paper_sandbox_submit_arm_api_mode_required",
    "paper_sandbox_submit_arm_endpoint_required",
    "paper_sandbox_submit_arm_min_notional_check_required",
    "paper_sandbox_submit_arm_lot_size_check_required",
    "paper_sandbox_submit_arm_risk_caps_check_required",
    "paper_sandbox_submit_arm_kill_switch_check_required",
    "paper_sandbox_submit_arm_no_exchange_submit_required",
    "paper_sandbox_submit_arm_no_live_real_required",
]


def repo_root() -> Path:
    start = Path.cwd().resolve()
    for item in [start, *start.parents]:
        if (item / "src" / "tradebot").is_dir() and (item / "tools").is_dir():
            return item
    return start


def main() -> int:
    root = repo_root()
    for rel in FILES:
        (root / rel).unlink(missing_ok=True)
    config = root / "src/tradebot/config.py"
    if config.exists():
        lines = config.read_text(encoding="utf-8").splitlines()
        filtered: list[str] = []
        skip_comment = False
        for line in lines:
            if "4B.4.3.6.6.30P paper sandbox submit-arm preflight controls" in line:
                skip_comment = True
                continue
            if skip_comment and any(field in line for field in CONFIG_FIELDS):
                continue
            skip_comment = False
            filtered.append(line)
        config.write_text("\n".join(filtered) + "\n", encoding="utf-8")
    print("4B.4.3.6.6.30P rollback applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
