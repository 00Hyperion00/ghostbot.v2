from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR
from pathlib import Path
from typing import Any, Protocol

from .binance_environment import BinanceEnvironmentError, binance_environment_snapshot, resolve_binance_environment
from .config import Settings
from .enums import ExecutionMode, MarketType
from .execution_policy import ExecutionPolicyAction, ExecutionPolicyError, enforce_execution_policy
from .models import SymbolRules

BINANCE_DEMO_AUTHENTICATED_NO_ORDER_PREFLIGHT_VERSION = "4B.4.3.6.6.27C-H1"
BINANCE_DEMO_AUTHENTICATED_NO_ORDER_ONLY = True
BINANCE_DEMO_AUTHENTICATED_FAIL_CLOSED = True
BINANCE_DEMO_REAL_ORDER_ENDPOINT_FORBIDDEN = True
BINANCE_DEMO_EVIDENCE_SECRETS_REDACTED = True

SAFE_REQUEST_PATHS = frozenset({
    "/api/v3/time",
    "/api/v3/exchangeInfo",
    "/api/v3/ticker/price",
    "/api/v3/openOrders",
    "/api/v3/order/test",
})
FORBIDDEN_REAL_ORDER_PATH = "/api/v3/order"


class DemoAuthenticatedProbeClient(Protocol):
    async def close(self) -> None: ...
    async def sync_server_time(self) -> dict[str, Any]: ...
    async def fetch_symbol_rules(self, symbol: str | None = None) -> SymbolRules: ...
    async def public_test(self) -> dict[str, Any]: ...
    async def fetch_open_orders(self, symbol: str | None = None) -> list[dict[str, Any]]: ...
    async def create_limit_order(
        self,
        *,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        client_order_id: str,
        time_in_force: str = "GTC",
        test: bool = False,
    ) -> dict[str, Any]: ...


@dataclass(slots=True)
class NetworkRequestEvidence:
    method: str
    path: str
    purpose: str
    attempted: bool = True
    ok: bool | None = None


@dataclass(slots=True)
class DemoProbeEvidence:
    ok: bool
    reason_code: str
    message: str
    generated_at_utc: str
    market_type: str
    execution_mode: str
    configured_rest_base_url: str
    symbol: str
    api_key_present: bool
    api_secret_present: bool
    profile_verified: bool = False
    policy_entry_allowed: bool | None = None
    policy_order_test_allowed: bool | None = None
    open_orders_check_performed: bool = False
    open_orders_count: int | None = None
    order_test_performed: bool = False
    order_test_ok: bool | None = None
    test_order_quantity: str | None = None
    test_order_price: str | None = None
    test_order_notional: str | None = None
    network_requests: list[NetworkRequestEvidence] = field(default_factory=list)
    real_order_endpoint_used: bool = False
    trading_action_performed: bool = False
    config_mutation_performed: bool = False
    scheduler_mutation_performed: bool = False
    no_order_guarantee: bool = True
    environment: dict[str, object] | None = None
    cause_reason_code: str | None = None

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["contractVersion"] = BINANCE_DEMO_AUTHENTICATED_NO_ORDER_PREFLIGHT_VERSION
        payload["readOnlyEvidence"] = True
        return payload


class DemoAuthenticatedProbeError(RuntimeError):
    def __init__(self, evidence: DemoProbeEvidence) -> None:
        super().__init__(f"{evidence.reason_code}: {evidence.message}")
        self.evidence = evidence
        self.code = evidence.reason_code


def utc_now_text() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def utc_artifact_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%SZ")


def _decimal_text(value: Decimal) -> str:
    return format(value.normalize(), "f")


def _positive_decimal(value: object, *, field_name: str) -> Decimal:
    try:
        number = Decimal(str(value))
    except Exception as error:
        raise ValueError(f"{field_name} must be decimal-compatible") from error
    if number <= 0:
        raise ValueError(f"{field_name} must be positive")
    return number


def _floor_to_step(value: Decimal, step: Decimal) -> Decimal:
    return (value / step).to_integral_value(rounding=ROUND_FLOOR) * step


def _ceil_to_step(value: Decimal, step: Decimal) -> Decimal:
    return (value / step).to_integral_value(rounding=ROUND_CEILING) * step


