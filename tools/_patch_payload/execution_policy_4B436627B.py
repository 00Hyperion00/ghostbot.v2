from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any

from .binance_environment import BinanceEndpointProfile, binance_environment_snapshot
from .config import Settings
from .enums import ExecutionMode, MarketType

EXECUTION_POLICY_GATE_VERSION = "4B.4.3.6.6.27B"
EXCHANGE_LEVEL_FAIL_CLOSED_EXECUTION_POLICY = True
EXECUTION_POLICY_UNKNOWN_ACTION_DENY = True
EXECUTION_POLICY_EXCHANGE_ADAPTER_ENFORCED = True


class ExecutionPolicyAction(str, Enum):
    ENTRY_NEW_RISK = "ENTRY_NEW_RISK"
    EXIT_RISK_REDUCING = "EXIT_RISK_REDUCING"
    CANCEL_PENDING = "CANCEL_PENDING"
    ORDER_TEST = "ORDER_TEST"
    READ_ONLY_QUERY = "READ_ONLY_QUERY"


class ExecutionPolicyError(RuntimeError):
    def __init__(self, code: str, message: str, *, action: str, execution_mode: str, market_type: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message
        self.action = action
        self.execution_mode = execution_mode
        self.market_type = market_type

    def to_snapshot(self) -> dict[str, object]:
        return {
            "policy_version": EXECUTION_POLICY_GATE_VERSION,
            "ok": False,
            "fail_closed": True,
            "allowed": False,
            "reason_code": self.code,
            "message": self.message,
            "action": self.action,
            "execution_mode": self.execution_mode,
            "market_type": self.market_type,
        }


@dataclass(frozen=True, slots=True)
class ExecutionPolicyDecision:
    allowed: bool
    reason_code: str
    action: str
    execution_mode: str
    market_type: str
    risk_reducing: bool
    order_test: bool
    live_real_requires_armed: bool
    live_real_requires_double_confirm: bool

    def to_snapshot(self) -> dict[str, object]:
        payload = asdict(self)
        payload.update(
            {
                "policy_version": EXECUTION_POLICY_GATE_VERSION,
                "ok": self.allowed,
                "fail_closed": True,
            }
        )
        return payload


def _text(value: object) -> str:
    return str(value or "").strip()


def _enum_values(enum_cls: type[Enum]) -> set[str]:
    return {str(item.value) for item in enum_cls}


def classify_limit_order_action(*, side: str, test: bool = False) -> str:
    if bool(test):
        return ExecutionPolicyAction.ORDER_TEST.value
    normalized_side = _text(side).upper()
    if normalized_side == "BUY":
        return ExecutionPolicyAction.ENTRY_NEW_RISK.value
    if normalized_side == "SELL":
        return ExecutionPolicyAction.EXIT_RISK_REDUCING.value
    return "UNKNOWN_LIMIT_ORDER_ACTION"


def _is_live_demo_environment(market_type: str) -> bool:
    return market_type in {MarketType.SPOT_DEMO.value, MarketType.SPOT_TESTNET.value}


def _deny(code: str, message: str, *, action: str, settings: Settings) -> None:
    raise ExecutionPolicyError(
        code,
        message,
        action=action,
        execution_mode=_text(settings.execution_mode),
        market_type=_text(settings.market_type),
    )


def evaluate_execution_policy(
    settings: Settings,
    endpoint_profile: BinanceEndpointProfile,
    *,
    action: str,
) -> ExecutionPolicyDecision:
    normalized_action = _text(action)
    execution_mode = _text(settings.execution_mode)
    market_type = _text(settings.market_type)
    known_actions = {item.value for item in ExecutionPolicyAction}

    if normalized_action not in known_actions:
        _deny(
            "EXECUTION_POLICY_ACTION_CLASS_UNKNOWN",
            "Unknown exchange action classes are denied by default",
            action=normalized_action or "UNKNOWN",
            settings=settings,
        )

    if execution_mode not in _enum_values(ExecutionMode):
        _deny(
            "EXECUTION_POLICY_EXECUTION_MODE_UNSUPPORTED",
            "Unsupported execution_mode for exchange order action",
            action=normalized_action,
            settings=settings,
        )

    if market_type not in _enum_values(MarketType):
        _deny(
            "EXECUTION_POLICY_MARKET_TYPE_UNSUPPORTED",
            "Unsupported market_type for exchange order action",
            action=normalized_action,
            settings=settings,
        )

    if endpoint_profile.market_type != market_type:
        _deny(
            "EXECUTION_POLICY_ENVIRONMENT_MISMATCH",
            "Endpoint profile and configured market_type are inconsistent",
            action=normalized_action,
            settings=settings,
        )

    if normalized_action == ExecutionPolicyAction.READ_ONLY_QUERY.value:
        return ExecutionPolicyDecision(
            allowed=True,
            reason_code="EXECUTION_POLICY_READ_ONLY_ALLOWED",
            action=normalized_action,
            execution_mode=execution_mode,
            market_type=market_type,
            risk_reducing=False,
            order_test=False,
            live_real_requires_armed=False,
            live_real_requires_double_confirm=False,
        )

    if execution_mode == ExecutionMode.DRY_RUN.value:
        _deny(
            "EXECUTION_POLICY_DRY_RUN_ORDER_BLOCKED",
            "dry_run mode cannot submit, test, or cancel exchange orders",
            action=normalized_action,
            settings=settings,
        )

    is_entry = normalized_action == ExecutionPolicyAction.ENTRY_NEW_RISK.value
    is_exit = normalized_action == ExecutionPolicyAction.EXIT_RISK_REDUCING.value
    is_cancel = normalized_action == ExecutionPolicyAction.CANCEL_PENDING.value
    is_order_test = normalized_action == ExecutionPolicyAction.ORDER_TEST.value

    if execution_mode == ExecutionMode.LIVE_DEMO.value:
        if not _is_live_demo_environment(market_type):
            _deny(
                "EXECUTION_POLICY_LIVE_DEMO_ENVIRONMENT_INVALID",
                "live_demo order actions require spot_demo or spot_testnet market_type",
                action=normalized_action,
                settings=settings,
            )
        return ExecutionPolicyDecision(
            allowed=True,
            reason_code="EXECUTION_POLICY_LIVE_DEMO_ALLOWED",
            action=normalized_action,
            execution_mode=execution_mode,
            market_type=market_type,
            risk_reducing=is_exit or is_cancel,
            order_test=is_order_test,
            live_real_requires_armed=False,
            live_real_requires_double_confirm=False,
        )

    if execution_mode == ExecutionMode.LIVE_REAL.value:
        if market_type != MarketType.SPOT_MAINNET.value:
            _deny(
                "EXECUTION_POLICY_LIVE_REAL_ENVIRONMENT_INVALID",
                "live_real order actions require spot_mainnet market_type",
                action=normalized_action,
                settings=settings,
            )
        if is_entry or is_order_test:
            if not bool(settings.live_trading_armed):
                _deny(
                    "EXECUTION_POLICY_LIVE_REAL_NOT_ARMED",
                    "live_real new-risk entry/order-test requires live_trading_armed=True",
                    action=normalized_action,
                    settings=settings,
                )
            if not bool(settings.live_real_double_confirm):
                _deny(
                    "EXECUTION_POLICY_LIVE_REAL_DOUBLE_CONFIRM_MISSING",
                    "live_real new-risk entry/order-test requires live_real_double_confirm=True",
                    action=normalized_action,
                    settings=settings,
                )
        return ExecutionPolicyDecision(
            allowed=True,
            reason_code=(
                "EXECUTION_POLICY_LIVE_REAL_NEW_RISK_ALLOWED"
                if is_entry or is_order_test
                else "EXECUTION_POLICY_LIVE_REAL_RISK_REDUCING_ALLOWED"
            ),
            action=normalized_action,
            execution_mode=execution_mode,
            market_type=market_type,
            risk_reducing=is_exit or is_cancel,
            order_test=is_order_test,
            live_real_requires_armed=is_entry or is_order_test,
            live_real_requires_double_confirm=is_entry or is_order_test,
        )

    _deny(
        "EXECUTION_POLICY_PROFILE_UNSAFE",
        "Execution profile is not safe for exchange order action",
        action=normalized_action,
        settings=settings,
    )


def enforce_execution_policy(
    settings: Settings,
    endpoint_profile: BinanceEndpointProfile,
    *,
    action: str,
) -> ExecutionPolicyDecision:
    return evaluate_execution_policy(settings, endpoint_profile, action=action)


def build_execution_policy_snapshot(settings: Settings, endpoint_profile: BinanceEndpointProfile) -> dict[str, object]:
    snapshot: dict[str, Any] = {
        "policy_version": EXECUTION_POLICY_GATE_VERSION,
        "exchange_level_fail_closed": True,
        "unknown_action_deny": True,
        "execution_mode": settings.execution_mode,
        "market_type": settings.market_type,
        "endpoint_environment": binance_environment_snapshot(endpoint_profile, configured_rest_base_url=settings.base_url),
        "actions": {},
    }
    actions: dict[str, object] = {}
    for action in ExecutionPolicyAction:
        try:
            decision = evaluate_execution_policy(settings, endpoint_profile, action=action.value)
            actions[action.value] = decision.to_snapshot()
        except ExecutionPolicyError as error:
            actions[action.value] = error.to_snapshot()
    snapshot["actions"] = actions
    snapshot["entry_new_risk_allowed"] = bool(actions[ExecutionPolicyAction.ENTRY_NEW_RISK.value].get("allowed"))
    snapshot["risk_reducing_exit_allowed"] = bool(actions[ExecutionPolicyAction.EXIT_RISK_REDUCING.value].get("allowed"))
    snapshot["cancel_pending_allowed"] = bool(actions[ExecutionPolicyAction.CANCEL_PENDING.value].get("allowed"))
    snapshot["order_test_allowed"] = bool(actions[ExecutionPolicyAction.ORDER_TEST.value].get("allowed"))
    return snapshot
