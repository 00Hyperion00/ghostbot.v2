from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tradebot.strict_config_unknown_key_fail_closed import main

if __name__ == "__main__":
    args = sys.argv[1:]
    if "--write-reports" not in args:
        args.append("--write-reports")
    raise SystemExit(main(args))
