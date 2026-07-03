from __future__ import annotations

import sys

from tradebot.phase_35_final_tag_audit import main

if __name__ == "__main__":
    argv = list(sys.argv[1:])
    if "--write-reports" not in argv:
        argv.append("--write-reports")
    raise SystemExit(main(argv))
