from __future__ import annotations

import json
import re
import subprocess
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from tradebot.operator_cockpit_v2_read_only import (
    DASHBOARD_HTML,
    OPERATOR_COCKPIT_V2_ACCURATE_MAE_MFE_EMPTY_STATE,
    OPERATOR_COCKPIT_V2_MAE_MFE_SCATTER_HOTFIX_VERSION,
    OPERATOR_COCKPIT_V2_READ_ONLY,
    OPERATOR_COCKPIT_V2_SIGNED_MAE_MFE_DOMAIN,
    collect_operator_cockpit_snapshot,
    make_operator_cockpit_server,
)


def _observation(
    symbol: str,
    timestamp: str,
    result: float | None,
    slippage: float,
    *,
    mae: float | None,
    mfe: float | None,
) -> dict[str, object]:
    return {
        "symbol": symbol,
        "timestamp_utc": timestamp,
        "observation_id": f"HYP-005-{symbol}-{timestamp}",
        "forward_return_bps_final": result,
        "spread_slippage_proxy_bps": slippage,
        "mae_bps": mae,
        "mfe_bps": mfe,
    }


def _task_query(name: str) -> dict[str, object]:
    if "R1" in name:
        return {"task_name": name, "state": "Ready", "last_task_result": 0, "number_of_missed_runs": 0}
    return {"task_name": name, "state": "Disabled", "last_task_result": 0, "number_of_missed_runs": 0}


def _backend_probe(_: str) -> dict[str, object]:
    return {"reachable": True, "status_code": 200, "payload": {"ok": True}}


def _fixture_root(tmp_path: Path) -> Path:
    root = tmp_path / "trade_botV2"
    reports = root / "reports" / "hyp005_r1_isolated"
    reports.mkdir(parents=True)
    rows = [
        _observation("ADAUSDT", "2026-05-16T08:00:00+00:00", 98.38, 5.5, mae=-55.09, mfe=161.35),
        _observation("XRPUSDT", "2026-05-17T20:00:00+00:00", -82.76, 6.7, mae=-269.69, mfe=7.85),
        _observation("ETHUSDT", "2026-05-23T00:00:00+00:00", 233.05, 4.8, mae=-296.89, mfe=382.32),
    ]
    (reports / "4B436625X_hyp005_shadow_merged_ledger_20260606_120000.jsonl").write_text(
        "\n".join(json.dumps(row) for row in rows), encoding="utf-8"
    )
    (reports / "4B436625V_hyp005_shadow_observation_logger_20260606_120000.json").write_text(
        json.dumps({"decision": "HYP005_SHADOW_OBSERVATION_LOGGER_READY"}), encoding="utf-8"
    )
    (reports / "4B436625X_hyp005_shadow_collection_orchestrator_20260606_120000.json").write_text(
        json.dumps({"decision": "HYP005_SHADOW_COLLECTION_ORCHESTRATOR_READY"}), encoding="utf-8"
    )
    (reports / "4B436625Y_hyp005_shadow_operator_daily_audit_20260606_120000.json").write_text(
        json.dumps(
            {
                "decision": "HYP005_SHADOW_OPERATOR_AUDIT_READY",
                "dashboard_status": "SHADOW_COLLECTION_IN_PROGRESS",
                "latest_logger_decision": "HYP005_SHADOW_OBSERVATION_LOGGER_READY",
                "latest_collection_decision": "HYP005_SHADOW_COLLECTION_ORCHESTRATOR_READY",
                "latest_acceptance_decision": "HYP005_SHADOW_PAPER_TRANSITION_BLOCK",
                "shadow_observation_count": len(rows),
                "shadow_sample_target": 30,
                "progress_pct": round((len(rows) / 30) * 100, 6),
                "paper_transition_ready": False,
                "approved_for_live_real": False,
                "post_requests_allowed": False,
                "order_actions_performed": False,
                "source_ledgers": 1,
                "source_reports": 3,
            }
        ),
        encoding="utf-8",
    )
    return root


def _dashboard_script_prefix() -> str:
    matched = re.search(r"<script>(.*?)</script>", DASHBOARD_HTML, flags=re.DOTALL)
    assert matched is not None
    script = matched.group(1)
    marker = "$('refresh').addEventListener"
    assert marker in script
    return script.split(marker, 1)[0]


