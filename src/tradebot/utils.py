from __future__ import annotations

import hashlib
import json
import math
import time
from decimal import Decimal, ROUND_DOWN
from typing import Any


def utc_ms() -> int:
    return int(time.time() * 1000)


def round_down_to_step(value: float, step: float) -> float:
    if step <= 0:
        return float(value)
    d_value = Decimal(str(value))
    d_step = Decimal(str(step))
    return float((d_value / d_step).to_integral_value(rounding=ROUND_DOWN) * d_step)


def round_price_to_tick(price: float, tick: float) -> float:
    return round_down_to_step(price, tick)


def stable_hash(payload: Any, length: int = 6) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha1(raw.encode('utf-8')).hexdigest()[:length]


def is_effective_zero(value: float, step_size: float) -> bool:
    threshold = max(step_size * 0.999, 1e-12)
    return abs(value) < threshold


def infer_dust(free_base: float, step_size: float) -> float:
    if free_base <= 0:
        return 0.0
    tradable = round_down_to_step(free_base, step_size)
    dust = max(0.0, free_base - tradable)
    if tradable <= 0:
        return free_base
    return dust


def ratio(a: float | None, b: float | None) -> float | None:
    if a is None or b is None or b == 0:
        return None
    return a / b