def build_safe_test_limit_order(
    *,
    symbol: str,
    ticker_price: object,
    rules: SymbolRules,
    requested_notional_usd: object = "15",
) -> dict[str, object]:
    """Build filter-aware LIMIT BUY parameters for /api/v3/order/test only."""
    current_price = _positive_decimal(ticker_price, field_name="ticker_price")
    tick_size = _positive_decimal(rules.tick_size, field_name="tick_size")
    step_size = _positive_decimal(rules.step_size, field_name="step_size")
    min_qty = _positive_decimal(rules.min_qty, field_name="min_qty")
    requested_notional = _positive_decimal(requested_notional_usd, field_name="requested_notional_usd")
    min_notional = Decimal(str(rules.min_notional or 0))
    max_qty = Decimal(str(rules.max_qty or 0))
    price = _floor_to_step(current_price, tick_size)
    if price <= 0:
        raise ValueError("rounded test-order price must be positive")
    target_notional = max(requested_notional, min_notional * Decimal("1.10"), Decimal("10"))
    quantity = _ceil_to_step(max(min_qty, target_notional / price), step_size)
    if max_qty > 0 and quantity > max_qty:
        raise ValueError("calculated test-order quantity exceeds max_qty")
    notional = quantity * price
    if min_notional > 0 and notional < min_notional:
        raise ValueError("calculated test-order notional is below min_notional")
    return {
        "symbol": str(symbol).upper(),
        "side": "BUY",
        "quantity": float(quantity),
        "price": float(price),
        "quantity_text": _decimal_text(quantity),
        "price_text": _decimal_text(price),
        "notional_text": _decimal_text(notional),
        "time_in_force": "GTC",
    }


def _base_evidence(settings: Settings, *, symbol: str) -> DemoProbeEvidence:
    return DemoProbeEvidence(
        ok=False,
        reason_code="DEMO_PREFLIGHT_NOT_STARTED",
        message="Authenticated demo no-order preflight has not started",
        generated_at_utc=utc_now_text(),
        market_type=str(settings.market_type),
        execution_mode=str(settings.execution_mode),
        configured_rest_base_url=str(settings.base_url).rstrip("/"),
        symbol=str(symbol).upper(),
        api_key_present=bool(settings.api_key),
        api_secret_present=bool(settings.api_secret),
    )


def _fail(evidence: DemoProbeEvidence, reason_code: str, message: str, *, cause: object | None = None) -> DemoAuthenticatedProbeError:
    evidence.ok = False
    evidence.reason_code = str(reason_code)
    evidence.message = str(message)
    if cause is not None:
        evidence.cause_reason_code = str(getattr(cause, "code", type(cause).__name__))
    return DemoAuthenticatedProbeError(evidence)


def _append_request(evidence: DemoProbeEvidence, *, method: str, path: str, purpose: str) -> NetworkRequestEvidence:
    if path == FORBIDDEN_REAL_ORDER_PATH or path not in SAFE_REQUEST_PATHS:
        evidence.real_order_endpoint_used = path == FORBIDDEN_REAL_ORDER_PATH
        raise _fail(evidence, "DEMO_PREFLIGHT_UNSAFE_REQUEST_PATH_BLOCKED", f"Unsafe request path blocked: {path}")
    item = NetworkRequestEvidence(method=str(method).upper(), path=str(path), purpose=str(purpose), attempted=True, ok=None)
    evidence.network_requests.append(item)
    return item


