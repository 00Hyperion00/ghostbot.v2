from __future__ import annotations

import sys

from tradebot.sqlite_audit_baseline import main

if __name__ == "__main__":
    args = list(sys.argv[1:])
    if "--write-reports" not in args:
        args.append("--write-reports")
    raise SystemExit(main(args))
