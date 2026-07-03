from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tradebot.install_contract_launcher_alignment_hotfix import main

if __name__ == "__main__":
    argv = sys.argv[1:]
    if "--write-report" not in argv:
        argv.append("--write-report")
    raise SystemExit(main(argv))
