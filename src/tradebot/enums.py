from __future__ import annotations

from enum import Enum


class BotState(str, Enum):
    STOPPED = "STOPPED"
    FLAT = "FLAT"
    BUY_PENDING = "BUY_PENDING"
    IN_POSITION = "IN_POSITION"
    SELL_PENDING = "SELL_PENDING"
    SAFE_MODE = "SAFE_MODE"


class ExecutionMode(str, Enum):
    DRY_RUN = "dry_run"
    LIVE_DEMO = "live_demo"
    LIVE_REAL = "live_real"


class MarketType(str, Enum):
    SPOT_DEMO = "spot_demo"
    SPOT_TESTNET = "spot_testnet"
    SPOT_MAINNET = "spot_mainnet"


class SignalType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class AutoSignalMode(str, Enum):
    NORMAL = "normal"
    RELAXED = "relaxed"
    TEST_BUY_ONCE = "test_buy_once"
    TEST_SELL_ONCE = "test_sell_once"


class LogLevel(str, Enum):
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