def _run_scatter_renderer(data: list[dict[str, object]]) -> dict[str, object]:
    data_json = json.dumps(data, ensure_ascii=False)
    node_script = _dashboard_script_prefix() + f"""
const document={{elements:{{}},getElementById(id){{if(!this.elements[id])this.elements[id]={{innerHTML:''}};return this.elements[id]}}}};
scatterChart('mae-mfe-chart',{data_json},'mae_bps','mfe_bps');
const html=document.elements['mae-mfe-chart'].innerHTML;
const circles=[...html.matchAll(/<circle class=\"scatter\" cx=\"([^\"]+)\" cy=\"([^\"]+)\"/g)].map(match=>({{cx:Number(match[1]),cy:Number(match[2])}}));
console.log(JSON.stringify({{html,circles}}));
"""
    completed = subprocess.run(
        ["node", "-e", node_script],
        text=True,
        encoding="utf-8",
        errors="strict",
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def test_26bh1_declares_signed_domain_and_accurate_empty_state_without_weakening_read_only() -> None:
    assert OPERATOR_COCKPIT_V2_MAE_MFE_SCATTER_HOTFIX_VERSION == "4B.4.3.6.6.26B-H1"
    assert OPERATOR_COCKPIT_V2_SIGNED_MAE_MFE_DOMAIN is True
    assert OPERATOR_COCKPIT_V2_ACCURATE_MAE_MFE_EMPTY_STATE is True
    assert OPERATOR_COCKPIT_V2_READ_ONLY is True


def test_26bh1_snapshot_preserves_negative_mae_and_positive_mfe_values(tmp_path: Path) -> None:
    snapshot = collect_operator_cockpit_snapshot(_fixture_root(tmp_path), task_query=_task_query, backend_probe=_backend_probe)
    scatter = snapshot["visualizations"]["mae_mfe_scatter"]
    assert len(scatter) == 3
    assert min(point["mae_bps"] for point in scatter) == -296.89
    assert max(point["mfe_bps"] for point in scatter) == 382.32
    assert all(point["mae_bps"] < 0 for point in scatter)


def test_26bh1_dashboard_html_contains_signed_scaler_tooltip_and_accurate_empty_state() -> None:
    assert "function signedDomain(values)" in DASHBOARD_HTML
    assert "function scaleSigned(value,domain,start,end)" in DASHBOARD_HTML
    assert "MAE / MFE verisi henüz oluşmadı." in DASHBOARD_HTML
    assert "Final Edge ${fmt(record.forward_return_bps_final,2)}" in DASHBOARD_HTML
    assert "26B-H1 · READ ONLY" in DASHBOARD_HTML


def test_26bh1_node_scatter_renderer_keeps_signed_mae_points_inside_canvas() -> None:
    rendered = _run_scatter_renderer(
        [
            {"symbol": "ADAUSDT", "timestamp_utc": "2026-05-16T08:00:00+00:00", "mae_bps": -55.09, "mfe_bps": 161.35, "forward_return_bps_final": 98.38},
            {"symbol": "XRPUSDT", "timestamp_utc": "2026-05-17T20:00:00+00:00", "mae_bps": -269.69, "mfe_bps": 7.85, "forward_return_bps_final": -82.76},
            {"symbol": "ETHUSDT", "timestamp_utc": "2026-05-23T00:00:00+00:00", "mae_bps": -296.89, "mfe_bps": 382.32, "forward_return_bps_final": 233.05},
        ]
    )
    circles = rendered["circles"]
    assert len(circles) == 3
    assert all(58 <= point["cx"] <= 730 for point in circles)
    assert all(28 <= point["cy"] <= 176 for point in circles)
    html = str(rendered["html"])
    assert "2026-05-23T00:00:00+00:00" in html
    assert "Final Edge" in html


def test_26bh1_node_scatter_renderer_shows_accurate_empty_state() -> None:
    rendered = _run_scatter_renderer([])
    assert rendered["circles"] == []
    assert "MAE / MFE verisi henüz oluşmadı." in str(rendered["html"])


def test_26bh1_http_snapshot_remains_read_only_and_mutation_blocked(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path)
    server = make_operator_cockpit_server(root, port=0, task_query=_task_query, backend_probe=_backend_probe)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    try:
        with urllib.request.urlopen(f"http://{host}:{port}/api/operator-cockpit-v2/snapshot", timeout=3) as response:
            payload = json.loads(response.read().decode("utf-8"))
            assert payload["read_only"] is True
            assert len(payload["visualizations"]["mae_mfe_scatter"]) == 3
        request = urllib.request.Request(
            f"http://{host}:{port}/api/operator-cockpit-v2/snapshot", data=b"{}", method="POST"
        )
        with pytest.raises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(request, timeout=3)
        assert caught.value.code == 405
        blocked = json.loads(caught.value.read().decode("utf-8"))
        assert blocked["error"] == "READ_ONLY_DASHBOARD_MUTATION_BLOCKED"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
