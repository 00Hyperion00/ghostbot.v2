from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

CONTRACT_VERSION = "4B.4.3.6.6.30C"
PAYLOAD_DIR = Path("tools/_patch_payload/4B436630C")
CONFIG_MARKER = "# 4B.4.3.6.6.30C paper transition candidate review controls"
CONFIG_INSERT_BEFORE = "    live_real_hard_block_required: bool = True"
CONFIG_BLOCK = """    # 4B.4.3.6.6.30C paper transition candidate review controls
    paper_transition_candidate_review_enabled: bool = True
    paper_transition_operator_evidence_required: bool = True
    paper_transition_runtime_envelope_freeze_required: bool = True
    paper_transition_runtime_envelope_frozen: bool = False
    paper_transition_runtime_envelope_freeze_phrase: str = "FREEZE_PAPER_TRANSITION_SANDBOX_ENVELOPE"
    paper_transition_runtime_envelope_freeze_token: str = ""
    paper_transition_final_risk_cap_verification_required: bool = True
    paper_transition_final_risk_cap_verified: bool = False
    paper_transition_still_no_order_enablement_required: bool = True
"""
COPY_FILES = (
    "docs/PAPER_TRANSITION_CANDIDATE_REVIEW_4B436630C.md",
    "src/tradebot/paper_transition_candidate_review.py",
    "tests/test_paper_transition_candidate_review_4B436630C.py",
    "tools/apply_4B436630C_paper_transition_candidate_review.py",
    "tools/check_4B436630C_paper_transition_candidate_review.py",
    "tools/run_4B436630C_paper_transition_candidate_review.py",
    "tools/rollback_4B436630C_paper_transition_candidate_review.py",
)


def _copy_files(root: Path, payload: Path) -> None:
    for rel in COPY_FILES:
        src = payload / rel
        dst = root / rel
        if not src.exists():
            raise FileNotFoundError(f"payload missing: {src}")
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def _patch_config(root: Path) -> dict[str, object]:
    path = root / "src" / "tradebot" / "config.py"
    text = path.read_text(encoding="utf-8")
    before_missing = [
        field for field in (
            "paper_transition_candidate_review_enabled",
            "paper_transition_operator_evidence_required",
            "paper_transition_runtime_envelope_freeze_required",
            "paper_transition_runtime_envelope_frozen",
            "paper_transition_runtime_envelope_freeze_phrase",
            "paper_transition_runtime_envelope_freeze_token",
            "paper_transition_final_risk_cap_verification_required",
            "paper_transition_final_risk_cap_verified",
            "paper_transition_still_no_order_enablement_required",
        ) if field not in text
    ]
    patched = False
    if CONFIG_MARKER not in text:
        if CONFIG_INSERT_BEFORE not in text:
            raise RuntimeError("config insert anchor missing")
        text = text.replace(CONFIG_INSERT_BEFORE, CONFIG_BLOCK + CONFIG_INSERT_BEFORE, 1)
        path.write_text(text, encoding="utf-8", newline="\n")
        patched = True
    after = path.read_text(encoding="utf-8")
    after_missing = [field for field in before_missing if field not in after]
    return {"patched": patched, "before_missing": before_missing, "after_missing": after_missing}


def _cleanup_payload(root: Path) -> dict[str, object]:
    payload_root = root / PAYLOAD_DIR
    removed = False
    if payload_root.exists():
        shutil.rmtree(payload_root)
        removed = True
    parent = payload_root.parent
    try:
        if parent.exists() and not any(parent.iterdir()):
            parent.rmdir()
    except OSError:
        pass
    return {"worktree_removed": removed}


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    payload = root / PAYLOAD_DIR
    if not payload.exists():
        raise SystemExit(f"payload directory not found: {payload}")
    _copy_files(root, payload)
    patch_result = _patch_config(root)
    payload_cleanup = _cleanup_payload(root)

    sys.path.insert(0, str(root / "src"))
    try:
        from tools.check_4B436630C_paper_transition_candidate_review import build_report
    except Exception:
        # Import path fallback when tools is not a package.
        import importlib.util
        checker = root / "tools" / "check_4B436630C_paper_transition_candidate_review.py"
        spec = importlib.util.spec_from_file_location("check_4B436630C", checker)
        if spec is None or spec.loader is None:
            raise
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        build_report = module.build_report
    report = build_report(root)
    report["patch_result"] = patch_result
    report["payload_cleanup"] = payload_cleanup
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    print(f"{CONTRACT_VERSION} paper transition candidate review patch applied")
    for key, value in report.get("checks", {}).items():
        print(f" - {key}: {value}")
    print(f" - patched_config_30c_missing_fields: {bool(patch_result['before_missing']) and not patch_result['after_missing']}")
    print(f" - runtime_overlay_activation_performed: {report.get('runtime_overlay_activation_performed')}")
    print(f" - training_performed: {report.get('training_performed')}")
    print(f" - reload_performed: {report.get('reload_performed')}")
    print(f" - trading_action_performed: {report.get('trading_action_performed')}")
    print(f" - paper_live_order_enablement_present: {report.get('paper_live_order_enablement_present')}")
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
