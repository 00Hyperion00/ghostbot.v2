from __future__ import annotations

from tradebot.operator_decision_token import main

if __name__ == "__main__":
    import sys
    raise SystemExit(main([*sys.argv[1:], "--write"]))
