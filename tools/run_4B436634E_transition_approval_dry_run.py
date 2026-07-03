from __future__ import annotations

from tradebot.transition_approval_dry_run import main

if __name__ == "__main__":
    import sys
    raise SystemExit(main([*sys.argv[1:], "--write"]))
