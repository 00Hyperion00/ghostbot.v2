from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

HYP005_R1_CANONICAL_EPOCH_HARDENING_VERSION = "4B.4.3.6.6.25AE-H5"
HYP005_R1_CANONICAL_EPOCH_SCHEDULER = True
HYP005_R1_UTC_ARTIFACT_STAMP = True
HYP005_R1_25W_SOURCE_ATTRIBUTION = True
HYP005_R1_DASHBOARD_SOURCE_ALIGNMENT = True
HYP005_R1_CANONICAL_FAIL_CLOSED_DAG = True

LEGACY_R1_REPORTS_DIR = Path("reports") / "hyp005_r1_isolated"
CANONICAL_R1_REPORTS_DIR = Path("reports") / "hyp005_r1_canonical"
BASELINE_TASK_NAME = "TradeBot_HYP005_NoOrderShadowCollection"
LEGACY_R1_TASK_NAME = "TradeBot_HYP005_R1_NoOrderShadowCollection"
CANONICAL_R1_TASK_NAME = "TradeBot_HYP005_R1_Canonical_NoOrderShadowCollection"
CANONICAL_SYMBOLS_ARG = "ADAUSDT,BNBUSDT,BTCUSDT,ETHUSDT,LINKUSDT,LTCUSDT,SOLUSDT,XRPUSDT"

UTC_ARTIFACT_STAMP_PATTERN = re.compile(r"^[0-9]{8}_[0-9]{6}Z$")
UTC_ARTIFACT_NAME_PATTERN = re.compile(r"_[0-9]{8}_[0-9]{6}Z(?:\.[^.]+)+$")


def utc_artifact_stamp() -> str:
    """Return a filename-safe UTC timestamp with an explicit Z suffix."""
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%SZ")


def is_utc_artifact_stamp(value: str) -> bool:
    return bool(UTC_ARTIFACT_STAMP_PATTERN.fullmatch(str(value)))


def is_utc_artifact_filename(value: str | Path) -> bool:
    return bool(UTC_ARTIFACT_NAME_PATTERN.search(Path(value).name))


def resolve_active_reports_dir(project_root: Path) -> Path:
    """Prefer canonical epoch data; retain legacy fallback only for pre-H5 fixtures."""
    root = project_root.resolve()
    canonical = (root / CANONICAL_R1_REPORTS_DIR).resolve()
    if canonical.exists():
        return canonical
    return (root / LEGACY_R1_REPORTS_DIR).resolve()
