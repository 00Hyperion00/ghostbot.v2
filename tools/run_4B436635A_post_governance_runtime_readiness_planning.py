from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradebot.post_governance_runtime_readiness_planning import main

if __name__ == "__main__":
    args = sys.argv[1:]
    if "--write-reports" not in args:
        args = [*args, "--write-reports"]
    raise SystemExit(main(args))
