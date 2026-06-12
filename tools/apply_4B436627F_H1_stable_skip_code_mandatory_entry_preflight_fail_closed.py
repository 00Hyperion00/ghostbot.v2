from __future__ import annotations

import py_compile
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = PROJECT_ROOT / "tools"
BACKUP_DIR = TOOLS_DIR / "_patch_backup_4B436627F_H1"
CREATED_MARKER = BACKUP_DIR / ".created_files.txt"

SIZING = PROJECT_ROOT / "src" / "tradebot" / "position_sizing.py"
ENGINE = PROJECT_ROOT / "src" / "tradebot" / "engine.py"
RISK_GUARDS_TEST = PROJECT_ROOT / "tests" / "test_risk_guards.py"
ENTRY_LIFECYCLE_TEST = PROJECT_ROOT / "tests" / "test_entry_lifecycle_guard.py"
LIVE_DEMO_LIFECYCLE_TEST = PROJECT_ROOT / "tests" / "test_live_demo_order_lifecycle_hardening.py"
CHECKER = TOOLS_DIR / "check_4B436627F_H1_stable_skip_code_mandatory_entry_preflight_fail_closed.py"
ROLLBACK = TOOLS_DIR / "rollback_4B436627F_H1_stable_skip_code_mandatory_entry_preflight_fail_closed.py"
HOTFIX_TEST = PROJECT_ROOT / "tests" / "test_risk_percent_position_sizing_4B436627F_H1.py"
DOC = PROJECT_ROOT / "docs" / "RISK_PERCENT_POSITION_SIZING_4B436627F_H1.md"

ACTIVE_FILES = [SIZING, ENGINE, RISK_GUARDS_TEST, ENTRY_LIFECYCLE_TEST, LIVE_DEMO_LIFECYCLE_TEST]


def _compile(path: Path) -> bool:
    try:
        py_compile.compile(str(path), doraise=True)
        return True
    except py_compile.PyCompileError:
        return False


def _contains(path: Path, marker: str) -> bool:
    return path.exists() and marker in path.read_text(encoding="utf-8")


def _backup(path: Path) -> None:
    relative = path.relative_to(PROJECT_ROOT)
    target = BACKUP_DIR / relative
    if target.exists():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, target)


