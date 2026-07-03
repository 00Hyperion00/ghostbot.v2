from __future__ import annotations

from tradebot.operator_signature_validation import main

if __name__ == "__main__":
    import sys
    raise SystemExit(main([*sys.argv[1:], "--write"]))
