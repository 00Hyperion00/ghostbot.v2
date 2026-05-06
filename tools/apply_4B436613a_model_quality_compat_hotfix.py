from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "src" / "tradebot" / "config.py"
RUNTIME_OBS_TEST_PATH = ROOT / "tests" / "test_runtime_observability_event_audit.py"


def ensure_position_max_hold_sec() -> dict[str, object]:
    text = CONFIG_PATH.read_text(encoding="utf-8")
    added = False
    if "position_max_hold_sec" not in text:
        marker = "    max_daily_trades: int = 0\n"
        if marker not in text:
            raise RuntimeError("Cannot find max_daily_trades anchor in config.py")
        text = text.replace(marker, marker + "    position_max_hold_sec: int = 0\n", 1)
        CONFIG_PATH.write_text(text, encoding="utf-8")
        added = True
    return {
        "exists": CONFIG_PATH.exists(),
        "position_max_hold_sec_present": "position_max_hold_sec" in CONFIG_PATH.read_text(encoding="utf-8"),
        "added": added,
    }


def patch_runtime_observability_test() -> dict[str, object]:
    if not RUNTIME_OBS_TEST_PATH.exists():
        return {"exists": False, "replacements": 0, "remaining_old_status_assert": 0}
    text = RUNTIME_OBS_TEST_PATH.read_text(encoding="utf-8")
    old_single = "assert status['contract_version'] == '4B.4.3.6.6.12'"
    new_single = "assert status['contract_version'] == '4B.4.3.6.6.13'"
    old_double = 'assert status["contract_version"] == "4B.4.3.6.6.12"'
    new_double = 'assert status["contract_version"] == "4B.4.3.6.6.13"'
    replacements = text.count(old_single) + text.count(old_double)
    text = text.replace(old_single, new_single).replace(old_double, new_double)
    RUNTIME_OBS_TEST_PATH.write_text(text, encoding="utf-8")
    updated = RUNTIME_OBS_TEST_PATH.read_text(encoding="utf-8")
    return {
        "exists": True,
        "replacements": replacements,
        "remaining_old_status_assert": updated.count(old_single) + updated.count(old_double),
        "new_status_assert_present": (new_single in updated) or (new_double in updated),
    }


def main() -> int:
    config_report = ensure_position_max_hold_sec()
    test_report = patch_runtime_observability_test()
    if not config_report["position_max_hold_sec_present"]:
        raise RuntimeError("position_max_hold_sec was not applied to config.py")
    if test_report["exists"] and test_report["remaining_old_status_assert"] != 0:
        raise RuntimeError("Old 4B.4.3.6.6.12 status contract assertion remains")
    print("4B.4.3.6.6.13a model quality compatibility hotfix applied")
    print(f" - config: {config_report}")
    print(f" - runtime_observability_test: {test_report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
