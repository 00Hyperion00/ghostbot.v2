from __future__ import annotations

from pathlib import Path

FILES = [
    "README_APPLY_4B436630N.txt",
    "docs/PAPER_SANDBOX_DRY_RUN_EXECUTION_GATE_4B436630N.md",
    "src/tradebot/paper_sandbox_dry_run_execution_gate.py",
    "tests/test_paper_sandbox_dry_run_execution_gate_4B436630N.py",
    "tools/apply_4B436630N_paper_sandbox_dry_run_execution_gate.py",
    "tools/check_4B436630N_paper_sandbox_dry_run_execution_gate.py",
    "tools/rollback_4B436630N_paper_sandbox_dry_run_execution_gate.py",
    "tools/run_4B436630N_paper_sandbox_dry_run_execution_gate.py",
]
CONFIG_FIELDS = [
    "paper_sandbox_dry_run_execution_gate_enabled",
    "paper_sandbox_dry_run_execution_consume_30m_required",
    "paper_sandbox_dry_run_execution_authorization_required",
    "paper_sandbox_dry_run_execution_operator_id",
    "paper_sandbox_dry_run_execution_authorization_phrase",
    "paper_sandbox_dry_run_execution_authorization_token",
    "paper_sandbox_dry_run_execution_authorization_issued",
    "paper_sandbox_dry_run_execution_authorization_issued_at_ms",
    "paper_sandbox_dry_run_execution_authorization_ttl_sec",
    "paper_sandbox_dry_run_execution_ledger_append_required",
    "paper_sandbox_dry_run_execution_ledger_path",
    "paper_sandbox_dry_run_execution_no_exchange_submit_required",
    "paper_sandbox_dry_run_execution_no_live_real_required",
    "paper_sandbox_dry_run_execution_simulated_fill_price_usd",
    "paper_sandbox_dry_run_execution_simulated_fee_bps",
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
        filtered = []
        skip_comment = False
        for line in lines:
            if "4B.4.3.6.6.30N paper sandbox dry-run execution gate controls" in line:
                skip_comment = True
                continue
            if skip_comment and any(field in line for field in CONFIG_FIELDS):
                continue
            skip_comment = False
            filtered.append(line)
        config.write_text("\n".join(filtered) + "\n", encoding="utf-8")
    print("4B.4.3.6.6.30N rollback applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
