from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Mapping, Sequence

OPERATOR_COCKPIT_HYP006_VISUALIZATION_EXPORT_GUARD_HOTFIX_VERSION = "4B.4.3.6.6.28F-H4"
RISK_SIZING_EXPORT_UNAVAILABLE_REASON = "RISK_SIZING_RUNTIME_EVENT_NOT_FOUND"
RISK_SIZING_EXPORT_OPERATOR_MESSAGE = (
    "Risk-sizing evidence yok: HYP-006 no-order shadow akışı risk-sizing runtime event üretmedi; "
    "paper/live/order kapalı."
)
HYP006_AUDIT_SOURCE_LABELS: dict[str, str] = {
    "hyp006_reports_dir": "HYP-006 canonical reports dir",
    "latest_28g_tracking": "28G sample expansion tracking",
    "latest_28f_baseline": "28F operator cockpit baseline",
    "latest_28f_dashboard_seed": "28F dashboard seed",
    "latest_28e_health": "28E scheduler execution health",
    "latest_hyp006_ledger": "HYP-006 no-order shadow ledger",
}
LEGACY_HYP005_SOURCE_KEYS = frozenset({
    "latest_25v_logger",
    "latest_25x_collection",
    "latest_25y_audit",
    "latest_merged_ledger",
    "r1_reports_dir",
})


def _as_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(parsed) or math.isinf(parsed):
        return None
    return parsed


def _return_bps(row: Mapping[str, Any]) -> float | None:
    for key in ("forward_return_bps_final_short_probe", "forward_return_bps_final", "forward_return_bps"):
        value = _as_float(row.get(key))
        if value is not None:
            return value
    return None


def sanitize_hyp006_audit_sources(sources: Mapping[str, Any]) -> dict[str, Any]:
    """Expose only active HYP-006 sources in the audit source panel.

    Legacy HYP-005 paths are intentionally suppressed from the visible active-source map.
    This does not delete files and does not mutate reports; it only normalizes cockpit display parity.
    """
    cleaned: dict[str, Any] = {}
    for key, value in sources.items():
        if key in LEGACY_HYP005_SOURCE_KEYS:
            continue
        if isinstance(value, str) and "hyp005_r1_canonical" in value.replace("\\", "/"):
            continue
        cleaned[key] = value
    cleaned["active_source_labels"] = {
        key: HYP006_AUDIT_SOURCE_LABELS[key]
        for key in HYP006_AUDIT_SOURCE_LABELS
        if key in cleaned and cleaned.get(key) is not None
    }
    cleaned["legacy_hyp005_active_sources_suppressed"] = True
    cleaned["source_label_contract_version"] = OPERATOR_COCKPIT_HYP006_VISUALIZATION_EXPORT_GUARD_HOTFIX_VERSION
    return cleaned


def build_hyp006_mae_mfe_proxy_scatter(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Build a no-order visual proxy when true execution MAE/MFE is unavailable.

    HYP-006-R1 currently records shadow forward edge, not exchange execution path. For operator
    visibility the proxy keeps negative final edge on the MAE axis and positive final edge on the
    MFE axis, explicitly marked as proxy data.
    """
    output: list[dict[str, Any]] = []
    for row in rows:
        ret = _return_bps(row)
        if ret is None:
            continue
        true_mae = _as_float(row.get("mae_bps") or row.get("max_adverse_excursion_bps"))
        true_mfe = _as_float(row.get("mfe_bps") or row.get("max_favorable_excursion_bps"))
        if true_mae is not None and true_mfe is not None:
            mae = true_mae
            mfe = true_mfe
            proxy = False
            note = "Ledger-provided MAE/MFE."
        else:
            mae = min(ret, 0.0)
            mfe = max(ret, 0.0)
            proxy = True
            note = "Proxy from final no-order forward edge; true execution MAE/MFE not collected."
        output.append({
            "symbol": row.get("symbol"),
            "timestamp_utc": row.get("timestamp_utc"),
            "observation_id": row.get("observation_id"),
            "mae_bps": round(mae, 6),
            "mfe_bps": round(mfe, 6),
            "forward_return_bps_final": round(ret, 6),
            "proxy": proxy,
            "proxy_note": note,
        })
    return output


def apply_risk_sizing_export_guard(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    """Mark risk-sizing evidence export as intentionally unavailable for no-order HYP-006."""
    result = dict(snapshot)
    gate = dict(result.get("risk_sizing_evidence_export_gate") or {})
    gate.update({
        "available": False,
        "fail_closed": True,
        "reason": RISK_SIZING_EXPORT_UNAVAILABLE_REASON,
        "operator_message": RISK_SIZING_EXPORT_OPERATOR_MESSAGE,
        "contract_version": OPERATOR_COCKPIT_HYP006_VISUALIZATION_EXPORT_GUARD_HOTFIX_VERSION,
    })
    blockers = list(gate.get("blockers") or [])
    if RISK_SIZING_EXPORT_UNAVAILABLE_REASON not in blockers:
        blockers.append(RISK_SIZING_EXPORT_UNAVAILABLE_REASON)
    gate["blockers"] = blockers
    result["risk_sizing_evidence_export_gate"] = gate

    actions = dict(result.get("safe_operator_actions") or {})
    locked = list(actions.get("locked") or [])
    if not any(isinstance(item, Mapping) and item.get("code") == "DOWNLOAD_RISK_SIZING_EVIDENCE_PACK_ZIP" for item in locked):
        locked.append({
            "code": "DOWNLOAD_RISK_SIZING_EVIDENCE_PACK_ZIP",
            "label": "Risk-sizing evidence ZIP",
            "reason": RISK_SIZING_EXPORT_OPERATOR_MESSAGE,
        })
    actions["locked"] = locked
    actions["risk_sizing_evidence_export_gate"] = gate
    actions["visualization_export_guard_version"] = OPERATOR_COCKPIT_HYP006_VISUALIZATION_EXPORT_GUARD_HOTFIX_VERSION
    result["safe_operator_actions"] = actions
    return result


def visualization_parity_ok(snapshot: Mapping[str, Any]) -> bool:
    sources = snapshot.get("sources")
    if not isinstance(sources, Mapping):
        return False
    source_text = str(sources)
    if "hyp005_r1_canonical" in source_text or any(key in sources for key in LEGACY_HYP005_SOURCE_KEYS):
        return False
    visuals = snapshot.get("visualizations")
    if not isinstance(visuals, Mapping):
        return False
    timeline = visuals.get("sample_timeline")
    scatter = visuals.get("mae_mfe_scatter")
    if not isinstance(timeline, list) or not timeline:
        return False
    if not all(isinstance(row, Mapping) and "cumulative_samples" in row for row in timeline):
        return False
    if not isinstance(scatter, list) or not scatter:
        return False
    gate = snapshot.get("risk_sizing_evidence_export_gate")
    if not isinstance(gate, Mapping):
        return False
    return gate.get("available") is False and RISK_SIZING_EXPORT_UNAVAILABLE_REASON in list(gate.get("blockers") or [])
