from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Mapping

AI_DECISION_CONTRACT_VERSION = "4B.4.3.6.6.27E"
DEFAULT_THRESHOLD_PROFILE = "runtime_settings"


class AIDecisionContractError(ValueError):
    """Fail-closed decision contract validation error."""


@dataclass(frozen=True, slots=True)
class AIDecisionContract:
    threshold: float = 0.60
    buy_threshold: float = 0.64
    sell_threshold: float = 0.57
    hold_band_low: float = 0.45
    hold_band_high: float = 0.55
    indecision_margin: float = 0.08
    threshold_profile: str = DEFAULT_THRESHOLD_PROFILE

    def validate(self) -> "AIDecisionContract":
        for field_name in (
            "threshold",
            "buy_threshold",
            "sell_threshold",
            "hold_band_low",
            "hold_band_high",
            "indecision_margin",
        ):
            value = float(getattr(self, field_name))
            if not 0.0 <= value <= 1.0:
                raise AIDecisionContractError(f"MODEL_THRESHOLD_CONFIG_INVALID:{field_name}")
        if float(self.hold_band_low) > float(self.hold_band_high):
            raise AIDecisionContractError("MODEL_THRESHOLD_HOLD_BAND_INVALID")
        if not str(self.threshold_profile or "").strip():
            raise AIDecisionContractError("MODEL_THRESHOLD_PROFILE_MISSING")
        return self

    def threshold_kwargs(self) -> dict[str, float | str]:
        return {
            "threshold": float(self.threshold),
            "buy_threshold": float(self.buy_threshold),
            "sell_threshold": float(self.sell_threshold),
            "hold_band_low": float(self.hold_band_low),
            "hold_band_high": float(self.hold_band_high),
            "indecision_margin": float(self.indecision_margin),
            "threshold_profile": str(self.threshold_profile),
        }

    def snapshot(self) -> dict[str, Any]:
        payload = self.threshold_kwargs()
        payload["contract_version"] = AI_DECISION_CONTRACT_VERSION
        payload["fingerprint"] = self.fingerprint()
        return payload

    def fingerprint(self) -> str:
        encoded = json.dumps(self.threshold_kwargs(), ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


def build_decision_contract(
    *,
    threshold: float | None = None,
    buy_threshold: float | None = None,
    sell_threshold: float | None = None,
    hold_band_low: float | None = None,
    hold_band_high: float | None = None,
    indecision_margin: float | None = None,
    threshold_profile: str | None = None,
    fallback: AIDecisionContract | None = None,
) -> AIDecisionContract:
    base = fallback or AIDecisionContract()
    return AIDecisionContract(
        threshold=float(base.threshold if threshold is None else threshold),
        buy_threshold=float(base.buy_threshold if buy_threshold is None else buy_threshold),
        sell_threshold=float(base.sell_threshold if sell_threshold is None else sell_threshold),
        hold_band_low=float(base.hold_band_low if hold_band_low is None else hold_band_low),
        hold_band_high=float(base.hold_band_high if hold_band_high is None else hold_band_high),
        indecision_margin=float(base.indecision_margin if indecision_margin is None else indecision_margin),
        threshold_profile=str(base.threshold_profile if threshold_profile is None else threshold_profile),
    ).validate()


def decision_contract_from_settings(settings: Any) -> AIDecisionContract:
    return build_decision_contract(
        threshold=getattr(settings, "ai_confidence_threshold", 0.60),
        buy_threshold=getattr(settings, "ai_buy_threshold", 0.64),
        sell_threshold=getattr(settings, "ai_sell_threshold", 0.57),
        hold_band_low=getattr(settings, "ai_hold_band_low", 0.45),
        hold_band_high=getattr(settings, "ai_hold_band_high", 0.55),
        indecision_margin=getattr(settings, "ai_indecision_margin", 0.08),
        threshold_profile=getattr(settings, "ai_threshold_profile", DEFAULT_THRESHOLD_PROFILE),
    )


def decision_contract_from_provider(provider: Any) -> AIDecisionContract:
    return build_decision_contract(
        threshold=getattr(provider, "threshold", 0.60),
        buy_threshold=getattr(provider, "buy_threshold", 0.64),
        sell_threshold=getattr(provider, "sell_threshold", 0.57),
        hold_band_low=getattr(provider, "hold_band_low", 0.45),
        hold_band_high=getattr(provider, "hold_band_high", 0.55),
        indecision_margin=getattr(provider, "indecision_margin", 0.08),
        threshold_profile=getattr(provider, "threshold_profile", DEFAULT_THRESHOLD_PROFILE),
    )


def decision_contract_from_payload(payload: Any, *, fallback: AIDecisionContract) -> AIDecisionContract:
    return build_decision_contract(
        threshold=getattr(payload, "threshold", None),
        buy_threshold=getattr(payload, "buy_threshold", None),
        sell_threshold=getattr(payload, "sell_threshold", None),
        hold_band_low=getattr(payload, "hold_band_low", None),
        hold_band_high=getattr(payload, "hold_band_high", None),
        indecision_margin=getattr(payload, "indecision_margin", None),
        threshold_profile=getattr(payload, "threshold_profile", None),
        fallback=fallback,
    )


def decision_contracts_match(left: AIDecisionContract, right: AIDecisionContract) -> bool:
    return left.threshold_kwargs() == right.threshold_kwargs()


def assert_startup_reload_parity(expected: AIDecisionContract, requested: AIDecisionContract) -> None:
    if not decision_contracts_match(expected, requested):
        raise AIDecisionContractError("MODEL_THRESHOLD_STARTUP_RELOAD_MISMATCH")


def decision_contract_diff(expected: AIDecisionContract, requested: AIDecisionContract) -> dict[str, dict[str, Any]]:
    left = expected.threshold_kwargs()
    right = requested.threshold_kwargs()
    return {
        key: {"startup": left[key], "reload": right[key]}
        for key in sorted(left)
        if left[key] != right[key]
    }
