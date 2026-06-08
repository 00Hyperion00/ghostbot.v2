from __future__ import annotations

import argparse
import json
import sys
import webbrowser
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tradebot.operator_cockpit_v2_read_only import (  # noqa: E402
    OPERATOR_COCKPIT_V2_SAFE_ACTIONS_VERSION,
    collect_operator_cockpit_snapshot,
    make_operator_cockpit_server,
)

OPERATOR_COCKPIT_V2_WINDOWS_UTF8_ONCE_JSON_RUNNER_HOTFIX_VERSION = "4B.4.3.6.6.26C-H1"
OPERATOR_COCKPIT_V2_ONCE_JSON_UTF8_STDOUT_CONTRACT = True


def _write_utf8_json_stdout(payload: Any) -> None:
    """Write JSON as UTF-8 bytes so Windows console locale cannot alter --once-json output."""
    encoded = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    stdout_buffer = getattr(sys.stdout, "buffer", None)
    if stdout_buffer is None:
        sys.stdout.write(encoded.decode("utf-8"))
        sys.stdout.flush()
        return
    stdout_buffer.write(encoded)
    stdout_buffer.flush()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="TradeBot V2 operator cockpit safe GET-only actions")
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8090)
    parser.add_argument("--open-browser", action="store_true")
    parser.add_argument("--allow-non-loopback", action="store_true")
    parser.add_argument("--once-json", action="store_true", help="Print one UTF-8 read-only safe-actions snapshot and exit")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_root = args.project_root.resolve()
    if args.once_json:
        _write_utf8_json_stdout(collect_operator_cockpit_snapshot(project_root))
        return 0
    if args.host not in {"127.0.0.1", "localhost", "::1"} and not args.allow_non_loopback:
        print("Non-loopback bind blocked. Use --allow-non-loopback only after an explicit security review.", file=sys.stderr)
        return 2
    server = make_operator_cockpit_server(project_root, host=args.host, port=args.port)
    url = f"http://{args.host}:{args.port}/dashboard"
    print(f"{OPERATOR_COCKPIT_V2_SAFE_ACTIONS_VERSION} Operator Cockpit V2 safe operator actions")
    print(f" - runner_hotfix_version: {OPERATOR_COCKPIT_V2_WINDOWS_UTF8_ONCE_JSON_RUNNER_HOTFIX_VERSION}")
    print(f" - url: {url}")
    print(" - safe_actions_transport: GET_ONLY")
    print(" - exports: IN_MEMORY_ONLY")
    print(" - once_json_stdout_contract: UTF8_BYTES")
    print(" - config_mutation_performed: False")
    print(" - scheduler_mutation_performed: False")
    print(" - trading_action_performed: False")
    print(" - external_chart_dependency_used: False")
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
