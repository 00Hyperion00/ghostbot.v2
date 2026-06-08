from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tradebot.operator_cockpit_v2_desktop_wrapper import (  # noqa: E402
    DEFAULT_DESKTOP_HOST,
    DEFAULT_DESKTOP_PORT,
    OPERATOR_COCKPIT_V2_DESKTOP_WRAPPER_VERSION,
    OPERATOR_COCKPIT_V2_NATIVE_EXPORT_BRIDGE_HOTFIX_VERSION,
    OPERATOR_COCKPIT_V2_EVIDENCE_PACK_TIMEOUT_HOTFIX_VERSION,
    DesktopWrapperError,
    launch_desktop_shell,
    run_headless_smoke,
)


def _write_utf8_json_stdout(payload: Any) -> None:
    encoded = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    stdout_buffer = getattr(sys.stdout, "buffer", None)
    if stdout_buffer is None:
        sys.stdout.write(encoded.decode("utf-8"))
        sys.stdout.flush()
        return
    stdout_buffer.write(encoded)
    stdout_buffer.flush()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="TradeBot V2 embedded local Operator Cockpit desktop shell")
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--host", default=DEFAULT_DESKTOP_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_DESKTOP_PORT)
    parser.add_argument("--allow-browser-fallback", action="store_true", help="Development-only fallback when pywebview is unavailable")
    parser.add_argument("--headless-smoke-json", action="store_true", help="Start, probe, stop and print one UTF-8 JSON result")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_root = args.project_root.resolve()
    try:
        if args.headless_smoke_json:
            _write_utf8_json_stdout(run_headless_smoke(project_root, host=args.host, port=args.port))
            return 0
        print(f"{OPERATOR_COCKPIT_V2_DESKTOP_WRAPPER_VERSION} Operator Cockpit V2 desktop wrapper / single-launch local application shell")
        print(" - desktop_ui: EMBEDDED_LOCAL_WEBVIEW")
        print(" - host_policy: LOOPBACK_ONLY")
        print(" - single_instance: True")
        print(" - browser_fallback_requires_explicit_flag: True")
        print(f" - native_export_bridge_hotfix_version: {OPERATOR_COCKPIT_V2_NATIVE_EXPORT_BRIDGE_HOTFIX_VERSION}")
        print(" - native_export_bridge: SAVE_DIALOG_ALLOWLIST_ONLY")
        print(f" - evidence_pack_timeout_hotfix_version: {OPERATOR_COCKPIT_V2_EVIDENCE_PACK_TIMEOUT_HOTFIX_VERSION}")
        print(" - native_export_timeout_contract: DETERMINISTIC")
        print(" - config_mutation_performed: False")
        print(" - scheduler_mutation_performed: False")
        print(" - trading_action_performed: False")
        return launch_desktop_shell(
            project_root,
            host=args.host,
            port=args.port,
            allow_browser_fallback=args.allow_browser_fallback,
        )
    except DesktopWrapperError as error:
        print(f"desktop_wrapper_error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
