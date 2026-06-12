from __future__ import annotations

import py_compile
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src" / "tradebot"
EXCHANGE_DIR = SRC_DIR / "exchange"
TOOLS_DIR = PROJECT_ROOT / "tools"
PAYLOAD_DIR = TOOLS_DIR / "_patch_payload"
BACKUP_DIR = TOOLS_DIR / "_patch_backup_4B436627B"

POLICY_PAYLOAD = PAYLOAD_DIR / "execution_policy_4B436627B.py"
POLICY_TARGET = SRC_DIR / "execution_policy.py"
BINANCE_CLIENT = EXCHANGE_DIR / "binance.py"
CHECKER = TOOLS_DIR / "check_execution_policy_gate_4B436627B.py"
ROLLBACK = TOOLS_DIR / "rollback_4B436627B_exchange_level_fail_closed_execution_policy_gate.py"
TEST_FILE = PROJECT_ROOT / "tests" / "test_execution_policy_gate_4B436627B.py"
DOC_FILE = PROJECT_ROOT / "docs" / "EXCHANGE_LEVEL_FAIL_CLOSED_EXECUTION_POLICY_GATE_4B436627B.md"


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
        raise RuntimeError(f"4B436627B_EXPECTED_SOURCE_FRAGMENT_MISSING:{path}:{old[:120]}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def _patch_binance_client() -> None:
    _replace_once(
        BINANCE_CLIENT,
        "from ..binance_environment import (\n    binance_environment_snapshot,\n    build_combined_market_stream_url,\n    resolve_binance_environment,\n)\nfrom ..models import Balance, Candle, SymbolRules\n",
        "from ..binance_environment import (\n    binance_environment_snapshot,\n    build_combined_market_stream_url,\n    resolve_binance_environment,\n)\nfrom ..execution_policy import (\n    EXECUTION_POLICY_GATE_VERSION,\n    ExecutionPolicyAction,\n    build_execution_policy_snapshot,\n    classify_limit_order_action,\n    enforce_execution_policy,\n)\nfrom ..models import Balance, Candle, SymbolRules\n",
    )
    _replace_once(
        BINANCE_CLIENT,
        "    def endpoint_environment_snapshot(self) -> dict[str, object]:\n        return binance_environment_snapshot(self.endpoint_profile, configured_rest_base_url=self.base_url)\n\n    def _sign(self, payload: str) -> str:\n",
        "    def endpoint_environment_snapshot(self) -> dict[str, object]:\n        return binance_environment_snapshot(self.endpoint_profile, configured_rest_base_url=self.base_url)\n\n    def execution_policy_snapshot(self) -> dict[str, object]:\n        return build_execution_policy_snapshot(self.settings, self.endpoint_profile)\n\n    def _signed_request_action(self, method: str, path: str, params: dict[str, Any] | None = None) -> str:\n        normalized_method = str(method or '').upper()\n        normalized_path = str(path or '')\n        request_params = dict(params or {})\n        if normalized_method == 'GET':\n            return ExecutionPolicyAction.READ_ONLY_QUERY.value\n        if normalized_method == 'POST' and normalized_path == '/api/v3/order/test':\n            return ExecutionPolicyAction.ORDER_TEST.value\n        if normalized_method == 'POST' and normalized_path == '/api/v3/order':\n            return classify_limit_order_action(side=str(request_params.get('side') or ''), test=False)\n        if normalized_method == 'DELETE' and normalized_path == '/api/v3/order':\n            return ExecutionPolicyAction.CANCEL_PENDING.value\n        return 'UNKNOWN_SIGNED_REQUEST_ACTION'\n\n    def _enforce_signed_request_policy(self, method: str, path: str, params: dict[str, Any] | None = None) -> None:\n        action = self._signed_request_action(method, path, params)\n        enforce_execution_policy(self.settings, self.endpoint_profile, action=action)\n\n    def _sign(self, payload: str) -> str:\n",
    )
    _replace_once(
        BINANCE_CLIENT,
        "    async def _signed_request(self, method: str, path: str, params: dict[str, Any] | None = None) -> Any:\n        if not self.settings.api_key or not self.settings.api_secret:\n            raise RuntimeError('API key/secret missing')\n        params = dict(params or {})\n",
        "    async def _signed_request(self, method: str, path: str, params: dict[str, Any] | None = None) -> Any:\n        self._enforce_signed_request_policy(method, path, params or {})\n        if not self.settings.api_key or not self.settings.api_secret:\n            raise RuntimeError('API key/secret missing')\n        params = dict(params or {})\n",
    )


def main() -> int:
    required = [POLICY_PAYLOAD, BINANCE_CLIENT, CHECKER, ROLLBACK, TEST_FILE, DOC_FILE]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        print("4B436627B_apply_error: required file missing")
        for item in missing:
            print(f" - missing: {item}")
        return 2

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    for path in (BINANCE_CLIENT,):
        _backup(path)
    if POLICY_TARGET.exists():
        _backup(POLICY_TARGET)
    shutil.copy2(POLICY_PAYLOAD, POLICY_TARGET)
    _patch_binance_client()

    checks: list[tuple[str, bool]] = [
        ("config_mutation_performed", False),
        ("scheduler_mutation_performed", False),
        ("trading_action_performed", False),
        ("policy_module_py_compile_ok", _compile(POLICY_TARGET)),
        ("binance_client_py_compile_ok", _compile(BINANCE_CLIENT)),
        ("checker_py_compile_ok", _compile(CHECKER)),
        ("rollback_py_compile_ok", _compile(ROLLBACK)),
        ("test_file_py_compile_ok", _compile(TEST_FILE)),
        ("policy_version_present", _contains(POLICY_TARGET, 'EXECUTION_POLICY_GATE_VERSION = "4B.4.3.6.6.27B"')),
        ("unknown_action_deny_present", _contains(POLICY_TARGET, 'EXECUTION_POLICY_ACTION_CLASS_UNKNOWN')),
        ("dry_run_block_present", _contains(POLICY_TARGET, 'EXECUTION_POLICY_DRY_RUN_ORDER_BLOCKED')),
        ("live_real_armed_gate_present", _contains(POLICY_TARGET, 'EXECUTION_POLICY_LIVE_REAL_NOT_ARMED')),
        ("live_real_double_confirm_gate_present", _contains(POLICY_TARGET, 'EXECUTION_POLICY_LIVE_REAL_DOUBLE_CONFIRM_MISSING')),
        ("binance_signed_request_policy_hook_present", _contains(BINANCE_CLIENT, 'self._enforce_signed_request_policy(method, path, params or {})')),
        ("binance_policy_snapshot_present", _contains(BINANCE_CLIENT, 'def execution_policy_snapshot(self)')),
        ("paper_live_order_enablement_present", False),
    ]
    print("4B.4.3.6.6.27B Exchange-level fail-closed execution policy gate applied")
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