def _restore_on_failure() -> None:
    if not BACKUP_DIR.exists():
        return
    for source in sorted(
        path
        for path in BACKUP_DIR.rglob("*")
        if path.is_file()
        and path != CREATED_MARKER
        and "__pycache__" not in path.parts
        and path.suffix not in {".pyc", ".pyo"}
    ):
        relative = source.relative_to(BACKUP_DIR)
        target = PROJECT_ROOT / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def _replace_once(path: Path, old: str, new: str, *, operation: str) -> None:
    text = path.read_text(encoding="utf-8")
    if new in text:
        return
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"27F_H1_ANCHOR_COUNT_INVALID:{operation}:{count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def _patch() -> None:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    for path in ACTIVE_FILES:
        if not path.exists():
            raise RuntimeError(f"27F_H1_REQUIRED_ACTIVE_FILE_MISSING:{path}")
        _backup(path)

    _replace_once(
        SIZING,
        'LEGACY_SIZING_MODE_ALIASES = {"risk_percent": "risk_percent_quote_balance"}\n',
        '''LEGACY_SIZING_MODE_ALIASES = {"risk_percent": "risk_percent_quote_balance"}\nSTABLE_ENTRY_SKIP_CODE_COMPAT_VERSION = "4B.4.3.6.6.27F-H1"\n\n_INSUFFICIENT_QUOTE_BALANCE_REASONS = frozenset({\n    "SIZING_QUOTE_BALANCE_NON_POSITIVE",\n    "SIZING_USABLE_QUOTE_BALANCE_NON_POSITIVE",\n    "SIZING_QUOTE_BUDGET_EXCEEDS_AVAILABLE_BALANCE",\n})\n_MIN_NOTIONAL_BLOCK_REASONS = frozenset({\n    "SIZING_QUOTE_BUDGET_BELOW_MIN_NOTIONAL",\n    "SIZING_QUANTITY_ROUNDED_TO_ZERO",\n    "SIZING_QUANTITY_BELOW_MIN_QTY",\n    "SIZING_ORDER_NOTIONAL_BELOW_BUFFERED_MIN_NOTIONAL",\n})\n''',
        operation="sizing_constants",
    )
    _replace_once(
        SIZING,
        '''class PositionSizingError(ValueError):\n    """Fail-closed quantity contract violation."""\n\n    def __init__(self, reason_code: str, message: str | None = None) -> None:\n        self.reason_code = reason_code\n        super().__init__(message or reason_code)\n\n\n''',
        '''class PositionSizingError(ValueError):\n    """Fail-closed quantity contract violation."""\n\n    def __init__(self, reason_code: str, message: str | None = None) -> None:\n        self.reason_code = reason_code\n        super().__init__(message or reason_code)\n\n\ndef stable_entry_skip_code_for_sizing_error(reason_code: str) -> str:\n    """Map internal sizing diagnostics to the stable external entry-block contract."""\n    normalized = str(reason_code or "").strip()\n    if normalized in _INSUFFICIENT_QUOTE_BALANCE_REASONS:\n        return "INSUFFICIENT_QUOTE_BALANCE"\n    if normalized in _MIN_NOTIONAL_BLOCK_REASONS:\n        return "MIN_NOTIONAL_BLOCKED"\n    return "ENTRY_SIZING_BLOCKED"\n\n\n''',
        operation="sizing_skip_code_mapper",
    )

    _replace_once(
        ENGINE,
        "from .order_preflight import OrderPreflightError, risk_reducing_exit_preflight_snapshot\n",
        "from .order_preflight import OrderPreflightError, blocked_entry_preflight_snapshot, risk_reducing_exit_preflight_snapshot\n",
        operation="engine_preflight_import",
    )
    _replace_once(
        ENGINE,
        "from .position_sizing import PositionSizingError, build_entry_sizing_decision\n",
        "from .position_sizing import PositionSizingError, build_entry_sizing_decision, stable_entry_skip_code_for_sizing_error\n",
        operation="engine_sizing_import",
    )
    _replace_once(
        ENGINE,
        '''            except PositionSizingError as error:\n                self.logger.warn('ENTRY_BLOCKED', 'Giriş miktarı fail-closed sizing kontratı tarafından engellendi', {\n                    'skipCode': error.reason_code,\n                    'price': price,\n                    'freeQuote': quote.free,\n                    'sizingMode': self.settings.sizing_mode,\n                    'sizingContractVersion': '4B.4.3.6.6.27F',\n                })\n                return\n''',
        '''            except PositionSizingError as error:\n                self.logger.warn('ENTRY_BLOCKED', 'Giriş miktarı fail-closed sizing kontratı tarafından engellendi', {\n                    'skipCode': stable_entry_skip_code_for_sizing_error(error.reason_code),\n                    'sizingReasonCode': error.reason_code,\n                    'price': price,\n                    'freeQuote': quote.free,\n                    'sizingMode': self.settings.sizing_mode,\n                    'sizingContractVersion': '4B.4.3.6.6.27F',\n                    'skipCodeCompatVersion': '4B.4.3.6.6.27F-H1',\n                })\n                return\n''',
        operation="engine_stable_sizing_skip_code",
    )
    _replace_once(
        ENGINE,
        '''            try:\n                preflight = await self.exchange.run_entry_order_preflight(\n                    symbol=self.settings.symbol,\n                    quantity=qty,\n                    price=price,\n                    client_order_id=client_id,\n                )\n            except OrderPreflightError as error:\n                self.runtime.last_preflight = f'BLOCKED | ENTRY | {error.code} | {datetime.now().strftime("%d.%m.%Y %H:%M:%S")}'\n                self.logger.warn('LIVE_PREFLIGHT_BLOCKED', 'Canlı giriş emri preflight tarafından engellendi', {**error.to_log_payload(),'notional': round(qty * price, 6),'price': price,'qty': qty,'route': self.settings.execution_mode.upper(),'side': 'BUY','symbol': self.settings.symbol})\n                self._save_runtime()\n                return\n''',
        '''            entry_preflight = getattr(self.exchange, 'run_entry_order_preflight', None)\n            if not callable(entry_preflight):\n                unavailable = blocked_entry_preflight_snapshot(\n                    symbol=self.settings.symbol,\n                    reason_code='PREFLIGHT_ADAPTER_UNAVAILABLE',\n                    message='Entry preflight adapter unavailable; new-risk entry denied',\n                    open_orders_check_performed=False,\n                    open_orders_count=None,\n                    order_test_performed=False,\n                    order_test_ok=None,\n                    policy_check_performed=False,\n                    policy_allowed=None,\n                ).to_log_payload()\n                self.runtime.last_preflight = f'BLOCKED | ENTRY | PREFLIGHT_ADAPTER_UNAVAILABLE | {datetime.now().strftime("%d.%m.%Y %H:%M:%S")}'\n                self.logger.warn('LIVE_PREFLIGHT_BLOCKED', 'Canlı giriş emri preflight adaptörü bulunamadığı için engellendi', {**unavailable,'causeReasonCode': 'ENTRY_PREFLIGHT_ADAPTER_UNAVAILABLE','notional': round(qty * price, 6),'price': price,'qty': qty,'route': self.settings.execution_mode.upper(),'side': 'BUY','symbol': self.settings.symbol})\n                self._save_runtime()\n                return\n            try:\n                preflight = await self.exchange.run_entry_order_preflight(\n                    symbol=self.settings.symbol,\n                    quantity=qty,\n                    price=price,\n                    client_order_id=client_id,\n                )\n            except OrderPreflightError as error:\n                self.runtime.last_preflight = f'BLOCKED | ENTRY | {error.code} | {datetime.now().strftime("%d.%m.%Y %H:%M:%S")}'\n                self.logger.warn('LIVE_PREFLIGHT_BLOCKED', 'Canlı giriş emri preflight tarafından engellendi', {**error.to_log_payload(),'notional': round(qty * price, 6),'price': price,'qty': qty,'route': self.settings.execution_mode.upper(),'side': 'BUY','symbol': self.settings.symbol})\n                self._save_runtime()\n                return\n            except Exception as error:\n                failed = blocked_entry_preflight_snapshot(\n                    symbol=self.settings.symbol,\n                    reason_code='PREFLIGHT_ADAPTER_CALL_FAILED',\n                    message='Entry preflight adapter call failed; new-risk entry denied',\n                    open_orders_check_performed=False,\n                    open_orders_count=None,\n                    order_test_performed=False,\n                    order_test_ok=None,\n                    policy_check_performed=False,\n                    policy_allowed=None,\n                ).to_log_payload()\n                self.runtime.last_preflight = f'BLOCKED | ENTRY | PREFLIGHT_ADAPTER_CALL_FAILED | {datetime.now().strftime("%d.%m.%Y %H:%M:%S")}'\n                self.logger.warn('LIVE_PREFLIGHT_BLOCKED', 'Canlı giriş emri preflight adaptör hatası nedeniyle engellendi', {**failed,'causeReasonCode': type(error).__name__,'notional': round(qty * price, 6),'price': price,'qty': qty,'route': self.settings.execution_mode.upper(),'side': 'BUY','symbol': self.settings.symbol})\n                self._save_runtime()\n                return\n''',
        operation="engine_mandatory_entry_preflight_fail_closed",
    )

    test_imports = {
        RISK_GUARDS_TEST: "from tradebot.models import Balance, Candle, Position, RuntimeState, SymbolRules\n",
        ENTRY_LIFECYCLE_TEST: "from tradebot.models import Balance, Candle, PendingOrder, RuntimeState, SymbolRules\n",
        LIVE_DEMO_LIFECYCLE_TEST: "from tradebot.models import Balance, Candle, PendingOrder, Position, RuntimeState, SymbolRules\n",
    }
    for path, model_import in test_imports.items():
        _replace_once(
            path,
            model_import,
            "from tradebot.order_preflight import successful_entry_preflight_snapshot\n" + model_import,
            operation=f"{path.name}_preflight_import",
        )
        _replace_once(
            path,
            "    async def create_limit_order(self, **kwargs):\n",
            "    async def run_entry_order_preflight(self, *, symbol: str, **kwargs):\n        return successful_entry_preflight_snapshot(symbol=symbol, open_orders_count=0).to_log_payload()\n\n    async def create_limit_order(self, **kwargs):\n",
            operation=f"{path.name}_preflight_stub",
        )


