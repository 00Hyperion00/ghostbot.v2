from __future__ import annotations

import json
from pathlib import Path

import pytest

from tradebot.operator_cockpit_v2_desktop_wrapper import (
    DesktopWrapperError,
    _dashboard_origin,
    _read_bounded_local_get,
    start_local_cockpit_server,
)

NATIVE_EXPORT_FIXTURE_HOTFIX_VERSION = "4B.4.3.6.6.26D-H2-H1"
NATIVE_EXPORT_FIXTURE_LEDGER_SEED = True
NATIVE_EXPORT_DETERMINISTIC_404_CONTRACT = True


def _seed_minimal_isolated_r1_ledger(project_root: Path) -> Path:
    """Seed one deterministic isolated-R1 merged-ledger row used by native-export integration tests."""
    reports_dir = project_root / "reports" / "hyp005_r1_isolated"
    reports_dir.mkdir(parents=True, exist_ok=True)
    ledger = reports_dir / "4B436625X_hyp005_shadow_merged_ledger_20260608_120000.jsonl"
    ledger.write_text(
        json.dumps(
            {
                "symbol": "BTCUSDT",
                "timestamp_utc": "2026-06-08T12:00:00+00:00",
                "observation_id": "HYP-005-BTCUSDT-4h-fixture-20260608T120000Z",
                "spread_slippage_proxy_bps": 4.25,
                "forward_return_bps_final": 12.5,
                "mae_bps": -18.0,
                "mfe_bps": 31.0,
            },
            ensure_ascii=False,
        ) + "\n",
        encoding="utf-8",
    )
    return ledger


def test_26dh2h1_declares_fixture_seed_and_deterministic_404_contract() -> None:
    assert NATIVE_EXPORT_FIXTURE_HOTFIX_VERSION == "4B.4.3.6.6.26D-H2-H1"
    assert NATIVE_EXPORT_FIXTURE_LEDGER_SEED is True
    assert NATIVE_EXPORT_DETERMINISTIC_404_CONTRACT is True


def test_26dh2h1_seeded_fixture_returns_latest_ledger_200_and_contains_btcusdt(tmp_path: Path) -> None:
    ledger = _seed_minimal_isolated_r1_ledger(tmp_path)
    assert ledger.exists()
    running = start_local_cockpit_server(tmp_path, port=0)
    try:
        origin = _dashboard_origin(running.url)
        payload = _read_bounded_local_get(origin, "/api/operator-cockpit-v2/export/latest-ledger", 1024, 2.0)
        assert b"BTCUSDT" in payload
        assert b"HYP-005-BTCUSDT" in payload
    finally:
        running.stop()


def test_26dh2h1_missing_ledger_contract_is_deterministic_404(tmp_path: Path) -> None:
    running = start_local_cockpit_server(tmp_path, port=0)
    try:
        origin = _dashboard_origin(running.url)
        with pytest.raises(DesktopWrapperError, match=r"NATIVE_DESKTOP_EXPORT_HTTP_ERROR: 404"):
            _read_bounded_local_get(origin, "/api/operator-cockpit-v2/export/latest-ledger", 1024, 2.0)
    finally:
        running.stop()


def test_26dh2h1_evidence_pack_size_limit_remains_deterministic_with_seeded_ledger(tmp_path: Path) -> None:
    _seed_minimal_isolated_r1_ledger(tmp_path)
    running = start_local_cockpit_server(tmp_path, port=0)
    try:
        origin = _dashboard_origin(running.url)
        with pytest.raises(DesktopWrapperError, match="NATIVE_DESKTOP_EXPORT_TOO_LARGE"):
            _read_bounded_local_get(origin, "/api/operator-cockpit-v2/export/evidence-pack.zip", 2, 2.0)
    finally:
        running.stop()


def test_26dh2h1_external_endpoint_remains_fail_closed_before_network_access(tmp_path: Path) -> None:
    _seed_minimal_isolated_r1_ledger(tmp_path)
    running = start_local_cockpit_server(tmp_path, port=0)
    try:
        origin = _dashboard_origin(running.url)
        with pytest.raises(DesktopWrapperError, match="NATIVE_DESKTOP_EXPORT_ENDPOINT_NOT_ALLOWED"):
            _read_bounded_local_get(origin, "https://example.com/file", 1024, 2.0)
    finally:
        running.stop()
