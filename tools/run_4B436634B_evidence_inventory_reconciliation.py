from __future__ import annotations

from tradebot.evidence_inventory_reconciliation import main

if __name__ == "__main__":
    import sys
    raise SystemExit(main([*sys.argv[1:], "--write"]))
