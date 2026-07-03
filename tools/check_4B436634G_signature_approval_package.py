from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from tradebot.signature_approval_package import run_cli

    return run_cli(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
