from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

TRUTHFUL_ORDER_PREFLIGHT_VERSION = "4B.4.3.6.6.27C"
TRUTHFUL_OPEN_ORDERS_VERIFICATION = True
TRUTHFUL_ORDER_TEST_VERIFICATION = True
ENTRY_NEW_RISK_PREFLIGHT_FAIL_CLOSED = True
RISK_REDUCING_EXIT_PREFLIGHT_NOT_FABRICATED = True


@dataclass(frozen=True, slots=True)
class OrderPreflightSnapshot:
    ok: bool
    action: str
    symbol: str
    reason_code: str
    message: str
    open_orders_check_performed: bool
    open_orders_count: int | None
    order_test_performed: bool
    order_test_ok: bool | None
    policy_check_performed: bool
    policy_allowed: bool | None
    trading_action_performed: bool = False

    def to_log_payload(self) -> dict[str, object]:
        payload = asdict(self)
        return {
            "preflightVersion": TRUTHFUL_ORDER_PREFLIGHT_VERSION,
            "ok": payload["ok"],
            "action": payload["action"],
            "symbol": payload["symbol"],
            "reasonCode": payload["reason_code"],
            "message": payload["message"],
            "openOrdersCheckPerformed": payload["open_orders_check_performed"],
            "openOrdersCount": payload["open_orders_count"],
            "orderTestPerformed": payload["order_test_performed"],
            "orderTestOk": payload["order_test_ok"],
            "policyCheckPerformed": payload["policy_check_performed"],
            "policyAllowed": payload["policy_allowed"],
            "tradingActionPerformed": payload["trading_action_performed"],
        }


class OrderPreflightError(RuntimeError):
    def __init__(self, snapshot: OrderPreflightSnapshot, *, cause_reason_code: str | None = None) -> None:
        super().__init__(f"{snapshot.reason_code}: {snapshot.message}")
        self.snapshot = snapshot
        self.code = snapshot.reason_code
        self.cause_reason_code = cause_reason_code

    def to_log_payload(self) -> dict[str, object]:
        payload = self.snapshot.to_log_payload()
        payload["causeReasonCode"] = self.cause_reason_code
        return payload


def successful_entry_preflight_snapshot(*, symbol: str, open_orders_count: int) -> OrderPreflightSnapshot:
    return OrderPreflightSnapshot(
        ok=True,
        action="ENTRY_NEW_RISK",
        symbol=str(symbol),
        reason_code="PREFLIGHT_ENTRY_VERIFIED",
        message="Entry preflight verified with real open-orders query and order-test request",
        open_orders_check_performed=True,
        open_orders_count=int(open_orders_count),
        order_test_performed=True,
        order_test_ok=True,
        policy_check_performed=True,
        policy_allowed=True,
        trading_action_performed=False,
    )


def blocked_entry_preflight_snapshot(
    *,
    symbol: str,
    reason_code: str,
    message: str,
    open_orders_check_performed: bool,
    open_orders_count: int | None,
    order_test_performed: bool,
    order_test_ok: bool | None,
    policy_check_performed: bool = True,
    policy_allowed: bool | None = True,
) -> OrderPreflightSnapshot:
    return OrderPreflightSnapshot(
        ok=False,
        action="ENTRY_NEW_RISK",
        symbol=str(symbol),
        reason_code=str(reason_code),
        message=str(message),
        open_orders_check_performed=bool(open_orders_check_performed),
        open_orders_count=None if open_orders_count is None else int(open_orders_count),
        order_test_performed=bool(order_test_performed),
        order_test_ok=order_test_ok,
        policy_check_performed=bool(policy_check_performed),
        policy_allowed=policy_allowed,
        trading_action_performed=False,
    )


def risk_reducing_exit_preflight_snapshot(*, symbol: str) -> OrderPreflightSnapshot:
    """Describe truthful exit semantics: policy-only, without fabricated network checks."""
    return OrderPreflightSnapshot(
        ok=True,
        action="EXIT_RISK_REDUCING",
        symbol=str(symbol),
        reason_code="PREFLIGHT_RISK_REDUCING_EXIT_POLICY_ONLY",
        message="Risk-reducing exit uses exchange policy enforcement; entry-only checks were not performed",
        open_orders_check_performed=False,
        open_orders_count=None,
        order_test_performed=False,
        order_test_ok=None,
        policy_check_performed=True,
        policy_allowed=True,
        trading_action_performed=False,
    )
