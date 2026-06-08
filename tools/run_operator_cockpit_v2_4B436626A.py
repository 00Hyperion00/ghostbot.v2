from __future__ import annotations

import argparse
import json
import sys
import webbrowser
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tradebot.operator_cockpit_v2_read_only import (  # noqa: E402
    OPERATOR_COCKPIT_V2_CONTRACT_VERSION,
    collect_operator_cockpit_snapshot,
    make_operator_cockpit_server,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="TradeBot V2 read-only operator cockpit shell")
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8090)
    parser.add_argument("--open-browser", action="store_true")
    parser.add_argument("--allow-non-loopback", action="store_true")
    parser.add_argument("--once-json", action="store_true", help="Print one read-only snapshot and exit")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_root = args.project_root.resolve()
    if args.once_json:
        print(json.dumps(collect_operator_cockpit_snapshot(project_root), ensure_ascii=False, indent=2))
        return 0
    if args.host not in {"127.0.0.1", "localhost", "::1"} and not args.allow_non_loopback:
        print("Non-loopback bind blocked. Use --allow-non-loopback only after an explicit security review.", file=sys.stderr)
        return 2
    server = make_operator_cockpit_server(project_root, host=args.host, port=args.port)
    url = f"http://{args.host}:{args.port}/dashboard"
    print(f"{OPERATOR_COCKPIT_V2_CONTRACT_VERSION} Operator Cockpit V2 read-only dashboard shell")
    print(f" - url: {url}")
    print(" - config_mutation_performed: False")
    print(" - scheduler_mutation_performed: False")
    print(" - trading_action_performed: False")
    if args.open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
