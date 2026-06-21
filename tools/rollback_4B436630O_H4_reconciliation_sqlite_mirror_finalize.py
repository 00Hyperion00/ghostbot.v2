from __future__ import annotations
from pathlib import Path
FILES=['README_APPLY_4B436630O_H4.txt','docs/PAPER_SANDBOX_EXECUTION_RECONCILIATION_SQLITE_MIRROR_FINALIZE_4B436630O_H4.md','tools/apply_4B436630O_H4_reconciliation_sqlite_mirror_finalize.py','tools/check_4B436630O_H4_reconciliation_sqlite_mirror_finalize.py','tools/rollback_4B436630O_H4_reconciliation_sqlite_mirror_finalize.py','tests/test_paper_sandbox_execution_reconciliation_gate_4B436630O_H4.py']
def main()->int:
    for f in FILES: Path(f).unlink(missing_ok=True)
    print('4B.4.3.6.6.30O-H4 rollback applied'); return 0
if __name__=='__main__': raise SystemExit(main())
