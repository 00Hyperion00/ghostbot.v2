from __future__ import annotations

import py_compile
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src" / "tradebot"
EXCHANGE_DIR = SRC_DIR / "exchange"
TOOLS_DIR = PROJECT_ROOT / "tools"
PAYLOAD_DIR = TOOLS_DIR / "_patch_payload"
BACKUP_DIR = TOOLS_DIR / "_patch_backup_4B436627C"
CREATED_PREFLIGHT_MARKER = BACKUP_DIR / ".order_preflight_created"

PREFLIGHT_PAYLOAD = PAYLOAD_DIR / "order_preflight_4B436627C.py"
PREFLIGHT_TARGET = SRC_DIR / "order_preflight.py"
BINANCE_CLIENT = EXCHANGE_DIR / "binance.py"
ENGINE = SRC_DIR / "engine.py"
CHECKER = TOOLS_DIR / "check_truthful_order_preflight_4B436627C.py"
ROLLBACK = TOOLS_DIR / "rollback_4B436627C_truthful_order_preflight_open_orders_verification.py"
TEST_FILE = PROJECT_ROOT / "tests" / "test_truthful_order_preflight_4B436627C.py"
DOC_FILE = PROJECT_ROOT / "docs" / "TRUTHFUL_ORDER_PREFLIGHT_OPEN_ORDERS_VERIFICATION_4B436627C.md"


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
        raise RuntimeError(f"4B436627C_EXPECTED_SOURCE_FRAGMENT_MISSING:{path}:{old[:160]}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def _restore_backups() -> None:
    if not BACKUP_DIR.exists():
        return
    for source in sorted(
        path
        for path in BACKUP_DIR.rglob("*")
        if path.is_file() and path != CREATED_PREFLIGHT_MARKER and "__pycache__" not in path.parts and path.suffix not in {".pyc", ".pyo"}
    ):
        relative = source.relative_to(BACKUP_DIR)
        target = PROJECT_ROOT / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    if CREATED_PREFLIGHT_MARKER.exists():
        PREFLIGHT_TARGET.unlink(missing_ok=True)


def _patch_binance_client() -> None:
    _replace_once(
        BINANCE_CLIENT,
        "from ..models import Balance, Candle, SymbolRules\n",
        "from ..models import Balance, Candle, SymbolRules\nfrom ..order_preflight import (\n    OrderPreflightError,\n    blocked_entry_preflight_snapshot,\n    successful_entry_preflight_snapshot,\n)\n",
    )
    _replace_once(
        BINANCE_CLIENT,
        "        return await self._signed_request('POST', path, params)\n\n    async def cancel_order(",
        "        return await self._signed_request('POST', path, params)\n\n    async def run_entry_order_preflight(\n        self,\n        *,\n        symbol: str,\n        quantity: float,\n        price: float,\n        client_order_id: str,\n        time_in_force: str = 'GTC',\n    ) -> dict[str, object]:\n        try:\n            self._enforce_signed_request_policy('POST', '/api/v3/order', {'side': 'BUY'})\n        except Exception as error:\n            cause_code = str(getattr(error, 'code', type(error).__name__))\n            snapshot = blocked_entry_preflight_snapshot(\n                symbol=symbol,\n                reason_code='PREFLIGHT_EXECUTION_POLICY_BLOCKED',\n                message='Execution policy blocked new-risk entry before network preflight',\n                open_orders_check_performed=False,\n                open_orders_count=None,\n                order_test_performed=False,\n                order_test_ok=None,\n                policy_check_performed=True,\n                policy_allowed=False,\n            )\n            raise OrderPreflightError(snapshot, cause_reason_code=cause_code) from error\n        try:\n            open_orders = await self.fetch_open_orders(symbol)\n        except Exception as error:\n            snapshot = blocked_entry_preflight_snapshot(\n                symbol=symbol,\n                reason_code='PREFLIGHT_OPEN_ORDERS_QUERY_FAILED',\n                message='Open-orders query failed; new-risk entry denied',\n                open_orders_check_performed=False,\n                open_orders_count=None,\n                order_test_performed=False,\n                order_test_ok=None,\n            )\n            raise OrderPreflightError(snapshot, cause_reason_code=type(error).__name__) from error\n        open_orders_count = len(open_orders)\n        if open_orders_count > 0:\n            snapshot = blocked_entry_preflight_snapshot(\n                symbol=symbol,\n                reason_code='PREFLIGHT_EXISTING_OPEN_ORDERS_BLOCKED',\n                message='Existing open orders detected; new-risk entry denied',\n                open_orders_check_performed=True,\n                open_orders_count=open_orders_count,\n                order_test_performed=False,\n                order_test_ok=None,\n            )\n            raise OrderPreflightError(snapshot)\n        try:\n            await self.create_limit_order(\n                symbol=symbol,\n                side='BUY',\n                quantity=quantity,\n                price=price,\n                client_order_id=client_order_id,\n                time_in_force=time_in_force,\n                test=True,\n            )\n        except Exception as error:\n            snapshot = blocked_entry_preflight_snapshot(\n                symbol=symbol,\n                reason_code='PREFLIGHT_ORDER_TEST_FAILED',\n                message='Order-test request failed; new-risk entry denied',\n                open_orders_check_performed=True,\n                open_orders_count=open_orders_count,\n                order_test_performed=True,\n                order_test_ok=False,\n            )\n            raise OrderPreflightError(snapshot, cause_reason_code=type(error).__name__) from error\n        return successful_entry_preflight_snapshot(\n            symbol=symbol,\n            open_orders_count=open_orders_count,\n        ).to_log_payload()\n\n    async def cancel_order(",
    )


def _patch_engine() -> None:
    _replace_once(
        ENGINE,
        "from .order_reconciliation import ORDER_RECONCILIATION_CONTRACT_VERSION, build_reconciliation_snapshot\n",
        "from .order_reconciliation import ORDER_RECONCILIATION_CONTRACT_VERSION, build_reconciliation_snapshot\nfrom .order_preflight import OrderPreflightError, risk_reducing_exit_preflight_snapshot\n",
    )
    _replace_once(
        ENGINE,
        "            self.runtime.last_preflight = f'OK | ENTRY | {self.settings.execution_mode.upper()} | {datetime.now().strftime(\"%d.%m.%Y %H:%M:%S\")}'\n            self.logger.info('LIVE_PREFLIGHT_OK', 'Canlı emir preflight başarılı', {'action': 'ENTRY','openOrdersCount': 0,'orderTestOk': True,'notional': round(qty * price, 6),'price': price,'qty': qty,'route': self.settings.execution_mode.upper(),'side': 'BUY','symbol': self.settings.symbol})\n            order = await self.exchange.create_limit_order(symbol=self.settings.symbol, side='BUY', quantity=qty, price=price, client_order_id=client_id)\n",
        "            try:\n                preflight = await self.exchange.run_entry_order_preflight(\n                    symbol=self.settings.symbol,\n                    quantity=qty,\n                    price=price,\n                    client_order_id=client_id,\n                )\n            except OrderPreflightError as error:\n                self.runtime.last_preflight = f'BLOCKED | ENTRY | {error.code} | {datetime.now().strftime(\"%d.%m.%Y %H:%M:%S\")}'\n                self.logger.warn('LIVE_PREFLIGHT_BLOCKED', 'Canlı giriş emri preflight tarafından engellendi', {**error.to_log_payload(),'notional': round(qty * price, 6),'price': price,'qty': qty,'route': self.settings.execution_mode.upper(),'side': 'BUY','symbol': self.settings.symbol})\n                self._save_runtime()\n                return\n            self.runtime.last_preflight = f'OK | ENTRY | {self.settings.execution_mode.upper()} | {datetime.now().strftime(\"%d.%m.%Y %H:%M:%S\")}'\n            self.logger.info('LIVE_PREFLIGHT_OK', 'Canlı emir preflight başarılı', {**preflight,'notional': round(qty * price, 6),'price': price,'qty': qty,'route': self.settings.execution_mode.upper(),'side': 'BUY','symbol': self.settings.symbol})\n            order = await self.exchange.create_limit_order(symbol=self.settings.symbol, side='BUY', quantity=qty, price=price, client_order_id=client_id)\n",
    )
    _replace_once(
        ENGINE,
        "            self.runtime.last_preflight = f'OK | EXIT | {self.settings.execution_mode.upper()} | {datetime.now().strftime(\"%d.%m.%Y %H:%M:%S\")}'\n            self.logger.info('LIVE_PREFLIGHT_OK', 'Canlı emir preflight başarılı', {'action': 'EXIT','openOrdersCount': 0,'orderTestOk': True,'notional': round(qty * price, 6),'price': price,'qty': qty,'route': self.settings.execution_mode.upper(),'side': 'SELL','symbol': self.settings.symbol})\n",
        "            exit_preflight = risk_reducing_exit_preflight_snapshot(symbol=self.settings.symbol).to_log_payload()\n            self.runtime.last_preflight = f'OK | EXIT | POLICY_ONLY | {self.settings.execution_mode.upper()} | {datetime.now().strftime(\"%d.%m.%Y %H:%M:%S\")}'\n            self.logger.info('LIVE_PREFLIGHT_OK', 'Risk azaltıcı çıkış policy preflight başarılı', {**exit_preflight,'notional': round(qty * price, 6),'price': price,'qty': qty,'route': self.settings.execution_mode.upper(),'side': 'SELL','symbol': self.settings.symbol})\n",
    )


def main() -> int:
    required = [PREFLIGHT_PAYLOAD, BINANCE_CLIENT, ENGINE, CHECKER, ROLLBACK, TEST_FILE, DOC_FILE]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        print("4B436627C_apply_error: required file missing")
        for item in missing:
            print(f" - missing: {item}")
        return 2

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    for path in (BINANCE_CLIENT, ENGINE):
        _backup(path)
    if PREFLIGHT_TARGET.exists():
        if not CREATED_PREFLIGHT_MARKER.exists():
            _backup(PREFLIGHT_TARGET)
    else:
        CREATED_PREFLIGHT_MARKER.write_text("created_by_4B436627C\n", encoding="utf-8")
    try:
        shutil.copy2(PREFLIGHT_PAYLOAD, PREFLIGHT_TARGET)
        _patch_binance_client()
        _patch_engine()
    except Exception as error:
        _restore_backups()
        print(f"4B436627C_apply_error: {error}")
        return 3

    checks: list[tuple[str, bool]] = [
        ("config_mutation_performed", False),
        ("scheduler_mutation_performed", False),
        ("trading_action_performed", False),
        ("preflight_module_py_compile_ok", _compile(PREFLIGHT_TARGET)),
        ("binance_client_py_compile_ok", _compile(BINANCE_CLIENT)),
        ("engine_py_compile_ok", _compile(ENGINE)),
        ("checker_py_compile_ok", _compile(CHECKER)),
        ("rollback_py_compile_ok", _compile(ROLLBACK)),
        ("test_file_py_compile_ok", _compile(TEST_FILE)),
        ("preflight_version_present", _contains(PREFLIGHT_TARGET, 'TRUTHFUL_ORDER_PREFLIGHT_VERSION = "4B.4.3.6.6.27C"')),
        ("real_open_orders_query_present", _contains(BINANCE_CLIENT, "open_orders = await self.fetch_open_orders(symbol)")),
        ("real_order_test_present", _contains(BINANCE_CLIENT, "test=True,")),
        ("entry_policy_before_network_present", _contains(BINANCE_CLIENT, "self._enforce_signed_request_policy('POST', '/api/v3/order', {'side': 'BUY'})")),
        ("engine_truthful_entry_preflight_present", _contains(ENGINE, "await self.exchange.run_entry_order_preflight(")),
        ("engine_truthful_exit_preflight_present", _contains(ENGINE, "risk_reducing_exit_preflight_snapshot")),
        ("fabricated_preflight_literals_absent", not _contains(ENGINE, "'openOrdersCount': 0,'orderTestOk': True")),
        ("paper_live_order_enablement_present", False),
    ]
    print("4B.4.3.6.6.27C Truthful order preflight / open-orders verification applied")
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
