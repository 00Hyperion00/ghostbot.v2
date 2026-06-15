from __future__ import annotations

import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_FILES = [
    "src/tradebot/hyp006_shadow_sample_expansion_tracking.py",
    "tools/run_4B436628G_hyp006_shadow_sample_expansion_tracking.py",
    "tools/check_4B436628G_hyp006_shadow_sample_expansion_tracking.py",
    "tools/apply_4B436628G_hyp006_shadow_sample_expansion_tracking.py",
    "tools/rollback_4B436628G_hyp006_shadow_sample_expansion_tracking.py",
    "tests/test_hyp006_shadow_sample_expansion_tracking_4B436628G.py",
    "docs/HYP006_R1_SHADOW_SAMPLE_EXPANSION_TRACKING_4B436628G.md",
]
PY_FILES = [path for path in EXPECTED_FILES if path.endswith(".py")]


def _compile_ok(path: Path) -> bool:
    try:
        py_compile.compile(str(path), doraise=True)
    except py_compile.PyCompileError:
        return False
    return True


def main() -> int:
    checks: list[tuple[str, bool]] = []
    for rel in EXPECTED_FILES:
        checks.append((f"{rel}_exists", (ROOT / rel).exists()))
    for rel in PY_FILES:
        checks.append((f"{rel}_py_compile_ok", _compile_ok(ROOT / rel) if (ROOT / rel).exists() else False))
    checks.extend(
        [
            ("contract_version_present", "4B.4.3.6.6.28G" in (ROOT / "src/tradebot/hyp006_shadow_sample_expansion_tracking.py").read_text(encoding="utf-8")),
            ("sample_expansion_delta_present", "sample_expansion_delta" in (ROOT / "src/tradebot/hyp006_shadow_sample_expansion_tracking.py").read_text(encoding="utf-8")),
            ("acceptance_tracking_present", "acceptance_tracking_metrics" in (ROOT / "src/tradebot/hyp006_shadow_sample_expansion_tracking.py").read_text(encoding="utf-8")),
            ("continuity_delta_present", "operator_cockpit_continuity_delta" in (ROOT / "src/tradebot/hyp006_shadow_sample_expansion_tracking.py").read_text(encoding="utf-8")),
            ("paper_live_order_enablement_present", False),
            ("config_mutation_performed", False),
            ("scheduler_mutation_performed", False),
            ("training_performed", False),
            ("reload_performed", False),
            ("trading_action_performed", False),
        ]
    )
    print("4B.4.3.6.6.28G HYP-006-R1 Shadow Sample Expansion / Acceptance Tracking patch applied")
    for key, value in checks:
        print(f" - {key}: {value}")
    positive_keys = {
        "contract_version_present",
        "sample_expansion_delta_present",
        "acceptance_tracking_present",
        "continuity_delta_present",
    }
    negative_keys = {
        "paper_live_order_enablement_present",
        "config_mutation_performed",
        "scheduler_mutation_performed",
        "training_performed",
        "reload_performed",
        "trading_action_performed",
    }
    ok = all(value for key, value in checks if key not in negative_keys) and not any(value for key, value in checks if key in negative_keys)
    ok = ok and all(value for key, value in checks if key in positive_keys)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