def main() -> int:
    required = [*ACTIVE_FILES, CHECKER, ROLLBACK, HOTFIX_TEST, DOC]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        print("4B436627F_H1_apply_error: required overlay file missing")
        for item in missing:
            print(f" - missing: {item}")
        return 2

    prerequisites = [
        (SIZING, 'POSITION_SIZING_CONTRACT_VERSION = "4B.4.3.6.6.27F"'),
        (ENGINE, "await self.exchange.run_entry_order_preflight("),
        (ENGINE, "except PositionSizingError as error:"),
    ]
    failed_prerequisites = [f"{path}:{marker}" for path, marker in prerequisites if not _contains(path, marker)]
    if failed_prerequisites:
        print("4B436627F_H1_apply_error: prerequisite marker missing")
        for item in failed_prerequisites:
            print(f" - missing_marker: {item}")
        return 2

    try:
        _patch()
        checks = [
            ("config_mutation_performed", False),
            ("scheduler_mutation_performed", False),
            ("training_performed", False),
            ("reload_performed", False),
            ("trading_action_performed", False),
            ("sizing_module_py_compile_ok", _compile(SIZING)),
            ("engine_py_compile_ok", _compile(ENGINE)),
            ("risk_guards_test_py_compile_ok", _compile(RISK_GUARDS_TEST)),
            ("entry_lifecycle_test_py_compile_ok", _compile(ENTRY_LIFECYCLE_TEST)),
            ("live_demo_lifecycle_test_py_compile_ok", _compile(LIVE_DEMO_LIFECYCLE_TEST)),
            ("checker_py_compile_ok", _compile(CHECKER)),
            ("rollback_py_compile_ok", _compile(ROLLBACK)),
            ("hotfix_test_py_compile_ok", _compile(HOTFIX_TEST)),
            ("stable_skip_code_mapper_present", _contains(SIZING, "def stable_entry_skip_code_for_sizing_error(")),
            ("raw_sizing_reason_preserved", _contains(ENGINE, "'sizingReasonCode': error.reason_code")),
            ("mandatory_preflight_adapter_gate_present", _contains(ENGINE, "PREFLIGHT_ADAPTER_UNAVAILABLE")),
            ("unexpected_preflight_failure_gate_present", _contains(ENGINE, "PREFLIGHT_ADAPTER_CALL_FAILED")),
            ("legacy_test_double_preflight_stubs_present", all(_contains(path, "async def run_entry_order_preflight(") for path in [RISK_GUARDS_TEST, ENTRY_LIFECYCLE_TEST, LIVE_DEMO_LIFECYCLE_TEST])),
            ("paper_live_order_enablement_present", False),
        ]
        print("4B.4.3.6.6.27F-H1 Risk-percent position sizing / stable skip-code compatibility / mandatory entry-preflight fail-closed / legacy test-double regression hotfix applied")
        ok = True
        false_expected = {
            "config_mutation_performed",
            "scheduler_mutation_performed",
            "training_performed",
            "reload_performed",
            "trading_action_performed",
            "paper_live_order_enablement_present",
        }
        for name, value in checks:
            print(f" - {name}: {value}")
            ok = ok and ((value is False) if name in false_expected else bool(value))
        if not ok:
            raise RuntimeError("4B436627F_H1_APPLY_POSTCHECK_FAILED")
        return 0
    except Exception as error:
        _restore_on_failure()
        print(f"4B436627F_H1_apply_error: {error}")
        print(" - transactional_restore_performed: True")
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
