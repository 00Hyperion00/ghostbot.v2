from __future__ import annotations

import py_compile
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src" / "tradebot"
EXCHANGE_DIR = SRC_DIR / "exchange"
TOOLS_DIR = PROJECT_ROOT / "tools"
PAYLOAD_DIR = TOOLS_DIR / "_patch_payload"
BACKUP_DIR = TOOLS_DIR / "_patch_backup_4B436627A"

ROUTER_PAYLOAD = PAYLOAD_DIR / "binance_environment_router_4B436627A.py"
ROUTER_TARGET = SRC_DIR / "binance_environment.py"
BINANCE_CLIENT = EXCHANGE_DIR / "binance.py"
CONFIG_SAFETY = SRC_DIR / "config_safety.py"
CHECKER = TOOLS_DIR / "check_binance_environment_router_4B436627A.py"
ROLLBACK = TOOLS_DIR / "rollback_4B436627A_binance_rest_ws_environment_consistency_router.py"
TEST_FILE = PROJECT_ROOT / "tests" / "test_binance_environment_router_4B436627A.py"
DOC_FILE = PROJECT_ROOT / "docs" / "BINANCE_REST_WS_ENVIRONMENT_CONSISTENCY_ROUTER_4B436627A.md"


def _compile(path: Path) -> bool:
    try:
        py_compile.compile(str(path), doraise=True)
    except py_compile.PyCompileError:
        return False
    return True


def _contains(path: Path, marker: str) -> bool:
    return path.exists() and marker in path.read_text(encoding="utf-8")


def _backup(path: Path) -> None:
    relative = path.relative_to(PROJECT_ROOT)
    target = BACKUP_DIR / relative
    if target.exists():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, target)


def _replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if new in text:
        return
    if old not in text:
        raise RuntimeError(f"4B436627A_EXPECTED_SOURCE_FRAGMENT_MISSING:{path}:{old[:100]}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def _patch_binance_client() -> None:
    _replace_once(
        BINANCE_CLIENT,
        "from ..config import Settings\nfrom ..models import Balance, Candle, SymbolRules\n",
        "from ..config import Settings\nfrom ..binance_environment import (\n    binance_environment_snapshot,\n    build_combined_market_stream_url,\n    resolve_binance_environment,\n)\nfrom ..models import Balance, Candle, SymbolRules\n",
    )
    _replace_once(
        BINANCE_CLIENT,
        "        self.base_url = settings.base_url.rstrip('/')\n        import httpx\n",
        "        self.base_url = settings.base_url.rstrip('/')\n        self.endpoint_profile = resolve_binance_environment(settings.market_type, self.base_url)\n        import httpx\n",
    )
    _replace_once(
        BINANCE_CLIENT,
        '''    def _market_ws_url(self) -> str:\n        symbol = self.settings.symbol.lower()\n        return f"wss://stream.binance.com:9443/stream?streams={symbol}@bookTicker/{symbol}@miniTicker/{symbol}@kline_{self.settings.kline_interval}"\n''',
        '''    def _market_ws_url(self) -> str:\n        return build_combined_market_stream_url(\n            self.endpoint_profile,\n            symbol=self.settings.symbol,\n            kline_interval=self.settings.kline_interval,\n        )\n\n    def endpoint_environment_snapshot(self) -> dict[str, object]:\n        return binance_environment_snapshot(self.endpoint_profile, configured_rest_base_url=self.base_url)\n''',
    )


def _patch_config_safety() -> None:
    _replace_once(
        CONFIG_SAFETY,
        "from .enums import AutoSignalMode, ExecutionMode, MarketType\n",
        "from .enums import AutoSignalMode, ExecutionMode, MarketType\nfrom .binance_environment import (\n    BINANCE_ENVIRONMENT_ROUTER_VERSION,\n    BinanceEnvironmentError,\n    binance_environment_snapshot,\n    resolve_binance_environment,\n)\n",
    )
    _replace_once(
        CONFIG_SAFETY,
        "    base_url_lower = cfg.base_url.lower()\n",
        '''    base_url_lower = cfg.base_url.lower()\n    try:\n        endpoint_profile = resolve_binance_environment(cfg.market_type, cfg.base_url)\n        endpoint_environment = binance_environment_snapshot(endpoint_profile, configured_rest_base_url=cfg.base_url)\n    except BinanceEnvironmentError as error:\n        endpoint_environment = error.to_snapshot()\n        criticals.append('Binance REST / WebSocket environment profili çelişiyor')\n        reason_codes.append(error.code)\n\n''',
    )
    _replace_once(
        CONFIG_SAFETY,
        "        'base_url_redacted': cfg.base_url,\n",
        "        'base_url_redacted': cfg.base_url,\n        'binance_environment_router_version': BINANCE_ENVIRONMENT_ROUTER_VERSION,\n        'binance_environment': endpoint_environment,\n",
    )


def main() -> int:
    required = [ROUTER_PAYLOAD, BINANCE_CLIENT, CONFIG_SAFETY, CHECKER, ROLLBACK, TEST_FILE, DOC_FILE]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        print("4B436627A_apply_error: required file missing")
        for item in missing:
            print(f" - missing: {item}")
        return 2

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    for path in (BINANCE_CLIENT, CONFIG_SAFETY):
        _backup(path)
    if ROUTER_TARGET.exists():
        _backup(ROUTER_TARGET)
    shutil.copy2(ROUTER_PAYLOAD, ROUTER_TARGET)
    _patch_binance_client()
    _patch_config_safety()

    checks: list[tuple[str, bool]] = [
        ("config_mutation_performed", False),
        ("scheduler_mutation_performed", False),
        ("trading_action_performed", False),
        ("router_module_py_compile_ok", _compile(ROUTER_TARGET)),
        ("binance_client_py_compile_ok", _compile(BINANCE_CLIENT)),
        ("config_safety_py_compile_ok", _compile(CONFIG_SAFETY)),
        ("checker_py_compile_ok", _compile(CHECKER)),
        ("rollback_py_compile_ok", _compile(ROLLBACK)),
        ("test_file_py_compile_ok", _compile(TEST_FILE)),
        ("router_version_present", _contains(ROUTER_TARGET, 'BINANCE_ENVIRONMENT_ROUTER_VERSION = "4B.4.3.6.6.27A"')),
        ("demo_stream_route_present", _contains(ROUTER_TARGET, 'wss://demo-stream.binance.com:9443/stream')),
        ("testnet_stream_route_present", _contains(ROUTER_TARGET, 'wss://stream.testnet.binance.vision:9443/stream')),
        ("mainnet_stream_route_present", _contains(ROUTER_TARGET, 'wss://stream.binance.com:9443/stream')),
        ("fail_closed_mismatch_present", _contains(ROUTER_TARGET, 'BINANCE_REST_WS_ENVIRONMENT_MISMATCH')),
        ("binance_client_router_wired", _contains(BINANCE_CLIENT, 'self.endpoint_profile = resolve_binance_environment')),
        ("config_safety_router_wired", _contains(CONFIG_SAFETY, "'binance_environment': endpoint_environment")),
        ("paper_live_order_enablement_present", False),
    ]
    print("4B.4.3.6.6.27A Binance REST / WebSocket environment consistency router applied")
    all_ok = True
    for name, value in checks:
        print(f" - {name}: {value}")
        if name in {"config_mutation_performed", "scheduler_mutation_performed", "trading_action_performed", "paper_live_order_enablement_present"}:
            all_ok = all_ok and (value is False)
        else:
            all_ok = all_ok and value
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
