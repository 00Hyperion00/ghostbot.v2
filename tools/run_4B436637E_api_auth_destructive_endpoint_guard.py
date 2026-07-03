from __future__ import annotations

import sys
from pathlib import Path

repo_root = Path.cwd()
src = repo_root / "src"
if str(src) not in sys.path:
    sys.path.insert(0, str(src))

from tradebot.api_auth_destructive_endpoint_guard import main

if __name__ == "__main__":
    raise SystemExit(main([*sys.argv[1:], "--write-reports"]))