def validate_demo_probe_evidence(payload: Mapping[str, object]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if payload.get("contractVersion") != BINANCE_DEMO_AUTHENTICATED_NO_ORDER_PREFLIGHT_VERSION:
        errors.append("DEMO_PREFLIGHT_EVIDENCE_CONTRACT_VERSION_INVALID")
    if payload.get("market_type") != MarketType.SPOT_DEMO.value:
        errors.append("DEMO_PREFLIGHT_EVIDENCE_PROFILE_INVALID")
    if payload.get("execution_mode") != ExecutionMode.LIVE_DEMO.value:
        errors.append("DEMO_PREFLIGHT_EVIDENCE_EXECUTION_MODE_INVALID")
    if payload.get("configured_rest_base_url") != "https://demo-api.binance.com":
        errors.append("DEMO_PREFLIGHT_EVIDENCE_REST_ENVIRONMENT_INVALID")
    if payload.get("real_order_endpoint_used") is not False:
        errors.append("DEMO_PREFLIGHT_REAL_ORDER_ENDPOINT_USED")
    if payload.get("trading_action_performed") is not False:
        errors.append("DEMO_PREFLIGHT_TRADING_ACTION_DETECTED")
    if payload.get("no_order_guarantee") is not True:
        errors.append("DEMO_PREFLIGHT_NO_ORDER_GUARANTEE_MISSING")
    requests = payload.get("network_requests")
    if not isinstance(requests, list):
        errors.append("DEMO_PREFLIGHT_NETWORK_REQUESTS_INVALID")
    else:
        paths: list[str] = []
        for row in requests:
            if not isinstance(row, Mapping):
                errors.append("DEMO_PREFLIGHT_NETWORK_REQUEST_ROW_INVALID")
                continue
            path = str(row.get("path") or "")
            paths.append(path)
            if path == FORBIDDEN_REAL_ORDER_PATH or path not in SAFE_REQUEST_PATHS:
                errors.append("DEMO_PREFLIGHT_UNSAFE_REQUEST_PATH_DETECTED")
        if payload.get("ok") is True:
            for expected in ("/api/v3/time", "/api/v3/openOrders", "/api/v3/order/test"):
                if expected not in paths:
                    errors.append(f"DEMO_PREFLIGHT_REQUIRED_PATH_MISSING:{expected}")
    if payload.get("ok") is True:
        if payload.get("profile_verified") is not True:
            errors.append("DEMO_PREFLIGHT_PROFILE_NOT_VERIFIED")
        if payload.get("open_orders_check_performed") is not True or payload.get("open_orders_count") != 0:
            errors.append("DEMO_PREFLIGHT_OPEN_ORDERS_NOT_VERIFIED")
        if payload.get("order_test_performed") is not True or payload.get("order_test_ok") is not True:
            errors.append("DEMO_PREFLIGHT_ORDER_TEST_NOT_VERIFIED")
    serialized = json.dumps(dict(payload), ensure_ascii=False).lower()
    for forbidden in ('"api_secret":', '"api_key":', "signature=", "x-mbx-apikey"):
        if forbidden in serialized:
            errors.append("DEMO_PREFLIGHT_SECRET_MATERIAL_DETECTED")
            break
    return not errors, errors


ClientFactory = Callable[[Settings], DemoAuthenticatedProbeClient]


async def run_demo_authenticated_no_order_probe(
    settings: Settings,
    *,
    client_factory: ClientFactory,
    symbol: str | None = None,
    requested_notional_usd: object = "15",
) -> DemoProbeEvidence:
    selected_symbol = str(symbol or settings.symbol).upper()
    evidence = _base_evidence(settings, symbol=selected_symbol)
    if str(settings.market_type) != MarketType.SPOT_DEMO.value or str(settings.execution_mode) != ExecutionMode.LIVE_DEMO.value:
        raise _fail(evidence, "DEMO_PREFLIGHT_PROFILE_REQUIRED", "Authenticated no-order probe requires spot_demo + live_demo")
    if str(settings.base_url).rstrip("/") != "https://demo-api.binance.com":
        raise _fail(evidence, "DEMO_PREFLIGHT_PROFILE_REQUIRED", "Authenticated no-order probe requires the Binance Demo REST origin")
    if selected_symbol != str(settings.symbol).upper():
        raise _fail(evidence, "DEMO_PREFLIGHT_SYMBOL_OVERRIDE_NOT_ALLOWED", "Probe symbol must match config symbol to avoid mixed ticker/rules evidence")
    if not settings.api_key or not settings.api_secret:
        raise _fail(evidence, "DEMO_PREFLIGHT_API_CREDENTIALS_MISSING", "Demo API key and secret are required before authenticated probe")
    try:
        profile = resolve_binance_environment(settings.market_type, settings.base_url)
        evidence.environment = binance_environment_snapshot(profile, configured_rest_base_url=settings.base_url)
        evidence.profile_verified = True
        entry_decision = enforce_execution_policy(settings, profile, action=ExecutionPolicyAction.ENTRY_NEW_RISK.value)
        test_decision = enforce_execution_policy(settings, profile, action=ExecutionPolicyAction.ORDER_TEST.value)
        evidence.policy_entry_allowed = bool(entry_decision.allowed)
        evidence.policy_order_test_allowed = bool(test_decision.allowed)
    except (BinanceEnvironmentError, ExecutionPolicyError) as error:
        raise _fail(evidence, "DEMO_PREFLIGHT_PROFILE_POLICY_BLOCKED", "Demo environment or execution policy blocked authenticated probe", cause=error) from error
    client = client_factory(settings)
    try:
        item = _append_request(evidence, method="GET", path="/api/v3/time", purpose="server_time_sync")
        try:
            await client.sync_server_time(); item.ok = True
        except Exception as error:
            item.ok = False
            raise _fail(evidence, "DEMO_PREFLIGHT_SERVER_TIME_SYNC_FAILED", "Demo server-time synchronization failed", cause=error) from error
        item = _append_request(evidence, method="GET", path="/api/v3/exchangeInfo", purpose="symbol_rules")
        try:
            rules = await client.fetch_symbol_rules(selected_symbol); item.ok = True
        except Exception as error:
            item.ok = False
            raise _fail(evidence, "DEMO_PREFLIGHT_SYMBOL_RULES_QUERY_FAILED", "Demo symbol-rules query failed", cause=error) from error
        item = _append_request(evidence, method="GET", path="/api/v3/ticker/price", purpose="public_reference_price")
        try:
            ticker = await client.public_test(); ticker_price = ticker["price"]; item.ok = True
        except Exception as error:
            item.ok = False
            raise _fail(evidence, "DEMO_PREFLIGHT_TICKER_QUERY_FAILED", "Demo ticker query failed", cause=error) from error
        try:
            order = build_safe_test_limit_order(symbol=selected_symbol, ticker_price=ticker_price, rules=rules, requested_notional_usd=requested_notional_usd)
            evidence.test_order_quantity = str(order["quantity_text"])
            evidence.test_order_price = str(order["price_text"])
            evidence.test_order_notional = str(order["notional_text"])
        except Exception as error:
            raise _fail(evidence, "DEMO_PREFLIGHT_ORDER_PARAMETER_BUILD_FAILED", "Safe demo order-test parameters could not be built", cause=error) from error
        item = _append_request(evidence, method="GET", path="/api/v3/openOrders", purpose="authenticated_open_orders_query")
        try:
            open_orders = await client.fetch_open_orders(selected_symbol)
            evidence.open_orders_check_performed = True
            evidence.open_orders_count = len(open_orders)
            item.ok = True
        except Exception as error:
            item.ok = False
            raise _fail(evidence, "DEMO_PREFLIGHT_OPEN_ORDERS_QUERY_FAILED", "Authenticated demo open-orders query failed", cause=error) from error
        if evidence.open_orders_count:
            raise _fail(evidence, "DEMO_PREFLIGHT_EXISTING_OPEN_ORDERS_BLOCKED", "Existing demo open orders detected; order-test was not attempted")
        item = _append_request(evidence, method="POST", path="/api/v3/order/test", purpose="authenticated_order_test_no_matching_engine")
        evidence.order_test_performed = True
        try:
            await client.create_limit_order(
                symbol=selected_symbol,
                side="BUY",
                quantity=float(order["quantity"]),
                price=float(order["price"]),
                client_order_id=f"TB-DEMO-PREFLIGHT-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
                time_in_force=str(order["time_in_force"]),
                test=True,
            )
            evidence.order_test_ok = True; item.ok = True
        except Exception as error:
            evidence.order_test_ok = False; item.ok = False
            raise _fail(evidence, "DEMO_PREFLIGHT_ORDER_TEST_FAILED", "Authenticated Binance Demo order-test failed", cause=error) from error
        evidence.ok = True
        evidence.reason_code = "DEMO_PREFLIGHT_AUTHENTICATED_NO_ORDER_VERIFIED"
        evidence.message = "Authenticated Binance Demo open-orders query and order-test completed without real order submission"
        valid, errors = validate_demo_probe_evidence(evidence.to_dict())
        if not valid:
            raise _fail(evidence, "DEMO_PREFLIGHT_EVIDENCE_SELF_CHECK_FAILED", ";".join(errors))
        return evidence
    finally:
        await client.close()


def write_evidence_json(path: Path, evidence: DemoProbeEvidence) -> Path:
    payload = evidence.to_dict()
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    with tempfile.NamedTemporaryFile(mode="wb", prefix=f".{path.name}.", suffix=".tmp", dir=path.parent, delete=False) as handle:
        temp_path = Path(handle.name)
        handle.write(encoded); handle.flush(); os.fsync(handle.fileno())
    try:
        temp_path.replace(path)
    finally:
        temp_path.unlink(missing_ok=True)
    return path
