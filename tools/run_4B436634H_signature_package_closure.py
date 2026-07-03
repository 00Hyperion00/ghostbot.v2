from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from tradebot.signature_package_closure import run_cli

    argv = list(sys.argv[1:])
    if "--write" not in argv:
        argv.append("--write")
    return run_cli(argv)


if __name__ == "__main__":
    raise SystemExit(main())
